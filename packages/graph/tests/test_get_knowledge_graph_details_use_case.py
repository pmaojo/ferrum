"""Tests for GetKnowledgeGraphDetailsUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from domain.entities import KnowledgeGraph, ScientificDomain
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from application.use_cases.knowledge_graph.get_knowledge_graph_details_use_case import (
    GetKnowledgeGraphDetailsUseCase,
    GetKnowledgeGraphDetailsRequest,
    GetKnowledgeGraphDetailsResponse,
    KnowledgeGraphStatisticsDTO,
    KnowledgeGraphDetailsDTO
)


class TestGetKnowledgeGraphDetailsUseCase:
    """Test cases for GetKnowledgeGraphDetailsUseCase."""

    @pytest.fixture
    def mock_kg_repository(self):
        """Mock knowledge graph repository."""
        return Mock()

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock()

    @pytest.fixture
    def mock_statistics_service(self):
        """Mock statistics service."""
        return Mock()

    @pytest.fixture
    def mock_metadata_repository(self):
        """Mock metadata repository."""
        return Mock()

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracing service."""
        tracer = Mock()
        tracer.start_span.return_value.__enter__ = Mock(return_value=Mock())
        tracer.start_span.return_value.__exit__ = Mock(return_value=None)
        return tracer

    @pytest.fixture
    def use_case(self, mock_kg_repository, mock_authorization_service,
                 mock_statistics_service, mock_metadata_repository, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return GetKnowledgeGraphDetailsUseCase(
            kg_repository=mock_kg_repository,
            authorization_service=mock_authorization_service,
            statistics_service=mock_statistics_service,
            metadata_repository=mock_metadata_repository,
            tracer=mock_tracer
        )

    @pytest.fixture
    def sample_kg(self):
        """Sample knowledge graph entity."""
        return KnowledgeGraph.create(
            name="Test KG",
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            ontology_version_id="ontology-456",
            is_public=False
        )

    @pytest.fixture
    def sample_statistics(self):
        """Sample statistics DTO."""
        return KnowledgeGraphStatisticsDTO(
            node_count=100,
            edge_count=200,
            node_types={"Person": 50, "Organization": 30, "Location": 20},
            edge_types={"knows": 100, "worksAt": 50, "locatedIn": 50},
            avg_node_degree=4.0,
            max_node_degree=10,
            min_node_degree=1,
            connected_components=1,
            density=0.04,
            clustering_coefficient=0.3,
            diameter=5
        )

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata dictionary."""
        return {
            "description": "Test knowledge graph description",
            "tags": ["test", "biology"],
            "version": "1.0.0",
            "last_indexed": "2024-01-15T10:00:00Z"
        }

    @pytest.fixture
    def valid_request(self):
        """Valid request for getting knowledge graph details."""
        return GetKnowledgeGraphDetailsRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-456",
            include_advanced_stats=False
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_basic_details_retrieval(
        self, use_case, valid_request, sample_kg, sample_statistics,
        sample_metadata, mock_kg_repository, mock_authorization_service,
        mock_statistics_service, mock_metadata_repository
    ):
        """Test successful knowledge graph details retrieval with basic stats."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = sample_kg
        mock_statistics_service.calculate_basic_statistics.return_value = sample_statistics
        mock_metadata_repository.get_metadata.return_value = sample_metadata

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, GetKnowledgeGraphDetailsResponse)
        assert response.success is True
        assert response.knowledge_graph is not None
        assert response.knowledge_graph.id == sample_kg.id
        assert response.knowledge_graph.name == sample_kg.name
        assert response.knowledge_graph.description == sample_metadata["description"]
        assert response.knowledge_graph.statistics == sample_statistics
        assert response.knowledge_graph.metadata == sample_metadata

        # Verify service calls
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-123",
            permission="read"
        )
        mock_kg_repository.get_by_id.assert_called_once_with("kg-123", "tenant-123")
        mock_statistics_service.calculate_basic_statistics.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123"
        )
        mock_metadata_repository.get_metadata.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123"
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_successful_advanced_details_retrieval(
        self, use_case, sample_kg, sample_statistics, sample_metadata,
        mock_kg_repository, mock_authorization_service,
        mock_statistics_service, mock_metadata_repository
    ):
        """Test successful knowledge graph details retrieval with advanced stats."""
        # Arrange
        request = GetKnowledgeGraphDetailsRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-456",
            include_advanced_stats=True
        )

        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = sample_kg
        mock_statistics_service.calculate_advanced_statistics.return_value = sample_statistics
        mock_metadata_repository.get_metadata.return_value = sample_metadata

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graph is not None

        # Verify advanced statistics were calculated
        mock_statistics_service.calculate_advanced_statistics.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-123"
        )
        mock_statistics_service.calculate_basic_statistics.assert_not_called()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_knowledge_graph_not_found(
        self, use_case, valid_request, mock_kg_repository, mock_authorization_service
    ):
        """Test error when knowledge graph is not found."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = None

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "not found" in response.error_message
        assert response.knowledge_graph is None

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_authorization_error(
        self, use_case, valid_request, mock_authorization_service
    ):
        """Test error when user is not authorized."""
        # Arrange
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User not authorized",
            user_id="user-456"
        )

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is False
        assert "not authorized" in response.error_message.lower()
        assert response.knowledge_graph is None

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_kg_id(self, use_case):
        """Test validation error when kg_id is empty."""
        # Arrange
        request = GetKnowledgeGraphDetailsRequest(
            kg_id="",
            tenant_id="tenant-123",
            user_id="user-456"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_tenant_id(self, use_case):
        """Test validation error when tenant_id is empty."""
        # Arrange
        request = GetKnowledgeGraphDetailsRequest(
            kg_id="kg-123",
            tenant_id="",
            user_id="user-456"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_empty_user_id(self, use_case):
        """Test validation error when user_id is empty."""
        # Arrange
        request = GetKnowledgeGraphDetailsRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id=""
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_validation_error_invalid_include_advanced_stats(self, use_case):
        """Test validation error when include_advanced_stats is not boolean."""
        # Arrange
        request = GetKnowledgeGraphDetailsRequest(
            kg_id="kg-123",
            tenant_id="tenant-123",
            user_id="user-456",
            include_advanced_stats="invalid"  # Should be boolean
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "must be a boolean value" in str(exc_info.value)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_statistics_service_error_handling(
        self, use_case, valid_request, sample_kg, mock_kg_repository,
        mock_authorization_service, mock_statistics_service, mock_metadata_repository
    ):
        """Test error handling when statistics service fails."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = sample_kg
        mock_statistics_service.calculate_basic_statistics.side_effect = Exception("Stats error")
        mock_metadata_repository.get_metadata.return_value = {}

        # Act & Assert
        with pytest.raises(Exception):
            await use_case.execute(valid_request)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_metadata_repository_error_handling(
        self, use_case, valid_request, sample_kg, sample_statistics,
        mock_kg_repository, mock_authorization_service,
        mock_statistics_service, mock_metadata_repository
    ):
        """Test error handling when metadata service fails."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = sample_kg
        mock_statistics_service.calculate_basic_statistics.return_value = sample_statistics
        mock_metadata_repository.get_metadata.side_effect = Exception("Metadata error")

        # Act & Assert
        with pytest.raises(Exception):
            await use_case.execute(valid_request)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_tracing_and_metrics(
        self, use_case, valid_request, sample_kg, sample_statistics,
        sample_metadata, mock_kg_repository, mock_authorization_service,
        mock_statistics_service, mock_metadata_repository, mock_tracer
    ):
        """Test that tracing and metrics are recorded correctly."""
        # Arrange
        mock_authorization_service.check_permission.return_value = None
        mock_kg_repository.get_by_id.return_value = sample_kg
        mock_statistics_service.calculate_basic_statistics.return_value = sample_statistics
        mock_metadata_repository.get_metadata.return_value = sample_metadata

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert response.success is True

        # Verify tracing
        mock_tracer.start_span.assert_called_once_with(
            name="get_knowledge_graph_details",
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-123"
        )

        # Verify metrics
        mock_tracer.record_metric.assert_called_with(
            name="knowledge_graph_details_retrieved",
            value=1,
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY.value,
            include_advanced_stats=False
        )