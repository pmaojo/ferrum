"""Stub of google.generativeai used for tests."""

from types import SimpleNamespace

# Functions expected to be patched in tests
configure = lambda **_: None
list_models = lambda: None

class GenerativeModel:
    def __init__(self, *_, **__):
        pass
    def generate_content(self, *_, **__):
        return SimpleNamespace(text="")

def get_embedding_model(*_, **__):
    return GenerativeModel()

def count_tokens(*_, **__):
    return SimpleNamespace(total_tokens=0)

class types(SimpleNamespace):
    class HarmCategory(SimpleNamespace):
        pass
    class HarmBlockThreshold(SimpleNamespace):
        pass

def list_models():
    """Stub list_models function used in tests."""
    return []