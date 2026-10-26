"""Offline timing and retry checks; no network or real waiting."""

from datetime import datetime, timezone
from email.utils import format_datetime
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.connections import ModelRegistry
from agents.model import ChatModel, ConfigurationError
from agents.request_pacing import RequestPacer, request_deadline, retry_after_seconds, shared_pacer
from agents.runtime import RunBudget


class RateError(Exception):
    def __init__(self, status=429, retry_after=None):
        self.status_code = status
        self.response = SimpleNamespace(headers={"retry-after": retry_after} if retry_after else {})


class Clock:
    def __init__(self):
        self.now = 100.0
        self.waits = []

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def response():
    message = SimpleNamespace(content="ok", tool_calls=[], model_dump=lambda **kw: {"role": "assistant", "content": "ok"})
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=message)])


class RequestPacingTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        for manager in (
            patch("agents.request_pacing.time.monotonic", lambda: self.clock.now),
            patch("agents.request_pacing.time.sleep", self.clock.sleep),
            patch.dict("agents.request_pacing._pacers", {}, clear=True),
        ):
            manager.start()
            self.addCleanup(manager.stop)

    def test_all_five_roles_and_multiple_registries_share_actual_start_spacing(self):
        starts, options = [], []

        def client(**kwargs):
            options.append(kwargs)
            def create(**request):
                starts.append(self.clock.now)
                return response()
            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=lambda: None)

        with patch.dict(os.environ, {"APINEX_API_KEY": "offline-test"}, clear=True), patch.dict("sys.modules", {
                "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            first = ModelRegistry(force_profile="apinex_test", env_file=None)
            second = ModelRegistry(force_profile="apinex_test", env_file=None)
            for role in first.config["agents"]:
                first.get(role).respond("Use evidence.", [], [])
            second.get("Original").respond("Use evidence.", [], [])
            self.assertEqual(starts, [100, 120, 140, 160, 180, 200])
            self.assertTrue(all(item["max_retries"] == 0 for item in options))
            self.assertTrue(all(item["model"] == "free/gpt-6-luna" for item in first.describe().values()))
            first.close()
            second.close()

    def test_long_requests_do_not_add_unnecessary_waits(self):
        pacer = RequestPacer(20)
        pacer.acquire()
        self.clock.now += 25
        pacer.acquire()
        self.assertEqual(self.clock.waits, [])

    def test_sharing_ignores_model_and_preserves_stricter_interval(self):
        first = shared_pacer("https://offline.invalid/v1/", "offline-key", 20)
        first.acquire()
        second = shared_pacer("https://offline.invalid/v1", "offline-key", 30)
        self.assertIs(first, second)
        self.assertIsNot(first, shared_pacer("https://offline.invalid/v1", "different-key", 20))
        second.acquire()
        self.assertEqual(self.clock.now, 130)

    def test_429_retry_after_delays_retry_and_counts_actual_requests(self):
        starts = []
        def create(**kwargs):
            starts.append(self.clock.now)
            if len(starts) == 1:
                raise RateError(retry_after="65")
            return response()
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        model = ChatModel(client, "offline-model", request_pacer=RequestPacer(20), rate_limit_retries=2)
        self.assertEqual(model.respond("Instructions", [], []).text, "ok")
        self.assertEqual(starts, [100, 165])
        self.assertEqual(model.request_count, 2)
        self.assertEqual(model.successful_requests, 1)

    def test_retries_are_bounded_with_shared_exponential_cooldown(self):
        starts = []
        def create(**kwargs):
            starts.append(self.clock.now)
            raise RateError()
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        pacer = RequestPacer(20)
        model = ChatModel(client, "offline-model", request_pacer=pacer, rate_limit_retries=2)
        with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
            model.respond("Instructions", [], [])
        self.assertEqual(starts, [100, 120, 160])
        self.assertEqual(model.request_count, 3)
        self.assertEqual(model.successful_requests, 0)
        pacer.acquire()
        self.assertEqual(self.clock.now, 240)

    def test_expired_workflow_does_not_start_a_request(self):
        starts = []
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: starts.append(self.clock.now) or response())))
        model = ChatModel(client, 'fixture')
        with self.assertRaisesRegex(RuntimeError, 'elapsed-time budget'):
            RunBudget(seconds=0).respond(model, 'Instructions', [], [])
        self.assertEqual(starts, [])
        self.assertEqual(model.request_count, 0)
        self.assertIsNone(request_deadline.get())

    def test_pacing_wait_rechecks_deadline_before_sending(self):
        for seconds in (10, 20):
            with self.subTest(seconds=seconds):
                self.clock.now = 100
                starts = []
                pacer = RequestPacer(20)
                pacer.acquire()
                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                    create=lambda **kwargs: starts.append(self.clock.now) or response())))
                model = ChatModel(client, 'fixture', request_pacer=pacer)
                with self.assertRaisesRegex(RuntimeError, 'elapsed-time budget'):
                    RunBudget(seconds=seconds).respond(model, 'Instructions', [], [])
                self.assertEqual(self.clock.now, 120)
                self.assertEqual(starts, [])
                self.assertEqual(model.request_count, 0)

    def test_retry_after_wait_cannot_send_after_workflow_deadline(self):
        starts = []
        def create(**kwargs):
            starts.append(self.clock.now)
            raise RateError()
        model = ChatModel(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
                          'fixture', request_pacer=RequestPacer(20), rate_limit_retries=2)
        budget = RunBudget(seconds=30)
        budget.consume('model')
        with self.assertRaisesRegex(RuntimeError, 'elapsed-time budget'):
            budget.respond(model, 'Instructions', [], [])
        self.assertEqual(starts, [100, 120])
        self.assertEqual(model.request_count, 2)
        self.assertEqual(model.successful_requests, 0)
        self.assertEqual(budget.models, 1)
        self.assertIsNone(request_deadline.get())

    def test_inflight_request_can_finish_and_deadline_does_not_leak(self):
        starts = []
        def create(**kwargs):
            starts.append(self.clock.now)
            self.clock.now += 40
            return response()
        model = ChatModel(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), 'fixture')
        budget = RunBudget(seconds=30)
        self.assertEqual(budget.respond(model, 'Instructions', [], []).text, 'ok')
        self.assertIsNone(request_deadline.get())
        with self.assertRaisesRegex(RuntimeError, 'elapsed-time budget'):
            budget.consume('tool')
        self.assertEqual(model.respond('Independent call', [], []).text, 'ok')
        self.assertEqual(starts, [100, 140])

    def test_other_http_errors_are_not_retried(self):
        for status in (400, 401, 403, 500):
            with self.subTest(status=status):
                def create(**kwargs):
                    raise RateError(status)
                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
                model = ChatModel(client, "offline-model", request_pacer=RequestPacer(20), rate_limit_retries=2)
                with self.assertRaisesRegex(RuntimeError, "HTTP " + str(status)):
                    model.respond("Instructions", [], [])
                self.assertEqual(model.request_count, 1)

    def test_retry_after_accepts_http_date_and_rejects_invalid_values(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        future = datetime(2026, 10, 20, 0, 1, tzinfo=timezone.utc)
        with patch("agents.request_pacing.datetime") as dates:
            dates.now.return_value = now
            self.assertEqual(retry_after_seconds(RateError(retry_after=format_datetime(future)), 20), 60)
        for value in (None, "bad", "nan", "inf", "-1", "3"):
            self.assertEqual(retry_after_seconds(RateError(retry_after=value), 20), 20)

    def test_invalid_pacing_is_rejected_before_credentials_are_read(self):
        for values in ({"request_interval_seconds": -1}, {"request_interval_seconds": float("nan")},
                       {"request_interval_seconds": True}, {"request_interval_seconds": 0},
                       {"rate_limit_retries": 4}, {"rate_limit_retries": True}, {"max_retries": 1}):
            with self.subTest(values=values), patch.object(ModelRegistry, "_key", side_effect=AssertionError("No key read")):
                registry = ModelRegistry(force_profile="apinex_test", env_file=None)
                registry.config["profiles"]["apinex_test"].update(values)
                with self.assertRaises(ConfigurationError):
                    registry.get("Original")


if __name__ == "__main__":
    unittest.main()
