from ..services import llm_client


class DummyProvider:
    def __init__(self, name):
        self.name = name
        self.called = False
        self.args = None

    def call(self, prompt: str, system: str, model: str | None = None) -> str:
        self.called = True
        self.args = (prompt, system, model)
        return self.name


def test_openai_provider_selected(monkeypatch):
    prov = DummyProvider("openai")
    monkeypatch.setenv("MODEL", "openai")
    monkeypatch.setitem(llm_client.PROVIDERS, "openai", prov)
    result = llm_client.call_llm("p", "s", "gpt-4")
    assert result == "openai"
    assert prov.called
    assert prov.args == ("p", "s", "gpt-4")


def test_ollama_provider_selected(monkeypatch):
    prov = DummyProvider("ollama")
    monkeypatch.setenv("MODEL", "ollama")
    monkeypatch.setitem(llm_client.PROVIDERS, "ollama", prov)
    result = llm_client.call_llm("p", "s")
    assert result == "ollama"
    assert prov.called


def test_anthropic_provider_selected(monkeypatch):
    prov = DummyProvider("anthropic")
    monkeypatch.setenv("MODEL", "anthropic")
    monkeypatch.setitem(llm_client.PROVIDERS, "anthropic", prov)
    result = llm_client.call_llm("p", "s")
    assert result == "anthropic"
    assert prov.called


def test_openai_provider_forwards_model(monkeypatch):
    captured = {}

    def fake_create(*, model, messages):
        captured["model"] = model
        class R:
            choices = [type("c", (), {"message": type("m", (), {"content": "ok"})()})()]
        return R()

    monkeypatch.setattr(llm_client.openai.ChatCompletion, "create", fake_create)
    prov = llm_client.OpenAIProvider()
    result = prov.call("p", "s", model="test-model")
    assert result == "ok"
    assert captured["model"] == "test-model"

