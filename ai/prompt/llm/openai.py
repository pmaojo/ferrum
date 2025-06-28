import openai

from .base import LLMBackend


class OpenAIBackend(LLMBackend):
    """Backend that delegates calls to the OpenAI API."""

    def __init__(self, model: str = "gpt-4"):
        self.model = model

    def generate_yaml(self, prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an architecture compiler."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
