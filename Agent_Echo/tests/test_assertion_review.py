"""Assertion-level withholding and traceability; judgments are scripted, not accuracy scores."""

from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents.execution_log import RunLog
from agents import OriginalAgent
from agents.model import ModelTurn
from agents.zero_sugar import ZeroSugarAgent, REVIEW_VERSION
from agents.validation import ValidationError
from test_agents import tool_turn, SequenceModel
from test_flow_improvements import plan
from test_review_contract_v3 import support
from test_review_contract_v2 import visible
from test_review_stages import PhaseModel, SCOPE


SOURCES = [
    {'citation_id': 'survey:A', 'text': 'Support is helpful but access is inconsistent.', 'scope': SCOPE.__dict__},
    {'citation_id': 'survey:B', 'text': 'Still frustrating, despite some useful support.', 'scope': SCOPE.__dict__},
]
FIRST = 'Both comments express favorable and unfavorable views. '
SECOND = 'Both report inconsistent access. [survey:A] [survey:B]'
ANSWER = FIRST + SECOND


def assertion(claim, refs, assessment='supported', kind='factual'):
    return {'claim': claim, 'kind': kind, 'citation_ids': refs, 'assessment': assessment,
            'reason': 'Controlled comparison of this assertion with its cited evidence.'}


class AssertionReviewTests(unittest.TestCase):
    def reviewer(self, response):
        model = PhaseModel([visible()], lambda context: tool_turn('submit_review', response(context)))
        return ZeroSugarAgent(SCOPE, model, 'live', document_lookup={s['citation_id']: s for s in SOURCES}), model

    @staticmethod
    def report(context, second='insufficient_evidence'):
        report = support(context)
        report['finding_reviews'][0]['assertions'] = [
            assertion(FIRST, ['survey:A', 'survey:B']), assertion(SECOND, ['survey:A', 'survey:B'], second)]
        return report

    def test_one_unsupported_part_overrides_accept_and_retains_a_targeted_repair(self):
        for assessment in ('contradicted', 'insufficient_evidence'):
            with self.subTest(assessment=assessment):
                agent, model = self.reviewer(lambda c: self.report(c, assessment))
                result = agent.review('Explain.', ANSWER, SOURCES)
                self.assertEqual(result.decision, 'revise')
                self.assertEqual(result.findings[0]['status'], 'withheld')
                self.assertEqual(result.deterministic_issues, [])
                self.assertEqual(result.findings[0]['assertions'][0]['assessment'], 'supported')
                self.assertEqual(result.repair_targets, ['Original'])
                self.assertEqual(len(result.corrections), 1)
                self.assertEqual(result.corrections[0]['kind'], 'unsupported_claim')
                self.assertIn('F1', result.corrections[0]['issue'])
                self.assertEqual(len(model.calls), 2)
                self.assertEqual(result.version, REVIEW_VERSION)

    def test_synthesis_can_use_different_source_subsets_for_different_assertions(self):
        answer = 'One comment reports inconsistent access. The other acknowledges useful support. [survey:A] [survey:B]'
        def respond(context):
            report = support(context)
            report['finding_reviews'][0]['assertions'] = [
                assertion('One comment reports inconsistent access.', ['survey:A']),
                assertion('The other acknowledges useful support. [survey:A] [survey:B]', ['survey:B'])]
            return report
        agent, _ = self.reviewer(respond)
        result = agent.review('Explain.', answer, SOURCES)
        self.assertEqual(result.decision, 'accept')
        self.assertEqual(result.findings[0]['assertions'][1]['citation_ids'], ['survey:B'])

    def test_proposal_may_be_novel_but_its_unsupported_premise_blocks_the_finding(self):
        answer = 'Both report inconsistent access. Trial a weekly check-in to investigate barriers. [survey:A] [survey:B]'
        def respond(context):
            report = support(context)
            report['finding_reviews'][0]['assertions'] = [
                assertion('Both report inconsistent access.', ['survey:A', 'survey:B'], 'insufficient_evidence'),
                assertion('Trial a weekly check-in to investigate barriers. [survey:A] [survey:B]', [], kind='proposal')]
            return report
        agent, _ = self.reviewer(respond)
        result = agent.review('Explain.', answer, SOURCES)
        self.assertEqual(result.decision, 'revise')
        self.assertEqual(result.findings[0]['assertions'][1]['assessment'], 'supported')

    def test_omitted_assertions_cannot_downgrade_a_live_review_to_the_legacy_contract(self):
        def respond(context):
            report = support(context)
            report['finding_reviews'][0].pop('assertions')
            report['issues'] = []  # Attempt the legacy root shape as well.
            report['repair_targets'] = []
            report.pop('numeric_reviews', None)
            return report
        agent, model = self.reviewer(respond)
        with self.assertRaisesRegex(RuntimeError, 'Verifier did not return'):
            agent.review('Explain.', ANSWER, SOURCES)
        self.assertEqual(len(model.calls), 4)
        self.assertEqual(agent.diagnostics['review_phases'][-1]['status'], 'failed')
        self.assertTrue(all(r['validation_code'] == 'finding_fields' for r in agent.diagnostics['rejected_attempts']))

    def test_original_revises_a_failed_assertion_before_releasing_the_new_candidate(self):
        initial = 'All teams improved. Investigate consistency.'
        revised = 'Team-wide improvement is unverified. Investigate consistency.'
        def respond(context):
            judgments = {c['correction_id']: {'mandatory': True, 'addressed': True,
                'reason': 'The revised answer qualifies the unsupported assertion.'}
                for c in context['review_obligations']}
            report = support(context, judgments)
            if context['candidate_answer'] == initial:
                report['finding_reviews'][0]['assertions'] = [
                    assertion('All teams improved.', [], 'insufficient_evidence'),
                    assertion('Investigate consistency.', [], kind='proposal')]
            return tool_turn('submit_review', report)
        model = PhaseModel([visible(), visible()], respond)
        original = SequenceModel([plan(numbers=False), ModelTurn(text=initial), ModelTurn(text=revised)])
        agent = OriginalAgent(None, SCOPE, lambda role: {'Original': original, 'ZeroSugar': model}[role], 'offline-unit-test')
        self.addCleanup(agent.close)
        result = agent.run('Explain.')
        self.assertEqual(result.status, 'complete')
        self.assertEqual(result.answer, revised)
        self.assertEqual(result.verification['drafts_checked'], 2)
        self.assertEqual(result.verification['reviews'][0]['findings'][0]['status'], 'withheld')
        self.assertEqual(result.verification['reviews'][1]['findings'][0]['status'], 'supported')
        self.assertEqual(len(model.calls), 4)

    def test_invalid_assertion_fields_and_references_are_rejected(self):
        agent, _ = self.reviewer(self.report)
        block = {'finding_id': 'F1', 'text': ANSWER, 'citation_ids': ['survey:A', 'survey:B']}
        valid = [assertion(FIRST, ['survey:A', 'survey:B']), assertion(SECOND, ['survey:A'], 'insufficient_evidence')]
        cases = [[], [{**valid[0], 'claim': 'x' * 601}, valid[1]],
                 [{**valid[0], 'citation_ids': ['unknown']}, valid[1]],
                 [{**valid[0], 'citation_ids': ['survey:A', 'survey:A']}, valid[1]],
                 [{**valid[0], 'citation_ids': []}, valid[1]],
                 [{k: v for k, v in valid[0].items() if k != 'assessment'}, valid[1]],
                 [{**valid[0], 'assessment': None}, valid[1]],
                 [{**valid[0], 'reason': ' '}, valid[1]],
                 [{**valid[0], 'kind': 'opinion'}, valid[1]]]
        for i, items in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValidationError):
                agent.validate_assertions(items, block, SOURCES, 'assertions')
        result = agent.validate_assertions(valid, block, SOURCES, 'assertions')
        self.assertEqual([r['assertion_id'] for r in result], ['F1:A1', 'F1:A2'])
        self.assertEqual([{k: v for k, v in r.items() if k != 'assertion_id'} for r in result], valid)

    def test_long_formatted_findings_do_not_need_literal_reconstruction(self):
        agent, _ = self.reviewer(self.report)
        block = {'finding_id': 'F1', 'text': '| formatted data |\n' * 1000,
                 'citation_ids': ['survey:A']}
        assessments = [assertion('The displayed source values are supported.', ['survey:A'])]
        result = agent.validate_assertions(assessments, block, SOURCES, 'assertions')
        self.assertEqual(result[0]['claim'], assessments[0]['claim'])
        self.assertEqual(result[0]['assertion_id'], 'F1:A1')

    def test_an_assertion_cannot_borrow_an_unrelated_findings_source(self):
        agent, _ = self.reviewer(self.report)
        block = {'finding_id': 'F1', 'text': 'Access is inconsistent.', 'citation_ids': ['survey:A']}
        with self.assertRaisesRegex(ValidationError, 'this finding only'):
            agent.validate_assertions([assertion(block['text'], ['survey:B'])], block, SOURCES, 'assertions')

    def test_validated_assessments_survive_export_but_log_events_only_include_counts(self):
        agent, _ = self.reviewer(self.report)
        with TemporaryDirectory() as folder:
            with RunLog(Path(folder)) as log:
                result = agent.review('Explain.', ANSWER, SOURCES)
            rows = [json.loads(line) for line in log.path.read_text(encoding='utf-8').splitlines()]
        exported = json.loads(json.dumps(asdict(result)))
        self.assertEqual(exported['findings'][0]['assertions'][1]['claim'], SECOND)
        event = next(r for r in rows if r['event'] == 'finding_reviewed')
        self.assertEqual((event['assertion_count'], event['unsupported_assertions']), (2, 1))
        self.assertNotIn(SECOND, json.dumps(rows))

    def test_saved_legacy_findings_remain_readable_without_fabricating_assertions(self):
        agent, _ = self.reviewer(self.report)
        report = support({'question': 'Explain.', 'findings': [{'finding_id': 'F1', 'text': ANSWER,
            'citation_ids': ['survey:A', 'survey:B']}], 'review_obligations': []})
        report['repair_targets'] = []
        report['finding_reviews'][0].pop('assertions')
        blocks = [{'finding_id': 'F1', 'text': ANSWER, 'citation_ids': ['survey:A', 'survey:B']}]
        checked = agent.validate_findings(report, blocks, SOURCES)
        self.assertNotIn('assertions', checked[0])


if __name__ == '__main__':
    unittest.main()
