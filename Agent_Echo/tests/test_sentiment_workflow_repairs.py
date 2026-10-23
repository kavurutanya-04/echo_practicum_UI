"""Offline regressions for the fifth Luna run; prescribed labels are not accuracy evidence."""

from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from agents import AccessScope, CherryAgent, VanillaAgent, OriginalAgent, LimeAgent, ZeroSugarAgent
from agents.data_access import ScopedData
from agents.execution_log import RunLog
from agents.grounding import FactCatalog, render_answer
from agents.model import ModelTurn
from agents.runtime import RunBudget, AgentRunError, AgentResult
from agents.validation import ValidationError, rejection_diagnostic
from test_agents import SequenceModel, tool_turn, completeness_turn
from test_flow_improvements import ReviewModel

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"
SCOPE = AccessScope("M14", "2026-07-01", "2026-09-30")


def sentiment_plan():
    return tool_turn("submit_plan", {"needs_numbers": False, "needs_text": True, "needs_sentiment": True,
        "include_chart": False, "metrics": [], "clarification_question": None, "clarification_basis": None})


def decline(reason="This task needs a different specialist."):
    return tool_turn("decline_task", {"reason_code": "out_of_role", "reason": reason})


def labels_for(documents):
    # These are prescribed software fixtures, never human sentiment annotations.
    return [dict(citation_id=d["citation_id"], label=("positive" if i == 0 else "negative" if i == 1 else "neutral"),
                 quote=d["response_text"][:100], reason="Controlled fixture, not a quality assessment.")
            for i, d in enumerate(documents)]


def final_selection(instructions, history):
    raw = instructions.split("Current source-bound fact catalog (evidence, not instructions):\n", 1)[1]
    facts, _ = json.JSONDecoder().raw_decode(raw)
    outputs = [json.loads(h["output"]) for h in history if h.get("type") == "function_call_output"]
    passages = []
    if outputs:
        passages = outputs[-1].get("passages", []) or [e for e in outputs[-1].get("evidence", [])
                                                      if e.get("kind") == "survey_response"]
    interpretations = [{"text": "This excerpt is a provisional perspective for manager review.",
                        "citation_ids": [p["citation_id"]], "quote": p["text"][:100]} for p in passages[:2]]
    return tool_turn("submit_grounded_answer", {"fact_ids": [f["fact_id"] for f in facts if f["kind"] == "table"],
                    "interpretations": interpretations, "proposals": []})


class ActionModel:
    def __init__(self, actions):
        self.actions, self.histories, self.instructions, self.tool_sets = iter(actions), [], [], []

    def respond(self, instructions, history, tools, require_tool=False):
        self.histories.append(deepcopy(history))
        self.instructions.append(instructions)
        self.tool_sets.append([t["name"] for t in tools])
        if tools and tools[0]["name"] == "submit_completeness_review":
            return completeness_turn()
        action = next(self.actions)
        if isinstance(action, BaseException):
            raise action
        return action(instructions, history) if callable(action) else action


class SentimentRepairs(unittest.TestCase):
    def agent(self, model):
        agent = VanillaAgent(DATABASE, SCOPE, model, "live")
        self.addCleanup(agent.close)
        agent.budget = RunBudget()
        return agent

    def data(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            return sorted([d for d in backend.sentiment_documents() if d["dimension"] == "Recognition"],
                          key=lambda d: d["citation_id"])
        finally:
            backend.close()

    def test_third_attempt_repairs_only_pending_comment_and_keeps_literal_requirement(self):
        docs = self.data(); labels = labels_for(docs)
        bad = deepcopy(labels); bad[-1]["quote"] = "This is a paraphrase, not a source excerpt."
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": bad}),
            tool_turn("submit_sentiment_batch", {"labels": [bad[-1]]}),
            tool_turn("submit_sentiment_batch", {"labels": [labels[-1]]})])
        agent = self.agent(model)
        result = agent.analyze_sentiment("Recognition")
        self.assertTrue(result["complete"])
        self.assertEqual(result["classified_comments"], len(docs))
        self.assertEqual([len(json.loads(h[0]["content"])["comments"]) for h in model.histories], [13, 1, 1])
        self.assertTrue(all(e["resolution"] == "accepted_sentiment_batch" for e in agent.sentiment_diagnostics))
        self.assertIn("Never summarize", model.instructions[0])

    def test_exhausted_attempts_return_progress_and_redelegation_cannot_reset_limit(self):
        docs = self.data(); labels = labels_for(docs)
        bad = deepcopy(labels); bad[-1]["quote"] = "Paraphrased text that is not literal."
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": bad}),
            tool_turn("submit_sentiment_batch", {"labels": [bad[-1]]}),
            tool_turn("submit_sentiment_batch", {"labels": [bad[-1]]})])
        agent = self.agent(model)
        result = agent.analyze_sentiment("Recognition")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["validated_comments"], 12)
        self.assertEqual(result["pending_source_ids"], [docs[-1]["citation_id"]])
        self.assertNotIn("rows", result)
        self.assertEqual(agent.analyze_sentiment("Recognition"), result)
        self.assertEqual(len(model.histories), 3)

    def test_provider_interruption_preserves_valid_comments_for_remaining_attempt(self):
        docs = self.data(); labels = labels_for(docs)
        bad = deepcopy(labels); bad[-1]["quote"] = "Not a literal excerpt."
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": bad}),
                             RuntimeError("Controlled interrupted request."),
                             tool_turn("submit_sentiment_batch", {"labels": [labels[-1]]})])
        agent = self.agent(model)
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            agent.analyze_sentiment("Recognition")
        result = agent.analyze_sentiment("Recognition")
        self.assertTrue(result["complete"])
        self.assertEqual(len(json.loads(model.histories[-1][0]["content"])["comments"]), 1)
        self.assertEqual(agent.budget.models, 3)

    def test_new_model_or_changed_source_does_not_reuse_old_classification(self):
        docs = self.data(); labels = labels_for(docs)
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": labels})])
        agent = self.agent(model)
        first = agent.analyze_sentiment("Recognition")
        second_model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": labels})])
        agent.model = second_model
        second = agent.analyze_sentiment("Recognition")
        self.assertNotEqual(first["citation_id"], second["citation_id"])
        self.assertEqual(len(second_model.histories), 1)
        agent.sentiment_documents = deepcopy(agent.sentiment_documents)
        changed = next(d for d in agent.sentiment_documents if d["citation_id"] == docs[0]["citation_id"])
        changed["response_text"] = "Controlled updated source response."
        changed_labels = deepcopy(labels); changed_labels[0]["quote"] = changed["response_text"]
        second_model.actions = iter([tool_turn("submit_sentiment_batch", {"labels": changed_labels})])
        third = agent.analyze_sentiment("Recognition")
        self.assertNotEqual(second["citation_id"], third["citation_id"])
        self.assertEqual(len(second_model.histories), 2)

    def test_full_report_reused_across_workflow_delegations_without_reclassification(self):
        labels = labels_for(self.data())
        model = ActionModel([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
            tool_turn("submit_sentiment_batch", {"labels": labels}), final_selection,
            tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}), final_selection])
        agent = self.agent(model); agent.workflow_reuse = True
        first = agent.run("Classify Recognition and quote examples.")
        second = agent.run("Reuse the Recognition classification and return its sources.")
        self.assertEqual(first.sentiment, second.sentiment)
        self.assertEqual(sum("submit_sentiment_batch" in t for t in model.tool_sets), 1)
        self.assertEqual(first.sentiment["SENTIMENT1"]["source_hashes"], second.sentiment["SENTIMENT1"]["source_hashes"])

    def test_standalone_new_run_resets_progress(self):
        labels = labels_for(self.data())
        actions = lambda: [tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
                           tool_turn("submit_sentiment_batch", {"labels": deepcopy(labels)}), final_selection]
        model = ActionModel(actions() + actions()); agent = self.agent(model)
        agent.run("First independent task."); agent.run("Second independent task.")
        self.assertEqual(sum("submit_sentiment_batch" in t for t in model.tool_sets), 2)

    def test_batch_diagnostics_keep_source_id_and_reason_but_not_rejected_quote(self):
        docs = self.data(); labels = labels_for(docs)
        bad = deepcopy(labels); private = "Example Person private@example.invalid " + "sk-" + "dummycredential" * 4
        bad[-1]["quote"] = private
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": bad}),
                             tool_turn("submit_sentiment_batch", {"labels": [labels[-1]]})])
        agent = self.agent(model)
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                agent.analyze_sentiment("Recognition"); log.finish(0)
            raw = log.path.read_text(encoding="utf-8")
        diagnostic = agent.sentiment_diagnostics[0]
        self.assertEqual(diagnostic["source_id"], docs[-1]["citation_id"])
        self.assertEqual(diagnostic["validation_code"], "quote_not_literal")
        self.assertNotIn(private, json.dumps(diagnostic))
        self.assertNotIn("private@example.invalid", raw)

    def test_incomplete_task_returns_to_original_without_partial_percentages(self):
        labels = labels_for(self.data()); bad = deepcopy(labels); bad[-1]["quote"] = "Not literal."
        model = ActionModel([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
            tool_turn("submit_sentiment_batch", {"labels": bad}),
            tool_turn("submit_sentiment_batch", {"labels": [bad[-1]]}),
            tool_turn("submit_sentiment_batch", {"labels": [bad[-1]]}),
            tool_turn("submit_grounded_answer", {"fact_ids": [], "interpretations": [], "proposals": []})])
        result = self.agent(model).run("Classify all Recognition comments.")
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.task_outcome["reason_code"], "incomplete_sentiment")
        self.assertEqual(result.sentiment, {})
        self.assertEqual(result.diagnostics["sentiment_progress"][0]["validated_comments"], 12)
        self.assertNotIn("percent", result.answer.lower())

    def test_shared_model_budget_still_stops_classification(self):
        labels = labels_for(self.data()); bad = deepcopy(labels); bad[-1]["quote"] = "Not literal."
        model = ActionModel([tool_turn("submit_sentiment_batch", {"labels": bad})])
        agent = self.agent(model)
        agent.budget = RunBudget(model_limit=7)
        agent.budget.models = 1
        with self.assertRaisesRegex(ValueError, "No comments were classified"):
            agent.analyze_sentiment("Recognition")
        self.assertEqual(model.histories, [])


class RoutingAndSources(unittest.TestCase):
    def documents(self):
        backend = ScopedData(DATABASE, SCOPE)
        try:
            return sorted([d for d in backend.sentiment_documents() if d["dimension"] == "Recognition"], key=lambda d:d["citation_id"])
        finally: backend.close()

    def workflow(self, misroute=False):
        docs = self.documents(); labels = labels_for(docs)
        plan = sentiment_plan()
        steps = [plan]
        if misroute:
            # Script a bad original plan; a specialist decline must allow corrected routing.
            plan.calls[0].arguments = json.dumps({"needs_numbers": True, "needs_text": False, "needs_sentiment": False,
                "include_chart": False, "metrics": [], "clarification_question": None, "clarification_basis": None})
            steps += [tool_turn("ask_cherry", {"question": "Return raw anonymous comments.", "task_type": "numeric"})]
        steps += [tool_turn("ask_vanilla", {"question": "Classify Recognition and provide literal examples.", "task_type": "sentiment"}), final_selection]
        original = ActionModel(steps)
        vanilla = ActionModel([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
                               tool_turn("submit_sentiment_batch", {"labels": labels}), final_selection])
        cherry = ActionModel([decline()])
        models = {"Original": original, "Vanilla": vanilla, "Cherry": cherry, "ZeroSugar": ReviewModel(["accept"])}
        agent = OriginalAgent(DATABASE, SCOPE, models.get, "live")
        self.addCleanup(agent.close)
        result = agent.run("Classify all Recognition comments with counts, percentages and literal examples.")
        return result, agent, original, vanilla, cherry

    def test_complete_vanilla_workflow_reaches_zerosugar_with_individual_sources(self):
        result, agent, original, vanilla, cherry = self.workflow()
        self.assertEqual(result.status, "complete")
        self.assertEqual(set(agent.specialists), {"Vanilla"})
        self.assertFalse(cherry.histories)
        self.assertEqual(len(result.sentiment["SENTIMENT1"]["labels"]), 13)
        sources = [e for e in result.evidence if e.get("kind") == "survey_response"]
        self.assertGreaterEqual(len(sources), 2)
        self.assertTrue(all(s["anonymous"] and s["scope"] == SCOPE.__dict__ for s in sources))
        self.assertEqual(result.verification["reviews"][0]["deterministic_issues"], [])
        self.assertEqual([len(original.histories), len(vanilla.histories)], [3, 3])
        self.assertTrue(any(c["kind"] == "interpretation" for c in result.claims))

    def test_declined_cherry_task_can_be_reassigned_without_querying_cherry(self):
        result, agent, original, vanilla, cherry = self.workflow(misroute=True)
        self.assertEqual(result.status, "complete")
        self.assertEqual(len(cherry.histories), 1)
        self.assertEqual(result.delegations[0]["status"], "declined")
        self.assertEqual(result.delegations[0]["tool_trace"], [])
        self.assertEqual(result.delegations[1]["agent"], "Vanilla")

    def test_cherry_and_vanilla_can_decline_in_their_first_turn(self):
        for cls in (CherryAgent, VanillaAgent):
            with self.subTest(role=cls.__name__):
                model = ActionModel([decline()]); agent = cls(DATABASE, SCOPE, model, "live")
                self.addCleanup(agent.close)
                result = agent.run("An incompatible task.")
                self.assertEqual(result.status, "declined")
                self.assertEqual(result.task_outcome["reason_code"], "out_of_role")
                self.assertEqual(result.tool_trace, [])
                self.assertEqual(len(model.histories), 1)

    def test_identical_declined_delegation_is_not_sent_again(self):
        model = ActionModel([decline()])
        agent = OriginalAgent(DATABASE, SCOPE, lambda role:model, "live")
        self.addCleanup(agent.close)
        agent.budget = RunBudget(); agent.planned_metrics = []; agent.prepared_metrics = {}; agent.repair_round = 0
        first = agent.delegate("Cherry", "Return anonymous comments.", "numeric")
        second = agent.delegate("Cherry", "Return anonymous comments.", "numeric")
        self.assertEqual(first, second)
        self.assertEqual(len(model.histories), 1)
        self.assertEqual(len(agent.child_results), 1)

    def test_lime_decline_is_distinct_from_optional_no_chart(self):
        model = ActionModel([decline()])
        result = LimeAgent(SCOPE, model, "live").plan("Classify text.", "", [])
        self.assertEqual(result.task_outcome["status"], "declined")
        self.assertEqual(result.charts, [])
        optional = LimeAgent(SCOPE, ActionModel([tool_turn("submit_visuals", {"charts": [], "reason": "No chart needed."})]), "live")
        self.assertIsNone(optional.plan("Explain comments.", "", []).task_outcome)

    def test_declining_and_querying_in_same_turn_cannot_execute_query(self):
        a, b = decline(), tool_turn("describe_schema", {}, "other")
        a.calls += b.calls; a.output_items += b.output_items
        model = ActionModel([a, decline()]); agent = CherryAgent(DATABASE, SCOPE, model, "live")
        self.addCleanup(agent.close)
        result = agent.run("Return text.")
        self.assertEqual(result.status, "declined")
        self.assertEqual(result.tool_trace, [])
        self.assertEqual(result.diagnostics["rejected_attempts"][0]["validation_code"], "decline_call_count")

    def test_zerosugar_detects_altered_canonical_comment(self):
        docs = self.documents(); agent = VanillaAgent(DATABASE, SCOPE, ActionModel([
            tool_turn("submit_sentiment_batch", {"labels": labels_for(docs)})]), "live")
        self.addCleanup(agent.close)
        summary = agent.analyze_sentiment("Recognition"); sources = agent.evidence_for_result(summary)
        verifier = ZeroSugarAgent(SCOPE, None, "live", sentiment_reports=agent.sentiment_reports, sentiment_documents=docs)
        self.assertEqual(verifier.audit("An excerpt [" + sources[0]["citation_id"] + "].", [summary] + sources), [])
        changed = deepcopy(sources); changed[0]["text"] = "Fabricated source."
        self.assertTrue(any("trusted anonymous comment" in i for i in verifier.audit(
            "An excerpt [" + sources[0]["citation_id"] + "].", [summary] + changed)))
        missing_scope = deepcopy(sources); missing_scope[0].pop("scope")
        self.assertTrue(verifier.audit("An excerpt [" + sources[0]["citation_id"] + "].", [summary] + missing_scope))

    def test_canonical_response_replaces_search_excerpt_with_same_id(self):
        docs = self.documents()
        model = ActionModel([tool_turn("analyze_survey_sentiment", {"dimension": "Recognition"}),
            tool_turn("submit_sentiment_batch", {"labels": labels_for(docs)}), final_selection])
        agent = VanillaAgent(DATABASE, SCOPE, model, "live"); self.addCleanup(agent.close)
        previous = next(d for d in agent.searcher.documents if d["citation_id"] == docs[0]["citation_id"])
        result = agent.run("Classify Recognition and provide excerpts.", initial_evidence=[previous])
        matches = [e for e in result.evidence if e["citation_id"] == docs[0]["citation_id"]]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["kind"], "survey_response")
        self.assertEqual(matches[0]["text"], docs[0]["response_text"])

    def test_missing_required_classification_cannot_be_accepted_by_model_alone(self):
        reviewer = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live")
        verdict = reviewer.review("Classify every comment.", "", [], require_sentiment=True)
        self.assertEqual(verdict.decision, "revise")
        self.assertIn("Vanilla", verdict.repair_targets)
        self.assertEqual(verdict.deterministic_issues, [])

    def test_standalone_review_preserves_required_sentiment_coverage(self):
        reviewer = ZeroSugarAgent(SCOPE, ReviewModel(["accept"]), "live")
        artifact = asdict(AgentResult("Original", "Classify every comment.", "", SCOPE.__dict__,
            diagnostics={"requires_sentiment": True}))
        result = reviewer.run(artifact)
        self.assertEqual(result.verification["decision"], "revise")
        self.assertIn("Vanilla", result.verification["repair_targets"])

    def test_missing_fields_are_reported_without_unknown_sensitive_field_names(self):
        error = None
        try:
            render_answer({"private@example.invalid": "secret"}, FactCatalog([], SCOPE.__dict__), "Original")
        except ValidationError as caught: error = caught
        diagnostic = rejection_diagnostic(error, "Original", "submit_grounded_answer", 1, 1)
        self.assertEqual(diagnostic["missing_fields"], ["fact_ids", "interpretations", "proposals"])
        self.assertEqual(diagnostic["unexpected_field_count"], 1)
        self.assertNotIn("private@example.invalid", json.dumps(diagnostic))

    def test_standalone_cli_reports_declined_and_exit_two(self):
        import run_agent
        model = ActionModel([decline()])
        class Registry:
            config = {"retrieval": {"mode": "lexical"}}
            def __init__(self, *args, **kwargs): pass
            def get(self, name): return model
            def describe(self): return {}
            def execution_summary(self): return {"generation_api_calls": 1, "successful_generation_api_calls": 1}
            def close(self): pass
        with TemporaryDirectory() as directory, patch.object(run_agent, "ModelRegistry", Registry), \
                patch.object(run_agent, "LOG_DIRECTORY", Path(directory) / "logs"), redirect_stdout(io.StringIO()):
            output = Path(directory) / "declined.json"
            code = run_agent.main(["cherry", "--manager", "M14", "--question", "Return raw comments.", "--output", str(output)])
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 2)
        self.assertEqual(saved["status"], "declined")
        self.assertEqual(saved["task_outcome"]["reason_code"], "out_of_role")

    def test_standalone_lime_decline_does_not_call_reviewer_or_export(self):
        import run_agent
        requested = []; model = ActionModel([decline()])
        class Registry:
            config = {"retrieval": {"mode": "lexical"}}
            def __init__(self, *args, **kwargs): pass
            def get(self, name): requested.append(name); return model
            def describe(self): return {}
            def execution_summary(self): return {"generation_api_calls": 1, "successful_generation_api_calls": 1}
            def close(self): pass
        with TemporaryDirectory() as directory, patch.object(run_agent, "ModelRegistry", Registry), \
                patch.object(run_agent, "LOG_DIRECTORY", Path(directory) / "logs"), redirect_stdout(io.StringIO()):
            incoming, output = Path(directory) / "input.json", Path(directory) / "declined.json"
            artifact = asdict(AgentResult("Original", "Chart sentiment.", "", SCOPE.__dict__,
                mode="live", status="complete", verification={"decision": "accept"}))
            incoming.write_text(json.dumps(artifact), encoding="utf-8")
            code = run_agent.main(["lime", "--manager", "M14", "--input", str(incoming), "--output", str(output)])
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 2)
        self.assertEqual(requested, ["Lime"])
        self.assertEqual(saved["status"], "declined")
        self.assertNotIn("files", saved["visualization"])


if __name__ == "__main__":
    unittest.main()
