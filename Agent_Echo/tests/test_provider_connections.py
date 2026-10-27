"""Offline routing, private-key loading and tool-loop contracts for trial APIs."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.connections import ModelRegistry
from agents.model import ChatModel, ConfigurationError, request_failure
from agents.preflight import check_connections
from agents.runtime import function_tool


class TrialProviderTests(unittest.TestCase):
    def test_chat_disables_parallel_calls_for_one_required_tool_only(self):
        for required, count in ((True, 1), (True, 2), (False, 1), (False, 0)):
            with self.subTest(required=required, count=count):
                requests = []
                message = SimpleNamespace(content="Fixture.", tool_calls=[],
                    model_dump=lambda **kw: {"role": "assistant", "content": "Fixture."})
                def create(**kwargs):
                    requests.append(kwargs)
                    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=message)])
                adapter = ChatModel(SimpleNamespace(chat=SimpleNamespace(
                    completions=SimpleNamespace(create=create))), "offline-model")
                tools = [function_tool(f"tool_{i}", "Fixture.", {}) for i in range(count)]
                adapter.respond("Instructions", [], tools, required)
                if required and count == 1:
                    self.assertIs(requests[0]["parallel_tool_calls"], False)
                    self.assertIs(requests[0]["tools"][0]["function"]["strict"], True)
                else:
                    self.assertNotIn("parallel_tool_calls", requests[0])
                self.assertEqual(requests[0]["tool_choice"], "none" if not count else "required" if required else "auto")

    def test_chat_preserves_explicit_strict_mode_without_mutating_tools(self):
        for strict in (True, False, None):
            with self.subTest(strict=strict):
                tools = [function_tool("lookup", "Read evidence.", {})]
                if strict is None:
                    tools[0].pop("strict")
                else:
                    tools[0]["strict"] = strict
                original = json.dumps(tools, sort_keys=True)
                requests = []
                message = SimpleNamespace(content="Done.", tool_calls=[],
                    model_dump=lambda **kw: {"role": "assistant", "content": "Done."})

                def create(**kwargs):
                    requests.append(kwargs)
                    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=message)])

                adapter = ChatModel(SimpleNamespace(chat=SimpleNamespace(
                    completions=SimpleNamespace(create=create))), "offline-model")
                adapter.respond("Instructions", [], tools, True)
                definition = requests[0]["tools"][0]["function"]
                self.assertEqual(definition, {key: value for key, value in tools[0].items() if key != "type"})
                self.assertEqual(json.dumps(tools, sort_keys=True), original)

    def test_responses_profiles_apply_configured_output_limit_and_usage(self):
        for profile in ('gw_azure', 'personal_openai'):
            for limit in (None, 3500, 6000):
                with self.subTest(profile=profile, limit=limit):
                    requests = []
                    response = SimpleNamespace(status='completed', output=[], output_text='Fixture.', usage=None)
                    client = SimpleNamespace(responses=SimpleNamespace(
                        create=lambda **kwargs: requests.append(kwargs) or response))
                    registry = ModelRegistry(force_profile=profile, env_file=None)
                    if limit is None:
                        registry.config['profiles'][profile].pop('max_output_tokens', None)
                    else:
                        registry.config['profiles'][profile]['max_output_tokens'] = limit
                    expected = 3500 if limit is None else limit
                    with patch.object(registry, '_client', return_value=client), patch('agents.model.record') as log:
                        registry.get('Original').respond('Instructions', [], [])
                    self.assertEqual(requests[0]['max_output_tokens'], expected)
                    self.assertFalse(requests[0]['store'])
                    log.assert_any_call('model_response_usage', adapter='responses', output_limit=expected)

    def test_final_default_uses_json_azure_settings_and_private_key(self):
        clients = []

        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)

        with TemporaryDirectory() as directory:
            private_file = Path(directory) / ".env"
            private_file.write_text(
                "GW_AZURE_OPENAI_KEY=offline-group-key\n"
                "NVIDIA_API_KEY=offline-unused-trial-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.dict("sys.modules", {
                "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
                registry = ModelRegistry(env_file=private_file)
                for profile in ("gw_azure", "gw_embeddings"):
                    registry.config["profiles"][profile]["endpoint"] = "https://offline-assigned-group.openai.azure.com/"
                registry.config["profiles"]["gw_azure"]["model"] = "offline-group-deployment"
                registry.config["profiles"]["gw_embeddings"]["model"] = "offline-group-embeddings"
                models = [registry.get(role) for role in registry.config["agents"]]
                self.assertTrue(all(model is models[0] for model in models))
                self.assertEqual(models[0].model, "offline-group-deployment")
                self.assertEqual(len(clients), 1)
                self.assertEqual(clients[0]["api_key"], "offline-group-key")
                self.assertEqual(clients[0]["azure_endpoint"], "https://offline-assigned-group.openai.azure.com/")
                self.assertEqual(clients[0]["api_version"], "2025-03-01-preview")
                self.assertTrue(all(item["profile"] == "gw_azure" for item in registry.describe().values()))
                self.assertEqual(registry.embeddings().model, "offline-group-embeddings")
                self.assertEqual(clients[1]["api_key"], "offline-group-key")
                self.assertNotIn("offline-group-key", json.dumps(registry.describe()))
                self.assertNotIn("GW_AZURE_OPENAI_KEY", os.environ)
                registry.close()

    def test_azure_does_not_fall_back_to_trial_keys_when_group_setup_is_missing(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "offline-nvidia", "OPENCODE_API_KEY": "offline-opencode"}, clear=True):
            registry = ModelRegistry(env_file=None)
            with self.assertRaisesRegex(ConfigurationError, "GW_AZURE_OPENAI_KEY"):
                registry.get("Original")
            self.assertEqual(registry.clients, {})
            self.assertEqual(registry.execution_summary()["generation_api_calls"], 0)

    def test_non_secret_environment_and_private_values_cannot_override_json(self):
        with TemporaryDirectory() as directory:
            private_file = Path(directory) / ".env"
            private_file.write_text("AZURE_OPENAI_DEPLOYMENT=offline-file-model\n", encoding="utf-8")
            with patch.dict(os.environ, {"AZURE_OPENAI_DEPLOYMENT": "offline-environment-model"}, clear=True):
                registry = ModelRegistry(env_file=private_file)
                registry.config["profiles"]["gw_azure"]["model"] = "offline-json-model"
                self.assertEqual(registry.describe()["Cherry"]["model"], "offline-json-model")
                self.assertEqual(registry._local_value("AZURE_OPENAI_DEPLOYMENT"), "")
                self.assertIsNone(registry._local_settings)

    def test_trial_profiles_route_probe_to_their_own_endpoint_and_model(self):
        for profile, variable, endpoint, model_name in (
            ("nvidia_test", "NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1",
             "nvidia/nemotron-3.5-super-vl-120b-a12b"),
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
                    progress = []
                    result = check_connections(registry, ["Cherry", "Vanilla"], progress=progress.append)
                    self.assertEqual(clients[0]["base_url"], endpoint)
                    self.assertEqual(clients[0]["api_key"], "offline-key")
                    self.assertEqual(clients[0]["timeout"], 120 if profile.startswith("nvidia_") else 45)
                    self.assertEqual(clients[0]["max_retries"], 0 if profile.startswith("nvidia_") else 1)
                    self.assertEqual(requests[0]["max_tokens"], 8192)
                    self.assertEqual(requests[0]["model"], model_name)
                    self.assertEqual(requests[0]["tool_choice"], "required")
                    self.assertEqual(requests[0]["tools"][0]["function"]["name"], "connection_check")
                    self.assertEqual(len(requests), 1)
                    self.assertEqual(result["execution"]["successful_generation_api_calls"], 1)
                    self.assertNotIn("offline-key", json.dumps(result))
                    self.assertEqual(len(progress), 1)
                    self.assertNotIn("offline-key", progress[0])
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
                self.assertIsNone(registry._local_settings)

    def test_invalid_timeout_and_retry_settings_fail_before_client_construction(self):
        for setting, values in (("timeout_seconds", (0, -1, 601, "120", True, float("nan"))),
                                ("max_retries", (-1, 4, "0", True))):
            for value in values:
                with self.subTest(setting=setting, value=value), patch.dict(os.environ, {}, clear=True):
                    registry = ModelRegistry(force_profile="nvidia_test", env_file=None)
                    registry.config["profiles"]["nvidia_test"][setting] = value
                    with self.assertRaisesRegex(ConfigurationError, setting):
                        registry.get("Cherry")
                    self.assertEqual(registry.clients, {})

    def test_output_limit_is_distinguished_from_provider_failure_without_raw_reasoning(self):
        response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="length",
            message=SimpleNamespace(content=None, reasoning_content="offline-private-text"))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
        model = ChatModel(client, "offline-model", max_output_tokens=8192)
        with self.assertRaisesRegex(RuntimeError, "output token budget exhausted") as raised:
            model.respond("Use tools.", [], [])
        self.assertNotIn("offline-private-text", str(raised.exception))
        self.assertEqual(model.successful_requests, 0)

    def test_environment_key_wins_without_reading_private_file(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "offline-env-key"}, clear=True), \
             patch("dotenv.dotenv_values", side_effect=AssertionError("Must not read a private file")):
            registry = ModelRegistry(force_profile="nvidia_test")
            self.assertEqual(registry._key("NVIDIA_API_KEY"), "offline-env-key")

    def test_incomplete_response_reports_only_a_safe_finish_reason(self):
        for reason, expected in (("malformed_function_call", "malformed_function_call"),
                                 ("offline-private-provider-detail", "unknown")):
            response = SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason)])
            client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
            model = ChatModel(client, "offline-model")
            with self.subTest(reason=reason), patch("agents.model.record") as logged:
                with self.assertRaisesRegex(RuntimeError, "finish reason: " + expected) as raised:
                    model.respond("Use evidence.", [], [])
                self.assertNotIn("offline-private-provider-detail", str(raised.exception))
                logged.assert_any_call("model_response_rejected", adapter="chat", finish_reason=expected)
                self.assertEqual(logged.call_args_list[-1].kwargs["finish_reason"], expected)
                self.assertNotIn("offline-private-provider-detail", str(logged.call_args_list))
                self.assertEqual(model.successful_requests, 0)

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
            self.assertEqual(models["Original"].model, "nvidia/nemotron-3.5-super-vl-120b-a12b")
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
             patch.object(ModelRegistry, "_local_value", side_effect=AssertionError("No private configuration access")), \
             patch.object(ModelRegistry, "_client", side_effect=AssertionError("No live client")), \
             patch("builtins.print"):
            self.assertEqual(run_agent.main(["--show-connections", "--profile", "nvidia_test"]), 0)
            self.assertEqual(run_agent.main(["cherry", "--manager", "M14", "--demo", "--profile", "opencode_test"]), 0)

    def test_json_endpoint_and_model_win_over_old_overrides_and_https_is_required(self):
        clients = []

        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)

        values = {"NVIDIA_API_KEY": "offline-key", "NVIDIA_MODEL": "offline-model",
                  "NVIDIA_BASE_URL": "https://offline-endpoint.invalid/v1"}
        with patch.dict(os.environ, values, clear=True), patch.dict("sys.modules", {
            "openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(force_profile="nvidia_test", env_file=None)
            registry.config["profiles"]["nvidia_test"].update(
                model="offline-json-model", endpoint="https://json-endpoint.invalid/v1")
            self.assertEqual(registry.get("Cherry").model, "offline-json-model")
            self.assertEqual(clients[0]["base_url"], "https://json-endpoint.invalid/v1")
            registry.close()
            invalid = ModelRegistry(force_profile="nvidia_test", env_file=None)
            invalid.config["profiles"]["nvidia_test"]["endpoint"] = "http://insecure.invalid/v1"
            with self.assertRaisesRegex(ConfigurationError, "HTTPS"):
                invalid.get("Cherry")
            self.assertEqual(len(clients), 1)

    def test_google_and_openai_clients_use_explicit_json_endpoints(self):
        clients = []
        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "offline-google", "OPENAI_API_KEY": "offline-openai",
                                   "OPENAI_BASE_URL": "https://ignored.invalid/v1"}, clear=True), \
             patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            for profile in ("google_test", "personal_openai"):
                registry = ModelRegistry(force_profile=profile, env_file=None)
                endpoint = "https://" + profile.replace("_", "-") + ".invalid/v1"
                registry.config["profiles"][profile].update(model="fixture-model", endpoint=endpoint)
                registry.get("Cherry")
                self.assertEqual(clients[-1]["base_url"], endpoint)
                registry.close()

    def test_legacy_non_secret_env_references_require_migration(self):
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "connections.json"
            config = ModelRegistry(env_file=None).config
            config["profiles"]["google_test"]["model_env"] = "GOOGLE_MODEL"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ConfigurationError, "Move model, endpoint and api_version"):
                ModelRegistry(config=config_path, env_file=None)

    def test_missing_json_endpoint_never_uses_sdk_or_environment_default(self):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://ignored.invalid/v1"}, clear=True), \
             patch.object(ModelRegistry, "_key", side_effect=AssertionError("No credential access")):
            for profile in ("google_test", "personal_openai", "nvidia_test"):
                with self.subTest(profile=profile):
                    registry = ModelRegistry(force_profile=profile, env_file=None)
                    registry.config["profiles"][profile].update(model="fixture", endpoint="")
                    with self.assertRaisesRegex(ConfigurationError, "endpoint in connections.json"):
                        registry.get("Cherry")
                    self.assertEqual(registry.clients, {})

    def test_azure_v1_uses_the_complete_json_url_without_hidden_suffix(self):
        clients = []
        def client(**kwargs):
            clients.append(kwargs)
            return SimpleNamespace(close=lambda: None)
        with patch.dict(os.environ, {"GW_AZURE_OPENAI_KEY": "offline-group"}, clear=True), \
             patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=client, AzureOpenAI=client)}):
            registry = ModelRegistry(env_file=None)
            endpoint = "https://assigned-resource.invalid/openai/v1/"
            registry.config["profiles"]["gw_azure"].update(azure_api="v1", endpoint=endpoint, model="assigned-deployment")
            registry.get("Cherry")
            self.assertEqual(clients[0]["base_url"], endpoint)
            self.assertNotIn("api_version", clients[0])
            registry.close()

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

    def test_http_diagnostics_distinguish_access_missing_models_and_limits_without_secrets(self):
        for status, expected in ((400, "parameters"), (401, "Authentication"), (403, "Access denied"),
                                 (404, "not found"), (429, "quota"), (503, "service error")):
            with self.subTest(status=status):
                error = RuntimeError("offline-key and private request text")
                error.status_code = status
                error.body = {"message": "offline-key and private request text"}
                diagnostic = str(request_failure(error))
                self.assertIn(f"HTTP {status}", diagnostic)
                self.assertIn(expected, diagnostic)
                self.assertNotIn("offline-key", diagnostic)
                self.assertNotIn("private request text", diagnostic)

    def test_opencode_free_restriction_and_timeouts_have_specific_safe_diagnostics(self):
        error = RuntimeError("offline-key")
        error.status_code = 403
        error.body = {"type": "FreeTierError", "message": "OpenCode's free tier can only be used from within OpenCode. offline-key"}
        diagnostic = str(request_failure(error))
        self.assertIn("FreeTierError", diagnostic)
        self.assertIn("cannot be used for Echo", diagnostic)
        self.assertNotIn("offline-key", diagnostic)
        timeout = type("APITimeoutError", (Exception,), {})("offline-key")
        self.assertIn("timed out", str(request_failure(timeout)))
        self.assertNotIn("offline-key", str(request_failure(timeout)))

    def test_ctrl_c_cancels_probe_cleanly_without_a_traceback(self):
        import run_agent
        from contextlib import redirect_stdout, redirect_stderr
        import io
        with patch("run_agent.check_connections", side_effect=KeyboardInterrupt), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
            result = run_agent.main(["--check-connection", "--profile", "nvidia_test"])
        self.assertEqual(result, 130)
        self.assertIn("cancelled", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
