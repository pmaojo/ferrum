import os
import sys
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

spec = importlib.util.spec_from_file_location(
    "llm_client", os.path.join(ROOT, "ai", "services", "llm_client.py")
)
llm_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_client)


class DummyProvider:
    def __init__(self, name):
        self.name = name
        self.called = False
        self.args = None

    def call(self, prompt: str, system: str) -> str:
        self.called = True
        self.args = (prompt, system)
        return self.name


def test_openai_provider_selected(monkeypatch):
    prov = DummyProvider("openai")
    monkeypatch.setitem(llm_client.PROVIDERS, "openai", prov)
    result = llm_client.call_llm("p", "s", "openai")
    assert result == "openai"
    assert prov.called
    assert prov.args == ("p", "s")


def test_ollama_provider_selected(monkeypatch):
    prov = DummyProvider("ollama")
    monkeypatch.setitem(llm_client.PROVIDERS, "ollama", prov)
    result = llm_client.call_llm("p", "s", "ollama")
    assert result == "ollama"
    assert prov.called


def test_anthropic_provider_selected(monkeypatch):
    prov = DummyProvider("anthropic")
    monkeypatch.setitem(llm_client.PROVIDERS, "anthropic", prov)
    result = llm_client.call_llm("p", "s", "anthropic")
    assert result == "anthropic"
    assert prov.called

