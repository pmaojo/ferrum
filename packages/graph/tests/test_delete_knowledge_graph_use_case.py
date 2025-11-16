"""Unit tests for DeleteKnowledgeGraphUseCase."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from domain.entities import KnowledgeGraph, ScientificDomain
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    ApplicationError
)
from application.use_cases.knowledge_graph.delete_knowledge_graph_use_case import (
    DeleteKnowledgeGraphUseCase,
    DeleteKnowledgeGraphRequest,
    DeleteKnowledgeGraphResponse
)


class TestDeleteKnowledgeGraphUseCase:
    """Test cases for DeleteKnowledgeGraphUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.kg_repository = Mock()
        self.authorization_service = Mock()
        self.query_repository = Mock()
        self.graph_stream_event_repository = Mock()
        self.community_repository = Mock()
        self.triple_repository = Mock()
        self.tracer = Mock()

        # Mock tracer span
        self.mock_span = Mock()
        self.tracer.start_span.return_value.__enter__ = Mock(return_value=self.mock_span)
        self.tracer.start_span.return_value.__exit__ = Mock(return_value=None)

        self.use_case = DeleteKnowledgeGraphUseCase(
            kg_repository=self.kg_repository,
            authorization_service=self.authorization_service,
            query_repository=self.query_repository,
            graph_stream_event_repository=self.graph_stream_event_repository,
            community_repository=self.community_repository,
            triple_repository=self.triple_repository,
            tracer=self.tracer
        )

        # Create a sample existing knowledge graph
        self.existing_kg = KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="onto-123"
        )
        self.existing_kg.id = "kg-123"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_deletion_with_cascading(self):
        """Test successful knowledge graph deletion with cascading deletion."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.delete_by_id.return_value = True

        # Mock cascading deletions
        self.query_repository.delete_by_kg_id.return_value = 5
        self.graph_stream_event_repository.delete_by_kg_id.return_value = 10
        self.community_repository.delete_by_kg_id.return_value = 3
        self.triple_repository.delete_by_kg_id.return_value = 100

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.deleted_kg_id == "kg-123"
        assert response.cascaded_deletions is not None
        assert response.cascaded_deletions["queries"] == 5
        assert response.cascaded_deletions["graph_stream_events"] == 10
        assert response.cascaded_deletions["communities"] == 3
        assert response.cascaded_deletions["triples"] == 100

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-123",
            resource_id="kg-123",
            permission="delete"
        )

        # Verify repository calls
        self.kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")
        self.kg_repository.delete_by_id.assert_called_once_with("kg-123", "tenant-123")

        # Verify cascading deletions were called in correct order
        self.query_repository.delete_by_kg_id.assert_called_once_with("kg-123", "tenant-123")
        self.graph_stream_event_repository.delete_by_kg_id.assert_called_once_with("kg-123", "tenant-123")
        self.community_repository.delete_by_kg_id.assert_called_once_with("kg-123", "tenant-123")
        self.triple_repository.delete_by_kg_id.assert_called_once_with("kg-123", "tenant-123")

        # Verify metrics
        self.tracer.record_metric.assert_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_deletion_with_no_related_data(self):
        """Test successful deletion when no related data exists."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.delete_by_id.return_value = True

        # Mock no cascading deletions
        self.query_repository.delete_by_kg_id.return_value = 0
        self.graph_stream_event_repository.delete_by_kg_id.return_value = 0
        self.community_repository.delete_by_kg_id.return_value = 0
        self.triple_repository.delete_by_kg_id.return_value = 0

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.deleted_kg_id == "kg-123"
        assert response.cascaded_deletions is not None
        assert response.cascaded_deletions["queries"] == 0
        assert response.cascaded_deletions["graph_stream_events"] == 0
        assert response.cascaded_deletions["communities"] == 0
        assert response.cascaded_deletions["triples"] == 0

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_kg_id(self):
        """Test validation error when kg_id is empty."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)
        assert exc_info.value.field == "kg_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_tenant_id(self):
        """Test validation error when tenant_id is empty."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="",
            user_id="user-123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)
        assert exc_info.value.field == "tenant_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_user_id(self):
        """Test validation error when user_id is empty."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id=""
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await self.use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)
        assert exc_info.value.field == "user_id"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_authorization_error(self):
        """Test authorization error when user doesn't have permission."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock authorization service to raise error
        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="Access denied",
            user_id="user-123",
            resource_id="kg-123",
            required_permission="delete"
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
        self.kg_repository.delete_by_id.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_not_found_error(self):
        """Test not found error when knowledge graph doesn't exist."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
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

        # Verify deletion was not attempted
        self.kg_repository.delete_by_id.assert_not_called()

        # Verify cascading deletions were not attempted
        self.query_repository.delete_by_kg_id.assert_not_called()
        self.graph_stream_event_repository.delete_by_kg_id.assert_not_called()
        self.community_repository.delete_by_kg_id.assert_not_called()
        self.triple_repository.delete_by_kg_id.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_deletion_failure(self):
        """Test failure when knowledge graph deletion fails."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.delete_by_id.return_value = False  # Deletion failed

        # Mock cascading deletions (should still happen)
        self.query_repository.delete_by_kg_id.return_value = 5
        self.graph_stream_event_repository.delete_by_kg_id.return_value = 10
        self.community_repository.delete_by_kg_id.return_value = 3
        self.triple_repository.delete_by_kg_id.return_value = 100

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await self.use_case.execute(request)

        assert "Failed to delete knowledge graph" in str(exc_info.value)
        assert exc_info.value.error_code == "KNOWLEDGE_GRAPH_DELETION_FAILED"

        # Verify cascading deletions were still attempted
        self.query_repository.delete_by_kg_id.assert_called_once()
        self.graph_stream_event_repository.delete_by_kg_id.assert_called_once()
        self.community_repository.delete_by_kg_id.assert_called_once()
        self.triple_repository.delete_by_kg_id.assert_called_once()

        # Verify main deletion was attempted
        self.kg_repository.delete_by_id.assert_called_once_with("kg-123", "tenant-123")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_cascading_deletion_order(self):
        """Test that cascading deletions happen in the correct order."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.delete_by_id.return_value = True

        # Mock cascading deletions
        self.query_repository.delete_by_kg_id.return_value = 1
        self.graph_stream_event_repository.delete_by_kg_id.return_value = 1
        self.community_repository.delete_by_kg_id.return_value = 1
        self.triple_repository.delete_by_kg_id.return_value = 1

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify call order by checking the mock call history
        # The knowledge graph should be deleted last
        calls = [
            call for call in [
                self.query_repository.delete_by_kg_id.call_args,
                self.graph_stream_event_repository.delete_by_kg_id.call_args,
                self.community_repository.delete_by_kg_id.call_args,
                self.triple_repository.delete_by_kg_id.call_args,
                self.kg_repository.delete_by_id.call_args
            ] if call is not None
        ]

        # All cascading deletions should happen before the main deletion
        assert len(calls) == 5

        # Verify the main KG deletion happened last
        self.kg_repository.delete_by_id.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_different_scientific_domains(self):
        """Test deletion works with different scientific domains."""
        domains = [
            ScientificDomain.BIOLOGY,
            ScientificDomain.CHEMISTRY,
            ScientificDomain.PHYSICS,
            ScientificDomain.MEDICINE,
            ScientificDomain.ENVIRONMENTAL_SCIENCE,
            ScientificDomain.ASTRONOMY
        ]

        for domain in domains:
            # Arrange
            request = DeleteKnowledgeGraphRequest(
                kg_id=f"kg-{domain.value}",
                tenant_id="tenant-123",
                user_id="user-123"
            )

            # Create KG with specific domain
            kg_with_domain = KnowledgeGraph.create(
                name=f"Test KG {domain.value}",
                tenant_id="tenant-123",
                domain=domain,
                ontology_version_id="onto-123"
            )
            kg_with_domain.id = f"kg-{domain.value}"

            # Mock repository responses
            self.kg_repository.get_by_id.return_value = kg_with_domain
            self.kg_repository.delete_by_id.return_value = True

            # Mock cascading deletions
            self.query_repository.delete_by_kg_id.return_value = 0
            self.graph_stream_event_repository.delete_by_kg_id.return_value = 0
            self.community_repository.delete_by_kg_id.return_value = 0
            self.triple_repository.delete_by_kg_id.return_value = 0

            # Act
            response = await self.use_case.execute(request)

            # Assert
            assert response.success is True
            assert response.deleted_kg_id == f"kg-{domain.value}"

            # Reset mocks for next iteration
            self.kg_repository.reset_mock()
            self.query_repository.reset_mock()
            self.graph_stream_event_repository.reset_mock()
            self.community_repository.reset_mock()
            self.triple_repository.reset_mock()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_metrics_recording(self):
        """Test that metrics are properly recorded."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock repository responses
        self.kg_repository.get_by_id.return_value = self.existing_kg
        self.kg_repository.delete_by_id.return_value = True

        # Mock cascading deletions with specific counts
        self.query_repository.delete_by_kg_id.return_value = 5
        self.graph_stream_event_repository.delete_by_kg_id.return_value = 10
        self.community_repository.delete_by_kg_id.return_value = 3
        self.triple_repository.delete_by_kg_id.return_value = 100

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify metrics were recorded
        self.tracer.record_metric.assert_called()

        # Check the metric call arguments
        metric_calls = self.tracer.record_metric.call_args_list
        success_metric_call = None

        for call in metric_calls:
            args, kwargs = call
            if kwargs.get("name") == "knowledge_graph_deleted":
                success_metric_call = kwargs
                break

        assert success_metric_call is not None
        assert success_metric_call["value"] == 1
        assert success_metric_call["tenant_id"] == "tenant-123"
        assert success_metric_call["domain"] == "biology"
        assert success_metric_call["cascaded_queries"] == 5
        assert success_metric_call["cascaded_events"] == 10
        assert success_metric_call["cascaded_communities"] == 3
        assert success_metric_call["cascaded_triples"] == 100

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_error_metrics_recording(self):
        """Test that error metrics are properly recorded."""
        # Arrange
        request = DeleteKnowledgeGraphRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-123"
        )

        # Mock authorization service to raise error
        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="Access denied",
            user_id="user-123",
            resource_id="kg-123",
            required_permission="delete"
        )

        # Act
        response = await self.use_case.execute(request)

        # Assert
        assert response.success is False

        # Verify error metrics were recorded
        self.tracer.record_metric.assert_called()

        # Check the error metric call arguments
        metric_calls = self.tracer.record_metric.call_args_list
        error_metric_call = None

        for call in metric_calls:
            args, kwargs = call
            if kwargs.get("name") == "knowledge_graph_deletion_errors":
                error_metric_call = kwargs
                break

        assert error_metric_call is not None
        assert error_metric_call["value"] == 1
        assert error_metric_call["tenant_id"] == "tenant-123"
        assert error_metric_call["error_type"] == "AuthorizationError"