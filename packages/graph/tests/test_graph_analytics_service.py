"""Unit tests for GraphAnalyticsService."""

from dataclasses import dataclass
from typing import List

from application.services import GraphAnalyticsService
from application.ports import GraphRepositoryPort
from domain.entities import Triple


@dataclass
class InMemoryGraphRepository(GraphRepositoryPort):
    triples: List[Triple]

    def get_triples(self, *, kg_id: str, tenant_id: str) -> List[Triple]:
        return self.triples


def _build_service() -> GraphAnalyticsService:
    triples = [
        Triple("A", "r", "B", "t"),
        Triple("B", "r", "C", "t"),
        Triple("C", "r", "D", "t"),
    ]
    repo = InMemoryGraphRepository(triples)
    return GraphAnalyticsService(repository=repo)


def test_analyze_structure_counts():
    service = _build_service()
    metrics = service.analyze_structure(kg_id="kg", tenant_id="t")
    assert metrics["node_count"] == 4.0
    assert metrics["edge_count"] == 3.0


def test_calculate_degree_centrality():
    service = _build_service()
    centrality = service.calculate_centrality(
        kg_id="kg", tenant_id="t", centrality_types=["degree"]
    )
    assert centrality["B"]["degree"] == 2.0


def test_find_shortest_path():
    service = _build_service()
    path = service.find_shortest_path(
        kg_id="kg", tenant_id="t", source_node_id="A", target_node_id="C"
    )
    assert path == {"nodes": ["A", "B", "C"], "length": 2.0}

