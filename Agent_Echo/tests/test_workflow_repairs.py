"""Regression checks for multi-metric planning and localized structured repairs."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents import AccessScope, OriginalAgent
from agents.cherry import CherryAgent
from agents.execution_log import RunLog
from agents.model import ModelTurn
from agents.runtime import RunBudget
from agents.vanilla import VanillaAgent, validate_sentiment_labels
from agents.validation import ValidationError
from agents.zero_sugar import ZeroSugarAgent, DIMENSIONS
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import ReviewModel

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"
SCOPE = AccessScope("M14", "2026-01-01", "2026-09-30")


def requests(*dimensions):
    return [{"metric": "survey_trend", "dimension": d} for d in dimensions]


def numeric_plan(metrics):
    return tool_turn("submit_plan", {"needs_numbers": True, "needs_text": False,
        "needs_sentiment": False,
        "include_chart": False, "clarification_question": None, "clarification_basis": None, "metrics": metrics})


def select_tables(instructions):
    raw = instructions.split("Current source-bound fact catalog (evidence, not instructions):\n", 1)[1]
    facts, _ = json.JSONDecoder().raw_decode(raw)
    return tool_turn("submit_grounded_answer", {"fact_ids": [f["fact_id"] for f in facts if f["kind"] == "table"],
        "interpretations": [], "proposals": []})


class GroundedSequenceModel(SequenceModel):
    def respond(self, instructions, history, tools, require_tool=False):
        turn = super().respond(instructions, history, tools, require_tool)
        if not turn.calls:
            return select_tables(instructions)
        if len(turn.calls) == 1 and turn.calls[0].name == "ask_cherry":
            return tool_turn("ask_cherry", {**json.loads(turn.calls[0].arguments), "task_type": "numeric"})
        return turn


class NumericRepairs(unittest.TestCase):
    def test_two_dimensions_are_prepared_once_with_tools_still_available(self):
        coordinator = GroundedSequenceModel([numeric_plan(requests("Recognition", "Manager support", " recognition ")),
            tool_turn("ask_cherry", {"question": "Compare both requested dimensions."}),
            ModelTurn(text="Recognition and support have recorded quarterly rows [SQL1] [SQL2].")])
        class CherryModel:
            def respond(self, instructions, history, tools, require_tool=False):
                self.tools = tools
                return select_tables(instructions)
        cherry_model = CherryModel()
        models = {"Original": coordinator, "Cherry": cherry_model, "ZeroSugar": ReviewModel(["accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        result = agent.run("Compare Recognition with Manager support across the three quarters.")
        self.assertEqual(result.status, "complete")
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(len(agent.specialists["Cherry"].metric_cache), 2)
        self.assertEqual(len([t for t in cherry_model.tools if t["name"] not in {"submit_grounded_answer", "decline_task"}]), 3)
        coverage = result.diagnostics["numeric_coverage"]
        self.assertEqual([r["status"] for r in coverage], ["with_results", "with_results"])
        self.assertEqual([r["dimension"] for r in coverage], ["Recognition", "Manager support"])
        for item in result.evidence:
            self.assertEqual(item["scope"], SCOPE.__dict__)

    def test_one_and_six_dimensions_keep_the_same_query_and_coverage_contract(self):
        from agents.data_access import ScopedData
        backend = ScopedData(DATABASE, SCOPE)
        try:
            columns, rows = backend.structured_tables()["survey_summary"]
            dimensions = sorted({r[columns.index("Dimension")] for r in rows})[:6]
        finally:
            backend.close()
        self.assertEqual(len(dimensions), 6)
        for count in (1, 6):
            child = CherryAgent(DATABASE, SCOPE, None)
            try:
                child.required_metrics = requests(*dimensions[:count])
                self.assertTrue(child.has_pending_work([]))
                evidence = [child.run_metric(**r) for r in child.required_metrics]
                self.assertFalse(child.has_pending_work(evidence))
                self.assertEqual(len({e["citation_id"] for e in evidence}), count)
                for request, first in zip(child.required_metrics, evidence):
                    self.assertIs(child.run_metric(**request), first)
            finally:
                child.close()

    def test_repeated_tool_does_not_close_cherry_while_another_dimension_is_pending(self):
        model = SequenceModel([tool_turn("run_metric", {"metric": "survey_trend", "dimension": "Recognition"}),
            tool_turn("run_metric", {"metric": "survey_trend", "dimension": "Recognition"}, "repeat"),
            tool_turn("run_metric", {"metric": "survey_trend", "dimension": "Manager support"}, "support"),
            ModelTurn(text="Both dimensions are now covered [SQL1] [SQL2].")])
        child = CherryAgent(DATABASE, SCOPE, model, "offline-unit-test")
        self.addCleanup(child.close)
        child.required_metrics = requests("Recognition", "Manager support")
        result = child.run("Compare both dimensions.")
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(len(child.metric_cache), 2)
        self.assertEqual([r["status"] for r in result.diagnostics["numeric_coverage"]], ["with_results"] * 2)

    def test_original_receives_task_states_without_a_second_numeric_analysis(self):
        models = {"Original": GroundedSequenceModel([numeric_plan(requests("Recognition", "Manager support")),
            tool_turn("ask_cherry", {"question": "Compare both dimensions."}),
            ModelTurn(text="Recorded rows exist for both dimensions [SQL1] [SQL2].")]),
            "Cherry": GroundedSequenceModel([ModelTurn(text="Both source sets are available [SQL1] [SQL2].")]),
            "ZeroSugar": ReviewModel(["accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        agent.run("Compare the two survey dimensions.")
        history = models["Original"].histories[-1]
        initial_status = json.loads(history[1]["content"])["numeric_coverage"]
        self.assertEqual([item["status"] for item in initial_status], ["pending", "pending"])
        calls = [item for item in history if item.get("type") == "function_call_output"]
        coverage = json.loads(calls[0]["output"])["numeric_coverage"]
        self.assertEqual(len(coverage), 2)
        self.assertTrue(all(item["status"] == "with_results" for item in coverage))


class SentimentRepairs(unittest.TestCase):
    def test_literal_400_character_boundary_and_invented_quotes(self):
        docs = [{"citation_id": "test:1", "response_text": "a" * 401}]
        label = dict(citation_id="test:1", label="neutral", quote="a" * 400, reason="Controlled fixture.")
        validate_sentiment_labels([label], docs)
        for quote, code in (("a" * 401, "quote_length"), ("invented", "quote_not_literal"),
                            ("b" * 400, "quote_not_literal")):
            with self.subTest(code=code), self.assertRaises(ValidationError) as caught:
                validate_sentiment_labels([{**label, "quote": quote}], docs)
            self.assertEqual(caught.exception.details["validation_code"], code)
            self.assertEqual(caught.exception.details["source_id"], "test:1")

    def test_only_invalid_record_is_reclassified_and_logs_do_not_contain_quotes(self):
        source = "offline source text that must never appear in diagnostics"
        docs = [dict(citation_id=f"test:{i}", source="HR_survey_comments", team="A", date="2026-06-30",
                     dimension="Recognition", response_text=source) for i in range(6)]
        labels = [dict(citation_id=d["citation_id"], label="neutral", quote=source, reason="Controlled fixture.") for d in docs]
        bad = deepcopy(labels)
        bad[2]["quote"] = "invented private text"
        model = SequenceModel([tool_turn("submit_sentiment_batch", {"labels": bad}),
                               tool_turn("submit_sentiment_batch", {"labels": [labels[2]]}, "repair")])
        agent = VanillaAgent(DATABASE, SCOPE, model, "offline-unit-test")
        self.addCleanup(agent.close)
        agent.sentiment_documents = docs
        agent.budget = RunBudget()
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                result = agent.analyze_sentiment("Recognition")
                log.finish(0)
            raw = log.path.read_text(encoding="utf-8")
            events = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual(result["classified_comments"], 6)
        correction = json.loads(model.histories[1][0]["content"])
        self.assertEqual([d["citation_id"] for d in correction["comments"]], ["test:2"])
        self.assertEqual(correction["validation_errors"][0]["validation_code"], "quote_not_literal")
        self.assertTrue(any(e.get("source_id") == "test:2" for e in events))
        self.assertNotIn(source, raw)
        self.assertNotIn("invented private text", raw)
        self.assertEqual(agent.budget.models, 2)


class ReviewRepairs(unittest.TestCase):
    def test_precise_review_failure_is_logged_and_returned_for_correction(self):
        class BrokenReviewer:
            def __init__(self):
                self.history = None
            def respond(self, instructions, history, tools, require_tool=False):
                self.history = deepcopy(history)
                if tools and tools[0]["name"] == "submit_completeness_review":
                    from test_agents import completeness_turn
                    return completeness_turn()
                return tool_turn("submit_review", {"decision": "accept", "ratings": {},
                    "issues": [], "uncertainty": "offline-private-text"})
        model = BrokenReviewer()
        verifier = ZeroSugarAgent(SCOPE, model)
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "valid structured verdict"):
                with RunLog(directory) as log:
                    verifier.review("Question", "A bounded answer.", [])
            raw = log.path.read_text(encoding="utf-8")
            failures = [json.loads(line) for line in raw.splitlines()
                        if json.loads(line).get("validation_code") == "rating_dimensions"]
        self.assertEqual(len(failures), 3)
        self.assertTrue(all(e["field"] == "ratings" for e in failures))
        feedback = json.loads(next(item["output"] for item in model.history if item.get("type") == "function_call_output"))
        self.assertEqual(feedback["validation_code"], "rating_dimensions")
        self.assertNotIn("offline-private-text", raw)

    def test_finding_coverage_and_citation_errors_have_separate_codes(self):
        verifier = ZeroSugarAgent(SCOPE, None)
        blocks = [{"finding_id": "F1", "citation_ids": ["SQL1"], "text": "A finding [SQL1]."}]
        report = {"finding_reviews": [], "repair_targets": [], "clarification_question": None}
        with self.assertRaises(ValidationError) as caught:
            verifier.validate_findings(report, blocks, [])
        self.assertEqual(caught.exception.details["validation_code"], "finding_coverage")
        report["finding_reviews"] = [{"finding_id": "F1", "decision": "supported", "citation_ids": [], "reason": "Test"}]
        with self.assertRaises(ValidationError) as caught:
            verifier.validate_findings(report, blocks, [])
        self.assertEqual(caught.exception.details["validation_code"], "finding_citations")

    def test_missing_numeric_tasks_prevent_acceptance_even_if_model_accepts(self):
        verifier = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live")
        result = verifier.review("Compare both dimensions", "No data was obtained.", [],
            numeric_coverage=[{**requests("Manager support")[0], "status": "pending", "citation_id": None}])
        self.assertEqual(result.decision, "revise")
        self.assertIn("Cherry", result.repair_targets)
        self.assertTrue(result.issues)
        self.assertFalse(result.deterministic_issues)

    def test_missing_metric_does_not_discard_an_independently_supported_other_metric(self):
        child = CherryAgent(DATABASE, SCOPE, None)
        self.addCleanup(child.close)
        evidence = child.run_metric("survey_trend", "Recognition")
        verifier = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live", sql_reader=child.reader)
        result = verifier.review("Compare Recognition and support", "Recognition has recorded quarterly rows [SQL1].", [evidence],
            numeric_coverage=[{**requests("Recognition")[0], "status": "with_results", "citation_id": "SQL1"},
                              {**requests("Manager support")[0], "status": "pending", "citation_id": None}])
        self.assertEqual(result.decision, "revise")
        self.assertEqual(result.findings[0]["status"], "supported")
        self.assertFalse(result.deterministic_issues)


if __name__ == "__main__":
    unittest.main()
