"""Source-bound output regressions, including errors observed in the Luna run."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agents import AccessScope, OriginalAgent
from agents.cherry import CherryAgent
from agents.grounding import FactCatalog, render_answer, audit_claims
from agents.model import ModelTurn
from agents.runtime import AgentRunError
from agents.validation import ValidationError
from agents.zero_sugar import ZeroSugarAgent
from test_agents import SequenceModel, tool_turn
from test_flow_improvements import ReviewModel
from test_workflow_repairs import GroundedSequenceModel, numeric_plan, requests
from audit_grounding import audit_artifact

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"
SCOPE = AccessScope("M14", "2026-01-01", "2026-09-30")


class GroundedClaimTests(unittest.TestCase):
    def setUp(self):
        self.child = CherryAgent(DATABASE, SCOPE, None)
        self.addCleanup(self.child.close)
        self.evidence = [self.child.run_metric("survey_trend", d) for d in ("Recognition", "Manager support")]
        self.catalog = FactCatalog(self.evidence, SCOPE.__dict__)

    def payload(self, ids=(), interpretations=(), proposals=()):
        return {"fact_ids": list(ids), "interpretations": list(interpretations), "proposals": list(proposals)}

    def test_support_decline_is_computed_not_generated_by_model(self):
        matches = [f for f in self.catalog.facts.values() if f["kind"] == "calculated"
                   and "Manager support" in f["text"] and f["operation"].get("type") == "difference"
                   and f["operation"].get("start") == "2026-03-31"
                   and f["operation"].get("end") == "2026-06-30"
                   and f["operation"].get("column") == "Favorable_Percent"]
        self.assertEqual(len(matches), 1)
        fact = matches[0]
        self.assertEqual(fact["operation"]["delta"], "-6.32")
        text, claims = render_answer(self.payload([fact["fact_id"]]), self.catalog, "Original")
        self.assertIn("decreased by 6.32 percentage points", text)
        self.assertEqual(claims[0]["scope"], SCOPE.__dict__)

    def test_all_period_comparison_cannot_be_rephrased_as_always_above(self):
        facts = [f for f in self.catalog.facts.values() if f["operation"].get("type") == "comparison_coverage"
                 and f["operation"].get("column") == "Mean_Score"]
        self.assertEqual(facts[0]["operation"]["counts"], {"higher": 1, "lower": 2, "equal": 0})
        self.assertIn("higher than Recognition on 1 dates, lower on 2", facts[0]["text"])

    def test_six_dimensions_across_eight_quarters_fit_the_bounded_catalog(self):
        scope = AccessScope("M14", "2024-10-01", "2026-09-30")
        child = CherryAgent(DATABASE, scope, None)
        try:
            dimensions = child.reader.describe()["survey_dimensions"][:6]
            evidence = [child.run_metric("survey_trend", d) for d in dimensions]
            catalog = FactCatalog(evidence, scope.__dict__)
            self.assertTrue(catalog.facts)
            self.assertLessEqual(len(catalog.facts), 1024)
            self.assertEqual(len(dimensions), 6)
        finally:
            child.close()

    def test_table_and_sources_are_one_explicit_claim(self):
        key = next(k for k,f in self.catalog.facts.items() if f["kind"] == "table")
        text, claims = render_answer(self.payload([key]), self.catalog, "Original")
        self.assertIn("| Team | Survey_Date |", text)
        self.assertEqual(claims[0]["citation_ids"], ["SQL1"])
        self.assertIn("[SQL1]", claims[0]["text"])
        self.assertEqual(len(claims), 2)  # table + explicit source limitation

    def test_invented_ids_numbers_and_factual_sql_paraphrases_are_rejected(self):
        with self.assertRaises(ValidationError):
            render_answer(self.payload(["FACT_invented"]), self.catalog, "Original")
        for text in ("Support rose by 9 points.", "Support stayed higher every quarter.", "Support improved."):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                render_answer(self.payload(interpretations=[{"text": text, "citation_ids": ["SQL2"], "quote": "invented"}]),
                              self.catalog, "Original")

    def test_tampered_calculated_claim_is_rejected_even_when_reviewer_accepts(self):
        key = next(k for k,f in self.catalog.facts.items() if f["kind"] == "calculated")
        payload = self.payload([key])
        text, claims = render_answer(payload, self.catalog, "Original")
        claims[0]["text"] = "Manager support increased by 9 points [SQL2]."
        bad_text = "\n\n".join(c["text"] for c in claims)
        grounding = {"version": "source-facts-v2", "role": "Original", "payload": payload}
        verifier = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live", sql_reader=self.child.reader)
        result = verifier.review("Compare dimensions", bad_text, self.evidence, claims=claims, grounding=grounding)
        self.assertEqual(result.decision, "revise")
        self.assertTrue(result.deterministic_issues)

    def test_wrong_source_values_cannot_pass_merely_by_rendering_them_consistently(self):
        evidence = deepcopy(self.evidence)
        evidence[0]["rows"][0]["Mean_Score"] = 9.99
        catalog = FactCatalog(evidence, SCOPE.__dict__)
        key = next(k for k,f in catalog.facts.items() if f["kind"] == "table")
        payload = self.payload([key])
        text, claims = render_answer(payload, catalog, "Original")
        verifier = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live", sql_reader=self.child.reader)
        result = verifier.review("Review numeric evidence", text, evidence, claims=claims,
            grounding={"version":"source-facts-v2","role":"Original","payload":payload})
        self.assertEqual(result.decision, "revise")
        self.assertTrue(any("replay" in issue for issue in result.deterministic_issues))

    def test_free_form_cherry_answers_cannot_bypass_grounding(self):
        self.child.model = SequenceModel([ModelTurn(text="Support improved by 9 points [SQL2].")] * 7)
        with self.assertRaises(AgentRunError):
            self.child.run("Compare both dimensions", initial_evidence=self.evidence)

    def test_literal_text_does_not_mark_interpretation_as_validated(self):
        source = {"citation_id": "CMT1", "text": "My manager helps, but my extra work is overlooked.",
                  "team": "Data Platforms", "date": "2026-06-30", "anonymous": True}
        catalog = FactCatalog([source], SCOPE.__dict__)
        payload = self.payload(interpretations=[{"text": "This suggests mixed experiences.",
            "citation_ids": ["CMT1"], "quote": "My manager helps, but my extra work is overlooked."}])
        text, claims = render_answer(payload, catalog, "Vanilla")
        self.assertIn("Provisional interpretation", text)
        self.assertEqual(claims[0]["validation"], "provisional_semantics")
        self.assertEqual(audit_claims(claims, text, catalog,
            {"version": "source-facts-v2", "role": "Vanilla", "payload": payload}), [])

    def test_fake_quote_and_numeric_text_prevalence_are_rejected(self):
        catalog = FactCatalog([{"citation_id": "CMT1", "text": "Helpful manager."}], SCOPE.__dict__)
        for text,quote in (("Support seems positive.","invented"), ("Most people are positive: 80%.", "Helpful")):
            with self.assertRaises(ValidationError):
                render_answer(self.payload(interpretations=[{"text":text,"citation_ids":["CMT1"],"quote":quote}]), catalog, "Vanilla", "source-facts-v2")

    def test_available_facts_cannot_be_recast_as_absent_data_by_empty_selection(self):
        with self.assertRaises(ValidationError) as caught:
            render_answer(self.payload(), self.catalog, "Original")
        self.assertEqual(caught.exception.details["validation_code"], "answer_omitted_facts")

    def test_unknown_scope_and_truncated_rows_are_not_renderable_facts(self):
        bad = deepcopy(self.evidence)
        bad[0]["scope"]["manager_id"] = "M15"
        with self.assertRaises(ValidationError):
            FactCatalog(bad, SCOPE.__dict__)
        truncated = deepcopy(self.evidence[0]); truncated["truncated"] = True
        self.assertEqual(FactCatalog([truncated], SCOPE.__dict__).facts, {})

    def test_empty_rows_remain_a_cited_limitation_not_a_zero_or_absence_claim(self):
        source = deepcopy(self.evidence[0]); source["rows"] = []
        catalog = FactCatalog([source], SCOPE.__dict__)
        text, claims = render_answer(self.payload(), catalog, "Original")
        self.assertIn("No source-grounded claims", text)
        self.assertIn("[SQL1]", text)
        self.assertEqual(claims[0]["kind"], "limitation")

    def test_vanilla_cannot_adopt_cherry_sql_facts_or_invent_numeric_proposals(self):
        key = next(iter(self.catalog.facts))
        with self.assertRaises(ValidationError):
            render_answer(self.payload([key]), self.catalog, "Vanilla")
        with self.assertRaises(ValidationError):
            render_answer(self.payload(proposals=[{"text":"Aim for 99% support.","citation_ids":["SQL2"],"quote":None}]), self.catalog, "Original", "source-facts-v2")

    def test_changed_table_cell_is_detected_by_independent_reconstruction(self):
        key = next(k for k,f in self.catalog.facts.items() if f["kind"] == "table")
        payload = self.payload([key])
        text, claims = render_answer(payload, self.catalog, "Original")
        claims[0]["text"] = claims[0]["text"].replace("3.53", "9.99")
        altered = "\n\n".join(c["text"] for c in claims)
        self.assertTrue(audit_claims(claims, altered, self.catalog,
            {"version":"source-facts-v2","role":"Original","payload":payload}))

    def test_conflicting_source_rows_are_rejected_instead_of_chosen_by_model(self):
        bad = deepcopy(self.evidence[0]); bad["citation_id"] = "SQL3"; bad["rows"][0]["Mean_Score"] = 1.0
        with self.assertRaises(ValidationError):
            FactCatalog([*self.evidence, bad], SCOPE.__dict__)

    def test_exploratory_sql_is_not_described_as_validated_metric(self):
        source = self.child.reader.execute("SELECT COUNT(*) AS Recorded_Rows FROM survey_summary")
        catalog = FactCatalog([source], SCOPE.__dict__)
        self.assertTrue(all("require independent review" in f["query_semantics"] for f in catalog.facts.values()))

    def test_old_artifact_audit_does_not_claim_semantic_accuracy_or_call_a_model(self):
        artifact = {"agent":"Cherry","question":"Compare both dimensions","scope":SCOPE.__dict__,
                    "mode":"live","status":"unverified","answer":"Support always stayed higher [SQL2].",
                    "evidence":self.evidence}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "old.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            packet = audit_artifact(path)
        self.assertEqual(packet["api_calls"], 0)
        self.assertEqual(packet["semantic_quality"], "human_review_required")
        self.assertIn("Manager support", packet["available_survey_dimensions"])
        self.assertTrue(any("Legacy narrative" in i for i in packet["runs"][0]["provenance_issues"]))
        self.assertIn("no preserved classification labels", packet["classification_quality"])

    def test_original_rejects_wrong_role_task_type_before_running_query(self):
        agent = OriginalAgent(DATABASE, SCOPE, lambda name: None, "live")
        self.addCleanup(agent.close)
        with self.assertRaisesRegex(ValueError, "task_type"):
            agent.delegate("Cherry", "Classify comments", "sentiment")
        self.assertEqual(agent.specialists, {})

    def test_live_workflow_reviews_explicit_claims_without_splitting_table_from_citations(self):
        models = {"Original": GroundedSequenceModel([numeric_plan(requests("Recognition", "Manager support")),
            tool_turn("ask_cherry", {"question": "Compare both dimensions", "task_type": "numeric"}),
            ModelTurn(text="Select the two source tables.")]),
            "Cherry": GroundedSequenceModel([ModelTurn(text="Select the two source tables.")]),
            "ZeroSugar": ReviewModel(["accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        result = agent.run("Compare Recognition and manager support with a table.")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.grounding["version"], "source-facts-v4")
        self.assertEqual(len(result.claims), len(result.findings))
        self.assertTrue(all(c["status"] == "supported" for c in result.findings))


if __name__ == "__main__":
    unittest.main()
