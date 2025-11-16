import pytest
from unittest.mock import Mock

from application.use_cases.knowledge_graph.version_knowledge_graph_use_case import (
    VersionKnowledgeGraphUseCase,
    VersionKnowledgeGraphRequest,
)
from adapters.knowledge_graph.inmemory_versioning_adapter import InMemoryVersioningAdapter


class TestVersionKnowledgeGraphUseCase:
    def setup_method(self):
        self.repo = InMemoryVersioningAdapter()
        self.tracer = Mock()
        self.tracer.start_span.return_value.__enter__ = lambda s: Mock(duration_ms=0)
        self.tracer.start_span.return_value.__exit__ = lambda *a: None
        self.use_case = VersionKnowledgeGraphUseCase(self.repo, self.tracer)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_versioning(self):
        request = VersionKnowledgeGraphRequest(
            kg_id="kg",
            tenant_id="t",
            user_id="u",
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert response.version.kg_id == "kg"
        assert response.version.version_id is not None

