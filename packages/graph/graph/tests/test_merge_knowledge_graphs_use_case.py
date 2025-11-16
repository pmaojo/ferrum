import pytest
from unittest.mock import Mock

from application.use_cases.knowledge_graph.merge_knowledge_graphs_use_case import (
    MergeKnowledgeGraphsUseCase,
    MergeKnowledgeGraphsRequest,
)
from adapters.knowledge_graph.simple_graph_merger_adapter import SimpleGraphMergerAdapter
from domain.entities import KnowledgeGraph, ScientificDomain


class InMemoryRepo:
    def __init__(self):
        self.store = {}

    def get_by_id(self, kg_id, tenant_id):
        return self.store.get(kg_id)

    def update(self, kg):
        self.store[kg.id] = kg


def make_graph(id_: str) -> KnowledgeGraph:
    return KnowledgeGraph.create(
        name=id_,
        tenant_id="t",
        domain=ScientificDomain.GENERAL,
        ontology_version_id="o",
    )


class TestMergeKnowledgeGraphsUseCase:
    def setup_method(self):
        self.repo = InMemoryRepo()
        self.repo.store["a"] = make_graph("a")
        self.repo.store["b"] = make_graph("b")
        self.repo.store["b"].node_count = 2
        self.repo.store["b"].edge_count = 3
        self.tracer = Mock()
        self.tracer.start_span.return_value.__enter__ = lambda s: Mock(duration_ms=0)
        self.tracer.start_span.return_value.__exit__ = lambda *a: None
        merger = SimpleGraphMergerAdapter(self.repo)
        self.use_case = MergeKnowledgeGraphsUseCase(merger, self.tracer)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_merge(self):
        request = MergeKnowledgeGraphsRequest(
            target_kg_id="a",
            source_kg_ids=["b"],
            tenant_id="t",
            user_id="u",
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert response.merged_graph.node_count == 2
        assert response.merged_graph.edge_count == 3

