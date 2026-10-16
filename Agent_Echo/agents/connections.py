"""Named profiles with keys in environment variables or a private local .env."""

import json
import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse

from .model import ConfigurationError, ResponsesModel, ChatModel
from .execution_log import logged_model

AGENTS = ("Original", "Cherry", "Vanilla", "Lime", "ZeroSugar")
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "connections.json"
DEFAULT_ENV = DEFAULT_CONFIG.with_name(".env")
GOOGLE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/"


class ModelRegistry:
    def __init__(self, config=DEFAULT_CONFIG, force_profile=None, env_file=DEFAULT_ENV):
        self.config = json.loads(Path(config).read_text(encoding="utf-8"))
        self.force_profile = force_profile
        self.clients, self.models = {}, {}
        self.env_file = Path(env_file) if env_file is not None else None
        self._local_settings = None
        if force_profile and force_profile not in self.config["profiles"]:
            raise ConfigurationError("Unknown connection profile.")

    def profile_for(self, agent):
        if agent not in AGENTS:
            raise ConfigurationError("Unknown agent role.")
        selected = self.force_profile or os.getenv(f"ECHO_{agent.upper()}_PROFILE") or \
            self.config["agents"].get(agent) or os.getenv("ECHO_DEFAULT_PROFILE") or self.config["default_profile"]
        if selected not in self.config["profiles"]:
            raise ConfigurationError("Selected connection profile is not defined.")
        if self.config["profiles"][selected]["api"] == "embeddings":
            raise ConfigurationError("An embedding profile cannot power an agent.")
        return selected

    def describe(self):
        # No key values or key-presence checks are read by this method.
        return {agent: {"profile": name, **self.config["profiles"][name]}
                for agent in AGENTS for name in [self.profile_for(agent)]}

    def execution_summary(self):
        """Actual adapter activity, without credentials or request content."""
        return {"generation_api_calls": sum(model.request_count for model in self.models.values()),
                "successful_generation_api_calls": sum(model.successful_requests for model in self.models.values()),
                "profiles_used": {name: {"model": model.model, "api_calls": model.request_count,
                    "successful_api_calls": model.successful_requests} for name, model in self.models.items()}}

    def _value(self, profile, field):
        variable = profile.get(field + "_env", "")
        return os.getenv(variable) or self._local_value(variable) or profile.get(field, "")

    def _local_value(self, variable):
        # Read only the explicitly requested variable, during live setup.
        # Agent/profile selection stays public; never change os.environ or print values.
        if not variable:
            return ""
        if self._local_settings is None:
            self._local_settings = {}
            if self.env_file is not None and self.env_file.is_file():
                try:
                    from dotenv import dotenv_values
                except ImportError:
                    raise ConfigurationError("Install requirements.txt to load the private .env file.") from None
                self._local_settings = dotenv_values(self.env_file, encoding="utf-8-sig", interpolate=False)
        return self._local_settings.get(variable) or ""

    def _key(self, variable):
        return os.getenv(variable) or self._local_value(variable)

    def _client(self, name):
        if name in self.clients:
            return self.clients[name]
        profile = self.config["profiles"].get(name)
        if not profile or profile.get("provider") not in {"azure", "openai", "google", "openai_compatible"}:
            raise ConfigurationError("Unsupported connection profile.")
        if profile.get("api") not in {"chat", "responses", "embeddings"} or (profile["provider"] == "google" and profile["api"] == "responses"):
            raise ConfigurationError("The profile API is unsupported for this provider.")
        if profile["provider"] == "openai_compatible" and profile["api"] != "chat":
            raise ConfigurationError("Custom compatible profiles currently support Chat Completions only.")
        model_name, endpoint = self._value(profile, "model"), self._value(profile, "endpoint")
        required = [profile["key_env"]]
        if not profile.get("model"):
            required.append(profile.get("model_env", "model"))
        if profile.get("endpoint_env") and not profile.get("endpoint"):
            required.append(profile["endpoint_env"])
        if not model_name or (profile.get("endpoint_env") and not endpoint):
            raise ConfigurationError("Missing profile configuration; set variables: " + ", ".join(required) +
                                     " in the environment or private .env file. No API connection was attempted.")
        if profile["provider"] == "openai_compatible" and not endpoint:
            raise ConfigurationError("A custom compatible profile requires an explicit HTTPS endpoint.")
        if endpoint and (urlparse(endpoint).scheme != "https" or not urlparse(endpoint).hostname):
            raise ConfigurationError("The configured cloud endpoint must use HTTPS.")
        timeout = profile.get("timeout_seconds", 45)
        retries = profile.get("max_retries", 1)
        if type(timeout) not in {int, float} or not 0 < timeout <= 600:
            raise ConfigurationError("timeout_seconds must be a number greater than 0 and at most 600.")
        if type(retries) is not int or not 0 <= retries <= 3:
            raise ConfigurationError("max_retries must be an integer from 0 to 3.")
        key = self._key(profile["key_env"])
        if not key:
            raise ConfigurationError("Missing profile configuration; set variables: " + ", ".join(required) +
                                     " in the environment or put the API key in the private .env file. No API connection was attempted.")
        try:
            from openai import AzureOpenAI, OpenAI
        except ImportError:
            raise ConfigurationError("Install requirements.txt in the project environment.") from None
        options = {"api_key": key, "timeout": timeout, "max_retries": retries}
        if profile["provider"] == "azure" and profile.get("azure_api", "legacy") == "legacy":
            client = AzureOpenAI(azure_endpoint=endpoint,
                api_version=self._value(profile, "api_version") or "2025-03-01-preview", **options)
        elif profile["provider"] == "azure":
            client = OpenAI(base_url=endpoint.rstrip("/") + "/openai/v1/", **options)
        elif profile["provider"] == "google":
            client = OpenAI(base_url=GOOGLE_ENDPOINT, **options)
        elif profile["provider"] == "openai_compatible":
            client = OpenAI(base_url=endpoint, **options)
        else:
            client = OpenAI(**options)
        self.clients[name] = client
        return client

    def get(self, agent):
        name = self.profile_for(agent)
        if name not in self.models:
            profile = self.config["profiles"][name]
            client = self._client(name)
            model_name = self._value(profile, "model")
            if profile["api"] == "chat":
                self.models[name] = ChatModel(client, model_name,
                    max_output_tokens=profile.get("max_output_tokens", 3500),
                    reasoning_effort=profile.get("reasoning_effort"),
                    clear_thinking=profile.get("clear_thinking"))
            else:
                self.models[name] = ResponsesModel(client, model_name)
        # A shared adapter is stateless: conversation history is held by each agent run.
        return logged_model(self.models[name], agent, name)

    def embeddings(self, name=None):
        name = name or self.config["retrieval"]["embedding_profile"]
        profile = self.config["profiles"].get(name)
        if not profile or profile["api"] != "embeddings":
            raise ConfigurationError("Select a defined embedding connection profile.")
        client = self._client(name)
        endpoint = self._value(profile, "endpoint") or profile["provider"]
        model_name = self._value(profile, "model")
        identity = name + ":" + profile["provider"] + ":" + model_name + ":" + hashlib.sha256(endpoint.encode()).hexdigest()[:16]
        return EmbeddingModel(client, model_name, identity)

    def close(self):
        for client in self.clients.values():
            client.close()
        self._local_settings = None


class EmbeddingModel:
    def __init__(self, client, model, identity):
        self.client, self.model, self.identity = client, model, identity

    def embed(self, texts):
        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
            vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        except Exception:
            raise RuntimeError("Embedding request failed; no semantic results were accepted.") from None
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding response count does not match the input batch.")
        return vectors
