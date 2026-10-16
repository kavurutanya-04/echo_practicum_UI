"""Check incremental diagnostics on success, errors and interrupted workflows."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import run_agent
from agents import AccessScope
from agents.connections import ModelRegistry
from agents.execution_log import RunLog, logged_model
from agents.model import ModelTurn
from agents.runtime import Specialist
from test_agents import SequenceModel, tool_turn


def entries(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class ExecutionLogTests(unittest.TestCase):
    def test_events_are_readable_before_the_run_finishes(self):
        with TemporaryDirectory() as directory:
            with RunLog(directory) as log:
                self.assertEqual(entries(log.path)[0]["event"], "run_started")
                log.finish(0)
            self.assertEqual(entries(log.path)[-1]["status"], "completed")

    def test_tool_loop_failure_preserves_steps_without_source_or_credentials(self):
        secret = "offline-secret-never-log-this"
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "turn budget"):
                with RunLog(directory) as log:
                    model = logged_model(SequenceModel([tool_turn("noop", {"text": secret}, str(i))
                                                        for i in range(7)]), "Cherry", "test")
                    agent = Specialist("Cherry", secret, model, AccessScope("M14"),
                        [{"name": "noop"}], {"noop": lambda text: {"rows": [{"text": text}]}})
                    agent.run(secret)
            events = entries(log.path)
            self.assertEqual(sum(e["event"] == "tool_finished" for e in events), 7)
            self.assertTrue(any(e["event"] == "agent_turn_limit" and e["agent"] == "Cherry" for e in events))
            self.assertEqual(events[-2]["error_category"], "agent_turn_limit")
            self.assertEqual(events[-1]["status"], "failed")
            self.assertNotIn(secret, log.path.read_text(encoding="utf-8"))

    def test_provider_failure_records_status_without_raw_payload(self):
        class FailedModel:
            def respond(self, *args):
                raise RuntimeError("Model request failed (HTTP 503). offline-secret")
        with TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                with RunLog(directory) as log:
                    logged_model(FailedModel(), "Vanilla", "test").respond("secret", [], [], False)
            failed = next(e for e in entries(log.path) if e["event"] == "model_failed")
            self.assertEqual(failed["http_status"], 503)
            self.assertEqual(failed["agent"], "Vanilla")
            self.assertNotIn("offline-secret", log.path.read_text(encoding="utf-8"))

    def test_cli_cancel_and_failure_save_logs_without_output_option(self):
        for error, expected, status in ((KeyboardInterrupt(), 130, "cancelled"),
                                        (RuntimeError("offline-secret"), 1, "failed")):
            with self.subTest(status=status), TemporaryDirectory() as directory:
                with patch.object(run_agent, "LOG_DIRECTORY", Path(directory)), \
                     patch("run_agent.check_connections", side_effect=error), \
                     redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
                    code = run_agent.main(["--check-connection", "--profile", "google_test"])
                self.assertEqual(code, expected)
                paths = list(Path(directory).glob("*.jsonl"))
                self.assertEqual(len(paths), 1)
                self.assertIn(str(paths[0]), stdout.getvalue())
                self.assertEqual(entries(paths[0])[-1]["status"], status)
                self.assertNotIn("offline-secret", paths[0].read_text(encoding="utf-8"))

    def test_cli_demo_is_logged_without_reading_credentials(self):
        with TemporaryDirectory() as directory:
            with patch.object(run_agent, "LOG_DIRECTORY", Path(directory)), \
                 patch.object(ModelRegistry, "_key", side_effect=AssertionError("No key access")), \
                 patch.object(ModelRegistry, "_local_value", side_effect=AssertionError("No env access")), \
                 redirect_stdout(io.StringIO()):
                code = run_agent.main(["cherry", "--manager", "M14", "--demo"])
            self.assertEqual(code, 0)
            log = next(Path(directory).glob("*.jsonl"))
            events = entries(log)
            self.assertTrue(any(e["event"] == "tool_finished" for e in events))
            self.assertTrue(any(e["event"] == "model_finished" for e in events))
            self.assertEqual(events[-1]["status"], "completed")

    def test_citation_repairs_leave_diagnostics(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "turn budget"):
                with RunLog(directory) as log:
                    model = SequenceModel([ModelTurn(text="Wrong [SQL999].") for _ in range(7)])
                    Specialist("Cherry", "", model, AccessScope("M14"), [], {}).run("Count.")
            self.assertEqual(sum(e["event"] == "citation_repair" for e in entries(log.path)), 7)

    def test_unexpected_exception_is_recorded_without_exposing_its_text(self):
        with TemporaryDirectory() as directory:
            with patch.object(run_agent, "LOG_DIRECTORY", Path(directory)), \
                 patch("run_agent.check_connections", side_effect=IndexError("offline-secret")), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = run_agent.main(["--check-connection", "--profile", "google_test"])
            self.assertEqual(code, 1)
            log = next(Path(directory).glob("*.jsonl"))
            events = entries(log)
            self.assertEqual(events[-2]["error_type"], "IndexError")
            self.assertEqual(events[-1]["status"], "failed")
            self.assertNotIn("offline-secret", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
