from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import sys
import types
import importlib
from pathlib import Path


@pytest.fixture
def client():
    base_path = Path(__file__).resolve().parent.parent / 'ui_adapters' / 'rest_api'
    package = types.ModuleType('ui_adapters.rest_api')
    package.__path__ = [str(base_path)]
    sys.modules['ui_adapters.rest_api'] = package

    stub = types.SimpleNamespace(ServiceContainer=object, get_container=lambda: None)
    sys.modules['ui_adapters.rest_api.dependencies'] = stub

    # Stub application services module structure
    app_pkg = types.ModuleType('application')
    services_pkg = types.ModuleType('application.services')
    sb_module = types.SimpleNamespace(
        persist_initial_snapshot=lambda project_path: None,
        synchronize=lambda mode, triples: None,
    )
    services_pkg.synchronization_bridge = sb_module
    app_pkg.services = services_pkg
    sys.modules['application'] = app_pkg
    sys.modules['application.services'] = services_pkg
    sys.modules['application.services.synchronization_bridge'] = sb_module

    sync = importlib.import_module('ui_adapters.rest_api.routes.sync')

    app = FastAPI()
    app.include_router(sync.router)
    return TestClient(app)


def test_init_route(monkeypatch, client):
    called = {}

    def fake_init(path):
        called['path'] = path
        return {'result': 'ok'}

    monkeypatch.setattr(
        'application.services.synchronization_bridge.persist_initial_snapshot',
        fake_init,
    )

    resp = client.post('/api/v1/init', json={'project_path': '/tmp/proj'})
    assert resp.status_code == 200
    assert resp.json() == {'result': 'ok'}
    assert called['path'] == '/tmp/proj'


def test_sync_incremental_route(monkeypatch, client):
    called = {}

    def fake_sync(mode, triples):
        called['mode'] = mode
        called['triples'] = triples
        return {'status': 'synced'}

    monkeypatch.setattr(
        'application.services.synchronization_bridge.synchronize',
        fake_sync,
    )

    payload = {
        'mode': 'incremental',
        'triples': [{'subject': 's', 'predicate': 'p', 'object': 'o'}],
    }

    resp = client.post('/api/v1/sync', json=payload)
    assert resp.status_code == 200
    assert resp.json() == {'status': 'synced'}
    assert called['mode'] == 'incremental'
    assert called['triples'] == payload['triples']
