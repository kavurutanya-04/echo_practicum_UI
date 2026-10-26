"""Offline phase-isolation and release regressions; scripted judgments are not accuracy evidence."""

from copy import deepcopy
import json
from tempfile import TemporaryDirectory
import unittest

from agents import AccessScope, OriginalAgent
from agents.execution_log import RunLog
from agents.grounding import FactCatalog, render_answer, audit_claims, GROUNDING_VERSION
from agents.model import ModelTurn
from agents.runtime import RunBudget
from agents.zero_sugar import ZeroSugarAgent, DIMENSIONS
from test_agents import SequenceModel, completeness_turn, tool_turn
from test_flow_improvements import plan

SCOPE = AccessScope('M14', '2026-07-01', '2026-09-30')
SOURCE = {'citation_id': 'survey:CMT1', 'text': 'My contributions are noticed.', 'scope': SCOPE.__dict__}


class PhaseModel:
    def __init__(self, completeness=None, support=None):
        self.completeness = iter(completeness or [completeness_turn()])
        self.support = support
        self.calls = []

    def respond(self, instructions, history, tools, require_tool=False):
        context = json.loads(history[0]['content'])
        self.calls.append((tools[0]['name'], deepcopy(context), deepcopy(tools)))
        if tools[0]['name'] == 'submit_completeness_review':
            turn = next(self.completeness)
            if isinstance(turn, BaseException):
                raise turn
            return turn
        if isinstance(self.support, BaseException):
            raise self.support
        if callable(self.support):
            return self.support(context)
        return support_turn(context)


def support_turn(context, issues=(), finding_decision='supported', correction_reviews=None):
    if correction_reviews is None:
        correction_reviews = [{'correction_id': c['correction_id'], 'status': 'resolved',
                               'reason': 'Controlled resolved-correction judgment.'} for c in context.get('previous_corrections', [])]
    return tool_turn('submit_review', {
        'decision': 'accept',
        'ratings': {d: {'score': 3, 'rationale': 'Controlled source-review fixture.'} for d in DIMENSIONS},
        'issues': list(issues), 'suggestions': [], 'uncertainty': 'Not measured semantic quality.',
        'finding_reviews': [{'finding_id': b['finding_id'], 'decision': finding_decision,
                             'reason': 'Controlled source judgment.'} for b in context['findings']],
        'repair_targets': ['Original'] if issues else [], 'clarification_question': None,
        'correction_reviews': list(correction_reviews),
    })


class ReviewStageTests(unittest.TestCase):
    def review(self, model, answer='Recognition is described favorably [survey:CMT1].', **kwargs):
        agent = ZeroSugarAgent(SCOPE, model, 'live', document_lookup={SOURCE['citation_id']: SOURCE})
        return agent, agent.review('Explain recognition and include an example.', answer, [SOURCE], **kwargs)

    def test_completeness_sees_only_question_and_exact_visible_answer(self):
        model = PhaseModel()
        agent, result = self.review(model)
        self.assertEqual(result.decision, 'accept')
        self.assertEqual([c[0] for c in model.calls], ['submit_completeness_review', 'submit_review'])
        first, second = model.calls[0][1], model.calls[1][1]
        self.assertEqual(set(first), {'question', 'candidate_answer'})
        self.assertEqual(first['candidate_answer'], second['candidate_answer'])
        self.assertNotIn('evidence', first)
        self.assertEqual(second['evidence'], [SOURCE])
        self.assertNotIn('request_deliverables', second)
        self.assertEqual([p['status'] for p in agent.diagnostics['review_phases']], ['completed', 'completed'])

    def test_missing_visible_example_cannot_be_overridden_by_source_acceptance(self):
        model = PhaseModel([completeness_turn('revise', ['The requested literal example is absent.'], score=2)])
        _, result = self.review(model)
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.findings[0]['status'], 'supported')
        self.assertEqual(result.ratings['Completeness']['score'], 2)
        self.assertEqual(result.corrections[0]['owner'], 'Original')
        self.assertIn('literal example', result.issues[0])

    def test_optional_style_suggestion_does_not_block(self):
        model = PhaseModel([completeness_turn(suggestions=['A shorter heading is optional.'])])
        _, result = self.review(model)
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(result.issues, [])
        self.assertEqual(result.suggestions, ['A shorter heading is optional.'])

    def test_visible_chart_labels_do_not_expose_provenance_to_completeness(self):
        model = PhaseModel()
        chart = {'kind': 'line', 'title': 'Recognition trend', 'x_label': 'Quarter',
                 'y_label': 'Score', 'unit': 'Score (1-5)', 'source_id': 'SQL_PRIVATE',
                 'sql': 'private query text', 'rows': [{'private_value': 123}]}
        agent = ZeroSugarAgent(SCOPE, model, 'live')
        agent.review('Show the trend chart.', 'A trend chart accompanies this answer.', [], {'charts': [chart, None], 'reason': 'Fixture.'})
        visible = model.calls[0][1]['visible_charts'][0]
        self.assertEqual(set(visible), {'kind', 'title', 'x_label', 'y_label', 'unit'})
        self.assertNotIn('SQL_PRIVATE', str(model.calls[0][1]))
        self.assertNotIn('private query text', str(model.calls[0][1]))
        self.assertEqual(model.calls[1][1]['visualization']['charts'], [chart, None])

    def test_negative_completeness_verdict_without_issue_text_still_blocks(self):
        model = PhaseModel([completeness_turn('revise')])
        _, result = self.review(model)
        self.assertEqual(result.decision, 'revise')
        self.assertTrue(result.issues)

    def test_source_rejection_still_blocks_complete_visible_answer(self):
        model = PhaseModel(support=lambda c: support_turn(c, finding_decision='revise'))
        _, result = self.review(model)
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.findings[0]['status'], 'withheld')

    def test_citations_are_attached_by_block_identity(self):
        model = PhaseModel()
        _, result = self.review(model)
        self.assertEqual(result.findings[0]['citation_ids'], [SOURCE['citation_id']])
        schema = model.calls[1][2][0]['parameters']['properties']['finding_reviews']['items']
        self.assertNotIn('citation_ids', schema['properties'])
        self.assertEqual(set(schema['required']), {'finding_id', 'decision', 'reason'})
        corrections = model.calls[1][2][0]['parameters']['properties']['corrections']['items']
        self.assertNotIn('request_excerpt', corrections['properties'])

    def test_current_corrections_need_no_copy_of_user_question_and_legacy_excerpt_is_not_retained(self):
        question = 'Include a literal example.'
        change = {'issue_index': 0, 'kind': 'missing_deliverable', 'owner': 'Original',
                  'requested_change': 'Show the available example.', 'citation_ids': [SOURCE['citation_id']]}
        for entry in (change, {**change, 'request_excerpt': question}):
            report = {'issues': ['The example is absent.'], 'corrections': [entry]}
            corrections, _ = ZeroSugarAgent.validate_corrections(report, question, [SOURCE], [])
            self.assertIsNone(corrections[0]['request_excerpt'])

    def test_completeness_retry_is_bounded_and_stage_specific(self):
        model = PhaseModel([tool_turn('submit_completeness_review', {})] * 3)
        agent = ZeroSugarAgent(SCOPE, model, 'live')
        with self.assertRaisesRegex(RuntimeError, 'Completeness verifier'):
            agent.review('Question', 'Answer', [])
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(agent.diagnostics['review_phases'][0]['status'], 'failed')
        self.assertTrue(all(e['phase'] == 'completeness' for e in agent.diagnostics['rejected_attempts']))

    def test_repaired_completeness_diagnostics_are_not_relabelled_as_support(self):
        model = PhaseModel([tool_turn('submit_completeness_review', {}), completeness_turn()])
        agent, result = self.review(model)
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(agent.diagnostics['rejected_attempts'][0]['resolution'], 'accepted_completeness_submission')
        self.assertEqual(len(model.calls), 3)

    def test_shared_budget_can_stop_before_support_without_approval(self):
        model = PhaseModel()
        agent = ZeroSugarAgent(SCOPE, model, 'live', budget=RunBudget(model_limit=1))
        with self.assertRaisesRegex(RuntimeError, 'budget exceeded'):
            agent.review('Question', 'Answer', [])
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(agent.diagnostics['review_phases'][-1]['status'], 'failed')

    def test_support_failure_keeps_completed_completeness_status(self):
        model = PhaseModel(support=RuntimeError('Controlled provider failure.'))
        agent = ZeroSugarAgent(SCOPE, model, 'live')
        with self.assertRaisesRegex(RuntimeError, 'Controlled provider failure'):
            agent.review('Question', 'Answer', [])
        self.assertEqual([p['status'] for p in agent.diagnostics['review_phases']], ['completed', 'failed'])

    def test_shared_tool_budget_also_stops_support_without_approval(self):
        model = PhaseModel()
        agent = ZeroSugarAgent(SCOPE, model, 'live', budget=RunBudget(tool_limit=1))
        with self.assertRaisesRegex(RuntimeError, 'budget exceeded'):
            agent.review('Question', 'Answer', [])
        self.assertEqual(agent.diagnostics['review_phases'][-1]['status'], 'failed')

    def test_numeric_proposal_is_a_review_signal_in_v3_not_a_measured_result(self):
        catalog = FactCatalog([SOURCE], SCOPE.__dict__)
        payload = {'fact_ids': [], 'interpretations': [], 'proposals': [{'text': 'Consider a target of 99 percent.',
            'citation_ids': [SOURCE['citation_id']], 'quote': None}]}
        _, claims = render_answer(payload, catalog, 'Original')
        proposal = next(c for c in claims if c['kind'] == 'proposal')
        self.assertTrue(proposal['review_warnings'])
        self.assertEqual(proposal['validation'], 'provisional_semantics')

    def test_unresolved_prior_correction_remains_pending(self):
        prior = [{'correction_id': 'C1', 'issue_index': 0, 'issue': 'Missing explanation.', 'owner': 'Original',
                  'kind': 'missing_deliverable', 'requested_change': 'Add the explanation.',
                  'citation_ids': [], 'request_excerpt': None}]
        model = PhaseModel(support=lambda c: support_turn(c, correction_reviews=[{
            'correction_id': 'C1', 'status': 'unresolved', 'reason': 'It is still absent.'}]))
        _, result = self.review(model, previous_corrections=prior)
        self.assertEqual(result.decision, 'revise')
        self.assertIn('Missing explanation.', result.issues)

    def test_prior_corrections_require_complete_assessments_even_if_field_is_omitted(self):
        prior = [{'correction_id': 'C1'}, {'correction_id': 'C2'}]
        assessment = {'correction_id': 'C1', 'status': 'resolved', 'reason': 'Present.'}
        for fields in ({}, {'correction_reviews': []}, {'correction_reviews': [assessment]}):
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, 'every prior correction'):
                ZeroSugarAgent.validate_corrections({'issues': [], **fields}, 'Question', [], prior)

    def test_legacy_review_without_prior_corrections_still_validates(self):
        self.assertEqual(ZeroSugarAgent.validate_corrections({'issues': []}, 'Question', [], []), ([], []))

    def test_omitted_prior_assessment_repairs_instead_of_accepting(self):
        def missing_assessments(context):
            turn = support_turn(context)
            report = json.loads(turn.calls[0].arguments)
            del report['correction_reviews']
            return tool_turn('submit_review', report)

        model = PhaseModel(support=missing_assessments)
        agent = ZeroSugarAgent(SCOPE, model, 'live', document_lookup={SOURCE['citation_id']: SOURCE})
        with self.assertRaisesRegex(RuntimeError, 'Verifier did not return'):
            agent.review('Explain recognition.', 'Recognition is favorable [survey:CMT1].', [SOURCE],
                         previous_corrections=[{'correction_id': 'C1'}])
        self.assertEqual(len(model.calls), 4)
        self.assertTrue(all(e['validation_code'] == 'correction_review_coverage'
                            for e in agent.diagnostics['rejected_attempts']))

    def test_phase_trace_contains_metadata_not_request_or_evidence_text(self):
        model = PhaseModel()
        agent = ZeroSugarAgent(SCOPE, model, 'live', document_lookup={SOURCE['citation_id']: SOURCE})
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                agent.review('Explain private@example.invalid.', 'Recognition is favorable [survey:CMT1].', [SOURCE])
                log.finish(0)
            raw = log.path.read_text(encoding='utf-8')
        self.assertNotIn('private@example.invalid', raw)
        self.assertNotIn(SOURCE['text'], raw)
        events = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual(len([e for e in events if e['event'] == 'review_phase_finished']), 2)

    def test_planning_schema_has_no_deliverable_checklist_and_reads_legacy_field(self):
        old = plan(numbers=False)
        args = json.loads(old.calls[0].arguments)
        args['deliverables'] = [{'untrusted': 'Do not retain a retired checklist.'}]
        model = SequenceModel([tool_turn('submit_plan', args)])
        agent = OriginalAgent(None, SCOPE, lambda _: model, 'live')
        agent.budget = RunBudget()
        result = agent.plan('Explain the available evidence.')
        self.assertNotIn('deliverables', result)
        self.assertEqual(len(model.histories), 1)

    def test_full_original_repair_preserves_real_pending_items_without_preplanning_them(self):
        original = SequenceModel([plan(numbers=False), ModelTurn(text='Initial explanation.'), ModelTurn(text='Revised explanation.')])
        reviewer = PhaseModel([completeness_turn('revise', ['Explain the requested limit.'], score=2), completeness_turn()])
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': original, 'ZeroSugar': reviewer}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        result = agent.run('Explain the evidence and its limits.')
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.verification['drafts_checked'], 2)
        self.assertEqual(len(reviewer.calls), 4)
        self.assertIn('Explain the requested limit.', str(original.histories[-1]))
        self.assertNotIn('request_deliverables', str(original.histories))
        self.assertEqual(result.diagnostics['pending_corrections'], [])

    def test_v3_quantities_are_review_signals_while_explicit_quotes_remain_literal(self):
        catalog = FactCatalog([SOURCE], SCOPE.__dict__)
        payload = {'fact_ids': [], 'interpretations': [{'text': 'The 13 comments express appreciation.',
            'citation_ids': [SOURCE['citation_id']], 'quote': None}], 'proposals': []}
        text, claims = render_answer(payload, catalog, 'Original')
        self.assertTrue(claims[0]['review_warnings'])
        self.assertEqual(audit_claims(claims, text, catalog, {'version': GROUNDING_VERSION, 'role': 'Original', 'payload': payload}), [])
        payload['interpretations'][0]['quote'] = 'An invented excerpt.'
        with self.assertRaises(ValueError):
            render_answer(payload, catalog, 'Original')


if __name__ == '__main__':
    unittest.main()
