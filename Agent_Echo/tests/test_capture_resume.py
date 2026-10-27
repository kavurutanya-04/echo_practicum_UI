"""Unrun regression fixtures for full capture and bounded live-phase resumption."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents.capture import capture_summary, checkpoint, checkpoint_progress, load_checkpoint, register_secret
from agents.data_access import ScopedData
from agents.execution_log import RunLog, logged_model
from agents.resume import resume_phase
from agents.zero_sugar import ZeroSugarAgent
from test_agents import DATABASE, SequenceModel, tool_turn
from test_flow_improvements import plan
from test_review_contract_v2 import visible
from test_review_contract_v3 import support
from test_review_stages import PhaseModel, SCOPE


class Registry:
    def __init__(self, model):
        self.model, self.roles = model, []

    def profile_for(self, role):
        return 'fixture_profile'

    def get(self, role):
        self.roles.append(role)
        return logged_model(self.model, role, 'fixture_profile')


class CaptureResumeTests(unittest.TestCase):
    def test_full_capture_keeps_rejected_arguments_and_redacts_credentials(self):
        secret = 'fixture-private-api-credential-4829'
        register_secret(secret)
        arguments = {'unexpected': 'source text ' * 200, 'api_key': secret}
        with TemporaryDirectory() as folder:
            with RunLog(Path(folder)):
                model = logged_model(SequenceModel([tool_turn('submit_review', arguments)]), 'ZeroSugar', 'fixture_profile')
                model.respond('Review.', [{'role': 'user', 'content': 'Retained evidence.'}], [], True)
                path = Path(capture_summary()['exchanges'])
            text = path.read_text(encoding='utf-8')
        self.assertIn('source text ' * 200, text)
        self.assertNotIn(secret, text)
        self.assertIn('credential omitted', text)

    def test_checkpoint_roundtrip_preserves_inputs_and_detects_changed_payload(self):
        with TemporaryDirectory() as folder:
            with RunLog(Path(folder)):
                path = checkpoint('planning', 'Original', SCOPE.__dict__, {'question': 'Explain.', 'mode': 'live'})
                checkpoint_progress(path, status='failed')
            saved = load_checkpoint(path)
            self.assertEqual(saved['payload']['question'], 'Explain.')
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            data['payload']['question'] = 'Changed.'
            Path(path).write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'payload has changed'):
                load_checkpoint(path)

    def test_review_resume_reuses_matching_completeness_and_never_requests_other_roles(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            documents = {d['citation_id']: d for d in backend.text_documents()}
            teams = list(backend.teams)
        finally:
            backend.close()
        source = next(d for d in documents.values() if d.get('anonymous'))
        answer = 'The comment gives its perspective. [' + source['citation_id'] + ']'
        first = PhaseModel([visible()], lambda c: tool_turn('submit_review', {}))
        registry = Registry(first)
        with TemporaryDirectory() as folder:
            with RunLog(Path(folder)):
                agent = ZeroSugarAgent(SCOPE, registry.get('ZeroSugar'), 'live', database=DATABASE,
                    document_lookup=documents, authorized_teams=teams)
                with self.assertRaises(RuntimeError):
                    agent.review('Explain.', answer, [source])
                saved = load_checkpoint(capture_summary()['resume_checkpoint'])
            second = PhaseModel(support=lambda c: tool_turn('submit_review', support(c)))
            registry = Registry(second)
            with RunLog(Path(folder)):
                result = resume_phase(saved, registry, DATABASE)
        self.assertEqual(registry.roles, ['ZeroSugar'])
        self.assertEqual([call[0] for call in second.calls], ['submit_review'])
        self.assertTrue(result.diagnostics['phase_only'])
        self.assertNotEqual(result.status, 'complete')

    def test_source_changes_stop_resume_before_any_model_request(self):
        registry = Registry(SequenceModel([]))
        saved = {'scope': SCOPE.__dict__, 'kind': 'review', 'role': 'ZeroSugar',
                 'payload': {'mode': 'live', 'database_hash': 'different-source'}}
        with self.assertRaisesRegex(ValueError, 'database changed'):
            resume_phase(saved, registry, DATABASE)
        self.assertEqual(registry.roles, [])

    def test_planning_resume_stops_after_the_plan_without_analysis_or_delegation(self):
        registry = Registry(SequenceModel([plan(numbers=False)]))
        saved = {'scope': SCOPE.__dict__, 'kind': 'planning', 'role': 'Original',
            'run_id': 'parent', 'source_path': 'retained', 'code_versions': {},
            'payload': {'mode': 'live', 'profile': 'fixture_profile', 'question': 'Explain.'}}
        result = resume_phase(saved, registry, DATABASE)
        self.assertEqual(registry.roles, ['Original'])
        self.assertTrue(result.diagnostics['phase_only'])
        self.assertNotEqual(result.status, 'complete')

    def test_original_generation_resume_cannot_delegate_to_vanilla(self):
        registry = Registry(SequenceModel([tool_turn('submit_grounded_answer',
            {'fact_ids': [], 'interpretations': [], 'proposals': []})]))
        saved = {'scope': SCOPE.__dict__, 'kind': 'specialist', 'role': 'Original',
            'run_id': 'parent', 'source_path': 'retained', 'code_versions': {},
            'payload': {'mode': 'live', 'profile': 'fixture_profile', 'question': 'Explain.',
                'history': [{'role': 'user', 'content': 'Explain.'}], 'evidence': [],
                'tool_trace': [], 'tool_cache': {}, 'close_next': False, 'diagnostics': {}}}
        result = resume_phase(saved, registry, DATABASE)
        self.assertEqual(registry.roles, ['Original'])
        self.assertTrue(result.diagnostics['phase_only'])
        self.assertNotEqual(result.status, 'complete')


if __name__ == '__main__':
    unittest.main()
