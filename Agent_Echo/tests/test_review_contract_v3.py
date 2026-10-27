"""Explicit correction judgments and derived states; no semantic accuracy claims."""

from copy import deepcopy
from dataclasses import asdict
import json
import unittest

from agents.validation import ValidationError
from agents import OriginalAgent
from agents.model import ModelTurn
from agents.zero_sugar import ZeroSugarAgent, REVIEW_VERSION
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import plan
from test_review_contract_v2 import current_support, reviewer, visible
from test_review_stages import PhaseModel, SOURCE, SCOPE


def support(context, judgments=None):
    report = current_support(context)
    report.pop('correction_reviews')
    if context.get('review_obligations'):
        report['correction_judgments'] = judgments if judgments is not None else {
            item['correction_id']: {'mandatory': True, 'addressed': False, 'reason': 'Visible requested content is missing.'}
            for item in context['review_obligations']}
    return report


class CorrectionJudgmentTests(unittest.TestCase):
    def test_missing_echo_action_routes_a_policy_repair_without_a_fabricated_user_excerpt(self):
        def assess(context):
            report = support(context)
            report['decision'] = 'revise'
            report['corrections'] = [{'issue': 'No reasoned manager action is visible.',
                'kind': 'policy_requirement', 'owner': 'Original',
                'requested_change': 'Add a concrete action reasoned from the analysis.',
                'request_excerpt': None, 'citation_ids': [SOURCE['citation_id']]}]
            return tool_turn('submit_review', report)

        model = PhaseModel([visible()], assess)
        agent = reviewer(model)
        result = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE], require_actionable=True)
        self.assertTrue(model.calls[1][1]['require_actionable'])
        self.assertTrue(agent.diagnostics['support_contract']['require_actionable'])
        self.assertNotIn('require_actionable', model.calls[0][1])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.repair_targets, ['Original'])
        self.assertEqual(result.findings[0]['status'], 'supported')
        self.assertEqual(result.corrections[0]['kind'], 'policy_requirement')
        self.assertIsNone(result.corrections[0]['request_excerpt'])

    def test_action_policy_schema_is_scoped_and_does_not_mutate_the_template(self):
        model = PhaseModel([visible(), visible()], lambda c: tool_turn('submit_review', support(c)))
        agent = reviewer(model)
        agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE], require_actionable=True)
        agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        for index, required in ((1, True), (3, False)):
            schema = model.calls[index][2][0]['parameters']['properties']['corrections']['items']
            self.assertEqual('policy_requirement' in schema['properties']['kind']['enum'], required)
            self.assertEqual(model.calls[index][1]['require_actionable'], required)
        template = agent.tools[0]['parameters']['properties']['corrections']['items']
        self.assertNotIn('policy_requirement', template['properties']['kind']['enum'])

    def test_policy_corrections_require_an_active_policy_original_owner_and_null_excerpt(self):
        change = {'issue_index': 0, 'kind': 'policy_requirement', 'owner': 'Original',
                  'requested_change': 'Add the reasoned action.', 'citation_ids': [], 'request_excerpt': None}
        for required, item in ((False, change), (True, {**change, 'owner': 'Vanilla'}),
                               (True, {**change, 'request_excerpt': 'Explain.'})):
            with self.subTest(required=required, item=item), self.assertRaises(ValidationError):
                ZeroSugarAgent.validate_corrections({'issues': ['Missing action.'], 'corrections': [item]},
                    'Explain.', [], [], require_actionable=required)
        corrections, _ = ZeroSugarAgent.validate_corrections(
            {'issues': ['Missing action.'], 'corrections': [change]}, 'Explain.', [], [], require_actionable=True)
        self.assertEqual(corrections[0]['kind'], 'policy_requirement')

    def test_original_passes_action_policy_and_repairs_before_complete_release(self):
        original = SequenceModel([plan(numbers=False), ModelTurn(text='Initial analysis.'),
                                  ModelTurn(text='Analysis with a proposed validation step and its rationale.')])

        def assess(context):
            judgments = {c['correction_id']: {'mandatory': True, 'addressed': True,
                'reason': 'The revised answer includes the proposed validation step.'}
                for c in context['review_obligations']}
            report = support(context, judgments)
            if not context['review_obligations']:
                report['decision'] = 'revise'
                report['corrections'] = [{'issue': 'The manager action is absent.',
                    'kind': 'policy_requirement', 'owner': 'Original',
                    'requested_change': 'Add a proposed validation step and its rationale.',
                    'request_excerpt': None, 'citation_ids': []}]
            return tool_turn('submit_review', report)

        model = PhaseModel([visible(), visible()], assess)
        agent = OriginalAgent(None, SCOPE,
                              lambda role: {'Original': original, 'ZeroSugar': model}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        result = agent.run('Explain.')
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.verification['drafts_checked'], 2)
        self.assertEqual(len(model.calls), 4)
        self.assertTrue(all(c[1]['require_actionable'] for c in model.calls if c[0] == 'submit_review'))
        self.assertIn('Add a proposed validation step', str(original.histories[-1]))
        self.assertEqual(result.diagnostics['pending_corrections'], [])

    def test_obligation_text_is_supplied_once_without_losing_prior_identity_or_current_repairs(self):
        prior = [{'correction_id': 'C_prior', 'issue': 'An inherited requirement.', 'owner': 'Original',
                  'kind': 'missing_deliverable', 'requested_change': 'Provide the requested detail.', 'citation_ids': []}]
        model = PhaseModel([visible(['A current requirement.'])], lambda c: tool_turn('submit_review', support(c)))
        reviewer(model).review('Explain.', 'Summary [survey:CMT1].', [SOURCE], previous_corrections=prior)
        payload = model.calls[1][1]
        self.assertEqual(payload['previous_corrections'], [{'correction_id': 'C_prior'}])
        self.assertEqual(set(payload['completeness_review']), {'decision', 'score', 'rationale', 'suggestions'})
        self.assertEqual(len(payload['review_obligations']), 2)
        self.assertEqual(payload['review_obligations'][0], prior[0])
        self.assertEqual(payload['review_obligations'][1]['issue'], 'A current requirement.')

    def test_schema_assigns_keys_and_omits_model_managed_states_and_replacements(self):
        model = PhaseModel([visible(['Show an example.'])], lambda c: tool_turn('submit_review', support(c)))
        agent = reviewer(model)
        result = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        properties = model.calls[1][2][0]['parameters']['properties']
        self.assertNotIn('correction_reviews', properties)
        judgments = properties['correction_judgments']
        self.assertEqual(set(judgments['required']), {c['correction_id'] for c in result.corrections})
        self.assertFalse(judgments['additionalProperties'])
        for item in judgments['properties'].values():
            self.assertEqual(set(item['properties']), {'mandatory', 'addressed', 'reason'})
            self.assertEqual(set(item['required']), {'mandatory', 'addressed', 'reason'})
            self.assertFalse(item['additionalProperties'])
        self.assertEqual(result.version, REVIEW_VERSION)
        self.assertEqual(result.version, 'review-v5')

    def test_all_explicit_judgments_map_to_stable_internal_states(self):
        obligations = [{'correction_id': key} for key in ('current', 'prior')]
        schema = ZeroSugarAgent.correction_judgment_schema(obligations)
        for required, addressed in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(required=required, addressed=addressed):
                judgments = {key: {'mandatory': required, 'addressed': addressed, 'reason': 'Controlled judgment.'}
                             for key in ('current', 'prior')}
                original = deepcopy(judgments)
                result = ZeroSugarAgent.derive_correction_reviews(judgments, schema, obligations[:1])
                expected = ('withdrawn', 'withdrawn') if not required else (
                    ('unresolved', 'unresolved') if not addressed else ('withdrawn', 'resolved'))
                self.assertEqual(tuple(item['status'] for item in result), expected)
                self.assertTrue(all(item['replacement_id'] is None for item in result))
                self.assertEqual(judgments, original)

    def test_real_current_omission_stays_pending_even_when_findings_are_supported(self):
        model = PhaseModel([visible(['Show an example.'])], lambda c: tool_turn('submit_review', support(c)))
        result = reviewer(model).review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.findings[0]['status'], 'supported')
        self.assertEqual(result.correction_reviews[0]['status'], 'unresolved')
        self.assertEqual(len(result.corrections), 1)
        self.assertEqual(len(result.correction_judgments), 1)

    def test_optional_or_false_omission_does_not_remain_a_blocker(self):
        def assess(context):
            judgments = {item['correction_id']: {'mandatory': False, 'addressed': False,
                         'reason': 'The requested extra category excerpt is optional.'}
                         for item in context['review_obligations']}
            return tool_turn('submit_review', support(context, judgments))
        agent = reviewer(PhaseModel([visible(['Add another category excerpt.'])], assess))
        result = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(result.corrections, [])
        self.assertEqual(result.correction_reviews[0]['status'], 'withdrawn')
        self.assertNotIn('retained_corrections', agent.diagnostics)

    def test_current_false_omission_can_be_addressed_in_the_visible_answer(self):
        def assess(context):
            judgments = {item['correction_id']: {'mandatory': True, 'addressed': True,
                         'reason': 'The requested content is already visible in the answer.'}
                         for item in context['review_obligations']}
            return tool_turn('submit_review', support(context, judgments))
        result = reviewer(PhaseModel([visible(['Show the visible content.'])], assess)).review(
            'Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(result.correction_reviews[0]['status'], 'withdrawn')

    def test_duplicate_judgment_can_retire_one_objection_without_a_replacement_graph(self):
        def assess(context):
            keys = [item['correction_id'] for item in context['review_obligations']]
            return tool_turn('submit_review', support(context, {
                keys[0]: {'mandatory': True, 'addressed': False, 'reason': 'The example is still absent.'},
                keys[1]: {'mandatory': False, 'addressed': False, 'reason': 'Redundant objection; the first preserves the repair.'}}))
        result = reviewer(PhaseModel([visible(['Show the example.', 'The example is absent.'])], assess)).review(
            'Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(len(result.corrections), 1)
        self.assertEqual([item['status'] for item in result.correction_reviews], ['unresolved', 'withdrawn'])

    def test_missing_extra_or_malformed_judgments_are_rejected_without_defaults(self):
        schema = ZeroSugarAgent.correction_judgment_schema([{'correction_id': 'C1'}])
        valid = {'mandatory': True, 'addressed': False, 'reason': 'Still missing.'}
        cases = [{}, {'C1': valid, 'unknown': valid}, {'C1': {'mandatory': True, 'reason': 'Missing judgment.'}},
                 {'C1': {**valid, 'mandatory': 1}}, {'C1': {**valid, 'addressed': 'false'}},
                 {'C1': {**valid, 'reason': ' '}}, {'C1': {**valid, 'reason': 'x' * 301}}]
        for judgments in cases:
            with self.subTest(keys=list(judgments)), self.assertRaises(ValidationError):
                ZeroSugarAgent.derive_correction_reviews(judgments, schema, [])

    def test_no_obligations_omit_the_judgment_field_and_rebuild_on_reuse(self):
        model = PhaseModel([visible(), visible()], lambda c: tool_turn('submit_review', support(c)))
        agent = reviewer(model)
        first = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        prior = [{'correction_id': 'C_prior', 'issue': 'Missing explanation.', 'owner': 'Original',
                  'kind': 'missing_deliverable', 'requested_change': 'Explain.', 'citation_ids': []}]
        second = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE], previous_corrections=prior)
        self.assertNotIn('correction_judgments', model.calls[1][2][0]['parameters']['properties'])
        self.assertIn('C_prior', model.calls[3][2][0]['parameters']['properties']['correction_judgments']['properties'])
        self.assertEqual(first.correction_judgments, {})
        self.assertEqual(second.corrections[0]['correction_id'], 'C_prior')
        self.assertEqual(asdict(second)['correction_reviews'][0]['status'], 'unresolved')

    def test_legacy_v2_response_keeps_its_validator_and_retention_guard(self):
        def assess(context):
            keys = {item['correction_id']: 'resolved' for item in context['review_obligations']}
            return tool_turn('submit_review', current_support(context, keys))
        result = reviewer(PhaseModel([visible(['Show the example.'])], assess)).review(
            'Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.version, 'review-v5')
        self.assertEqual(result.correction_reviews[0]['status'], 'unresolved')
