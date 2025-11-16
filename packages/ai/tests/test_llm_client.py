from ..services import llm_client


class DummyProvider:
    def __init__(self, name):
        self.name = name
        self.called = False
        self.args = None

    def call(
        self,
        prompt: str,
        system: str,
        model: str | None = None,
        config: llm_client.LlmConfig | None = None,
    ) -> str:
        self.called = True
        self.args = (prompt, system, model, config)
        return self.name


def test_openai_provider_selected(monkeypatch):
    prov = DummyProvider("openai")
    cfg = llm_client.LlmConfig(model="openai")
    monkeypatch.setitem(llm_client.PROVIDERS, "openai", prov)
    result = llm_client.call_llm("p", "s", "gpt-4", config=cfg)
    assert result == "openai"
    assert prov.called
    assert prov.args == ("p", "s", "gpt-4", cfg)


def test_ollama_provider_selected(monkeypatch):
    prov = DummyProvider("ollama")
    cfg = llm_client.LlmConfig(model="ollama")
    monkeypatch.setitem(llm_client.PROVIDERS, "ollama", prov)
    result = llm_client.call_llm("p", "s", config=cfg)
    assert result == "ollama"
    assert prov.called


def test_anthropic_provider_selected(monkeypatch):
    prov = DummyProvider("anthropic")
    cfg = llm_client.LlmConfig(model="anthropic")
    monkeypatch.setitem(llm_client.PROVIDERS, "anthropic", prov)
    result = llm_client.call_llm("p", "s", config=cfg)
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
    cfg = llm_client.LlmConfig()
    result = prov.call("p", "s", model="test-model", config=cfg)
    assert result == "ok"
    assert captured["model"] == "test-model"


def test_load_config_uses_env_and_file(tmp_path, monkeypatch):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("model: ollama")
    monkeypatch.setenv("LLM_CONFIG", str(cfg_file))
    monkeypatch.setenv("MODEL", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "abc")
    cfg = llm_client.load_config()
    assert cfg.model == "openai"
    assert cfg.openai_api_key == "abc"
