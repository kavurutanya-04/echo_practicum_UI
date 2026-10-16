"""Offline routing, private-key loading and tool-loop contracts for trial APIs."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.connections import ModelRegistry
from agents.model import ChatModel, ConfigurationError
from agents.preflight import check_connections
from agents.runtime import function_tool


class TrialProviderTests(unittest.TestCase):
    def test_trial_profiles_route_probe_to_their_own_endpoint_and_model(self):
        for profile, variable, endpoint, model_name in (
            ("nvidia_test", "NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1",
             "nvidia/nemotron-3-ultra-550b-a55b"),
            ("nvidia_glm_test", "NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1",
             "z-ai/glm-5.3-flash"),
            ("opencode_test", "OPENCODE_API_KEY", "https://opencode.ai/inference/openai/v1",
             "deepseek-v4.1-flash-free"),
        ):
            with self.subTest(profile=profile):
                clients, requests = [], []
                call = SimpleNamespace(id="probe", function=SimpleNamespace(
                    name="connection_check", arguments='{"status":"ok"}'))
                message = SimpleNamespace(content=None, tool_calls=[call], model_dump=lambda **kw: {
                    "role": "assistant", "tool_calls": [{"id": "probe", "type": "function",
                    "function": {"name": "connection_check", "arguments": '{"status":"ok"}'}}]})

                def create(**kwargs):
                    requests.append(kwargs)
                    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="tool_calls", message=message)])

                def client(**kwargs):
                    clients.append(kwargs)
                    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=lambda: None)

                values = {variable: "offline-key", "OPENAI_BASE_URL": "https://wrong-endpoint.invalid/v1"}
                with patch.dict(os.environ, values, clear=True), patch.dict("sys.modules", {
                    "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
                    registry = ModelRegistry(force_profile=profile, env_file=None)
                    result = check_connections(registry, ["Cherry", "Vanilla"])
                    self.assertEqual(clients[0]["base_url"], endpoint)
                    self.assertEqual(clients[0]["api_key"], "offline-key")
                    self.assertEqual(requests[0]["model"], model_name)
                    self.assertEqual(requests[0]["tool_choice"], "required")
                    self.assertEqual(requests[0]["tools"][0]["function"]["name"], "connection_check")
                    self.assertEqual(len(requests), 1)
                    self.assertEqual(result["execution"]["successful_generation_api_calls"], 1)
                    self.assertNotIn("offline-key", json.dumps(result))
                    if profile == "nvidia_glm_test":
                        self.assertEqual(requests[0]["reasoning_effort"], "low")
                        self.assertIs(requests[0]["extra_body"]["chat_template_kwargs"]["clear_thinking"], True)
                    else:
                        self.assertNotIn("reasoning_effort", requests[0])
                        self.assertNotIn("extra_body", requests[0])
                    registry.close()

    def test_private_keys_are_literal_and_do_not_change_environment(self):
        with TemporaryDirectory() as directory:
            private_file = Path(directory) / ".env"
            private_file.write_text('NVIDIA_API_KEY="offline-${OTHER}-key"\n', encoding="utf-8")
            with patch.dict(os.environ, {"OTHER": "must-not-expand"}, clear=True):
                registry = ModelRegistry(force_profile="nvidia_test", env_file=private_file)
                self.assertEqual(registry._key("NVIDIA_API_KEY"), "offline-${OTHER}-key")
                self.assertNotIn("NVIDIA_API_KEY", os.environ)
                self.assertNotIn("offline-${OTHER}-key", json.dumps(registry.describe()))
                registry.close()
                self.assertIsNone(registry._local_keys)

    def test_environment_key_wins_without_reading_private_file(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "offline-env-key"}, clear=True), \
             patch("dotenv.dotenv_values", side_effect=AssertionError("Must not read a private file")):
            registry = ModelRegistry(force_profile="nvidia_test")
            self.assertEqual(registry._key("NVIDIA_API_KEY"), "offline-env-key")

    def test_missing_trial_key_does_not_use_another_providers_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "offline-other-key"}, clear=True):
            for profile in ("nvidia_test", "nvidia_glm_test", "opencode_test"):
                registry = ModelRegistry(force_profile=profile, env_file=None)
                with self.assertRaisesRegex(ConfigurationError, "No API connection was attempted"):
                    registry.get("Cherry")
                self.assertEqual(registry.clients, {})

    def test_one_workflow_can_use_three_models_and_two_provider_keys(self):
        clients = []

        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)

        values = {"NVIDIA_API_KEY": "offline-nvidia-key", "OPENCODE_API_KEY": "offline-opencode-key"}
        assignments = {"Original": "nvidia_test", "Cherry": "nvidia_glm_test", "Vanilla": "opencode_test",
                       "Lime": "nvidia_test", "ZeroSugar": "nvidia_glm_test"}
        with patch.dict(os.environ, values, clear=True), patch.dict("sys.modules", {
            "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(env_file=None)
            registry.config["agents"].update(assignments)
            models = {role: registry.get(role) for role in assignments}
            self.assertEqual(models["Cherry"].model, "z-ai/glm-5.3-flash")
            self.assertEqual(models["Vanilla"].model, "deepseek-v4.1-flash-free")
            self.assertEqual(models["Original"].model, "nvidia/nemotron-3-ultra-550b-a55b")
            self.assertIs(models["Cherry"], models["ZeroSugar"])
            self.assertIs(models["Original"], models["Lime"])
            self.assertIsNot(models["Original"], models["Cherry"])
            self.assertEqual(len(clients), 3)
            self.assertEqual({item["api_key"] for item in clients}, set(values.values()))
            self.assertNotIn("offline-nvidia-key", json.dumps(registry.describe()))
            self.assertNotIn("offline-opencode-key", json.dumps(registry.describe()))
            registry.close()

    def test_new_collaborator_can_load_both_keys_from_their_own_private_file(self):
        clients = []

        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)

        with TemporaryDirectory() as directory:
            private_file = Path(directory) / ".env"
            private_file.write_text("NVIDIA_API_KEY=offline-local-nvidia\nOPENCODE_API_KEY=offline-local-opencode\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.dict("sys.modules", {
                "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
                for profile in ("nvidia_test", "nvidia_glm_test", "opencode_test"):
                    registry = ModelRegistry(force_profile=profile, env_file=private_file)
                    registry.get("Cherry")
                    registry.close()
                self.assertEqual([item["api_key"] for item in clients], [
                    "offline-local-nvidia", "offline-local-nvidia", "offline-local-opencode"])
                self.assertNotIn("NVIDIA_API_KEY", os.environ)

    def test_inspection_and_demo_do_not_read_keys_or_construct_clients(self):
        import run_agent
        with patch.object(ModelRegistry, "_key", side_effect=AssertionError("No key access")), \
             patch.object(ModelRegistry, "_client", side_effect=AssertionError("No live client")), \
             patch("builtins.print"):
            self.assertEqual(run_agent.main(["--show-connections", "--profile", "nvidia_test"]), 0)
            self.assertEqual(run_agent.main(["cherry", "--manager", "M14", "--demo", "--profile", "opencode_test"]), 0)

    def test_endpoint_and_model_overrides_are_explicit_and_https_required(self):
        clients = []

        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)

        values = {"NVIDIA_API_KEY": "offline-key", "NVIDIA_MODEL": "offline-model",
                  "NVIDIA_BASE_URL": "https://offline-endpoint.invalid/v1"}
        with patch.dict(os.environ, values, clear=True), patch.dict("sys.modules", {
            "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(force_profile="nvidia_test", env_file=None)
            self.assertEqual(registry.get("Cherry").model, "offline-model")
            self.assertEqual(clients[0]["base_url"], values["NVIDIA_BASE_URL"])
            registry.close()
            with patch.dict(os.environ, {"NVIDIA_BASE_URL": "http://offline-endpoint.invalid/v1"}):
                with self.assertRaisesRegex(ConfigurationError, "HTTPS"):
                    ModelRegistry(force_profile="nvidia_test", env_file=None).get("Cherry")
            self.assertEqual(len(clients), 1)

    def test_reasoning_content_survives_a_tool_round_trip(self):
        requests = []
        call = SimpleNamespace(id="tool-1", function=SimpleNamespace(name="lookup", arguments="{}"))
        message = SimpleNamespace(content=None, tool_calls=[call], model_dump=lambda **kw: {
            "role": "assistant", "tool_calls": [{"id": "tool-1", "type": "function",
            "function": {"name": "lookup", "arguments": "{}"}}], "reasoning_content": "offline-reasoning"})

        def create(**kwargs):
            requests.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason="tool_calls", message=message)])

        model = ChatModel(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), "fixture")
        tools = [function_tool("lookup", "Read evidence.", {})]
        turn = model.respond("Instructions", [{"role": "user", "content": "Question"}], tools, True)
        history = [{"role": "user", "content": "Question"}, *turn.output_items,
                   {"type": "function_call_output", "call_id": "tool-1", "output": "{}"}]
        model.respond("Instructions", history, tools)
        self.assertEqual(requests[1]["messages"][2]["reasoning_content"], "offline-reasoning")
        self.assertEqual(requests[1]["messages"][3]["tool_call_id"], "tool-1")

    def test_provider_error_does_not_expose_raw_payload(self):
        def create(**kwargs):
            raise RuntimeError("offline-key and private request payload")

        model = ChatModel(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), "fixture")
        with self.assertRaises(RuntimeError) as raised:
            model.respond("Instructions", [{"role": "user", "content": "Question"}], [])
        self.assertNotIn("offline-key", str(raised.exception))
        self.assertIn("selected profile", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
