from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))
from ui_adapters.rest_api.settings import RestApiSettings


def test_invalid_port(monkeypatch):
    monkeypatch.setenv("GRAPHRAG_PORT", "not-an-int")
    with pytest.raises(ValidationError):
        RestApiSettings()


def test_invalid_boolean(monkeypatch):
    monkeypatch.setenv("USE_EMBEDDINGS", "maybe")
    with pytest.raises(ValidationError):
        RestApiSettings()


def test_allowed_origins_parsing(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://a.com","http://b.com"]')
    settings = RestApiSettings()
    assert settings.allowed_origins == ["https://a.com", "http://b.com"]
