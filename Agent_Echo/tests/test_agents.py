"""Offline checks of authorization, numeric evidence, retrieval and agent loops."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents import AccessScope, CherryAgent, VanillaAgent
from agents.data_access import ScopedData, open_source
from agents.model import ConfigurationError, ModelTurn, ResponsesModel, ScriptedDemoModel, ToolCall
from agents.runtime import Specialist, function_tool
from agents.tools import SQLReader, TextSearch

DATABASE = Path(__file__).resolve().parents[1] / "data" / "echo.db"


class SequenceModel:
    def __init__(self, turns):
        self.turns = iter(turns)
        self.histories = []

    def respond(self, instructions, history, tools, require_tool=False):
        self.histories.append(json.loads(json.dumps(history)))
        return next(self.turns)


def tool_turn(name, arguments, identifier="test-call"):
    call = ToolCall(identifier, name, json.dumps(arguments))
    return ModelTurn(calls=[call], output_items=[{
        "type": "function_call", "call_id": call.call_id, "name": call.name,
        "arguments": call.arguments}])


class StructuredAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_hash = hashlib.sha256(DATABASE.read_bytes()).hexdigest()
        cls.scope = AccessScope("M14", "2026-07-01", "2026-09-30")
        cls.agent = CherryAgent(DATABASE, cls.scope, ScriptedDemoModel("Cherry"), "offline-scripted-demo")

    @classmethod
    def tearDownClass(cls):
        cls.agent.close()
        assert hashlib.sha256(DATABASE.read_bytes()).hexdigest() == cls.original_hash

    def test_count_matches_direct_scoped_source(self):
        result = self.agent.reader.execute("SELECT COUNT(*) AS employees FROM employees")
        with open_source(DATABASE) as source:
            expected = source.execute("""SELECT COUNT(*) FROM HR_employees WHERE Pilot_Manager_ID=?
                AND Hire_Date<=? AND (Termination_Date IS NULL OR Termination_Date>=?)""",
                ("M14", "2026-09-30", "2026-07-01")).fetchone()[0]
        self.assertEqual(result["rows"][0]["employees"], expected)
        self.assertEqual(expected, 35)

    def test_other_manager_rows_are_absent_even_without_sql_filter(self):
        ids = {r["Employee_ID"] for r in self.agent.reader.execute("SELECT Employee_ID FROM employees")["rows"]}
        with open_source(DATABASE) as source:
            other = {r[0] for r in source.execute("SELECT Employee_ID FROM HR_employees WHERE Pilot_Manager_ID='M15'")}
        self.assertTrue(ids.isdisjoint(other))

    def test_unauthorized_and_mutating_sql_is_denied(self):
        forbidden = [
            "SELECT * FROM HR_employees", "SELECT * FROM sqlite_master",
            "SELECT * FROM pragma_database_list", "PRAGMA table_info(employees)",
            "ATTACH DATABASE ':memory:' AS extra", "DELETE FROM employees",
            "UPDATE employees SET Employee_Name='changed'", "DROP TABLE employees",
            "CREATE TABLE copy AS SELECT * FROM employees", "BEGIN", "VACUUM",
            "SELECT load_extension('anything')", "SELECT randomblob(10000000)",
            "WITH x AS (SELECT * FROM employees) DELETE FROM employees",
            "SELECT * FROM employees; DELETE FROM employees",
        ]
        for query in forbidden:
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.agent.reader.execute(query)

    def test_ctes_and_legitimate_aggregations_work(self):
        result = self.agent.reader.execute("""WITH c AS (SELECT Employee_ID, COUNT(*) AS n FROM contributions
            WHERE Home_Team <> Beneficiary_Team GROUP BY Employee_ID)
            SELECT SUM(n) AS total FROM c""")
        with open_source(DATABASE) as source:
            expected = source.execute("""SELECT COUNT(*) FROM OP_contributions c JOIN HR_employees e
                ON c.Employee_ID=e.Employee_ID WHERE e.Pilot_Manager_ID='M14'
                AND c.Home_Team<>c.Beneficiary_Team AND c.Contribution_Date BETWEEN '2026-07-01' AND '2026-09-30'""").fetchone()[0]
        self.assertEqual(result["rows"][0]["total"], expected)
        self.assertEqual(expected, 159)

    def test_time_and_result_limits(self):
        result = self.agent.reader.execute("SELECT * FROM work_requests")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["rows"]), 100)
        with self.assertRaises(ValueError):
            self.agent.reader.execute("WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT SUM(n) FROM x")

    def test_private_fields_and_individual_program_history_are_absent(self):
        schema = self.agent.reader.describe()["tables"]
        self.assertNotIn("Employee_ID", schema["program_summary"])
        for name in ("Anonymous_Response_Token", "Response_Text", "Contact_Email", "Salary", "Message"):
            self.assertFalse(any(name in columns for columns in schema.values()))
        self.assertNotIn("HR_program_participation", schema)

    def test_quarter_scope_applies_to_metrics_and_events(self):
        for table, column in (("contributions", "Contribution_Date"), ("survey_summary", "Survey_Date"),
                              ("capacity", "Week_Start"), ("priority_decisions", "Decision_Date")):
            result = self.agent.reader.execute(f"SELECT MIN({column}) AS first, MAX({column}) AS last FROM {table}")["rows"][0]
            self.assertGreaterEqual(result["first"], self.scope.start_date)
            self.assertLessEqual(result["last"], self.scope.end_date)

    def test_program_counts_match_source_and_small_groups_are_suppressed(self):
        rows = self.agent.reader.execute("SELECT * FROM program_summary LIMIT 1")["rows"]
        self.assertTrue(rows)
        row = rows[0]
        self.assertGreaterEqual(row["Eligible_Employees"], 5)
        with open_source(DATABASE) as source:
            expected = source.execute("""SELECT COUNT(*) FROM HR_program_participation p JOIN HR_employees e
                ON p.Employee_ID=e.Employee_ID WHERE e.Pilot_Manager_ID='M14' AND p.Program_ID=?
                AND p.Reporting_Period=? AND p.Team=?""", (row["Program_ID"], row["Reporting_Period"], row["Team"])).fetchone()[0]
        self.assertEqual(row["Eligible_Records"], expected)

    def test_demo_runs_tools_and_retains_sql_evidence(self):
        result = self.agent.run("Show quarterly recognition survey metrics.")
        self.assertEqual(result.mode, "offline-scripted-demo")
        self.assertEqual([t["tool"] for t in result.tool_trace], ["describe_schema", "execute_sql"])
        self.assertEqual(len(result.evidence[0]["rows"]), 1)
        self.assertIn("[" + result.evidence[0]["citation_id"] + "]", result.answer)


class TextualAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = AccessScope("M14", "2026-07-01", "2026-09-30")
        cls.agent = VanillaAgent(DATABASE, cls.scope, ScriptedDemoModel("Vanilla"), "offline-scripted-demo")

    @classmethod
    def tearDownClass(cls):
        cls.agent.close()

    def test_anonymous_surveys_have_provenance_without_identity_tokens(self):
        result = self.agent.searcher.search("recognition", "HR_survey_comments", "Recognition", 6)
        self.assertTrue(result["passages"])
        for passage in result["passages"]:
            self.assertTrue(passage["anonymous"])
            self.assertEqual(passage["team"], "Data Platforms")
            self.assertEqual(passage["date"], "2026-09-30")
            self.assertNotIn("Employee_ID", passage)
            self.assertNotIn("Anonymous_Response_Token", passage)
            with open_source(DATABASE) as source:
                original = source.execute("SELECT Response_Text FROM HR_survey_comments WHERE Comment_ID=?", (passage["record_id"],)).fetchone()[0]
            self.assertIn(original[:200], passage["text"])

    def test_every_named_document_belongs_to_permitted_employee(self):
        with open_source(DATABASE) as source:
            for doc in self.agent.searcher.documents:
                if doc["anonymous"]:
                    continue
                if doc["source"] == "OP_priority_decisions":
                    query = """SELECT e.Pilot_Manager_ID FROM OP_priority_decisions d JOIN OP_work_requests w
                        ON d.Work_Request_ID=w.Work_Request_ID JOIN HR_employees e ON w.Assigned_Employee_ID=e.Employee_ID WHERE d.Decision_ID=?"""
                else:
                    table, key, employee = {
                        "HR_recognition_feedback": ("HR_recognition_feedback", "Interaction_ID", "Employee_ID"),
                        "OP_contributions": ("OP_contributions", "Contribution_ID", "Employee_ID"),
                        "OP_work_requests": ("OP_work_requests", "Work_Request_ID", "Assigned_Employee_ID"),
                    }[doc["source"]]
                    query = f"SELECT e.Pilot_Manager_ID FROM {table} t JOIN HR_employees e ON t.{employee}=e.Employee_ID WHERE t.{key}=?"
                self.assertEqual(source.execute(query, (doc["record_id"],)).fetchone()[0], "M14")
                self.assertTrue(self.scope.start_date <= doc["date"] <= self.scope.end_date)

    def test_filters_are_applied_before_top_k(self):
        documents = [dict(citation_id=str(i), source="feedback", dimension="", text="recognition recognition", team="A") for i in range(20)]
        documents.append(dict(citation_id="survey:test", source="survey", dimension="Recognition", text="recognition", team="A"))
        search = TextSearch(documents, self.scope)
        try:
            result = search.search("recognition", "survey", "Recognition", 1)
            self.assertEqual(result["passages"][0]["citation_id"], "survey:test")
        finally:
            search.close()

    def test_search_query_cannot_inject_sql_or_fts_operators(self):
        result = self.agent.searcher.search('"; DROP TABLE passages; -- OR NOT *', limit=2)
        self.assertLessEqual(len(result["passages"]), 2)
        self.assertTrue(self.agent.searcher.search("recognition")["passages"])
        self.assertEqual(self.agent.searcher.search("!!!")["passages"], [])

    def test_identical_passages_do_not_fill_the_evidence_sample(self):
        documents = [dict(citation_id=str(i), source="survey", dimension="", text="recognition helps", team="A") for i in range(8)]
        documents.append(dict(citation_id="different", source="survey", dimension="", text="recognition needs work", team="A"))
        search = TextSearch(documents, self.scope)
        try:
            hits = search.search("recognition", limit=4)["passages"]
            self.assertEqual(len(hits), 2)
            self.assertEqual(len({p["text"] for p in hits}), 2)
        finally:
            search.close()

    def test_demo_returns_cited_passages_not_numeric_prevalence(self):
        result = self.agent.run("Find recognition survey examples.")
        self.assertEqual(len(result.evidence), 4)
        self.assertIn("No LLM interpretation", result.answer)
        self.assertTrue(all("[" + p["citation_id"] + "]" in result.answer for p in result.evidence))


class RuntimeTests(unittest.TestCase):
    def test_invalid_scopes_and_injected_manager_strings_are_rejected(self):
        with self.assertRaises(ValueError):
            AccessScope("M14", "2024-01-01", "2026-09-30")
        with self.assertRaises(ValueError):
            AccessScope("M14", "2026-09-30", "2026-07-01")
        with self.assertRaises(ValueError):
            ScopedData(DATABASE, AccessScope("M14' OR 1=1 --"))

    def test_missing_configuration_fails_without_api_import_or_connection(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(ConfigurationError) as raised:
            ResponsesModel.from_environment()
        self.assertIn("No API connection was attempted", str(raised.exception))

    def test_agent_repairs_failed_query_and_bad_citation(self):
        scope = AccessScope("M14")
        reader = SQLReader({"employees": (["Employee_ID"], [("E01",)])}, scope)
        model = SequenceModel([
            tool_turn("execute_sql", {"sql": "SELECT * FROM secret"}),
            tool_turn("execute_sql", {"sql": "SELECT COUNT(*) AS total FROM employees"}, "fixed"),
            ModelTurn(text="One employee [SQL999]."),
            ModelTurn(text="One employee [SQL1]."),
        ])
        agent = Specialist("Cherry", "Use evidence.", model, scope, [], {"execute_sql": reader.execute})
        try:
            result = agent.run("Count employees.")
            self.assertIn("error", result.tool_trace[0]["result"])
            self.assertEqual(result.answer, "One employee [SQL1].")
            self.assertTrue(any("Repair citation" in item.get("content", "") for item in model.histories[-1]))
            json.dumps(asdict(result))
        finally:
            reader.close()

    def test_runaway_loop_stops_without_an_answer(self):
        turns = [tool_turn("noop", {}, str(i)) for i in range(8)]
        agent = Specialist("Test", "", SequenceModel(turns), AccessScope("M14"), [], {"noop": lambda: {}})
        with self.assertRaisesRegex(RuntimeError, "turn budget"):
            agent.run("Loop forever.")

    def test_responses_adapter_preserves_tool_call_items(self):
        call_item = {"type": "function_call", "call_id": "provider-call", "name": "describe_schema", "arguments": "{}"}
        output = SimpleNamespace(type="function_call", call_id="provider-call", name="describe_schema",
            arguments="{}", model_dump=lambda **kwargs: call_item)
        response = SimpleNamespace(status="completed", output=[output], output_text="")
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return response
        adapter = ResponsesModel(SimpleNamespace(responses=SimpleNamespace(create=create)), "test-deployment")
        turn = adapter.respond("Instructions", [{"role": "user", "content": "Question"}],
            [function_tool("describe_schema", "Schema", {})], True)
        self.assertEqual(turn.calls[0].call_id, "provider-call")
        self.assertEqual(turn.output_items, [call_item])
        self.assertEqual(captured["tool_choice"], "required")
        self.assertFalse(captured["store"])


if __name__ == "__main__":
    unittest.main()
