import os
from dataclasses import dataclass
from typing import Protocol, Dict

import requests
import openai
import yaml
from anthropic import Anthropic



@dataclass
class LlmConfig:
    """Configuration options for LLM providers."""

    model: str = "openai"
    openai_api_key: str = ""
    ollama_endpoint: str = "http://localhost:1234/v1/chat/completions"


def load_config() -> LlmConfig:
    """Load configuration from ``LLM_CONFIG`` YAML and environment variables."""

    path = os.environ.get("LLM_CONFIG", "llm-config.yaml")
    data: Dict[str, Dict[str, str]] = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

    return LlmConfig(
        model=os.environ.get("MODEL", data.get("model", "openai")),
        openai_api_key=os.environ.get(
            "OPENAI_API_KEY", data.get("openai", {}).get("api_key", "")
        ),
        ollama_endpoint=os.environ.get(
            "LOCAL_ENDPOINT",
            data.get("ollama", {}).get(
                "endpoint", "http://localhost:1234/v1/chat/completions"
            ),
        ),
    )


class LlmProvider(Protocol):
    """Simple protocol for language model providers."""

    def call(
        self, prompt: str, system: str, model: str | None, config: LlmConfig
    ) -> str:
        """Return the model response for the given prompt using ``model`` if provided."""


class OpenAIProvider:
    def call(
        self, prompt: str, system: str, model: str | None, config: LlmConfig
    ) -> str:
        openai.api_key = config.openai_api_key
        selected = model or "gpt-4"
        response = openai.ChatCompletion.create(
            model=selected,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()


class OllamaProvider:
    def call(
        self, prompt: str, system: str, model: str | None, config: LlmConfig
    ) -> str:
        payload = {
            "model": model or "lmstudio",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(config.ollama_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class AnthropicProvider:
    def call(
        self, prompt: str, system: str, model: str | None, config: LlmConfig
    ) -> str:
        client = Anthropic()
        response = client.messages.create(
            model=model or "claude-2",
            messages=[{"role": "user", "content": prompt}],
            system=system,
        )
        return response.content[0].text.strip()


PROVIDERS: Dict[str, LlmProvider] = {
    "openai": OpenAIProvider(),
    "ollama": OllamaProvider(),
    "local": OllamaProvider(),
    "anthropic": AnthropicProvider(),
}


def call_llm(
    prompt: str,
    system: str,
    model: str | None = None,
    config: LlmConfig | None = None,
) -> str:
    """Call the configured language model provider."""

    cfg = config or load_config()
    selected = os.environ.get("MODEL", cfg.model)
    provider = PROVIDERS.get(selected)
    if provider is None:
        raise ValueError(f"Unknown model {selected}")
    return provider.call(prompt, system, model, cfg)
