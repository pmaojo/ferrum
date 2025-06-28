import requests

from .base import LLMBackend


class LocalLLMBackend(LLMBackend):
    """Backend for local models compatible with the OpenAI API schema."""

    def __init__(self, endpoint: str = "http://localhost:1234/v1/chat/completions", model: str = "lmstudio"):
        self.endpoint = endpoint
        self.model = model

    def generate_yaml(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a YAML architecture assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(self.endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
