"""Review repair is not approval; scripted responses exercise the run-fifteen failures."""

import json
from tempfile import TemporaryDirectory
import unittest

from agents import OriginalAgent
from agents.execution_log import RunLog
from agents.model import ModelTurn
from agents.zero_sugar import ZeroSugarAgent, ReviewRepairNeeded
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import plan
from test_review_contract_v2 import current_support, reviewer, visible
from test_review_stages import PhaseModel, SCOPE, SOURCE


class ReviewRecoveryTests(unittest.TestCase):
    def original(self, model):
        generator = SequenceModel([plan(numbers=False), ModelTurn(text='First draft.'),
                                   ModelTurn(text='Revised draft with the requested detail.'),
                                   ModelTurn(text='Third draft.'), ModelTurn(text='Fourth draft.')])
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': generator, 'ZeroSugar': model}[role],
                              'offline-unit-test')
        self.addCleanup(agent.close)
        return agent

    def test_optional_omissions_do_not_consume_support_retries(self):
        def support(context):
            report = current_support(context)
            report.pop('clarification_question')
            report.pop('suggestions')
            return tool_turn('submit_review', report)
        model = PhaseModel([visible()], support)
        agent = reviewer(model)
        result = agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'accept')
        self.assertIsNone(result.clarification_question)
        self.assertEqual(result.suggestions, [])
        self.assertEqual(len(model.calls), 2)
        self.assertEqual({entry['field'] for entry in agent.diagnostics['metadata_normalizations']},
                         {'suggestions', 'clarification_question'})
        self.assertEqual(agent.diagnostics['rejected_attempts'], [])

    def test_malformed_optional_suggestions_cannot_erase_mandatory_work(self):
        report = json.loads(visible(['Show the requested literal example.'], 'Include a literal example.').calls[0].arguments)
        report['suggestions'] = [{'private': 'person@example.invalid'}]
        model = PhaseModel([tool_turn('submit_completeness_review', report)],
                           lambda context: tool_turn('submit_review', current_support(context)))
        agent = reviewer(model)
        result = agent.review('Include a literal example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(len(result.corrections), 1)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(result.suggestions, [])
        self.assertNotIn('person@example.invalid', json.dumps(agent.diagnostics))

    def test_optional_defaults_never_supply_a_missing_finding_review(self):
        def support(context):
            report = current_support(context)
            report.pop('finding_reviews')
            report.pop('suggestions')
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible()], support))
        with self.assertRaises(RuntimeError):
            agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(len(agent.diagnostics['rejected_attempts']), 3)
        self.assertEqual(agent.diagnostics['rejected_attempts'][0]['missing_fields'], ['finding_reviews'])
        self.assertNotIn('support_review', agent.diagnostics)

    def test_clarification_owner_still_needs_an_actual_question(self):
        def support(context):
            report = current_support(context, corrections=[{
                'issue': 'Metric is ambiguous.', 'kind': 'missing_deliverable', 'owner': 'clarify',
                'requested_change': 'Clarify the metric.', 'citation_ids': []}])
            report.pop('clarification_question')
            return tool_turn('submit_review', report)
        agent = reviewer(PhaseModel([visible()], support))
        with self.assertRaises(RuntimeError):
            agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertTrue(all(entry['validation_code'] == 'clarification_required'
                            for entry in agent.diagnostics['rejected_attempts']))

    def test_false_omission_can_be_withdrawn_while_real_omission_stays_pending(self):
        table = '| positive | negative | neutral | mixed | indeterminate |\n| 8 | 2 | 0 | 3 | 0 |'
        answer = table + '\nDenominator: 13. [survey:CMT1]'
        def support(context):
            report = current_support(context)
            report['correction_reviews'][0].update(
                status='withdrawn', reason='All five categories are already visible in the table, including zeroes.')
            report['correction_reviews'][1]['status'] = 'resolved'
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Categories are absent.', 'Literal excerpts are absent.'],
                                    'Show every category and literal examples.')], support)
        agent = reviewer(model)
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                result = agent.review('Show every category and literal examples.', answer, [SOURCE])
                log.finish(0)
            events = [json.loads(line) for line in log.path.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.issues, ['Literal excerpts are absent.'])
        self.assertEqual([item['status'] for item in result.correction_reviews], ['withdrawn', 'unresolved'])
        event = next(item for item in events if item['event'] == 'review_obligation_retained')
        self.assertEqual(event['correction_id'], result.corrections[0]['correction_id'])
        self.assertEqual(event['submitted_status'], 'resolved')
        self.assertEqual(event['effective_status'], 'unresolved')
        self.assertNotIn(table, json.dumps(events))
        self.assertEqual(len(model.calls), 2)

    def test_scope_context_is_authorization_only_and_is_not_written_to_phase_logs(self):
        model = PhaseModel([visible()], lambda context: tool_turn('submit_review', current_support(context)))
        agent = ZeroSugarAgent(SCOPE, model, 'live', authorized_teams=['Data Platforms'],
                               document_lookup={SOURCE['citation_id']: SOURCE})
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                agent.review('Explain.', 'Summary [survey:CMT1].', [SOURCE])
                log.finish(0)
            log_text = log.path.read_text(encoding='utf-8')
        context = model.calls[0][1]
        self.assertEqual(context['authorized_scope'], SCOPE.__dict__)
        self.assertEqual(context['authorized_teams'], ['Data Platforms'])
        self.assertNotIn('evidence', context)
        self.assertNotIn('Data Platforms', log_text)

    def test_incomplete_support_returns_repairs_without_a_verdict(self):
        model = PhaseModel([visible(['Show the requested example.'], 'Include an example.')],
                           lambda context: tool_turn('submit_review', {}))
        agent = reviewer(model)
        with self.assertRaises(ReviewRepairNeeded) as caught:
            agent.review('Include an example.', 'Summary [survey:CMT1].', [SOURCE])
        self.assertEqual(len(caught.exception.corrections), 1)
        self.assertEqual(caught.exception.candidate_id, agent.diagnostics['candidate_id'])
        self.assertEqual(agent.diagnostics['review_phases'][-1]['status'], 'failed')
        self.assertNotIn('support_review', agent.diagnostics)

    def test_original_revises_after_failed_support_then_requires_both_new_reviews(self):
        def support(context):
            if context['candidate_answer'] == 'First draft.':
                return tool_turn('submit_review', {})
            report = current_support(context, statuses={
                item['correction_id']: 'resolved' for item in context['review_obligations']})
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Show the detail.'], 'detail'), visible()], support)
        agent = self.original(model)
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                result = agent.run('Explain with the requested detail.')
                log.finish(0)
            events = [json.loads(line) for line in log.path.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.verification['completed_reviews'], 1)
        self.assertEqual(result.verification['drafts_checked'], 2)
        self.assertEqual(result.verification['released_candidate_id'], result.verification['reviews'][0]['candidate_id'])
        self.assertEqual(result.diagnostics['review_history'][0]['review_phases'][-1]['status'], 'failed')
        event = next(item for item in events if item['event'] == 'review_repair_requested')
        self.assertFalse(event['support_review_completed'])
        self.assertEqual(event['released_findings'], 0)
        self.assertNotEqual(event['candidate_id'], result.verification['released_candidate_id'])

    def test_failed_review_after_repair_never_releases_unverified_content(self):
        model = PhaseModel([visible(['Show the detail.'], 'detail') for _ in range(4)],
                           lambda context: tool_turn('submit_review', {}))
        result = self.original(model).run('Explain with detail.')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.findings, [])
        self.assertEqual(result.verification['completed_reviews'], 0)
        self.assertEqual(result.verification['drafts_checked'], 4)
        self.assertNotIn('released_candidate_id', result.verification)
        self.assertNotIn('Revised draft', result.answer)

    def test_fourth_draft_can_complete_after_three_rejected_candidates(self):
        def support(context):
            report = current_support(context, statuses={
                item['correction_id']: 'resolved' for item in context['review_obligations']})
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Show the detail.'], 'detail') for _ in range(3)] + [visible()], support)
        agent = self.original(model)
        result = agent.run('Explain with detail.')
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.verification['drafts_checked'], 4)
        self.assertEqual(result.verification['completed_reviews'], 4)
        self.assertEqual([review['decision'] for review in result.verification['reviews']],
                         ['revise', 'revise', 'revise', 'accept'])
        self.assertEqual(result.answer, 'Fourth draft.')
        self.assertEqual(agent.budget.model_limit, 32)

    def test_recovery_is_available_after_the_second_and_third_drafts(self):
        def support(context):
            if context['candidate_answer'] != 'Fourth draft.':
                return tool_turn('submit_review', {})
            report = current_support(context, statuses={
                item['correction_id']: 'resolved' for item in context['review_obligations']})
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(['Show the detail.'], 'detail') for _ in range(3)] + [visible()], support)
        result = self.original(model).run('Explain with detail.')
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.verification['drafts_checked'], 4)
        self.assertEqual(result.verification['completed_reviews'], 1)
        self.assertEqual([entry['review_phases'][-1]['status'] for entry in result.diagnostics['review_history']],
                         ['failed', 'failed', 'failed', 'completed'])
        self.assertEqual(result.verification['released_candidate_id'], result.verification['reviews'][0]['candidate_id'])

    def test_global_call_budget_can_stop_before_four_drafts_without_approval(self):
        model = PhaseModel([visible(['Show the detail.'], 'detail') for _ in range(4)],
                           lambda context: tool_turn('submit_review', {}))
        agent = self.original(model)
        agent.model_call_limit = 6
        result = agent.run('Explain with detail.')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure['error_category'], 'workflow_call_limit')
        self.assertEqual(result.verification['completed_reviews'], 0)
        self.assertLess(result.verification['drafts_checked'], 4)
        self.assertEqual(result.findings, [])

    def test_provider_failure_does_not_become_a_repair_verdict(self):
        model = PhaseModel([visible(['Show the detail.'], 'detail')], RuntimeError('HTTP 504'))
        agent = self.original(model)
        result = agent.run('Explain with detail.')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure['error_category'], 'provider_http')
        self.assertEqual(result.verification['drafts_checked'], 1)
        self.assertEqual(len(agent.review_history), 1)


if __name__ == '__main__':
    unittest.main()
