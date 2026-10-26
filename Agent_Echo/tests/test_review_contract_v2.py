"""Review transport/state regressions; scripted judgments do not measure model quality."""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from agents import OriginalAgent
from agents.grounding import FactCatalog, render_answer, audit_claims
from agents.model import ModelTurn
from agents.validation import ValidationError
from agents.zero_sugar import ZeroSugarAgent, candidate_id
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import plan, FixtureCherry
from test_review_stages import PhaseModel, SCOPE, SOURCE, support_turn


def visible(issues=()):
    return tool_turn('submit_completeness_review', {
        'decision': 'revise' if issues else 'accept', 'score': 2 if issues else 3,
        'rationale': 'Controlled visible-answer assessment.',
        'corrections': [{'issue': issue, 'requested_change': 'Address: ' + issue} for issue in issues],
        'suggestions': [],
    })


def current_support(context, statuses=None, corrections=(), numeric='not_required'):
    report = json.loads(support_turn(context).calls[0].arguments)
    report.pop('issues')
    report.pop('repair_targets')
    report['corrections'] = list(corrections)
    report['correction_reviews'] = [{
        'correction_id': item['correction_id'],
        'status': (statuses or {}).get(item['correction_id'], 'unresolved'),
        'reason': 'Controlled reassessment against the request and visible draft.',
        'replacement_id': None,
    } for item in context.get('review_obligations', [])]
    report['numeric_reviews'] = [{'request_id': item['request_id'], 'decision': numeric,
                                 'reason': 'Controlled metric relevance judgment.'}
                                for item in context.get('pending_numeric_requests', [])]
    return report


def reviewer(model):
    return ZeroSugarAgent(SCOPE, model, 'live', document_lookup={SOURCE['citation_id']: SOURCE})


class ReviewContractTests(unittest.TestCase):
    def test_new_correction_list_derives_issues_and_targets(self):
        change = {'issue': 'Explain the limit.', 'kind': 'missing_deliverable', 'owner': 'Original',
                  'requested_change': 'State the actual coverage limit.', 'citation_ids': [SOURCE['citation_id']]}
        model = PhaseModel([visible()], lambda c: tool_turn('submit_review', current_support(c, corrections=[change])))
        result = reviewer(model).review('Explain.', 'Supported text [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.issues, ['Explain the limit.'])
        self.assertEqual(result.repair_targets, ['Original'])
        properties = model.calls[1][2][0]['parameters']['properties']
        self.assertNotIn('issues', properties)
        self.assertNotIn('repair_targets', properties)

    def test_real_visible_omission_survives_supported_findings(self):
        model = PhaseModel([visible(['The requested example is absent.'])],
                           lambda c: tool_turn('submit_review', current_support(c)))
        result = reviewer(model).review('Include an example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.findings[0]['status'], 'supported')
        self.assertEqual(result.corrections[0]['owner'], 'Original')

    def test_improper_caveat_requirement_can_be_withdrawn_with_reason(self):
        def support(context):
            statuses = {item['correction_id']: 'withdrawn' for item in context['review_obligations']}
            return tool_turn('submit_review', current_support(context, statuses))
        model = PhaseModel([visible(['Remove the uncertainty disclosure.'])], support)
        result = reviewer(model).review('Explain.', 'Model labels need validation [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(result.corrections, [])
        self.assertEqual(result.correction_reviews[0]['status'], 'withdrawn')

    def test_current_omission_cannot_be_marked_resolved_from_evidence(self):
        calls = []
        def support(context):
            report = current_support(context)
            if not calls:
                report['correction_reviews'][0]['status'] = 'resolved'
            calls.append(report)
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Show the example.'])], support)
        agent = reviewer(model)
        result = agent.review('Include an example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(len(calls), 2)
        self.assertEqual(agent.diagnostics['rejected_attempts'][0]['validation_code'], 'visible_correction_resolution')

    def test_duplicate_observations_can_consolidate_without_losing_the_repair(self):
        def support(context):
            report = current_support(context)
            first, second = report['correction_reviews']
            second.update(status='consolidated', replacement_id=first['correction_id'])
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Show the positive example.', 'Positive quotation is absent.'])], support)
        result = reviewer(model).review('Include an example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(len(result.corrections), 1)
        self.assertEqual(result.decision, 'revise')

    def test_consolidation_cannot_cycle_or_hide_a_closed_obligation(self):
        prior = [{'correction_id': key} for key in ('A', 'B')]
        for statuses in [('consolidated', 'consolidated'), ('consolidated', 'resolved')]:
            assessments = [{'correction_id': key, 'status': status, 'reason': 'Controlled judgment.',
                            'replacement_id': ('B' if key == 'A' else 'A') if status == 'consolidated' else None}
                           for key, status in zip(('A', 'B'), statuses)]
            with self.subTest(statuses=statuses), self.assertRaises(ValidationError):
                ZeroSugarAgent.validate_corrections({'issues': [], 'correction_reviews': assessments}, '', [], prior)

    def test_prior_pending_identity_is_preserved(self):
        prior = [{'correction_id': 'C_prior', 'issue': 'Explain uncertainty.', 'owner': 'Original',
                  'kind': 'missing_deliverable', 'requested_change': 'Explain uncertainty.', 'citation_ids': []}]
        model = PhaseModel([visible()], lambda c: tool_turn('submit_review', current_support(c)))
        result = reviewer(model).review('Explain.', 'Summary [survey:CMT1].', [SOURCE], previous_corrections=prior)
        self.assertEqual(result.corrections[0]['correction_id'], 'C_prior')

    def test_every_obligation_must_be_assessed(self):
        def support(context):
            report = current_support(context)
            report['correction_reviews'] = []
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible(['Show the example.'])], support))
        with self.assertRaises(RuntimeError):
            agent.review('Include an example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(len(agent.diagnostics['rejected_attempts']), 3)

    def test_numeric_relevance_controls_pending_work(self):
        for relevance in ('required', 'not_required', 'uncertain'):
            with self.subTest(relevance=relevance):
                model = PhaseModel([visible()], lambda c: tool_turn('submit_review', current_support(c, numeric=relevance)))
                result = reviewer(model).review('Explain comments.', 'Summary [survey:CMT1].', [SOURCE],
                    numeric_coverage=[{'metric': 'survey_trend', 'dimension': 'Recognition', 'status': 'pending'}])
                self.assertEqual('Cherry' in result.repair_targets, relevance != 'not_required')
                self.assertEqual(result.decision, 'accept' if relevance == 'not_required' else 'revise')

    def test_unknown_numeric_request_is_not_a_valid_relevance_review(self):
        with self.assertRaises(ValidationError):
            ZeroSugarAgent.validate_numeric_reviews([{'request_id': 'N_other', 'decision': 'not_required', 'reason': 'Not requested.'}],
                                                   [{'request_id': 'N1'}])

    def test_invalid_completeness_diagnostics_explain_type_index_and_length(self):
        for bad, expected in [([{}], {'item_index': 0}), ([''], {'actual_characters': 0}),
                              (['x' * 601], {'actual_characters': 601}), ('wrong', {'detail': {'value_type': 'str'}})]:
            report = {'decision': 'revise', 'score': 2, 'rationale': 'Fixture.', 'issues': bad, 'suggestions': []}
            agent = reviewer(PhaseModel([tool_turn('submit_completeness_review', report), visible()]))
            agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
            diagnostic = agent.diagnostics['rejected_attempts'][0]
            for key, value in expected.items():
                if isinstance(value, dict):
                    self.assertEqual(diagnostic[key]['value_type'], value['value_type'])
                else:
                    self.assertEqual(diagnostic[key], value)

    def test_completed_completeness_survives_support_failure_and_is_redacted(self):
        model = PhaseModel([visible(['Missing detail for person@example.com.'])], RuntimeError('Provider failed.'))
        agent = reviewer(model)
        with self.assertRaises(RuntimeError):
            agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        snapshot = agent.diagnostics['completeness_review']
        self.assertNotIn('person@example.com', str(snapshot))
        self.assertIn('[REDACTED]', str(snapshot))
        self.assertEqual(agent.diagnostics['review_phases'][0]['status'], 'completed')

    def test_current_blocking_verdict_needs_actionable_work(self):
        def support(context):
            report = current_support(context)
            report['decision'] = 'revise'
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible()], support))
        with self.assertRaises(RuntimeError):
            agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertTrue(all(item['validation_code'] == 'review_actionable_revision' for item in agent.diagnostics['rejected_attempts']))

    def test_failed_new_review_releases_the_earlier_version_only(self):
        original = SequenceModel([plan(numbers=False), ModelTurn(text='Earlier reviewed answer.'),
                                  ModelTurn(text='New draft with the requested explanation.')])
        invalid = tool_turn('submit_completeness_review', {'decision': 'revise', 'score': 2, 'rationale': 'Fixture.',
                                                           'issues': [{}], 'suggestions': []})
        model = PhaseModel([visible(['Explain the limit.']), invalid, invalid, invalid],
                           lambda c: tool_turn('submit_review', current_support(c)))
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': original, 'ZeroSugar': model}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        result = agent.run('Explain the evidence and its limits.')
        self.assertEqual(result.status, 'partial')
        self.assertIn('Earlier reviewed answer.', result.answer)
        self.assertNotIn('New draft with the requested explanation.', result.answer)
        self.assertEqual(result.verification['completed_reviews'], 1)
        self.assertEqual(result.verification['released_candidate_id'], candidate_id('Earlier reviewed answer.'))
        self.assertEqual(result.verification['unreviewed_candidate']['answer'], 'New draft with the requested explanation.')
        self.assertEqual(len(result.diagnostics['review_history']), 2)

    def test_reused_reviewer_does_not_attach_an_old_completed_phase_to_new_failure(self):
        invalid = tool_turn('submit_completeness_review', {})
        model = PhaseModel([visible(), invalid, invalid, invalid],
                           lambda c: tool_turn('submit_review', current_support(c)))
        agent = reviewer(model)
        agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        with self.assertRaises(RuntimeError):
            agent.review('Explain again.', 'A different summary [survey:CMT1].', [SOURCE])
        self.assertNotIn('completeness_review', agent.diagnostics)
        self.assertNotIn('support_review', agent.diagnostics)

    def test_original_retires_an_unrequested_metric_without_querying_it(self):
        original = SequenceModel([plan(metric='survey_trend', dimension='Recognition'), ModelTurn(text='Text analysis.')])
        model = PhaseModel([visible()], lambda c: tool_turn('submit_review', current_support(c)))
        with patch('agents.original.CherryAgent', FixtureCherry):
            agent = OriginalAgent('unused', SCOPE, lambda role: {'Original': original, 'ZeroSugar': model}.get(role), 'offline-unit-test')
            self.addCleanup(agent.close)
            result = agent.run('Explain comment text only.')
            self.assertEqual(result.status, 'complete')
            self.assertEqual(agent.planned_metrics, [])
            self.assertEqual(agent.specialists['Cherry'].required_metrics, [])
            self.assertEqual(agent.specialists['Cherry'].metric_calls, 0)
            self.assertEqual(result.verification['reviews'][0]['repair_targets'], [])

    def test_v4_changes_origin_text_but_preserves_v3_replay_and_warnings(self):
        source = {'citation_id': 'SQL1', 'producer': 'Cherry', 'rows': [{'Comments': 13}], 'scope': SCOPE.__dict__}
        catalog = FactCatalog([source], SCOPE.__dict__)
        table = next(key for key, fact in catalog.facts.items() if fact['kind'] == 'table')
        payload = {'fact_ids': [table], 'interpretations': [{'text': 'There are 13 recorded comments.',
                   'quote': None, 'citation_ids': ['SQL1']}], 'proposals': []}
        for version in ('source-facts-v3', 'source-facts-v4'):
            answer, claims = render_answer(payload, catalog, 'Original', version)
            self.assertEqual('synthetic' in answer, version == 'source-facts-v3')
            self.assertTrue(claims[1]['review_warnings'])
            self.assertEqual(audit_claims(claims, answer, catalog, {'version': version, 'payload': payload, 'role': 'Original'}), [])


if __name__ == '__main__':
    unittest.main()
