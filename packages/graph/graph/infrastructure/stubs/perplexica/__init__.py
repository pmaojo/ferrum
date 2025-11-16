"""Stub package for the imaginary Perplexica client used in tests."""

from types import SimpleNamespace

from .exceptions import QuotaExceeded

__all__ = ["Client", "exceptions"]


class Client:
    """Minimal Perplexica client stub."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, *, prompt: str, model: str, stream: bool = False, **kwargs):
        if stream:
            return [SimpleNamespace(text="")]  # iterable of chunks
        return SimpleNamespace(text="")

    def embed(self, *, text, model: str):
        if isinstance(text, list):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.0]) for _ in text])
        return SimpleNamespace(embedding=[0.0])

    def moderate(self, *, text: str):
        return SimpleNamespace(result={"flagged": False})

    def count_tokens(self, text: str):
        return SimpleNamespace(total_tokens=len(text.split()))

    def list_models(self):
        return []



