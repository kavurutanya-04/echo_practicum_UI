"""Evidence-bound visuals, retrieval context and real-connection failure boundaries."""

from dataclasses import asdict
import csv
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from agents import AccessScope, VanillaAgent, LimeAgent, ZeroSugarAgent, OriginalAgent
from agents.connections import ModelRegistry
from agents.model import ConfigurationError, ModelTurn, ScriptedDemoModel
from agents.preflight import check_connections
from agents.lime import validate_visuals
from agents.vanilla import sentiment_summary, validate_sentiment_labels, SENTIMENT_LABELS
from agents.data_access import ScopedData
from agents.runtime import RunBudget
from test_agents import SequenceModel, tool_turn
from test_workflow import report
import run_agent

SCOPE = AccessScope("M14", "2026-07-01", "2026-09-30")
DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"


def evidence():
    return [{"citation_id": "SQL1", "producer": "Cherry", "sql": "SELECT Team, Survey_Date, Mean_Score, Responses FROM survey_summary",
        "scope": SCOPE.__dict__, "truncated": False, "rows": [
            {"Team": "A", "Survey_Date": "2026-07-01", "Mean_Score": 3.2, "Responses": 10},
            {"Team": "A", "Survey_Date": "2026-08-01", "Mean_Score": None, "Responses": 8},
            {"Team": "A", "Survey_Date": "2026-09-01", "Mean_Score": 3.7, "Responses": 12}]}]


def plan():
    return {"charts": [{"source_id": "SQL1", "kind": "line", "x": "Survey_Date", "y": "Mean_Score",
        "series": "Team", "denominator": "Responses", "title": "Recognition trend <synthetic>",
        "x_label": "Survey date", "y_label": "Mean recognition score", "unit": "Score (1-5)"}],
        "reason": "The question asks for the quarterly trend; missing values remain missing."}


class VisualizationTests(unittest.TestCase):
    def test_export_preserves_exact_rows_missing_values_provenance_and_escaping(self):
        model = SequenceModel([tool_turn("submit_visuals", plan())])
        result = LimeAgent(SCOPE, model, "offline-scripted-demo").plan("Show the trend.", "Trend [SQL1].", evidence())
        with TemporaryDirectory() as output:
            files = LimeAgent.export(asdict(result), evidence(), SCOPE, output)
            svg = Path(files[0]["svg"]).read_text(encoding="utf-8")
            ET.fromstring(svg)
            self.assertIn("&lt;synthetic&gt;", svg)
            self.assertIn("N/A", svg)
            # The line cannot bridge the null August value.
            self.assertEqual(svg.count("<polyline"), 2)
            with Path(files[0]["csv"]).open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["Mean_Score"] for row in rows], ["3.2", "", "3.7"])
            meta = json.loads(Path(files[0]["metadata"]).read_text())
            self.assertEqual(meta["scope"], SCOPE.__dict__)
            self.assertEqual(meta["source_sql"], evidence()[0]["sql"])
            self.assertEqual(meta["row_count"], 3)
            # A category comparison is rendered from the same SQL rows, without re-aggregation.
            bar = plan(); bar["charts"][0]["kind"] = "bar"
            validate_visuals(bar, evidence(), SCOPE)
            bar_files = LimeAgent.export(bar, evidence(), SCOPE, Path(output) / "bars")
            bar_svg = Path(bar_files[0]["svg"]).read_text(encoding="utf-8")
            ET.fromstring(bar_svg)
            self.assertIn('Mean_Score=3.2; Responses=10', bar_svg)
            self.assertIn('Mean_Score=3.7; Responses=12', bar_svg)
            self.assertIn("N/A", bar_svg)

    def test_rejects_unknown_sources_columns_truncation_and_foreign_scope(self):
        for mutation in ("source", "column", "truncated", "scope", "producer"):
            proposed, sources = plan(), evidence()
            if mutation == "source": proposed["charts"][0]["source_id"] = "survey:comment"
            if mutation == "column": proposed["charts"][0]["y"] = "invented"
            if mutation == "truncated": sources[0]["truncated"] = True
            if mutation == "scope": sources[0]["scope"] = AccessScope("M15").__dict__
            if mutation == "producer": sources[0]["producer"] = "Vanilla"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_visuals(proposed, sources, SCOPE)

    def test_rejects_duplicate_points_fake_numbers_nonfinite_values_and_missing_denominators(self):
        for mutation in ("duplicate", "string", "nan", "denominator", "zero_denominator", "invalid_date"):
            proposed, sources = plan(), evidence()
            if mutation == "duplicate": sources[0]["rows"].append(deepcopy(sources[0]["rows"][0]))
            if mutation == "string": sources[0]["rows"][0]["Mean_Score"] = "3.2"
            if mutation == "nan": sources[0]["rows"][0]["Mean_Score"] = float("nan")
            if mutation == "denominator": proposed["charts"][0]["denominator"] = None
            if mutation == "zero_denominator": sources[0]["rows"][0]["Responses"] = 0
            if mutation == "invalid_date": sources[0]["rows"][0]["Survey_Date"] = "2026-99-99"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_visuals(proposed, sources, SCOPE)

    def test_text_only_evidence_produces_no_chart_and_no_files(self):
        proposed = {"charts": [], "reason": "Only selected text examples exist; no indicator table."}
        model = SequenceModel([tool_turn("submit_visuals", proposed)])
        result = LimeAgent(SCOPE, model).plan("Explain themes.", "Limited context.", [
            {"citation_id": "survey:1", "text": "An anonymous comment", "anonymous": True}])
        self.assertEqual(json.loads(model.histories[0][0]["content"])["evidence"], [])
        with TemporaryDirectory() as output:
            self.assertEqual(LimeAgent.export(asdict(result), [], SCOPE, output), [])
            self.assertEqual(list(Path(output).iterdir()), [])

    def test_lime_repairs_invalid_plan_using_tool_feedback(self):
        invalid = plan(); invalid["charts"][0]["source_id"] = "SQL999"
        model = SequenceModel([tool_turn("submit_visuals", invalid), tool_turn("submit_visuals", plan())])
        result = LimeAgent(SCOPE, model).plan("Show trend.", "Trend [SQL1].", evidence())
        self.assertEqual(len(result.tool_trace), 2)
        self.assertIn("existing SQL", model.histories[1][-1]["output"])

    def test_verifier_forces_revision_for_bad_chart_even_if_model_accepts(self):
        invalid = plan(); invalid["charts"][0]["y"] = "invented"
        reviewer = ZeroSugarAgent(SCOPE, SequenceModel([tool_turn("submit_review", report())]),
                                 sql_reader=SimpleNamespace(execute=lambda sql: evidence()[0]))
        verdict = reviewer.review("Show trend.", "Trend [SQL1].", evidence(), invalid)
        self.assertEqual(verdict.decision, "revise")
        self.assertTrue(any("Invalid visualization" in item for item in verdict.deterministic_issues))


class RagAndConnectionTests(unittest.TestCase):
    def test_retrieved_text_is_in_the_next_generation_call_and_cited_in_output(self):
        agent = VanillaAgent(DATABASE, SCOPE, ScriptedDemoModel("Vanilla"), "offline-scripted-demo")
        first = agent.searcher.search("recognition", "HR_survey_comments", "Recognition", 2)
        self.assertTrue(first["passages"])
        citation = first["passages"][0]["citation_id"]
        model = SequenceModel([tool_turn("search_text", {"query": "recognition", "source": "HR_survey_comments",
            "dimension": "Recognition", "limit": 2}), ModelTurn(text=f"Selected example [{citation}].")])
        agent.model = model
        try:
            result = agent.run("Show recognition comments.")
            context = json.loads(model.histories[1][-1]["output"])
            self.assertEqual(context["passages"][0]["text"], first["passages"][0]["text"])
            self.assertTrue(result.rag["context_supplied_to_generator"])
            self.assertIn(citation, result.rag["cited_ids"])
            self.assertEqual(result.rag["retrieval_calls"][0]["metadata"]["returned_count"], 2)
            self.assertEqual(result.rag["generation_mode"], "offline-scripted-demo")
        finally:
            agent.close()

    def test_empty_retrieval_cannot_be_marked_as_context_supplied(self):
        model = SequenceModel([tool_turn("search_text", {"query": "zzzxxyynevermatch", "source": None,
            "dimension": None, "limit": 2}), ModelTurn(text="No matching context was found.")])
        agent = VanillaAgent(DATABASE, SCOPE, model, "offline-scripted-demo")
        try:
            result = agent.run("Find an unavailable topic.")
            self.assertFalse(result.rag["context_supplied_to_generator"])
            self.assertEqual(result.rag["retrieval_calls"][0]["returned_ids"], [])
        finally:
            agent.close()

    def test_live_cli_without_configuration_fails_and_does_not_write_demo_artifact(self):
        with TemporaryDirectory() as output, patch.dict("os.environ", {}, clear=True), \
             patch.object(ModelRegistry, "_local_value", return_value=""), \
             redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            target = Path(output) / "live.json"
            code = run_agent.main(["original", "--manager", "M14", "--profile", "google_test",
                                   "--question", "Review recognition.", "--output", str(target)])
            self.assertEqual(code, 1)
            self.assertFalse(target.exists())
            self.assertIn("no offline fallback", stdout.getvalue())
            self.assertIn("GOOGLE_API_KEY", stderr.getvalue())

    def test_real_connection_probe_requires_credentials_instead_of_running_fixture(self):
        with patch.dict("os.environ", {}, clear=True):
            registry = ModelRegistry(force_profile="google_test", env_file=None)
            with self.assertRaises(ConfigurationError):
                check_connections(registry, ["Lime"])
            self.assertEqual(registry.execution_summary()["generation_api_calls"], 0)


class SentimentTests(unittest.TestCase):
    def documents(self):
        responses = ["I feel appreciated.", "I feel overlooked.", "We meet on Mondays.",
                     "Helpful feedback, but little recognition.", "N/A", "I feel appreciated."]
        return [dict(citation_id=f"survey:{index}", record_id=str(index), source="HR_survey_comments",
                     team="A", date="2026-09-01", dimension="Recognition", anonymous=True,
                     question="How is recognition?", response_text=text) for index, text in enumerate(responses)]

    def labels(self):
        return [dict(citation_id=doc["citation_id"], label=label, quote=doc["response_text"], reason="Test fixture.")
                for doc, label in zip(self.documents(), [*SENTIMENT_LABELS, "positive"])]

    def agent(self, turns):
        agent = VanillaAgent(DATABASE, SCOPE, SequenceModel(turns), "offline-unit-test")
        agent.sentiment_documents = self.documents()
        self.addCleanup(agent.close)
        return agent

    def test_complete_population_preserves_duplicate_text_and_denominators(self):
        agent = self.agent([tool_turn("submit_sentiment_batch", {"labels": self.labels()})])
        summary = agent.analyze_sentiment("Recognition")
        self.assertEqual(summary["eligible_comments"], 6)
        self.assertEqual(summary["classified_comments"], 6)
        row = summary["rows"][0]
        self.assertEqual(row["positive_count"], 2)
        self.assertEqual(row["positive_percent"], 33.33)
        self.assertEqual(row["indeterminate_percent"], 16.67)
        self.assertEqual(sum(row[label + "_count"] for label in SENTIMENT_LABELS), 6)
        self.assertFalse(summary["human_validated"])
        self.assertEqual(len(agent.sentiment_reports["SENTIMENT1"]["source_hashes"]), 6)
        context = json.loads(agent.model.histories[0][0]["content"])
        self.assertEqual(len(context["comments"]), 6)
        self.assertNotIn("Response_Score", json.dumps(context))
        self.assertEqual(agent.analyze_sentiment("Recognition"), summary)
        self.assertEqual(len(agent.model.histories), 1)

    def test_unknown_duplicate_missing_ids_fake_quotes_and_empty_labels_are_rejected(self):
        for mutation in ("unknown", "duplicate", "missing", "quote", "category", "empty"):
            labels, documents = self.labels(), self.documents()
            if mutation == "unknown": labels[0]["citation_id"] = "survey:foreign"
            if mutation == "duplicate": labels[1]["citation_id"] = labels[0]["citation_id"]
            if mutation == "missing": labels.pop()
            if mutation == "quote": labels[0]["quote"] = "invented text"
            if mutation == "category": labels[0]["label"] = "happy"
            if mutation == "empty": documents[0]["response_text"] = ""; labels[0]["quote"] = None
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_sentiment_labels(labels, documents)

    def test_small_groups_are_suppressed_and_not_used_as_examples(self):
        documents = self.documents(); documents[-1]["team"] = "B"
        report = dict(citation_id="SENTIMENT1", dimension=None, scope=SCOPE.__dict__, mode="offline-unit-test", labels=self.labels())
        summary = sentiment_summary(report, documents)
        self.assertEqual(len(summary["rows"]), 1)
        self.assertEqual(summary["rows"][0]["Eligible_Comments"], 5)
        self.assertEqual(summary["suppressed_groups"], 1)
        self.assertNotIn("survey:5", [item["citation_id"] for item in summary["examples"]])

    def test_failed_classification_never_publishes_partial_percentages(self):
        invalid = self.labels()[:-1]
        agent = self.agent([tool_turn("submit_sentiment_batch", {"labels": invalid}) for _ in range(2)])
        with self.assertRaisesRegex(RuntimeError, "no partial percentages"):
            agent.analyze_sentiment("Recognition")
        self.assertEqual(agent.sentiment_reports, {})

    def test_budget_preflight_refuses_large_population_without_model_calls(self):
        agent = self.agent([])
        agent.budget = RunBudget(model_limit=6)
        with self.assertRaisesRegex(ValueError, "No comments were classified"):
            agent.analyze_sentiment("Recognition")
        self.assertEqual(agent.model.histories, [])
        self.assertEqual(agent.sentiment_reports, {})

    def test_real_scope_population_has_no_identity_or_response_scores(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            documents = backend.sentiment_documents()
            _, rows = backend.survey_rows(comments=True)
            self.assertEqual(len(documents), len(rows))
            self.assertEqual({doc["record_id"] for doc in documents}, {row["Comment_ID"] for row in rows})
            for doc in documents:
                self.assertTrue(SCOPE.start_date <= doc["date"] <= SCOPE.end_date)
                self.assertTrue(doc["anonymous"])
                self.assertFalse({"Employee_ID", "Employee_Name", "Anonymous_Response_Token", "Response_Score"} & doc.keys())
        finally:
            backend.close()

    def test_verifier_recomputes_sentiment_and_rejects_altered_counts(self):
        agent = self.agent([tool_turn("submit_sentiment_batch", {"labels": self.labels()})])
        summary = agent.analyze_sentiment("Recognition")
        verifier = ZeroSugarAgent(SCOPE, None, "offline-unit-test", sentiment_reports=agent.sentiment_reports,
                                 sentiment_documents=agent.sentiment_documents)
        self.assertEqual(verifier.audit("Provisional result [SENTIMENT1].", [summary]), [])
        altered = deepcopy(summary); altered["rows"][0]["positive_count"] = 999
        self.assertTrue(verifier.audit("Result [SENTIMENT1].", [altered]))
        agent.sentiment_reports["SENTIMENT1"]["source_hashes"]["survey:0"] = "altered"
        self.assertTrue(verifier.audit("Result [SENTIMENT1].", [summary]))

    def test_sentiment_tool_context_is_not_mislabeled_as_ranked_text_rag(self):
        agent = self.agent([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
            tool_turn("submit_sentiment_batch", {"labels": self.labels()}),
            ModelTurn(text="Provisional positive comment share: 33.33%, 2 of 6 comments [SENTIMENT1].")])
        result = agent.run("Classify all Recognition comments.")
        self.assertIn("SENTIMENT1", result.sentiment)
        self.assertFalse(result.rag["context_supplied_to_generator"])
        self.assertEqual(result.rag["retrieval_calls"], [])
        context = json.loads(agent.model.histories[-1][-1]["output"])
        self.assertEqual(context["classified_comments"], 6)
        self.assertEqual(context["rows"][0]["positive_count"], 2)

    def test_multiple_batches_classify_every_id_before_summarizing(self):
        documents = [dict(self.documents()[2], citation_id=f"survey:{index}", record_id=str(index)) for index in range(21)]
        ordered = sorted(documents, key=lambda doc: doc["citation_id"])
        labels = [dict(citation_id=doc["citation_id"], label="neutral", quote=doc["response_text"], reason="Test fixture.") for doc in ordered]
        agent = self.agent([tool_turn("submit_sentiment_batch", {"labels": labels[:20]}),
                            tool_turn("submit_sentiment_batch", {"labels": labels[20:]})])
        agent.sentiment_documents = documents
        summary = agent.analyze_sentiment(None)
        self.assertEqual(summary["classified_comments"], 21)
        self.assertEqual(summary["rows"][0]["neutral_percent"], 100)
        self.assertEqual([len(json.loads(history[0]["content"])["comments"]) for history in agent.model.histories], [20, 1])

    def test_original_retains_labels_for_independent_source_and_aggregation_review(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            documents = sorted([doc for doc in backend.sentiment_documents() if doc["dimension"] == "Recognition"],
                               key=lambda doc: doc["citation_id"])
        finally:
            backend.close()
        # These neutral labels are test inputs, never a claim about the real text's sentiment.
        labels = [dict(citation_id=doc["citation_id"], label="neutral", quote=doc["response_text"][:120], reason="Test fixture.") for doc in documents]
        vanilla_turns = [tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"})]
        vanilla_turns += [tool_turn("submit_sentiment_batch", {"labels": labels[offset:offset + 20]}) for offset in range(0, len(labels), 20)]
        vanilla_turns += [ModelTurn(text="Provisional labels for all eligible comments [SENTIMENT1].")]
        models = {"Original": SequenceModel([tool_turn("ask_vanilla", {"question": "Classify all Recognition survey comments."}),
                    ModelTurn(text="Provisional comment labels, pending human validation [SENTIMENT1].")]),
                  "Vanilla": SequenceModel(vanilla_turns), "Lime": ScriptedDemoModel("Lime"),
                  "ZeroSugar": ScriptedDemoModel("ZeroSugar")}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "offline-unit-test")
        try:
            result = agent.run("Classify survey sentiment for Recognition.")
            self.assertEqual(result.verification["decision"], "accept")
            self.assertEqual(len(result.sentiment["SENTIMENT1"]["labels"]), len(documents))
            self.assertEqual(result.visualization["charts"], [])
            self.assertEqual(result.verification["reviews"][0]["deterministic_issues"], [])
            reviewer = ZeroSugarAgent(SCOPE, SequenceModel([tool_turn("submit_review", report())]), "offline-unit-test", database=DATABASE)
            try:
                reviewer.run(asdict(result))
                self.assertEqual(reviewer.audit(result.answer, result.evidence), [])
            finally:
                reviewer.close()
        finally:
            agent.close()


if __name__ == "__main__":
    unittest.main()
