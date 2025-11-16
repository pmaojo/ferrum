import pytest
from unittest.mock import Mock

from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
    ValidateKnowledgeGraphUseCase,
    ValidateKnowledgeGraphRequest,
    ValidationRule,
)
from adapters.knowledge_graph.rule_based_validator_adapter import RuleBasedValidatorAdapter


class TestValidateKnowledgeGraphUseCase:
    def setup_method(self):
        self.validator = RuleBasedValidatorAdapter()
        self.tracer = Mock()
        self.tracer.start_span.return_value.__enter__ = lambda s: Mock(duration_ms=0)
        self.tracer.start_span.return_value.__exit__ = lambda *a: None
        self.use_case = ValidateKnowledgeGraphUseCase(self.validator, self.tracer)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validate(self):
        request = ValidateKnowledgeGraphRequest(
            kg_id="kg",
            rules=[ValidationRule(name="r1", expression="x")],
            tenant_id="t",
            user_id="u",
        )
        response = await self.use_case.execute(request)
        assert response.success
        assert response.is_valid
        assert response.details[0]["rule"] == "r1"

