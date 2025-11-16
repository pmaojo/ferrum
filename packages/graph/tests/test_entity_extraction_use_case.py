import pytest
from unittest.mock import Mock

from application.use_cases.knowledge_graph.entity_extraction_use_case import (
    EntityExtractionUseCase,
    EntityExtractionRequest,
    ExtractionConfig,
)
from adapters.knowledge_graph.regex_entity_extractor_adapter import (
    RegexEntityExtractorAdapter,
)


class TestEntityExtractionUseCase:
    def setup_method(self):
        self.extractor = RegexEntityExtractorAdapter()
        self.tracer = Mock()
        self.tracer.start_span.return_value.__enter__ = lambda s: Mock(duration_ms=0)
        self.tracer.start_span.return_value.__exit__ = lambda *a: None
        self.use_case = EntityExtractionUseCase(self.extractor, self.tracer)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_extract_entities(self):
        request = EntityExtractionRequest(
            documents=["Alice knows Bob."],
            config=ExtractionConfig(entity_types=["Alice", "Bob"], relationship_patterns=["knows"]),
            kg_id="kg",
            tenant_id="t",
            user_id="u",
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert len(response.entities) == 2

