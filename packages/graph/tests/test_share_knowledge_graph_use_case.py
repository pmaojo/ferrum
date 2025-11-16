"""Unit tests for ShareKnowledgeGraphUseCase."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from domain.entities import KnowledgeGraph, ScientificDomain, SharingLink
from application.exceptions import ValidationError, AuthorizationError, NotFoundError
from application.use_cases.knowledge_graph.share_knowledge_graph_use_case import (
    ShareKnowledgeGraphUseCase,
    ShareKnowledgeGraphRequest,
)


class TestShareKnowledgeGraphUseCase:
    """Test cases for ShareKnowledgeGraphUseCase."""

    def setup_method(self):
        self.kg_repository = Mock()
        self.sharing_repository = Mock()
        self.authorization_service = Mock()
        self.tracer = Mock()

        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = ShareKnowledgeGraphUseCase(
            kg_repository=self.kg_repository,
            sharing_repository=self.sharing_repository,
            authorization_service=self.authorization_service,
            tracer=self.tracer,
        )

        self.sample_kg = KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123",
        )
        self.sample_kg.id = "kg-123"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_share(self, mocker):
        request = ShareKnowledgeGraphRequest(
            kg_id="kg-123",
            permissions=["view"],
            expiry_days=7,
            tenant_id="tenant-123",
            user_id="user-123",
        )

        self.kg_repository.get_by_id.return_value = self.sample_kg
        mocker.patch("secrets.token_urlsafe", return_value="token123")

        expires = datetime.utcnow() + timedelta(days=7)
        created_link = SharingLink.create(
            kg_id="kg-123",
            tenant_id="tenant-123",
            token="token123",
            permissions=["view"],
            expires_at=expires,
            created_by="user-123",
        )

        self.sharing_repository.create.return_value = created_link

        response = await self.use_case.execute(request)

        assert response.success is True
        assert response.sharing_link is not None
        assert response.sharing_link.token == "token123"
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-123", resource_id="kg-123", permission="share"
        )
        self.sharing_repository.create.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_kg_id(self):
        request = ShareKnowledgeGraphRequest(
            kg_id="",
            permissions=["view"],
            tenant_id="tenant-123",
            user_id="user-123",
        )

        with pytest.raises(ValidationError):
            await self.use_case.execute(request)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_not_found(self):
        request = ShareKnowledgeGraphRequest(
            kg_id="missing",
            permissions=["view"],
            tenant_id="tenant-123",
            user_id="user-123",
        )

        self.kg_repository.get_by_id.return_value = None

        response = await self.use_case.execute(request)

        assert response.success is False
        assert "not found" in response.error_message

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_authorization_error(self):
        request = ShareKnowledgeGraphRequest(
            kg_id="kg-123",
            permissions=["view"],
            tenant_id="tenant-123",
            user_id="user-123",
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="forbidden",
            user_id="user-123",
            resource_id="kg-123",
        )

        response = await self.use_case.execute(request)

        assert response.success is False
        assert "forbidden" in response.error_message
