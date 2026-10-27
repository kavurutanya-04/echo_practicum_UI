"""Field-error transport regressions; no live provider calls or semantic judgments."""

from copy import deepcopy
from dataclasses import asdict
import json
from tempfile import TemporaryDirectory
import unittest

from agents import OriginalAgent
from agents.execution_log import RunLog, error_summary
from agents.model import ModelTurn
from agents.validation import ValidationError, object_fields, repair_feedback, rejection_diagnostic, schema_id
from agents.zero_sugar import ZeroSugarAgent
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import plan
from test_review_contract_v2 import current_support, reviewer, visible
from test_review_stages import PhaseModel, SCOPE, SOURCE


class TracedPhaseModel(PhaseModel):
    def __init__(self, completeness=None, support=None):
        super().__init__(completeness, support)
        self.histories = []

    def respond(self, instructions, history, tools, require_tool=False):
        self.histories.append(deepcopy(history))
        return super().respond(instructions, history, tools, require_tool)


class ReviewFieldDiagnosticsTests(unittest.TestCase):
    def test_completeness_rationale_logs_type_and_length_without_content(self):
        private = 'private-person@example.invalid'
        for value in ('', '   ', private + 'x' * 1200, {private: 'not a string'}):
            with self.subTest(value_type=type(value).__name__):
                bad = json.loads(visible().calls[0].arguments)
                bad['rationale'] = value
                model = TracedPhaseModel([tool_turn('submit_completeness_review', bad), visible()],
                                         lambda c: tool_turn('submit_review', current_support(c)))
                agent = reviewer(model)
                with TemporaryDirectory() as directory, RunLog(directory, agent='ZeroSugar') as log:
                    agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
                    events = [json.loads(line) for line in log.path.read_text(encoding='utf-8').splitlines()]
                entry = agent.diagnostics['rejected_attempts'][0]
                event = next(e for e in events if e['event'] == 'structured_response_repair')
                feedback = json.loads(next(item['output'] for item in model.histories[1]
                                           if item.get('type') == 'function_call_output'))
                for diagnostic in (entry, event, feedback):
                    self.assertEqual(diagnostic['validation_code'], 'completeness_rationale')
                    self.assertEqual(diagnostic['expected_type'], 'str')
                    self.assertEqual(diagnostic['actual_type'], type(value).__name__)
                    self.assertEqual(diagnostic['max_characters'], 1200)
                    if isinstance(value, str):
                        self.assertEqual(diagnostic['actual_characters'], len(value))
                    else:
                        self.assertNotIn('actual_characters', diagnostic)
                self.assertNotIn(private, json.dumps(entry) + json.dumps(events) + json.dumps(feedback))
                self.assertEqual(entry['resolution'], 'accepted_completeness_submission')

    def test_root_mismatch_reaches_artifact_log_and_specific_repair(self):
        submissions = []
        def support(context):
            report = current_support(context)
            if not submissions:
                report.pop('finding_reviews')
                report['debug_info'] = 'private-value-person@example.invalid'
            submissions.append(report)
            return tool_turn('submit_review', report)
        model = TracedPhaseModel([visible()], support)
        original = SequenceModel([plan(numbers=False), ModelTurn(text='A scoped answer.')])
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': original, 'ZeroSugar': model}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                result = agent.run('Explain the available evidence.')
                log.finish(0)
            events = [json.loads(line) for line in log.path.read_text(encoding='utf-8').splitlines()]
        artifact = json.loads(json.dumps(asdict(result)))
        self.assertEqual(result.status, 'complete')
        entry = artifact['diagnostics']['verification']['rejected_attempts'][0]
        event = next(e for e in events if e['event'] == 'structured_response_repair')
        feedback = json.loads(next(item['output'] for item in model.histories[-1] if item.get('type') == 'function_call_output'))
        for diagnostic in (entry, event, feedback):
            self.assertEqual(diagnostic['missing_fields'], ['finding_reviews'])
            self.assertEqual(diagnostic['unexpected_fields'], ['debug_info'])
            self.assertEqual(diagnostic['expected_type'], 'dict')
            self.assertEqual(diagnostic['phase'], 'support')
            self.assertEqual(diagnostic['tool_schema_id'], schema_id(model.calls[1][2][0]['parameters']))
        self.assertIn('Add required fields: ["finding_reviews"]', feedback['correction'])
        self.assertIn('Remove additional fields: ["debug_info"]', feedback['correction'])
        self.assertEqual(entry['resolution'], 'accepted_review_submission')
        repaired = next(e for e in events if e['event'] == 'structured_response_repaired')
        self.assertEqual(repaired['condition_id'], entry['condition_id'])
        self.assertEqual(repaired['accepted_model_turn'], 2)
        self.assertNotIn('private-value-person@example.invalid', json.dumps(artifact) + json.dumps(events) + json.dumps(feedback))

    def test_root_type_errors_report_the_received_type(self):
        for value, expected_type in (([], 'list'), ('wrong', 'str'), (None, 'NoneType')):
            with self.subTest(expected_type=expected_type):
                model = PhaseModel([visible()], lambda c: tool_turn('submit_review', value))
                agent = reviewer(model)
                with self.assertRaises(RuntimeError):
                    agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
                entry = agent.diagnostics['rejected_attempts'][0]
                self.assertEqual(entry['actual_type'], expected_type)
                self.assertEqual(entry['received_fields'], [])
                self.assertIn('finding_reviews', entry['missing_fields'])
                self.assertNotIn('numeric_reviews', entry['missing_fields'])

    def test_nested_correction_uses_declared_item_schema_and_position(self):
        report = current_support({'findings': []})
        report['corrections'] = [{'issue': 'Missing context.', 'kind': 'missing_deliverable',
                                  'requested_change': 'Explain context.', 'request_excerpt': 'Explain.',
                                  'citation_ids': [], 'extra': 'private value'}]
        agent = reviewer(PhaseModel())
        with self.assertRaises(ValidationError) as caught:
            agent.normalize_review(report)
        diagnostic = rejection_diagnostic(caught.exception, 'ZeroSugar', 'submit_review', 1, 1)
        self.assertEqual(diagnostic['field'], 'corrections[0]')
        self.assertEqual(diagnostic['item_index'], 0)
        self.assertEqual(diagnostic['missing_fields'], ['owner'])
        self.assertEqual(diagnostic['unexpected_fields'], ['extra'])
        self.assertEqual(diagnostic['schema_id'], schema_id(agent.tools[0]['parameters']['properties']['corrections']['items']))
        self.assertNotIn('private value', json.dumps(diagnostic))

    def test_expected_fields_come_from_the_actual_tool_schema(self):
        agent = reviewer(PhaseModel())
        schema = agent.tools[0]['parameters']
        schema['properties']['declared_probe'] = {'type': 'string'}
        schema['required'].append('declared_probe')
        with self.assertRaises(ValidationError) as caught:
            agent.normalize_review(current_support({'findings': []}))
        self.assertEqual(caught.exception.details['missing_fields'], ['declared_probe'])
        self.assertEqual(caught.exception.details['schema_id'], schema_id(schema))

    def test_completeness_root_fields_survive_persistence_and_repair(self):
        bad = json.loads(visible().calls[0].arguments)
        bad.pop('rationale')
        bad['extra'] = 'Do not persist this value.'
        model = TracedPhaseModel([tool_turn('submit_completeness_review', bad), visible()],
                                 lambda c: tool_turn('submit_review', current_support(c)))
        agent = reviewer(model)
        agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        entry = agent.diagnostics['rejected_attempts'][0]
        self.assertEqual(entry['missing_fields'], ['rationale'])
        self.assertEqual(entry['unexpected_fields'], ['extra'])
        self.assertEqual(entry['resolution'], 'accepted_completeness_submission')
        feedback = json.loads(next(item['output'] for item in model.histories[1] if item.get('type') == 'function_call_output'))
        self.assertIn('rationale', feedback['correction'])
        self.assertNotIn('Do not persist this value.', str(entry))

    def test_same_condition_is_counted_and_final_acceptance_marks_repairs(self):
        attempts = []
        def support(context):
            report = current_support(context)
            if len(attempts) < 2:
                report.pop('finding_reviews')
            attempts.append(report)
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible()], support))
        result = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'accept')
        first, second = agent.diagnostics['rejected_attempts']
        self.assertEqual(first['condition_id'], second['condition_id'])
        self.assertEqual(second['condition_status'], 'repeated')
        self.assertEqual(second['same_condition_attempts'], 2)
        self.assertTrue(all(e['accepted_model_turn'] == 3 for e in (first, second)))

    def test_a_different_error_is_linked_without_claiming_early_success(self):
        attempts = []
        def support(context):
            report = current_support(context)
            if not attempts:
                report.pop('finding_reviews')
            elif len(attempts) == 1:
                report['corrections'] = [{'issue': 'Missing context.'}]
            attempts.append(report)
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible()], support))
        agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        first, second = agent.diagnostics['rejected_attempts']
        self.assertEqual(second['condition_status'], 'changed')
        self.assertEqual(second['previous_condition_id'], first['condition_id'])
        self.assertNotEqual(first['condition_id'], second['condition_id'])
        self.assertEqual(second['field'], 'corrections[0]')

    def test_three_invalid_submissions_remain_blocked(self):
        def support(context):
            report = current_support(context)
            report.pop('finding_reviews')
            return tool_turn('submit_review', report)
        model = PhaseModel([visible()], support)
        original = SequenceModel([plan(numbers=False), ModelTurn(text='A scoped answer.')])
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': original, 'ZeroSugar': model}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        result = agent.run('Explain.')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.findings, [])
        entries = result.diagnostics['verification']['rejected_attempts']
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[-1]['same_condition_attempts'], 3)
        self.assertTrue(all(entry['resolution'] == 'unresolved' for entry in entries))

    def test_field_names_are_bounded_redacted_and_values_are_absent(self):
        schema = {'properties': {'required': {}}, 'required': ['required'], 'additionalProperties': False}
        with self.assertRaises(ValidationError) as caught:
            object_fields({'person@example.invalid': 'private value', 'x' * 200: 'other private value',
                           'Full source comment masquerading as a key.': 'private value'},
                          schema, 'controlled', 'review', 'Use the declared fields.')
        for diagnostic in (error_summary(caught.exception), repair_feedback(caught.exception),
                           rejection_diagnostic(caught.exception, 'ZeroSugar', 'submit_review', 1, 1)):
            text = json.dumps(diagnostic)
            self.assertNotIn('person@example.invalid', text)
            self.assertNotIn('private value', text)
            self.assertNotIn('Full source comment masquerading as a key.', text)
            self.assertTrue(diagnostic['field_names_redacted'])
            self.assertTrue(diagnostic['field_names_truncated'])
            self.assertTrue(all(len(name) <= 160 for name in diagnostic['unexpected_fields']))


if __name__ == '__main__':
    unittest.main()
