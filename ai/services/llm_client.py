import os
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


def call_openai(prompt: str, system: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def call_ollama(prompt: str, system: str) -> str:
    payload = {
        "model": "lmstudio",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    response = requests.post(LOCAL_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def call_anthropic(prompt: str, system: str) -> str:
    client = Anthropic()
    response = client.messages.create(
        model="claude-2",
        messages=[{"role": "user", "content": prompt}],
        system=system,
    )
    return response.content[0].text.strip()


def call_llm(prompt: str, system: str, model: str | None = None) -> str:
    selected = model or os.environ.get("MODEL", MODEL)
    if selected == "openai":
        return call_openai(prompt, system)
    if selected in {"local", "ollama"}:
        return call_ollama(prompt, system)
    if selected == "anthropic":
        return call_anthropic(prompt, system)
    raise ValueError(f"Unknown model {selected}")
