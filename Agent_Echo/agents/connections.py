"""Named connection profiles. Keys remain in environment variables, never JSON."""

import json
import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse

from .model import ConfigurationError, ResponsesModel, ChatModel

AGENTS = ("Original", "Cherry", "Vanilla", "ZeroSugar")
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "connections.json"
GOOGLE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/"


class ModelRegistry:
    def __init__(self, config=DEFAULT_CONFIG, force_profile=None):
        self.config = json.loads(Path(config).read_text(encoding="utf-8"))
        self.force_profile = force_profile
        self.clients, self.models = {}, {}
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

    def _client(self, name):
        if name in self.clients:
            return self.clients[name]
        profile = self.config["profiles"].get(name)
        if not profile or profile.get("provider") not in {"azure", "openai", "google"}:
            raise ConfigurationError("Unsupported connection profile.")
        if profile.get("api") not in {"chat", "responses", "embeddings"} or (profile["provider"] == "google" and profile["api"] == "responses"):
            raise ConfigurationError("The profile API is unsupported for this provider.")
        required = [profile["key_env"], profile["model_env"]]
        if profile.get("endpoint_env"):
            required.append(profile["endpoint_env"])
        if any(not os.getenv(variable) for variable in required):
            raise ConfigurationError("Missing profile configuration; set variables: " + ", ".join(required) +
                                     ". No API connection was attempted.")
        endpoint = os.getenv(profile.get("endpoint_env", ""), "")
        if endpoint and (urlparse(endpoint).scheme != "https" or not urlparse(endpoint).hostname):
            raise ConfigurationError("The configured cloud endpoint must use HTTPS.")
        try:
            from openai import AzureOpenAI, OpenAI
        except ImportError:
            raise ConfigurationError("Install requirements.txt in the project environment.") from None
        options = {"api_key": os.environ[profile["key_env"]], "timeout": 45, "max_retries": 1}
        if profile["provider"] == "azure" and profile.get("azure_api", "legacy") == "legacy":
            client = AzureOpenAI(azure_endpoint=endpoint,
                api_version=os.getenv(profile.get("api_version_env", "AZURE_OPENAI_API_VERSION"), "2025-03-01-preview"), **options)
        elif profile["provider"] == "azure":
            client = OpenAI(base_url=endpoint.rstrip("/") + "/openai/v1/", **options)
        elif profile["provider"] == "google":
            client = OpenAI(base_url=GOOGLE_ENDPOINT, **options)
        else:
            client = OpenAI(**options)
        self.clients[name] = client
        return client

    def get(self, agent):
        name = self.profile_for(agent)
        if name not in self.models:
            profile = self.config["profiles"][name]
            client = self._client(name)
            model_name = os.environ[profile["model_env"]]
            adapter = ChatModel if profile["api"] == "chat" else ResponsesModel
            self.models[name] = adapter(client, model_name)
        # A shared adapter is stateless: conversation history is held by each agent run.
        return self.models[name]

    def embeddings(self, name=None):
        name = name or self.config["retrieval"]["embedding_profile"]
        profile = self.config["profiles"].get(name)
        if not profile or profile["api"] != "embeddings":
            raise ConfigurationError("Select a defined embedding connection profile.")
        client = self._client(name)
        endpoint = os.getenv(profile.get("endpoint_env", ""), profile["provider"])
        identity = name + ":" + profile["provider"] + ":" + os.environ[profile["model_env"]] + ":" + hashlib.sha256(endpoint.encode()).hexdigest()[:16]
        return EmbeddingModel(client, os.environ[profile["model_env"]], identity)

    def close(self):
        for client in self.clients.values():
            client.close()


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
