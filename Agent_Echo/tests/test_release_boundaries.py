"""Partial-release replay and manager-payload boundaries, without a running server."""

import ast
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents import OriginalAgent
from agents.data_access import ScopedData
from agents.grounding import FactCatalog, render_answer
from agents.lime import LimeAgent
from agents.runtime import AgentResult
from agents.zero_sugar import ZeroSugarAgent, candidate_id
from audit_grounding import audit_artifact
from test_agents import DATABASE, tool_turn
from test_review_contract_v2 import visible, current_support
from test_review_stages import PhaseModel, SCOPE
from test_visuals_rag import evidence, plan


class ReleaseBoundaryTests(unittest.TestCase):
    def test_manager_payload_preserves_review_failure_without_sending_drafts(self):
        # Execute the actual pure payload helpers without starting FastAPI, importing
        # optional server dependencies or reading local connection/credential files.
        path = Path(__file__).resolve().parents[2] / 'Echo_UI/backend/app.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in {'how_it_was_made', 'without_comment_text'}]
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
        artifact = {'status': 'partial', 'answer': 'Earlier reviewed blocks.',
                    'evidence': [{'citation_id': 'survey:C1', 'source': 'HR_survey_comments', 'text': 'private source'}],
                    'verification': {'decision': 'revise', 'status': 'failed', 'drafts_checked': 2,
                                     'completed_reviews': 1, 'reviews': [{}], 'latest_candidate_id': 'new',
                                     'released_candidate_id': 'old', 'unreviewed_candidate': {'answer': 'private new draft'}}}
        cleaned = namespace['without_comment_text'](artifact)
        self.assertEqual(cleaned['verification']['status'], 'failed')
        self.assertEqual(cleaned['verification']['released_candidate_id'], 'old')
        self.assertEqual(cleaned['made']['completed_reviews'], 1)
        self.assertNotIn('private source', str(cleaned))
        self.assertNotIn('private new draft', str(cleaned))

    def test_partial_artifact_replays_its_reviewed_version_and_detects_tampering(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            documents = backend.sentiment_documents()
            doc = next(d for d in documents if d['dimension'] == 'Recognition')
        finally:
            backend.close()
        source = {key: doc[key] for key in ('citation_id', 'source', 'record_id', 'team', 'date', 'dimension', 'anonymous')}
        source.update(kind='survey_response', scope=SCOPE.__dict__, text=doc['response_text'])
        selection = {'fact_ids': [], 'interpretations': [{'text': 'An illustrative comment.',
                     'quote': source['text'][:100], 'citation_ids': [source['citation_id']]}], 'proposals': []}
        answer, claims = render_answer(selection, FactCatalog([source], SCOPE.__dict__), 'Original')
        grounding = {'version': 'source-facts-v4', 'role': 'Original', 'payload': selection}
        model = PhaseModel([visible()], lambda c: tool_turn('submit_review', current_support(c)))
        verifier = ZeroSugarAgent(SCOPE, model, 'live', sentiment_documents=documents)
        verdict = verifier.review('Show an illustrative comment.', answer, [source], claims=claims, grounding=grounding)
        self.assertEqual(verdict.decision, 'accept')
        agent = OriginalAgent(None, SCOPE, lambda _: None, 'live')
        agent.reviewed_candidate = {'candidate_id': candidate_id(answer, [source]), 'answer': answer, 'claims': claims,
                                    'grounding': grounding, 'evidence': [source], 'sentiment': {}, 'visualization': {}}
        candidate = AgentResult('Original', 'Show an illustrative comment.', 'A newer unreviewed answer.', SCOPE.__dict__)
        candidate.verification = {'decision': 'revise', 'status': 'failed', 'reviews': [asdict(verdict)]}
        result = agent.incomplete(candidate, verdict)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'partial.json'
            path.write_text(json.dumps(asdict(result)), encoding='utf-8')
            self.assertEqual(audit_artifact(path)['runs'][0]['provenance_issues'], [])
            result.claims[0]['text'] = 'Tampered released claim.'
            path.write_text(json.dumps(asdict(result)), encoding='utf-8')
            self.assertIn('Published claims differ from the reviewed release selection.',
                          audit_artifact(path)['runs'][0]['provenance_issues'])

    def test_export_does_not_invent_dataset_origin(self):
        with TemporaryDirectory() as directory:
            files = LimeAgent.export(plan(), evidence(), SCOPE, directory)
            self.assertTrue(files)
            for exported in files:
                self.assertNotIn('synthetic data', Path(exported['svg']).read_text(encoding='utf-8'))
                self.assertNotIn('synthetic', json.loads(Path(exported['metadata']).read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
