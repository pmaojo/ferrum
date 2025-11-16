"""Unit tests for UpdateKnowledgeGraphUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import KnowledgeGraph, ScientificDomain
from application.exceptions import (
    ValidationError,
    BusinessRuleViolationError,
    NotFoundError,
    AuthorizationError
)
from application.use_cases.knowledge_graph.update_knowledge_graph_use_case import (
    UpdateKnowledgeGraphUseCase,
    UpdateKnowledgeGraphRequest,
    UpdateKnowledgeGraphResponse
)


class TestUpdateKnowledgeGraphUseCase:
    """Test cases for UpdateKnowledgeGraphUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.kg_repository = Mock()
        self.authorization_service = Mock()
        self.metadata_repository = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = UpdateKnowledgeGraphUseCase(
            kg_repository=self.kg_repository,
            authorization_service=self.authorization_service,
            metadata_repository=self.metadata_repository,
            tracer=self.tracer
        )

        # Create a sample existing knowledge graph
        self.existing_kg = KnowledgeGraph.create(
            name="Original KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_update_name(self):
        """Test successful knowledge graph name update."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Updated KG",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.get_by_name.return_value = None  # No conflict
        self.kg_repository.update.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.name == "Updated KG"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-123",
            resource_id="kg-123",
            permission="update"
        )

        # Verify repository calls
        self.kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")
        self.kg_repository.get_by_name.assert_called_once_with("Updated KG", "tenant-123")
        self.kg_repository.update.assert_called_once()

        # Verify metrics
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_update_description(self):
        """Test successful knowledge graph description update."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            description="Updated description",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.update.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.description == "Updated description"

        self.metadata_repository.save_description.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123",
            description="Updated description",
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_update_is_public(self):
        """Test successful knowledge graph visibility update."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            is_public=True,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.update.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.is_public is True

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_update_multiple_fields(self):
        """Test successful update of multiple fields."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Updated KG",
            description="Updated description",
            is_public=True,
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.get_by_name.return_value = None  # No conflict
        self.kg_repository.update.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.name == "Updated KG"
        assert response.knowledge_graph.description == "Updated description"
        assert response.knowledge_graph.is_public is True

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_kg_id(self):
        """Test validation error when kg_id is empty."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="",
            name="Updated KG",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)
        assert exc_info.value.field == "kg_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_name(self):
        """Test validation error when name is empty string."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "name cannot be empty" in str(exc_info.value)
        assert exc_info.value.field == "name"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_long_name(self):
        """Test validation error when name is too long."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="x" * 256,  # Too long
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "cannot exceed 255 characters" in str(exc_info.value)
        assert exc_info.value.field == "name"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_long_description(self):
        """Test validation error when description is too long."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            description="x" * 1001,  # Too long
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Description cannot exceed 1000 characters" in str(exc_info.value)
        assert exc_info.value.field == "description"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_no_fields_to_update(self):
        """Test validation error when no fields are provided for update."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "At least one field must be provided" in str(exc_info.value)
        assert exc_info.value.field == "update_fields"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_authorization_error(self):
        """Test authorization error when user doesn't have permission."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Updated KG",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock authorization service to raise error
        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="Access denied",
            user_id="user-123",
            resource_id="kg-123",
            required_permission="update"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "Access denied" in response.error_message

        # Verify authorization check was called
        self.authorization_service.check_permission.assert_called_once()

        # Verify repository was not called
        self.kg_repository.get_by_id.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_not_found_error(self):
        """Test not found error when knowledge graph doesn't exist."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Updated KG",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository to return None
        self.kg_repository.get_by_id.return_value = None

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "not found" in response.error_message

        # Verify repository was called
        self.kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")

        # Verify update was not called
        self.kg_repository.update.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_business_rule_violation_duplicate_name(self):
        """Test business rule violation when new name already exists."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Existing KG",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock existing KG with different ID but same name
        conflicting_kg = KnowledgeGraph.create(
            name="Existing KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123"
        )
        conflicting_kg.id = "different-kg-id"

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.get_by_name.return_value = conflicting_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False
        assert "already exists" in response.error_message

        # Verify repository checks
        self.kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")
        self.kg_repository.get_by_name.assert_called_once_with("Existing KG", "tenant-123")

        # Verify update was not called
        self.kg_repository.update.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_same_name_update_allowed(self):
        """Test that updating to the same name is allowed."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Original KG",  # Same as existing name
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.get_by_name.return_value = self.existing_kg  # Same KG
        self.kg_repository.update.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None

        # Verify repository calls
        self.kg_repository.get_by_id.assert_called_once()
        # Note: update may not be called if no actual changes are made

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_no_actual_changes_still_succeeds(self):
        """Test that request with no actual changes still succeeds."""
        # Arrange
        request = UpdateKnowledgeGraphRequest(
            kg_id="kg-123",
            name="Original KG",  # Same as existing
            is_public=False,     # Same as existing
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.get_by_name.return_value = self.existing_kg

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None

        # Verify repository get was called but update might not be called
        self.kg_repository.get_by_id.assert_called_once()