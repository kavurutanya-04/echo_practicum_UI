"""Offline provider contracts, semantic retrieval, verification and workflow checks."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents import AccessScope, OriginalAgent, ZeroSugarAgent
from agents.zero_sugar import DIMENSIONS
from agents.connections import EmbeddingModel, ModelRegistry
from agents.model import ChatModel, ConfigurationError, ModelTurn, ScriptedDemoModel
from agents.runtime import RunBudget
from agents.semantic_search import SemanticTextSearch, normalized
from agents.tools import SQLReader
from test_agents import SequenceModel, tool_turn

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"


def report(decision="accept", issues=()):
    return {"decision": decision, "ratings": {name: {"score": 3, "rationale": "Offline fixture."} for name in DIMENSIONS},
            "issues": list(issues), "uncertainty": "No live model evaluation."}


class ConnectionTests(unittest.TestCase):
    def test_profiles_default_and_role_override(self):
        with patch.dict("os.environ", {"ECHO_DEFAULT_PROFILE": "google_test", "ECHO_ZEROSUGAR_PROFILE": "personal_openai"}, clear=True):
            registry = ModelRegistry()
            self.assertEqual(registry.profile_for("Cherry"), "google_test")
            self.assertEqual(registry.profile_for("ZeroSugar"), "personal_openai")
            self.assertEqual(registry.clients, {})

    def test_command_line_profile_overrides_all_roles(self):
        with patch.dict("os.environ", {"ECHO_CHERRY_PROFILE": "gw_azure"}, clear=True):
            profiles = ModelRegistry(force_profile="google_test").describe()
            self.assertTrue(all(value["profile"] == "google_test" for value in profiles.values()))
            self.assertNotIn("api_key", json.dumps(profiles))

    def test_missing_profile_values_do_not_construct_a_client(self):
        with patch.dict("os.environ", {}, clear=True):
            registry = ModelRegistry(force_profile="google_test", env_file=None)
            with self.assertRaises(ConfigurationError):
                registry.get("Vanilla")
            self.assertEqual(registry.clients, {})

    def test_invalid_and_embedding_profiles_cannot_power_agents(self):
        with self.assertRaises(ConfigurationError):
            ModelRegistry(force_profile="unknown")
        with self.assertRaises(ConfigurationError):
            ModelRegistry(force_profile="gw_embeddings").profile_for("Cherry")

    def test_same_profile_shares_one_client_without_shared_conversation_state(self):
        constructed = []
        def client(**kwargs):
            constructed.append(kwargs)
            return SimpleNamespace(close=lambda: None)
        with patch.dict("os.environ", {"GOOGLE_MODEL": "test-model", "GOOGLE_API_KEY": "offline-fake-key"}, clear=True), \
             patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(force_profile="google_test", env_file=None)
            first, second = registry.get("Cherry"), registry.get("Vanilla")
            self.assertIs(first, second)
            self.assertEqual(len(constructed), 1)
            self.assertIn("generativelanguage.googleapis.com", constructed[0]["base_url"])
            self.assertFalse(hasattr(first, "history"))
            registry.close()

    def test_azure_matches_professor_endpoint_key_and_version_pattern(self):
        constructed = []
        def client(**kwargs):
            constructed.append(kwargs)
            return SimpleNamespace(close=lambda: None)
        values = {"AZURE_OPENAI_ENDPOINT": "https://offline-assigned-resource.openai.azure.com/",
                  "AZURE_OPENAI_DEPLOYMENT": "offline-deployment", "GW_AZURE_OPENAI_KEY": "offline-fake-key"}
        with patch.dict("os.environ", values, clear=True), patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(env_file=None)
            self.assertEqual(registry.get("Cherry").model, "offline-deployment")
            self.assertEqual(constructed[0]["api_version"], "2025-03-01-preview")
            self.assertEqual(constructed[0]["azure_endpoint"], values["AZURE_OPENAI_ENDPOINT"])
            registry.close()

    def test_google_tool_response_preserves_thought_signature_metadata(self):
        captured = []
        call = SimpleNamespace(id="call-1", function=SimpleNamespace(name="test", arguments="{}"))
        raw = {"role": "assistant", "tool_calls": [{"id": "call-1", "type": "function",
            "function": {"name": "test", "arguments": "{}"}, "extra_content": {"google": {"thought_signature": "fixture-signature"}}}]}
        message = SimpleNamespace(content=None, tool_calls=[call], model_dump=lambda **kwargs: raw)
        def create(**kwargs):
            captured.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason="tool_calls", message=message)])
        model = ChatModel(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), "fixture")
        turn = model.respond("Instructions", [{"role": "user", "content": "Question"}], [])
        model.respond("Instructions", [{"role": "user", "content": "Question"}, *turn.output_items,
            {"type": "function_call_output", "call_id": "call-1", "output": "{}"}], [])
        self.assertEqual(captured[1]["messages"][2]["tool_calls"][0]["extra_content"]["google"]["thought_signature"], "fixture-signature")
        self.assertEqual(captured[1]["messages"][3]["tool_call_id"], "call-1")

    def test_embeddings_are_reordered_by_input_index(self):
        response = SimpleNamespace(data=[SimpleNamespace(index=1, embedding=[0, 1]), SimpleNamespace(index=0, embedding=[1, 0])])
        model = EmbeddingModel(SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kwargs: response)), "fixture", "fixture")
        self.assertEqual(model.embed(["first", "second"]), [[1, 0], [0, 1]])


class FixtureEmbeddings:
    def __init__(self, identity="fixture"):
        self.identity, self.calls = identity, []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[1, 0] if any(word in text.lower() for word in ("appreciation", "recognized")) else [0, 1] for text in texts]


class SemanticTests(unittest.TestCase):
    def documents(self):
        return [dict(citation_id="survey:1", source="HR_survey_comments", record_id="1", team="A", date="2026-09-30", dimension="Recognition", anonymous=True, text="Our efforts are recognized."),
                dict(citation_id="survey:2", source="HR_survey_comments", record_id="2", team="A", date="2026-09-30", dimension="Benefits", anonymous=True, text="The gym benefit is useful.")]

    def test_semantic_search_finds_synonyms_without_keyword_overlap(self):
        model = FixtureEmbeddings()
        with TemporaryDirectory() as cache:
            search = SemanticTextSearch(self.documents(), AccessScope("M14"), model, cache, "semantic")
            try:
                result = search.search("appreciation", dimension="Recognition", limit=1)
                self.assertEqual(result["passages"][0]["citation_id"], "survey:1")
                self.assertEqual(result["passages"][0]["cosine_similarity"], 1.0)
            finally:
                search.close()

    def test_cache_reuse_and_provider_model_separation(self):
        with TemporaryDirectory() as cache:
            first = FixtureEmbeddings("first")
            search = SemanticTextSearch(self.documents(), AccessScope("M14"), first, cache)
            search.close()
            second = FixtureEmbeddings("first")
            search = SemanticTextSearch(self.documents(), AccessScope("M14"), second, cache)
            self.assertEqual(second.calls, [])
            search.close()
            third = FixtureEmbeddings("different-model")
            search = SemanticTextSearch(self.documents(), AccessScope("M14"), third, cache)
            self.assertTrue(third.calls)
            search.close()

    def test_vector_validation_and_dimension_mismatch(self):
        for vector in ([], [0, 0], [float("nan"), 1], [True, 1]):
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                normalized(vector)
        model = FixtureEmbeddings()
        with TemporaryDirectory() as cache:
            search = SemanticTextSearch(self.documents(), AccessScope("M14"), model, cache)
            model.embed = lambda texts: [[1, 0, 1]]
            try:
                with self.assertRaisesRegex(ValueError, "dimensions differ"):
                    search.search("appreciation")
            finally:
                search.close()

    def test_embedding_budget_stops_index_creation(self):
        with TemporaryDirectory() as cache, self.assertRaisesRegex(RuntimeError, "budget"):
            SemanticTextSearch(self.documents(), AccessScope("M14"), FixtureEmbeddings(), cache,
                               budget=RunBudget(embedding_limit=0))


class VerifierTests(unittest.TestCase):
    def test_unknown_citation_cannot_be_overridden_by_a_model_acceptance(self):
        verifier = ZeroSugarAgent(AccessScope("M14"), ScriptedDemoModel("ZeroSugar"), "offline-scripted-demo")
        result = verifier.review("Question", "Claim [SQL999].", [{"citation_id": "SQL1"}])
        self.assertEqual(result.decision, "revise")
        self.assertTrue(result.deterministic_issues)

    def test_tampered_sql_results_are_detected_by_replay(self):
        scope = AccessScope("M14")
        reader = SQLReader({"employees": (["Employee_ID"], [("E1",), ("E2",)])}, scope)
        try:
            evidence = reader.execute("SELECT COUNT(*) AS total FROM employees")
            evidence["rows"][0]["total"] = 999
            verifier = ZeroSugarAgent(scope, ScriptedDemoModel("ZeroSugar"), sql_reader=reader)
            result = verifier.review("Count employees", "There are 999 employees [SQL1].", [evidence])
            self.assertEqual(result.decision, "revise")
            self.assertIn("SQL evidence does not match a read-only query replay.", result.deterministic_issues)
        finally:
            reader.close()

    def test_tampered_text_and_anonymous_identity_are_rejected(self):
        original = dict(citation_id="survey:1", source="HR_survey_comments", record_id="1", team="A", date="2026-09-30", anonymous=True, text="Original text")
        changed = {**original, "text": "Invented text", "Employee_ID": "E001"}
        verifier = ZeroSugarAgent(AccessScope("M14"), ScriptedDemoModel("ZeroSugar"), document_lookup={"survey:1": original})
        result = verifier.review("Question", "Claim [survey:1].", [changed])
        self.assertEqual(result.decision, "revise")
        self.assertEqual(len(result.deterministic_issues), 2)

    def test_incomplete_or_out_of_range_rubric_is_rejected(self):
        candidate = report()
        candidate["ratings"]["Accuracy"]["score"] = True
        with self.assertRaises(ValueError):
            ZeroSugarAgent.validate(candidate)
        candidate = report()
        del candidate["ratings"]["Completeness"]
        with self.assertRaises(ValueError):
            ZeroSugarAgent.validate(candidate)

    def test_scope_and_period_violations_are_detected(self):
        verifier = ZeroSugarAgent(AccessScope("M14", "2026-07-01", "2026-09-30"), ScriptedDemoModel("ZeroSugar"))
        issues = verifier.audit("Claim [SQL1].", [{"citation_id": "SQL1", "scope": AccessScope("M15").__dict__, "date": "2025-01-01"}])
        self.assertIn("Evidence scope differs from the authorized caller scope.", issues)
        self.assertIn("Evidence date is outside the authorized period.", issues)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_hash = hashlib.sha256(DATABASE.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(DATABASE.read_bytes()).hexdigest() == cls.original_hash

    def test_complete_offline_workflow_delegates_and_always_verifies(self):
        agent = OriginalAgent(DATABASE, AccessScope("M14"), lambda name: ScriptedDemoModel(name), "offline-scripted-demo")
        try:
            result = agent.run("Review recognition with metrics and comments.")
            self.assertEqual([child["agent"] for child in result.delegations], ["Cherry", "Vanilla"])
            self.assertEqual(result.verification["decision"], "accept")
            self.assertEqual(len(result.verification["reviews"]), 1)
            self.assertTrue(all(child["scope"] == result.scope for child in result.delegations))
            self.assertIn("No LLM analysis", result.answer)
        finally:
            agent.close()

    def build_revision_workflow(self, accept_second):
        coordinator = SequenceModel([tool_turn("submit_plan", {"needs_numbers": True, "needs_text": False,
            "include_chart": False, "clarification_question": None}), tool_turn("ask_cherry", {"question": "Show recognition metrics."}),
            ModelTurn(text="Unsupported claim [SQL1]."), ModelTurn(text="Corrected description of the evidence [SQL1].")])
        verdicts = iter([report("revise", ["Correct the unsupported claim."]), report("accept" if accept_second else "revise", [] if accept_second else ["Still unsupported."])])
        def factory(name):
            if name == "Original":
                return coordinator
            if name == "ZeroSugar":
                return SequenceModel([tool_turn("submit_review", next(verdicts))])
            return ScriptedDemoModel(name)
        return OriginalAgent(DATABASE, AccessScope("M14"), factory, "offline-scripted-demo")

    def test_rejected_candidate_is_revised_and_reviewed_again(self):
        agent = self.build_revision_workflow(True)
        try:
            result = agent.run("Review recognition.")
            self.assertEqual(result.verification["drafts_checked"], 2)
            self.assertEqual(result.verification["decision"], "accept")
            self.assertIn("Corrected", result.answer)
        finally:
            agent.close()

    def test_twice_rejected_answer_is_withheld(self):
        agent = self.build_revision_workflow(False)
        try:
            result = agent.run("Review recognition.")
            self.assertEqual(result.verification["decision"], "revise")
            self.assertIn("No verified answer", result.answer)
            self.assertNotIn("Unsupported claim", result.answer)
            self.assertEqual(len(result.verification["rejected_drafts"]), 2)
        finally:
            agent.close()

    def test_global_budget_limits_nested_calls(self):
        budget = RunBudget(model_limit=1, tool_limit=1)
        budget.consume("model")
        with self.assertRaises(RuntimeError):
            budget.consume("model")
        elapsed = RunBudget(seconds=-1)
        with self.assertRaises(RuntimeError):
            elapsed.consume("tool")


if __name__ == "__main__":
    unittest.main()
