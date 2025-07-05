import os
from typing import Protocol, Dict

import requests
import openai
import yaml
from anthropic import Anthropic


config_path = os.environ.get("LLM_CONFIG", "llm-config.yaml")
CONFIG = {}
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f) or {}

MODEL = os.environ.get("MODEL", CONFIG.get("model", "openai"))
LOCAL_ENDPOINT = os.environ.get(
    "LOCAL_ENDPOINT",
    CONFIG.get("ollama", {}).get(
        "endpoint", "http://localhost:1234/v1/chat/completions"
    ),
)

openai.api_key = os.environ.get(
    "OPENAI_API_KEY", CONFIG.get("openai", {}).get("api_key", "")
)


class LlmProvider(Protocol):
    """Simple protocol for language model providers."""

    def call(self, prompt: str, system: str, model: str | None = None) -> str:
        """Return the model response for the given prompt using ``model`` if provided."""


class OpenAIProvider:
    def call(self, prompt: str, system: str, model: str | None = None) -> str:
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
    def call(self, prompt: str, system: str, model: str | None = None) -> str:
        payload = {
            "model": model or "lmstudio",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(LOCAL_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class AnthropicProvider:
    def call(self, prompt: str, system: str, model: str | None = None) -> str:
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


def call_llm(prompt: str, system: str, model: str | None = None) -> str:
    selected = os.environ.get("MODEL", MODEL)
    provider = PROVIDERS.get(selected)
    if provider is None:
        raise ValueError(f"Unknown model {selected}")
    return provider.call(prompt, system, model)
