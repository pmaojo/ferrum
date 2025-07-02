import os
import sys
import types
import pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

# Stub agents modules before importing the router
sys.modules['agents'] = types.ModuleType('agents')
for mod_name in [
    'agents.generator',
    'agents.explainer',
    'agents.validator',
    'agents.component_designer',
    'agents.usecase_designer',
    'agents.filler',
    'agents.coordinator',
    'agents.team',
]:
    module = types.ModuleType(mod_name)
    sys.modules[mod_name] = module

sys.modules['agents.generator'].generate_yaml = lambda *a, **k: ""
sys.modules['agents.explainer'].explain_yaml = lambda *a, **k: ""
sys.modules['agents.validator'].validate_yaml = lambda *a, **k: True
sys.modules['agents.validator'].validate_usecase_prompt = lambda *a, **k: True
sys.modules['agents.component_designer'].design_component = lambda *a, **k: ""
sys.modules['agents.usecase_designer'].design_usecase = lambda *a, **k: ""
sys.modules['agents.filler'].fill_code = lambda *a, **k: ""
sys.modules['agents.filler'].fetch_context = lambda *a, **k: ""
class _C:
    def __init__(self, tools=None):
        pass

    def chat(self, messages, model=None):
        return ""

sys.modules['agents.coordinator'].Coordinator = _C
sys.modules['agents.team'].BackendExpert = object
sys.modules['agents.team'].FrontendExpert = object
sys.modules['agents.team'].UXDesigner = object
sys.modules['agents.team'].Coach = object

from fastapi.testclient import TestClient
from ai.main import app
import ai.router as router

client = TestClient(app)


def test_chat_route(monkeypatch):
    def fake_chat(self, messages, model=None):
        assert messages == [{'role': 'user', 'content': 'hi'}]
        assert model == 'gpt-4'
        return 'hello'

    monkeypatch.setattr(router, 'agent', type('obj', (), {'chat': fake_chat})())

    resp = client.post('/chat', json={'messages': [{'role': 'user', 'content': 'hi'}], 'model': 'gpt-4'})
    assert resp.status_code == 200
    assert resp.json() == {'message': 'hello'}


def test_fill_todo_route(monkeypatch):
    def fake_fill(task, anchor, model=None):
        assert task == 'add feature'
        assert anchor == 'file.rs'
        return 'filled code'

    monkeypatch.setattr(router, 'fill_code', fake_fill)
    resp = client.post('/fill-todo', json={'code': 'file.rs', 'instructions': 'add feature'})
    assert resp.status_code == 200
    assert resp.json() == {'code': 'filled code'}


def test_ai_team_route(monkeypatch):
    def fake_team(self, messages, model=None):
        assert messages == [{'role': 'user', 'content': 'plan'}]
        assert model == 'gpt-4'
        return 'team reply'

    monkeypatch.setattr(router, 'coordinator', type('obj', (), {'chat': fake_team})())

    resp = client.post('/ai-team', json={'messages': [{'role': 'user', 'content': 'plan'}], 'model': 'gpt-4'})
    assert resp.status_code == 200
    assert resp.json() == {'message': 'team reply'}


def test_refactor_route(monkeypatch):
    def fake_refactor(yaml, model=None):
        assert yaml == 'foo: bar'
        return 'refactored'

    monkeypatch.setattr(router.tools, 'suggest_refactor', fake_refactor)

    resp = client.post('/refactor/yaml', json={'yaml': 'foo: bar'})
    assert resp.status_code == 200
    assert resp.json() == {'text': 'refactored'}


def test_simulate_route(monkeypatch):
    def fake_simulate(yaml, model=None):
        assert yaml == 'foo: bar'
        return 'flow'

    monkeypatch.setattr(router.tools, 'simulate_flow', fake_simulate)

    resp = client.post('/simulate/flow', json={'yaml': 'foo: bar'})
    assert resp.status_code == 200
    assert resp.json() == {'text': 'flow'}

