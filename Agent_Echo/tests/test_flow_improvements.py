"""Behavioral checks for metrics, bounded closure, routing and partial release."""

import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from agents import AccessScope, OriginalAgent, ZeroSugarAgent
from agents.execution_log import RunLog
from agents.findings import cited_findings, clarification_question, normalize_citations
from agents.metrics import MetricCatalog
from agents.model import ModelTurn, ScriptedDemoModel
from agents.runtime import Specialist, function_tool, RunBudget, AgentRunError, AgentResult, reject_calls
from agents.tools import SQLReader
from agents.zero_sugar import DIMENSIONS
from agents.cherry import CherryAgent
from test_agents import SequenceModel, tool_turn, completeness_turn, assertion_reviews


SCOPE = AccessScope("M14", "2026-07-01", "2026-09-30")


def tables():
    return {
        "employees": (["Employee_ID", "Team_Display_Name"], [("E1", "A"), ("E2", "A")]),
        "contributions": (["Contribution_ID", "Home_Team", "Beneficiary_Team"],
                          [("C1", "A", "B"), ("C1", "A", "B"), ("C2", "A", "C"), ("C3", "A", "A")]),
        "recognition_feedback": (["Interaction_ID", "Contribution_ID", "Interaction_Type"],
            [("R1", "C1", "Manager recognition"), ("R2", "C1", "Manager recognition"), ("R3", "C1", "Partner feedback")]),
        "survey_summary": (["Team", "Survey_Date", "Dimension", "Responses", "Mean_Score", "Favorable_Percent"],
                             [("A", "2026-09-30", "Recognition", 10, 3.2, 40.0)]),
    }


def plan(numbers=True, text=False, chart=False, question=None, metric="none", dimension="", basis=None):
    return tool_turn("submit_plan", {"needs_numbers": numbers, "needs_text": text,
                                    "needs_sentiment": False,
                                    "include_chart": chart, "clarification_question": question,
                                    "clarification_basis": basis,
                                    "metrics": [] if metric == "none" else [{"metric": metric, "dimension": dimension or None}]})


class FixtureCherry(Specialist):
    numeric_coverage = CherryAgent.numeric_coverage
    has_pending_work = CherryAgent.has_pending_work
    def __init__(self, database, scope, model, mode, budget=None):
        self.reader = SQLReader(tables(), scope)
        self.metric_calls = 0
        def run_metric(metric, dimension=None):
            self.metric_calls += 1
            return MetricCatalog(self.reader).run(metric, dimension)
        definitions = [function_tool("run_metric", "Validated metric", {"metric": {"type": "string"}, "dimension": {"type": ["string", "null"]}})]
        super().__init__("Cherry", "Use evidence.", model, scope, definitions, {"run_metric": run_metric}, mode, budget)

    def close(self):
        self.reader.close()


class ReviewModel:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def respond(self, instructions, history, tools, require_tool=False):
        self.calls += 1
        if tools and tools[0]["name"] == "submit_completeness_review":
            return completeness_turn()
        payload = json.loads(history[0]["content"])
        outcome = next(self.outcomes)
        report = {"decision": "accept" if outcome == "accept" else "revise",
            "ratings": {d: {"score": 1 if d == "Safety / Appropriateness" and outcome == "unsafe" else 3,
                            "rationale": "Controlled test fixture."} for d in DIMENSIONS},
            "issues": [] if outcome == "accept" else ["Correct the specified issue."], "uncertainty": "Test fixture.",
            "finding_reviews": [{"finding_id": b["finding_id"],
                "decision": "revise" if "fabricated" in b["text"] else "supported",
                "reason": "Controlled test decision.", "assertions": assertion_reviews(b, evidence=payload.get("evidence"))} for b in payload["findings"]],
            "repair_targets": [] if outcome == "accept" else ["Lime" if outcome == "chart" else "Original"],
            "clarification_question": None,
            "correction_reviews": [{"correction_id": item["correction_id"], "status": "resolved",
                                    "reason": "Scripted resolution against the revised fixture."}
                                   for item in payload.get("previous_corrections", [])]}
        return tool_turn("submit_review", report)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.reader = SQLReader(tables(), SCOPE)

    def tearDown(self):
        self.reader.close()

    def test_distinct_metric_handles_duplicate_contributions_and_multiple_feedback(self):
        result = MetricCatalog(self.reader).run("cross_team_contributions")
        self.assertEqual(result["rows"], [{"Total_Contributions": 2, "With_Manager_Recognition": 1,
            "Without_Manager_Recognition": 1, "With_Partner_Feedback": 1, "Without_Any_Feedback": 1}])
        self.assertEqual(result["scope"], SCOPE.__dict__)
        self.assertIn("interaction period", result["metric_definition"])
        self.assertEqual(MetricCatalog(self.reader).run("cross_team_contributions", "None")["rows"], result["rows"])

    def test_known_unsafe_join_is_rejected_while_custom_sql_remains_available(self):
        with self.assertRaisesRegex(ValueError, "duplicate contributions"):
            self.reader.execute("SELECT COUNT(*) FROM contributions c LEFT JOIN recognition_feedback f ON c.Contribution_ID=f.Contribution_ID")
        rows = self.reader.execute("SELECT COUNT(DISTINCT Contribution_ID) AS n FROM contributions WHERE Home_Team<>Beneficiary_Team")["rows"]
        self.assertEqual(rows, [{"n": 2}])

    def test_metric_dimension_is_bound_and_empty_population_has_zero_counts(self):
        result = MetricCatalog(self.reader).run("survey_trend", "Recognition' OR 1=1 --")
        self.assertEqual(result["rows"], [])
        self.assertEqual(len(result["parameters"]), 1)
        with self.assertRaises(ValueError):
            MetricCatalog(self.reader).run("unknown")
        empty = tables(); empty["contributions"] = (empty["contributions"][0], [])
        reader = SQLReader(empty, SCOPE)
        try:
            row = MetricCatalog(reader).run("cross_team_contributions")["rows"][0]
            self.assertTrue(all(value == 0 for value in row.values()))
        finally:
            reader.close()

    def test_metric_metadata_tampering_is_detected_beyond_sql_replay(self):
        result = MetricCatalog(self.reader).run("cross_team_contributions")
        result["metric_definition"] = "Missing notes prove unfair treatment."
        verifier = ZeroSugarAgent(SCOPE, ScriptedDemoModel("ZeroSugar"), "offline-unit-test", sql_reader=self.reader)
        self.assertIn("Metric evidence differs from its validated definition.", verifier.audit("Two [SQL1].", [result]))

    def test_survey_dimension_case_and_whitespace_preserve_rows_and_replay(self):
        expected = MetricCatalog(self.reader).run("survey_trend", "Recognition")["rows"]
        self.assertTrue(expected)
        for dimension in ("recognition", "RECOGNITION", "  Recognition  "):
            with self.subTest(dimension=dimension):
                result = MetricCatalog(self.reader).run("survey_trend", dimension)
                self.assertEqual(result["rows"], expected)
                self.assertEqual(result["metric_version"], 2)
                verifier = ZeroSugarAgent(SCOPE, None, sql_reader=self.reader)
                self.assertEqual(verifier.audit("Survey results [" + result["citation_id"] + "].", [result]), [])
        for dimension in ("Recognitio", "Unknown", "Recognition' OR 1=1 --"):
            self.assertEqual(MetricCatalog(self.reader).run("survey_trend", dimension)["rows"], [])


class ClosingTests(unittest.TestCase):
    def test_only_standalone_markdown_separators_are_excluded_from_findings(self):
        for separator in ("---", "***", "___", "-----", "- - -", " * * * ", "  _ _ _\t"):
            with self.subTest(separator=separator):
                blocks = cited_findings("Two contributions [SQL1].\n\n" + separator +
                                       "\n\nThere are nine fabricated contributions.")
                self.assertEqual([b["text"] for b in blocks],
                    ["Two contributions [SQL1].", "There are nine fabricated contributions."])
                self.assertEqual(blocks[-1]["citation_ids"], [])
        for text in ("--- Unsupported assertion", "---\nThere are nine contributions.",
                     "### There are 9 contributions", "- There are nine contributions."):
            self.assertEqual(len(cited_findings(text)), 1)

    def test_prepared_evidence_reaches_model_before_tool_free_interpretation(self):
        evidence = {"citation_id": "SQL1", "rows": [{"Responses": 32, "Mean_Score": 3.53}],
                    "scope": SCOPE.__dict__}
        observed = []
        class EvidenceModel:
            def respond(self, instructions, history, tools, require_tool=False):
                observed.append((history, tools, require_tool))
                self_payload = json.loads(history[-1]["content"].split("\n", 1)[1])
                row = self_payload["evidence"][0]["rows"][0]
                return ModelTurn(text=f"Mean {row['Mean_Score']} from {row['Responses']} responses [SQL1].")
        agent = Specialist("Cherry", "Use evidence.", EvidenceModel(), SCOPE, [], {})
        result = agent.run("Show survey scores.", initial_evidence=[evidence])
        self.assertEqual(result.answer, "Mean 3.53 from 32 responses [SQL1].")
        self.assertEqual(result.evidence, [evidence])
        self.assertEqual(result.tool_trace, [])
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][1:], ([], False))

    def test_structured_repair_answers_every_outstanding_call(self):
        a, b = tool_turn("submit_plan", {}, "a"), tool_turn("submit_plan", {}, "b")
        turn = ModelTurn(calls=a.calls+b.calls)
        history = []
        reject_calls(history, turn, "One call only.")
        self.assertEqual([item["call_id"] for item in history], ["a", "b"])

    def test_only_known_explicit_citations_are_normalized(self):
        text = "Evidence `SQL1` and [SQL1, SQL2], but `SQL999` is unknown."
        normalized = normalize_citations(text, {"SQL1", "SQL2"})
        self.assertIn("Evidence [SQL1] and [SQL1] [SQL2]", normalized)
        self.assertIn("`SQL999`", normalized)

    def test_seventh_turn_has_no_tools_and_returns_existing_evidence(self):
        turns = [tool_turn("query", {"index": i}, str(i)) for i in range(6)]
        turns.append(ModelTurn(text="Evidence is available [SQL6]."))
        class Observed(SequenceModel):
            def respond(self, instructions, history, tools, require_tool=False):
                self.last_tools = tools
                self.last_instructions = instructions
                return super().respond(instructions, history, tools, require_tool)
        model = Observed(turns)
        agent = Specialist("Cherry", "", model, SCOPE, [{"name": "query"}],
                           {"query": lambda index: {"citation_id": f"SQL{index+1}"}})
        result = agent.run("Query and finish.")
        self.assertEqual(result.answer, "Evidence is available [SQL6].")
        self.assertEqual(model.last_tools, [])
        self.assertIn("closing turn", model.last_instructions)

    def test_repeated_query_reuses_result_and_closes_with_no_new_execution(self):
        calls = []
        model = SequenceModel([tool_turn("query", {}), tool_turn("query", {}, "repeat"), ModelTurn(text="One result [SQL1].")])
        def query():
            calls.append(1)
            return {"citation_id": "SQL1"}
        result = Specialist("Cherry", "", model, SCOPE, [{"name": "query"}], {"query": query}).run("Count.")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result.evidence), 1)


class OutcomeTests(unittest.TestCase):
    def test_survey_plan_repairs_nonexistent_dimension_before_preparing_metric(self):
        with patch("agents.original.CherryAgent", FixtureCherry):
            coordinator = SequenceModel([plan(metric="survey_trend", dimension="quarter"),
                                         plan(metric="survey_trend", dimension=" recognition ")])
            agent = OriginalAgent("unused", SCOPE, lambda name: coordinator, "offline-unit-test")
            agent.budget = RunBudget()
            try:
                result = agent.plan("Show Recognition scores by quarter.")
                self.assertEqual(result["metrics"][0]["dimension"], "Recognition")
                self.assertEqual(agent.specialists["Cherry"].metric_calls, 0)
            finally:
                agent.close()

    def test_nullable_tool_string_does_not_become_a_fake_clarification(self):
        for value in (None, "None", "null", "N/A", "  "):
            self.assertIsNone(clarification_question(value))
        model = SequenceModel([plan(False, False, False, "None")])
        agent = OriginalAgent("unused", SCOPE, lambda name: model, "offline-unit-test")
        agent.budget = RunBudget()
        self.assertIsNone(agent.plan("Explain the boundary.")["clarification_question"])

    def workflow(self, outcomes, texts, chart=False, prepared=False):
        coordinator = SequenceModel([plan(chart=chart, metric="cross_team_contributions" if prepared else "none"), tool_turn("ask_cherry", {"question": "Count distinct cross-team contributions."})]
                                    + [ModelTurn(text=text) for text in texts])
        reviewer = ReviewModel(outcomes)
        cherry = SequenceModel([tool_turn("run_metric", {"metric": "cross_team_contributions", "dimension": None}),
                                ModelTurn(text="Two distinct contributions [SQL1].")])
        if prepared:
            cherry = SequenceModel([ModelTurn(text="Two distinct contributions [SQL1].")])
        requested = []
        def factory(name):
            requested.append(name)
            if name == "Original": return coordinator
            if name == "Cherry": return cherry
            if name == "ZeroSugar": return reviewer
            if name == "Lime" and chart: return ScriptedDemoModel("Lime")
            raise AssertionError("Unneeded role constructed: " + name)
        return OriginalAgent("unused", SCOPE, factory, "offline-unit-test"), reviewer, requested

    def test_numerical_plan_skips_text_and_charts_and_finishes_complete(self):
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, reviewer, requested = self.workflow(["accept"], ["There are two distinct contributions [SQL1]."])
            try:
                result = agent.run("Count cross-team contributions.")
                self.assertEqual(result.status, "complete")
                self.assertEqual(result.findings[0]["status"], "supported")
                self.assertNotIn("Vanilla", requested)
                self.assertNotIn("Lime", requested)
            finally: agent.close()

    def test_markdown_separators_do_not_force_a_supported_workflow_to_partial(self):
        text = "Two distinct contributions [SQL1].\n\n---\n\nMissing notes do not prove absent recognition [SQL1]."
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, _, _ = self.workflow(["accept"], [text])
            try:
                result = agent.run("Count contributions and explain limitations.")
                self.assertEqual(result.status, "complete")
                self.assertEqual(result.verification["decision"], "accept")
                self.assertEqual(len(result.findings), 2)
                self.assertTrue(all(f["status"] == "supported" for f in result.findings))
            finally:
                agent.close()

    def test_planned_metric_runs_before_cherry_without_exploratory_queries(self):
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, _, _ = self.workflow(["accept"], ["Two distinct contributions [SQL1]."], prepared=True)
            try:
                result = agent.run("Count cross-team contributions.")
                self.assertEqual(result.status, "complete")
                child = agent.specialists["Cherry"]
                self.assertEqual(child.metric_calls, 1)
                self.assertEqual(result.delegations[0]["tool_trace"], [])
                self.assertIn("Total_Contributions", result.evidence[0]["rows"][0])
            finally: agent.close()

    def test_uncited_factual_block_cannot_escape_finding_review(self):
        text = "Two contributions [SQL1].\n\nThere are nine fabricated contributions."
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, _, _ = self.workflow(["partial"] * 4, [text] * 4)
            try:
                result = agent.run("Count.")
                self.assertEqual(len(result.findings), 2)
                self.assertEqual(result.status, "partial")
                self.assertNotIn("fabricated", result.answer)
                self.assertIn("explicit evidence citation", str(result.findings[1]["deterministic_issues"]))
            finally: agent.close()

    def test_recovered_specialist_failure_does_not_force_a_partial_final_status(self):
        class RecoveredCherry(FixtureCherry):
            def run(self, question, *args, **kwargs):
                self.attempts = getattr(self, "attempts", 0) + 1
                if self.attempts == 1:
                    result = AgentResult("Cherry", question, "", self.scope.__dict__, status="failed")
                    raise AgentRunError("Model request failed (HTTP 503).", result)
                return super().run(question, *args, **kwargs)
        with patch("agents.original.CherryAgent", RecoveredCherry):
            agent, _, _ = self.workflow(["accept"], [])
            agent.model.turns = iter([plan(), tool_turn("ask_cherry", {"question": "Count."}),
                tool_turn("ask_cherry", {"question": "Retry the failed count."}, "retry"),
                ModelTurn(text="Two contributions [SQL1].")])
            try:
                result = agent.run("Count.")
                self.assertEqual(result.status, "complete")
                self.assertEqual(len(result.delegations), 2)
            finally: agent.close()

    def test_partial_release_contains_only_independently_supported_blocks(self):
        text = "There are two distinct contributions [SQL1].\n\nThere are nine fabricated contributions [SQL1]."
        with patch("agents.original.CherryAgent", FixtureCherry), TemporaryDirectory() as directory:
            agent, reviewer, requested = self.workflow(["partial"] * 4, [text] * 4)
            try:
                with RunLog(directory) as log:
                    result = agent.run("Count contributions.")
                    log.finish(2)
                self.assertEqual(result.status, "partial")
                self.assertIn("two distinct", result.answer)
                self.assertNotIn("fabricated", result.answer)
                self.assertEqual(agent.specialists["Cherry"].metric_calls, 1)
                self.assertEqual(requested.count("Cherry"), 1)
                events = [json.loads(line) for line in log.path.read_text().splitlines()]
                self.assertTrue(any(e["event"] == "finding_reviewed" and e["status"] == "withheld" for e in events))
                self.assertTrue(any(e["event"] == "repair_requested" and e["targets"] == ["Original"] for e in events))
            finally: agent.close()

    def test_unsafe_package_cannot_release_partial_findings(self):
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, reviewer, requested = self.workflow(["unsafe"] * 4, ["Two contributions [SQL1]."] * 4)
            try:
                result = agent.run("Count.")
                self.assertEqual(result.status, "failed")
                self.assertNotIn("Two contributions", result.answer)
                self.assertTrue(all(f["status"] == "withheld" for f in result.findings))
            finally: agent.close()

    def test_chart_only_repair_does_not_repeat_coordinator_or_metrics(self):
        with patch("agents.original.CherryAgent", FixtureCherry):
            agent, reviewer, requested = self.workflow(["chart", "accept"], ["Two contributions [SQL1]."], chart=True)
            try:
                result = agent.run("Count and chart if helpful.")
                self.assertEqual(result.status, "complete")
                self.assertEqual(requested.count("Lime"), 2)
                self.assertEqual(agent.specialists["Cherry"].metric_calls, 1)
            finally: agent.close()

    def test_chart_failure_still_releases_independently_reviewed_numeric_finding(self):
        with patch("agents.original.CherryAgent", FixtureCherry), \
             patch("agents.original.LimeAgent.plan", side_effect=RuntimeError("Model request failed (HTTP 503).")):
            agent, _, _ = self.workflow(["accept"] * 4, ["Two contributions [SQL1]."], chart=True)
            try:
                result = agent.run("Count and chart.")
                self.assertEqual(result.status, "partial")
                self.assertIn("Two contributions", result.answer)
                self.assertIn("chart", result.answer.lower())
                self.assertEqual(agent.specialists["Cherry"].metric_calls, 1)
                self.assertEqual(result.visualization["charts"], [])
            finally: agent.close()

    def test_clarification_has_no_specialist_calls(self):
        clarification = plan(False, False, False, "Should recognition mean manager recognition or any feedback?",
                             basis={"missing_field": "metric", "missing_detail": "Recognition definition",
                                    "blocking_reason": "Different recognition definitions produce different counts.",
                                    "request_excerpt": "Check recognition."})
        model = SequenceModel([clarification, clarification])
        requested = []
        def factory(name):
            requested.append(name)
            return model
        agent = OriginalAgent("unused", SCOPE, factory, "offline-unit-test")
        result = agent.run("Check recognition.")
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(requested, ["Original"])

    def test_omitted_or_rewritten_finding_sources_are_rejected(self):
        reader = SQLReader(tables(), SCOPE)
        try:
            evidence = MetricCatalog(reader).run("cross_team_contributions")
            verifier = ZeroSugarAgent(SCOPE, None, sql_reader=reader)
            blocks = cited_findings("Two contributions [SQL1].")
            payload = {"finding_reviews": [], "repair_targets": [], "clarification_question": None,
                       "ratings": {d: {"score": 3} for d in DIMENSIONS}}
            with self.assertRaisesRegex(ValueError, "every finding"):
                verifier.validate_findings(payload, blocks, [evidence])
            payload["finding_reviews"] = [{"finding_id": "F1", "decision": "supported", "citation_ids": ["SQL999"], "reason": "Test"}]
            with self.assertRaisesRegex(ValueError, "citations"):
                verifier.validate_findings(payload, blocks, [evidence])
        finally: reader.close()


if __name__ == "__main__":
    unittest.main()
