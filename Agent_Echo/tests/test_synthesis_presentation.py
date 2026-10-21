"""Focused source-contract and review regressions; scripted labels are not quality evidence."""

from copy import deepcopy
import json
import unittest
from types import SimpleNamespace

from agents import AccessScope
from agents.grounding import FactCatalog, render_answer, audit_claims, GROUNDING_VERSION
from agents.original import OriginalAgent, INSTRUCTIONS as ORIGINAL_INSTRUCTIONS
from agents.runtime import AgentResult
from agents.validation import ValidationError
from agents.zero_sugar import ZeroSugarAgent, DIMENSIONS
from test_agents import tool_turn
from test_sentiment_workflow_repairs import ActionModel

SCOPE = AccessScope("M14", "2026-07-01", "2026-09-30")
TEXTS = [{"citation_id": "survey:CMT1", "text": "Specific feedback helped me.", "scope": SCOPE.__dict__},
         {"citation_id": "survey:CMT2", "text": "Support is helpful but access is inconsistent.", "scope": SCOPE.__dict__}]


def payload(refs=None, quote=None):
    return {"fact_ids": [], "interpretations": [{"text": "The cited comments describe helpful support alongside inconsistent access.",
            "citation_ids": refs or [s["citation_id"] for s in TEXTS], "quote": quote}], "proposals": []}


def review_turn(instructions, history, decision="accept", issues=(), suggestions=(), finding_decision="supported"):
    context = json.loads(history[0]["content"])
    return tool_turn("submit_review", {"decision": decision,
        "ratings": {d: {"score": 3, "rationale": "Controlled fixture."} for d in DIMENSIONS},
        "issues": list(issues), "suggestions": list(suggestions), "uncertainty": "Scripted review, not measured semantic quality.",
        "finding_reviews": [{"finding_id": c["finding_id"], "decision": finding_decision,
            "citation_ids": c["citation_ids"], "reason": "Controlled fixture."} for c in context["findings"]],
        "repair_targets": ["Original"] if issues or decision == "revise" else [], "clarification_question": None})


class SynthesisPresentationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = FactCatalog(TEXTS, SCOPE.__dict__)

    def test_synthesis_cites_multiple_texts_and_is_reproducible(self):
        data = payload()
        text, claims = render_answer(data, self.catalog, "Original")
        self.assertEqual(claims[0]["citation_ids"], [s["citation_id"] for s in TEXTS])
        self.assertIsNone(claims[0]["quote"])
        self.assertIn("[survey:CMT1] [survey:CMT2]", text)
        self.assertEqual(audit_claims(claims, text, self.catalog,
            {"version": GROUNDING_VERSION, "role": "Original", "payload": data}), [])

    def test_individual_examples_still_require_literal_quotes(self):
        for quote, code in ((None, "interpretation_quote_type"), ("Fabricated excerpt.", "interpretation_quote_not_literal")):
            with self.subTest(code=code), self.assertRaises(ValidationError) as caught:
                render_answer(payload(["survey:CMT1"], quote), self.catalog, "Original")
            self.assertEqual(caught.exception.details["validation_code"], code)
        with self.assertRaises(ValidationError):
            render_answer(payload(["survey:CMT1", "survey:CMT1"]), self.catalog, "Original")

    def test_synthesis_cannot_use_unknown_or_numeric_only_sources_or_prevalence(self):
        numeric = {"citation_id": "SQL1", "producer": "Cherry", "rows": [{"Value": 5}], "scope": SCOPE.__dict__}
        catalog = FactCatalog(TEXTS + [numeric], SCOPE.__dict__)
        for data, code in ((payload(["survey:CMT1", "SQL404"]), "narrative_source_unknown"),
                           (payload(["survey:CMT1", "SQL1"]), "interpretation_source_not_text")):
            with self.subTest(code=code), self.assertRaises(ValidationError) as caught:
                render_answer(data, catalog, "Original")
            self.assertEqual(caught.exception.details["validation_code"], code)
        data = payload()
        data["interpretations"][0]["text"] = "The majority appreciate recognition."
        with self.assertRaises(ValidationError) as caught:
            render_answer(data, self.catalog, "Original")
        self.assertEqual(caught.exception.details["validation_code"], "numeric_interpretation")

    def test_exact_table_cells_are_not_repeated_and_legacy_format_still_replays(self):
        source = {"citation_id": "SQL1", "producer": "Cherry", "rows": [{"Team": "A", "Count": 13}], "scope": SCOPE.__dict__}
        catalog = FactCatalog([source], SCOPE.__dict__)
        data = {"fact_ids": list(catalog.facts), "interpretations": [], "proposals": []}
        current_text, current = render_answer(data, catalog, "Original")
        legacy_text, legacy = render_answer(data, catalog, "Original", "source-facts-v1")
        self.assertNotIn("observed", [c["kind"] for c in current])
        self.assertIn("observed", [c["kind"] for c in legacy])
        self.assertIn("13", current_text)
        self.assertEqual(audit_claims(legacy, legacy_text, catalog,
            {"version": "source-facts-v1", "role": "Original", "payload": data}), [])
        # Without a table, individual cells remain available.
        cell_ids = [k for k, fact in catalog.facts.items() if fact["kind"] == "observed"]
        _, cells = render_answer({**data, "fact_ids": cell_ids}, catalog, "Original")
        self.assertIn("observed", [c["kind"] for c in cells])

    def test_narrative_headings_are_not_repeated_and_questions_stay_direct(self):
        data = payload(["survey:CMT1"], TEXTS[0]["text"])
        data["interpretations"].append({"text": "This cited comment describes inconsistent access.",
            "citation_ids": ["survey:CMT2"], "quote": TEXTS[1]["text"]})
        data["proposals"] = [{"text": "What would make access more consistent?", "citation_ids": ["survey:CMT2"], "quote": None},
                             {"text": "Which feedback should we continue?", "citation_ids": ["survey:CMT1"], "quote": None}]
        text, _ = render_answer(data, self.catalog, "Original")
        self.assertEqual(text.count("Provisional interpretation:"), 1)
        self.assertEqual(text.count("Proposed actions / questions"), 1)
        self.assertIn("What would make access more consistent?", text)
        self.assertNotIn("Keep supported finding blocks unchanged", ORIGINAL_INSTRUCTIONS)
        # Old stored narratives retain their original prefixes and quote requirements.
        old_text, old_claims = render_answer(data, self.catalog, "Original", "source-facts-v1")
        self.assertEqual(old_text.count("Provisional interpretation for manager review:"), 2)
        self.assertEqual(audit_claims(old_claims, old_text, self.catalog,
            {"version": "source-facts-v1", "role": "Original", "payload": data}), [])

    def reviewed(self, response, evidence=None):
        data = payload()
        text, claims = render_answer(data, self.catalog, "Original")
        model = ActionModel([response])
        verifier = ZeroSugarAgent(SCOPE, model, "live", document_lookup={s["citation_id"]: s for s in TEXTS})
        return verifier.review("Summarize the cited perspectives.", text, evidence or TEXTS, claims=claims,
            grounding={"version": GROUNDING_VERSION, "role": "Original", "payload": data}), model, text

    def test_optional_suggestions_do_not_trigger_revision_and_review_sees_same_candidate(self):
        result, model, text = self.reviewed(lambda i, h: review_turn(i, h, suggestions=["Consider a shorter heading."]))
        self.assertEqual(result.decision, "accept")
        self.assertEqual(result.suggestions, ["Consider a shorter heading."])
        self.assertEqual(json.loads(model.histories[0][0]["content"])["candidate_answer"], text)

    def test_mandatory_issue_or_unsupported_meaning_still_requires_revision(self):
        for response in (lambda i, h: review_turn(i, h, issues=["A required team question is missing."]),
                         lambda i, h: review_turn(i, h, decision="revise", finding_decision="revise")):
            result, _, _ = self.reviewed(response)
            self.assertEqual(result.decision, "revise")
        changed = deepcopy(TEXTS)
        changed[0]["text"] = "Altered source."
        result, _, _ = self.reviewed(review_turn, changed)
        self.assertEqual(result.decision, "revise")
        self.assertTrue(result.deterministic_issues)

    def test_partial_release_retains_disclosure_when_first_section_block_is_withheld(self):
        candidate = AgentResult("Original", "Question", "", SCOPE.__dict__)
        verdict = SimpleNamespace(findings=[
            {"text": "Provisional interpretation: unsupported heading block.", "kind": "interpretation", "status": "withheld"},
            {"text": "The cited comment describes helpful feedback. [survey:CMT1]", "kind": "interpretation", "status": "supported"}],
            repair_targets=["Original"], deterministic_issues=[], ratings={"Safety / Appropriateness": {"score": 3}},
            clarification_question=None)
        result = OriginalAgent(None, SCOPE, lambda name: None, "live").incomplete(candidate, verdict)
        self.assertEqual(result.status, "partial")
        self.assertIn("Interpretations remain provisional", result.answer)
        self.assertNotIn("unsupported heading block", result.answer)


if __name__ == "__main__":
    unittest.main()
