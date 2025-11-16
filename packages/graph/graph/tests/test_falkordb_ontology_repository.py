import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
pytest.importorskip("redis")

spec = importlib.util.spec_from_file_location(
    "falkordb_ontology_repository",
    Path(__file__).resolve().parents[1]
    / "adapters"
    / "repositories"
    / "falkordb_ontology_repository.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FalkorDBOntologyRepository = module.FalkorDBOntologyRepository
from domain.entities import OntologyVersion, ScientificDomain

def create_repo_with_result(result):
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.execute_command.return_value = result
    with patch('adapters.falkordb_ontology_repository.redis.Redis.from_url', return_value=mock_client):
        repo = FalkorDBOntologyRepository('redis://localhost:6379')
    return repo, mock_client



class FakeRedis:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.queries = []

    def ping(self):
        pass

    def execute_command(self, command, graph_name, query, params=None):
        self.queries.append(query)
        for marker, resp in self.responses.items():
            if marker in query:
                return resp
        return []


def test_get_version_history_parses_results(mocker):
    history_resp = [
        [
            "id",
            "checksum",
            "parent_version",
            "tenant_id",
            "domain",
            "created_at",
            "axioms",
        ],
        [
            ["v2", "cs2", "v1", "t", "general", "2023-01-02T00:00:00", ["A"]],
            ["v1", "cs1", None, "t", "general", "2023-01-01T00:00:00", ["B"]],
        ],
    ]
    fake = FakeRedis({"ORDER BY": history_resp})
    mocker.patch.object(module, "redis")
    module.redis.from_url.return_value = fake
    repo = FalkorDBOntologyRepository("redis://test")
    history = repo.get_ontology_version_history(tenant_id="t", limit=2)
    assert len(history) == 2
    assert history[0].id == "v2"
    assert history[1].id == "v1"


def test_delete_ontology_version_executes_detach_delete(mocker):
    fake = FakeRedis({"DETACH DELETE": []})
    mocker.patch.object(module, "redis")
    module.redis.from_url.return_value = fake
    repo = FalkorDBOntologyRepository("redis://test")
    result = repo.delete_ontology_version(version_id="v1", tenant_id="t")
    assert result is True
    assert any("DETACH DELETE" in q for q in fake.queries)
