from anthropic import Anthropic

from .base import LLMBackend


class AnthropicBackend(LLMBackend):
    """Backend for Anthropic's Claude models."""

    def __init__(self, model: str = "claude-2"):
        self.client = Anthropic()
        self.model = model

    def generate_yaml(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            system="You are an architecture compiler.",
        )
        return response.content[0].text.strip()
