import os
import requests
import openai
from anthropic import Anthropic


MODEL = os.environ.get("MODEL", "openai")
LOCAL_ENDPOINT = os.environ.get(
    "LOCAL_ENDPOINT", "http://localhost:1234/v1/chat/completions"
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


def call_llm(prompt: str, system: str) -> str:
    model = os.environ.get("MODEL", MODEL)
    if model == "openai":
        return call_openai(prompt, system)
    if model in {"local", "ollama"}:
        return call_ollama(prompt, system)
    if model == "anthropic":
        return call_anthropic(prompt, system)
    raise ValueError(f"Unknown model {model}")
