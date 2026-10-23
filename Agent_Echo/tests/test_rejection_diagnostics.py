"""Rejected-answer diagnostics: precise conditions, minimized retention, no live API."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents import AccessScope, OriginalAgent
from agents.cherry import CherryAgent
from agents.execution_log import RunLog, error_summary
from agents.grounding import FactCatalog, render_answer
from agents.model import ModelTurn, ToolCall
from agents.runtime import AgentRunError
from agents.validation import ValidationError, rejection_diagnostic, repair_feedback
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import ReviewModel
from test_workflow_repairs import GroundedSequenceModel, numeric_plan, requests

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"
SCOPE = AccessScope("M14", "2026-01-01", "2026-09-30")


def payload(ids=(), proposals=(), interpretations=()):
    return {"fact_ids": list(ids), "interpretations": list(interpretations), "proposals": list(proposals)}


def proposal(text):
    return {"text": text, "citation_ids": ["SQL1"], "quote": None}


class RejectionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.child = CherryAgent(DATABASE, SCOPE, None, "live")
        self.addCleanup(self.child.close)
        self.evidence = [self.child.run_metric("survey_trend", "Recognition")]
        self.catalog = FactCatalog(self.evidence, SCOPE.__dict__)
        self.good = payload([next(iter(self.catalog.facts))])

    def caught(self, data, role="Original", catalog=None):
        with self.assertRaises(ValidationError) as caught:
            # Preserve rejection checks for the historical v2 replay contract.
            render_answer(data, catalog or self.catalog, role, "source-facts-v2")
        return caught.exception

    def test_fact_rejections_distinguish_type_count_item_type_and_unknown_id(self):
        for chosen, code, index in (("not a list", "fact_ids_type", None),
                                    ([next(iter(self.catalog.facts))] * 25, "fact_ids_count", None),
                                    ([False], "fact_id_type", 0),
                                    (["FACT_000000000000"], "fact_id_unknown", 0)):
            with self.subTest(code=code):
                error = self.caught({**payload(), "fact_ids": chosen})
                self.assertEqual(error.details["validation_code"], code)
                self.assertEqual(error.details.get("item_index"), index)
        error = self.caught(payload(["FACT_000000000000"]))
        item = rejection_diagnostic(error, "Original", "submit_grounded_answer", 1, 1)
        self.assertEqual(item["detail"]["safe_fragment"], "FACT_000000000000")
        self.assertNotIn("safe_fragment", error_summary(error))

    def test_quarter_reference_is_allowed_but_numeric_target_is_rejected(self):
        text, _ = render_answer(payload(self.good["fact_ids"], proposals=[proposal("Recheck the survey in Q4.")]), self.catalog, "Original")
        self.assertIn("Q4", text)
        error = self.caught(payload(self.good["fact_ids"], proposals=[proposal("Recheck Q4 with a target of 99 percent.")]))
        self.assertEqual(error.details["validation_code"], "numeric_proposal")

    def test_sensitive_proposal_content_is_not_added_to_logs_or_local_diagnostic(self):
        secret = "sk-" + "fakecredential" * 4
        private = "Example Person, private@example.invalid, +1 202 555 0198, confidential health detail"
        text = "Review Q4 for " + private + " using " + secret
        error = self.caught(payload(self.good["fact_ids"], proposals=[proposal(text)]))
        item = rejection_diagnostic(error, "Original", "submit_grounded_answer", 1, 1)
        serialized = json.dumps(item)
        for value in (secret, private, "Example Person", "private@example.invalid", "confidential health detail"):
            self.assertNotIn(value, serialized)
        self.assertNotIn("safe_fragment", item["detail"])
        self.assertTrue(item["detail"]["content_omitted"])
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                from agents.execution_log import record
                record("structured_response_repair", agent="Original", **error_summary(error))
                log.finish(0)
            raw = log.path.read_text(encoding="utf-8")
        self.assertNotIn(secret, raw)
        self.assertNotIn("Q4", raw)
        self.assertNotIn("private@example.invalid", raw)
        self.assertIn("numeric_proposal", raw)

    def test_arbitrary_invalid_id_text_is_omitted_even_in_local_diagnostic(self):
        private_id = "private@example.invalid " + "sk-" + "fakecredential" * 4
        error = self.caught(payload([private_id]))
        item = rejection_diagnostic(error, "Cherry", "submit_grounded_answer", 1, 1)
        self.assertNotIn(private_id, json.dumps(item))
        self.assertEqual(item["detail"]["value_length"], len(private_id))
        self.assertTrue(item["detail"]["content_omitted"])
        self.assertNotIn("safe_fragment", item["detail"])

    def test_numeric_values_are_omitted_while_rule_and_position_are_retained(self):
        text = "Consider an allowance of 987654321 for Example Person."
        error = self.caught(payload(self.good["fact_ids"], proposals=[proposal(text)]))
        item = rejection_diagnostic(error, "Original", "submit_grounded_answer", 1, 1)
        self.assertEqual(item["detail"]["match_start"], text.index("9"))
        self.assertNotIn("987654321", json.dumps(item))
        self.assertNotIn("Example Person", json.dumps(item))
        self.assertNotIn("safe_fragment", item["detail"])

    def test_private_details_are_separate_from_repair_and_log_metadata(self):
        error = ValidationError("controlled", "proposals[0].text", "Controlled application message.",
                                item_index=0, unexpected_text="private@example.invalid",
                                local_details={"safe_fragment": "private@example.invalid", "raw_text": "Secret text"})
        logged = error_summary(error)
        self.assertEqual(logged["item_index"], 0)
        self.assertNotIn("unexpected_text", logged)
        self.assertNotIn("local_details", repair_feedback(error))
        item = rejection_diagnostic(error, "Original", "submit_grounded_answer", 1, 1)
        self.assertNotIn("private@example.invalid", json.dumps(item))
        self.assertNotIn("Secret text", json.dumps(item))

    def test_cherry_role_violation_reports_expected_and_actual_count_without_text(self):
        data = payload(self.good["fact_ids"], interpretations=[{"private": "Example Person"}])
        error = self.caught(data, "Cherry")
        item = rejection_diagnostic(error, "Cherry", "submit_grounded_answer", 1, 1)
        self.assertEqual((item["expected_count"], item["actual_count"]), (0, 1))
        self.assertEqual(item["validation_code"], "narrative_role")
        self.assertNotIn("Example Person", json.dumps(item))

    def test_quote_failures_distinguish_source_type_length_and_literal_match(self):
        catalog = FactCatalog([{"citation_id": "CMT1", "text": "A controlled source comment."}], SCOPE.__dict__)
        for quote, code in ((None, "interpretation_quote_type"), ("x" * 401, "interpretation_quote_length"),
                            ("A fabricated private excerpt", "interpretation_quote_not_literal")):
            with self.subTest(code=code):
                data = payload(interpretations=[{"text": "This suggests uncertainty.", "citation_ids": ["CMT1"], "quote": quote}])
                error = self.caught(data, "Vanilla", catalog)
                item = rejection_diagnostic(error, "Vanilla", "submit_grounded_answer", 1, 1)
                self.assertEqual(item["validation_code"], code)
                self.assertEqual(item["field"], "interpretations[0].quote")
                self.assertNotIn("fabricated private excerpt", json.dumps(item))
        data = payload(interpretations=[{"text": "This suggests uncertainty.", "citation_ids": ["SQL1"], "quote": "x"}])
        self.assertEqual(self.caught(data).details["validation_code"], "interpretation_source_not_text")

    def test_success_preserves_the_rejected_attempt_and_its_later_correction(self):
        self.child.model = SequenceModel([tool_turn("submit_grounded_answer", payload(["FACT_000000000000"])),
                                          tool_turn("submit_grounded_answer", self.good)])
        result = self.child.run("Show Recognition.", initial_evidence=self.evidence)
        entries = result.diagnostics["rejected_attempts"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["resolution"], "accepted_source_submission")
        self.assertEqual(entries[0]["accepted_model_turn"], 2)
        self.assertNotIn("FACT_000000000000", result.answer)
        self.assertNotIn("rejected_attempts", json.dumps(result.claims))
        # Confirm the exact object saved by the CLI retains the diagnosis after JSON serialization.
        from dataclasses import asdict
        serialized = json.loads(json.dumps(asdict(result)))
        self.assertEqual(serialized["diagnostics"]["rejected_attempts"], entries)
        self.assertEqual(len(self.child.model.histories), 2)

    def test_exhausted_attempts_preserve_unresolved_diagnoses_without_releasing_them(self):
        turn = tool_turn("submit_grounded_answer", payload(["FACT_000000000000"]))
        self.child.model = SequenceModel([turn] * 7)
        with self.assertRaises(AgentRunError) as caught:
            self.child.run("Show Recognition.", initial_evidence=self.evidence)
        result = caught.exception.result
        self.assertEqual(len(result.diagnostics["rejected_attempts"]), 7)
        self.assertTrue(all(e["resolution"] == "unresolved" for e in result.diagnostics["rejected_attempts"]))
        self.assertEqual(result.answer, "")
        self.assertEqual(result.claims, [])

    def test_freeform_rejection_retains_diagnosis_but_not_raw_prose(self):
        private = "Private medical note about Example Person."
        self.child.model = SequenceModel([ModelTurn(text=private), tool_turn("submit_grounded_answer", self.good)])
        result = self.child.run("Show Recognition.", initial_evidence=self.evidence)
        self.assertEqual(result.diagnostics["rejected_attempts"][0]["validation_code"], "grounded_answer_required")
        self.assertNotIn(private, json.dumps(result.diagnostics))
        self.assertNotIn("last_unverified_text", result.diagnostics)

    def test_malformed_json_does_not_persist_provider_text_or_exception_message(self):
        raw = '{"private@example.invalid": "' + "sk-" + "fakecredential" * 4
        turn = ModelTurn(calls=[ToolCall("test", "submit_grounded_answer", raw)])
        self.child.model = SequenceModel([turn, tool_turn("submit_grounded_answer", self.good)])
        result = self.child.run("Show Recognition.", initial_evidence=self.evidence)
        item = result.diagnostics["rejected_attempts"][0]
        self.assertEqual(item["validation_code"], "invalid_json")
        self.assertIn("line", item)
        self.assertNotIn("private@example.invalid", json.dumps(item))
        self.assertNotIn("fakecredential", json.dumps(item))

    def test_diagnostics_are_reset_for_a_new_standalone_run(self):
        bad = tool_turn("submit_grounded_answer", payload(["FACT_000000000000"]))
        good = tool_turn("submit_grounded_answer", self.good)
        self.child.model = SequenceModel([bad, good, deepcopy(good)])
        first = self.child.run("Show Recognition.", initial_evidence=self.evidence)
        second = self.child.run("Show Recognition again.", initial_evidence=self.evidence)
        self.assertEqual(len(first.diagnostics["rejected_attempts"]), 1)
        self.assertEqual(second.diagnostics["rejected_attempts"], [])

    def test_local_history_is_bounded_and_reports_omissions(self):
        self.child.model = SequenceModel([tool_turn("submit_grounded_answer", payload(["FACT_000000000000"])),
                                          tool_turn("submit_grounded_answer", self.good)])
        prior = {"rejected_attempts": [{"status": "rejected_unverified", "resolution": "unresolved"} for _ in range(16)]}
        result = self.child.run("Show Recognition.", initial_evidence=self.evidence, diagnostics=prior)
        self.assertEqual(len(result.diagnostics["rejected_attempts"]), 16)
        self.assertEqual(result.diagnostics["rejected_attempts_omitted"], 1)

    def test_original_preserves_rejections_across_independent_review_repair_rounds(self):
        bad = tool_turn("submit_grounded_answer", payload(proposals=[proposal("Recheck the survey in Q4.")]))
        coordinator = GroundedSequenceModel([numeric_plan(requests("Recognition")),
            tool_turn("ask_cherry", {"question": "Show Recognition.", "task_type": "numeric"}), bad,
            ModelTurn(text="Select the source table."), bad, ModelTurn(text="Select the source table.")])
        cherry = GroundedSequenceModel([tool_turn("submit_grounded_answer", payload(["FACT_000000000000"])),
                                       ModelTurn(text="Select the source table.")])
        models = {"Original": coordinator, "Cherry": cherry, "ZeroSugar": ReviewModel(["revise", "accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        result = agent.run("Show the Recognition survey trend.")
        self.assertEqual(result.status, "complete")
        entries = result.diagnostics["rejected_attempts"]
        self.assertEqual([e["rejection_index"] for e in entries], [1, 2])
        self.assertTrue(all(e["resolution"] == "accepted_source_submission" for e in entries))
        child_entries = result.delegations[0]["diagnostics"]["rejected_attempts"]
        self.assertEqual(len(child_entries), 1)
        self.assertEqual(child_entries[0]["agent"], "Cherry")
        self.assertNotIn("Q4", result.answer)
        # Six coordinator calls are the scripted plan/delegation/two rejected+accepted pairs, no diagnostic calls.
        self.assertEqual(len(coordinator.histories), 6)


if __name__ == "__main__":
    unittest.main()
