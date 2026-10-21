"""Focused regressions for retained evidence, precise repairs and failure stages."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from agents import AccessScope, OriginalAgent
from agents.cherry import CherryAgent
from agents.execution_log import RunLog
from agents.grounding import FactCatalog, render_answer
from agents.lime import LimeAgent
from agents.model import ChatModel
from agents.runtime import Specialist
from agents.validation import ValidationError, repair_feedback, rejection_diagnostic
from test_agents import tool_turn
from test_flow_improvements import ReviewModel
from test_sentiment_workflow_repairs import ActionModel, final_selection, labels_for, sentiment_plan
from test_workflow_repairs import numeric_plan, requests
from agents.data_access import ScopedData

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"
SCOPE = AccessScope("M14", "2026-07-01", "2026-09-30")
SOURCE = {"citation_id": "survey:CMT1", "text": "My work was appreciated.", "scope": SCOPE.__dict__}


def answer(text="Recognition was appreciated in Q3 2026.", refs=None):
    return {"fact_ids": [], "interpretations": [{"text": text,
        "citation_ids": [SOURCE["citation_id"]] if refs is None else refs, "quote": SOURCE["text"]}], "proposals": []}


class RecoveryFeedbackTests(unittest.TestCase):
    def test_temporal_references_do_not_allow_analytic_quantities(self):
        catalog = FactCatalog([SOURCE], SCOPE.__dict__)
        for period in ("Q3", "Q3 2026", "2026-Q3", "2026-09-30"):
            rendered, _ = render_answer(answer("Recognition was appreciated during " + period + "."), catalog, "Vanilla")
            self.assertIn(period, rendered)
        for text in ("Q3 includes 13 comments.", "The majority appreciated recognition in Q3.",
                     "Recognition changed on 2026-02-30."):
            with self.assertRaises(ValidationError) as caught:
                render_answer(answer(text), catalog, "Vanilla")
            self.assertEqual(caught.exception.details["validation_code"], "numeric_interpretation")

    def test_source_error_identifies_position_without_persisting_bad_value(self):
        catalog = FactCatalog([SOURCE], SCOPE.__dict__)
        for refs, code in ((None, None), ([], "narrative_sources_empty"),
                           ("survey:CMT1", "narrative_sources_type"), ([False], "narrative_source_type"),
                           (["private@example.invalid"], "narrative_source_unknown")):
            if code is None:
                continue
            with self.subTest(code=code), self.assertRaises(ValidationError) as caught:
                render_answer(answer(refs=refs), catalog, "Vanilla")
            error = caught.exception
            self.assertEqual(error.details["validation_code"], code)
            self.assertIn("correction", repair_feedback(error))
            self.assertNotIn("private@example.invalid", json.dumps(rejection_diagnostic(error, "Vanilla", "submit_grounded_answer", 1, 1)))

    def test_repeated_rejection_reaches_next_call_with_prior_submission_and_sources(self):
        bad, good = answer(refs=[]), answer()
        model = ActionModel([tool_turn("submit_grounded_answer", deepcopy(bad)),
                             tool_turn("submit_grounded_answer", deepcopy(bad)), tool_turn("submit_grounded_answer", good)])
        agent = Specialist("Vanilla", "Use scoped sources.", model, SCOPE, [], {}, "live")
        agent.source_grounding = True
        result = agent.run("Interpret recognition.", initial_evidence=[SOURCE])
        feedback = [json.loads(h["output"]) for h in model.histories[-1] if h.get("type") == "function_call_output"]
        self.assertEqual(feedback[-1]["same_condition_attempts"], 2)
        self.assertEqual(feedback[-1]["field"], "interpretations[0].citation_ids")
        self.assertIn("Change the indicated field", feedback[-1]["correction"])
        self.assertIn(SOURCE["citation_id"], model.instructions[-1])
        self.assertTrue(all(e["resolution"] == "accepted_source_submission" for e in result.diagnostics["rejected_attempts"]))

    def workflow(self, specialist, reviewer=None):
        original = ActionModel([sentiment_plan() if specialist == "Vanilla" else numeric_plan(requests("Recognition")),
            tool_turn("ask_vanilla" if specialist == "Vanilla" else "ask_cherry",
                      {"question": "Obtain the requested Recognition evidence.", "task_type": "sentiment" if specialist == "Vanilla" else "numeric"}),
            final_selection])
        failure = RuntimeError("Model output token budget exhausted before completion.")
        if specialist == "Vanilla":
            backend = ScopedData(DATABASE, SCOPE)
            try:
                docs = sorted([d for d in backend.sentiment_documents() if d["dimension"] == "Recognition"], key=lambda d:d["citation_id"])
            finally:
                backend.close()
            child = ActionModel([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
                                 tool_turn("submit_sentiment_batch", {"labels": labels_for(docs)}), failure])
        else:
            child = ActionModel([failure])
        models = {"Original": original, specialist: child, "ZeroSugar": reviewer or ReviewModel(["accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        return agent.run("Review Recognition" + (" comment classification and examples." if specialist == "Vanilla" else " survey metrics."))

    def test_retained_cherry_and_vanilla_evidence_requires_completed_review(self):
        for role in ("Cherry", "Vanilla"):
            with self.subTest(role=role):
                result = self.workflow(role)
                self.assertEqual(result.status, "complete")
                self.assertEqual(result.verification["status"], "completed")
                self.assertEqual(result.diagnostics["recovered_specialists"], [role])
                child = result.delegations[0]
                self.assertEqual(child["status"], "failed")
                self.assertTrue(child["task_outcome"]["evidence_retained"])
                self.assertFalse(child["task_outcome"]["presentation_complete"])

    def test_failed_review_does_not_release_recovered_work(self):
        result = self.workflow("Cherry", ActionModel([RuntimeError("Model output token budget exhausted before completion.")]))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.verification["status"], "failed")
        self.assertEqual(result.failure["stage"], "verification")
        self.assertEqual(result.findings, [])

    def test_failed_planning_marks_review_as_not_run(self):
        model = ActionModel([RuntimeError("Model output token budget exhausted before completion.")])
        agent = OriginalAgent(DATABASE, SCOPE, lambda name: model, "live")
        self.addCleanup(agent.close)
        result = agent.run("Review Recognition.")
        self.assertEqual(result.verification["status"], "not_run")
        self.assertEqual(result.verification["drafts_checked"], 0)
        self.assertEqual(result.status, "failed")

    def test_lime_repairs_exact_source_field_and_keeps_diagnostics(self):
        cherry = CherryAgent(DATABASE, SCOPE, None, "live")
        self.addCleanup(cherry.close)
        source = cherry.run_metric("survey_trend", "Recognition")
        chart = {"kind": "bar", "title": "Recognition", "source_id": source["citation_id"],
                 "x": "Survey_Date", "y": "Mean_Score", "x_label": "Survey date", "y_label": "Mean score",
                 "series": None, "unit": "score points", "denominator": "Responses"}
        bad = {**chart, "source_id": "SQL404"}
        model = ActionModel([tool_turn("submit_visuals", {"charts": [bad], "reason": "Compare recorded scores."}),
                             tool_turn("submit_visuals", {"charts": [chart], "reason": "Compare recorded scores."})])
        result = LimeAgent(SCOPE, model, "live").plan("Chart Recognition.", "", [source])
        feedback = json.loads(model.histories[-1][-1]["output"])
        self.assertEqual(feedback["field"], "charts[0].source_id")
        self.assertEqual(result.diagnostics["rejected_attempts"][0]["resolution"], "accepted_visual_submission")

    def test_truncated_output_records_counters_without_response_content(self):
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=6000, total_tokens=6100,
                                completion_tokens_details=SimpleNamespace(reasoning_tokens=5900))
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="length")], usage=usage)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: response)))
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log, self.assertRaisesRegex(RuntimeError, "output token budget"):
                ChatModel(client, "fixture", max_output_tokens=6000).respond("", [], [])
            events = [json.loads(line) for line in log.path.read_text(encoding="utf-8").splitlines()]
        counts = next(e for e in events if e["event"] == "model_response_usage")
        self.assertEqual((counts["output_limit"], counts["output_tokens"], counts["reasoning_tokens"]), (6000, 6000, 5900))


if __name__ == "__main__":
    unittest.main()
