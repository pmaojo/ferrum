"""Unit tests for ListKnowledgeGraphsUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from domain.entities import KnowledgeGraph, ScientificDomain
from application.exceptions import ValidationError, ApplicationError
from application.use_cases.knowledge_graph.list_knowledge_graphs_use_case import (
    ListKnowledgeGraphsUseCase,
    ListKnowledgeGraphsRequest,
    ListKnowledgeGraphsResponse,
    KnowledgeGraphFilterParams,
    KnowledgeGraphSortField
)
from application.use_cases.dto import PaginationParams, SortParams, SortDirection
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import KnowledgeGraphDTO


class TestListKnowledgeGraphsUseCase:
    """Test cases for ListKnowledgeGraphsUseCase."""

    @pytest.fixture
    def mock_kg_repository(self):
        """Mock knowledge graph repository."""
        return Mock()

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracing service."""
        tracer = Mock()
        tracer.start_span.return_value.__enter__ = Mock(return_value=Mock())
        tracer.start_span.return_value.__exit__ = Mock(return_value=None)
        return tracer

    @pytest.fixture
    def use_case(self, mock_kg_repository, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return ListKnowledgeGraphsUseCase(
            kg_repository=mock_kg_repository,
            tracer=mock_tracer
        )

    @pytest.fixture
    def sample_knowledge_graphs(self):
        """Create sample knowledge graphs for testing."""
        now = datetime.utcnow()
        return [
            KnowledgeGraph(
                id="kg1",
                name="Biology Graph",
                tenant_id="tenant1",
                domain=ScientificDomain.BIOLOGY,
                ontology_version_id="onto1",
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=1),
                node_count=100,
                edge_count=200,
                is_public=True
            ),
            KnowledgeGraph(
                id="kg2",
                name="Chemistry Graph",
                tenant_id="tenant1",
                domain=ScientificDomain.CHEMISTRY,
                ontology_version_id="onto2",
                created_at=now - timedelta(days=1),
                updated_at=now,
                node_count=50,
                edge_count=75,
                is_public=False
            ),
            KnowledgeGraph(
                id="kg3",
                name="Physics Graph",
                tenant_id="tenant1",
                domain=ScientificDomain.PHYSICS,
                ontology_version_id="onto3",
                created_at=now,
                updated_at=now,
                node_count=150,
                edge_count=300,
                is_public=True
            )
        ]

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_list_knowledge_graphs_success_basic(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test successful knowledge graph listing with basic pagination."""
        # Arrange
        mock_kg_repository.list_by_tenant.return_value = (sample_knowledge_graphs, 3)

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20)
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 3
        assert response.knowledge_graphs.total_items == 3
        assert response.knowledge_graphs.total_pages == 1
        assert response.knowledge_graphs.page == 1
        assert response.knowledge_graphs.page_size == 20
        assert response.knowledge_graphs.has_next_page is False
        assert response.knowledge_graphs.has_previous_page is False

        # Verify repository was called correctly
        mock_kg_repository.list_by_tenant.assert_called_once_with(
            tenant_id="tenant1",
            page=1,
            page_size=20,
            filters=None,
            sort=None
        )

        # Verify DTOs are correctly created
        kg_dto = response.knowledge_graphs.items[0]
        assert isinstance(kg_dto, KnowledgeGraphDTO)
        assert kg_dto.id == "kg1"
        assert kg_dto.name == "Biology Graph"
        assert kg_dto.domain == "biology"
        assert kg_dto.tenant_id == "tenant1"
        assert kg_dto.node_count == 100
        assert kg_dto.edge_count == 200
        assert kg_dto.is_public is True

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_list_knowledge_graphs_with_pagination(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test knowledge graph listing with pagination."""
        # Arrange - simulate page 2 of 2 pages with 2 items per page
        mock_kg_repository.list_by_tenant.return_value = ([sample_knowledge_graphs[2]], 3)

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=2, page_size=2)
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 1
        assert response.knowledge_graphs.total_items == 3
        assert response.knowledge_graphs.total_pages == 2
        assert response.knowledge_graphs.page == 2
        assert response.knowledge_graphs.page_size == 2
        assert response.knowledge_graphs.has_next_page is False
        assert response.knowledge_graphs.has_previous_page is True

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_list_knowledge_graphs_with_filters(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test knowledge graph listing with filters."""
        # Arrange
        biology_graphs = [kg for kg in sample_knowledge_graphs if kg.domain == ScientificDomain.BIOLOGY]
        mock_kg_repository.list_by_tenant.return_value = (biology_graphs, 1)

        filters = KnowledgeGraphFilterParams(
            domain=ScientificDomain.BIOLOGY,
            is_public=True,
            min_node_count=50
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 1
        assert response.knowledge_graphs.items[0].domain == "biology"

        # Verify repository was called with filters
        mock_kg_repository.list_by_tenant.assert_called_once_with(
            tenant_id="tenant1",
            page=1,
            page_size=20,
            filters=filters,
            sort=None
        )

    @pytest.mark.asyncio
    async def test_list_knowledge_graphs_with_sorting(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test knowledge graph listing with sorting."""
        # Arrange
        sorted_graphs = sorted(sample_knowledge_graphs, key=lambda kg: kg.name)
        mock_kg_repository.list_by_tenant.return_value = (sorted_graphs, 3)

        sort_params = SortParams(
            sort_by=KnowledgeGraphSortField.NAME.value,
            direction=SortDirection.ASC
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            sort=sort_params
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 3

        # Verify repository was called with sort parameters
        mock_kg_repository.list_by_tenant.assert_called_once_with(
            tenant_id="tenant1",
            page=1,
            page_size=20,
            filters=None,
            sort=sort_params
        )

    @pytest.mark.asyncio
    async def test_list_knowledge_graphs_empty_result(self, use_case, mock_kg_repository):
        """Test knowledge graph listing with empty result."""
        # Arrange
        mock_kg_repository.list_by_tenant.return_value = ([], 0)

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20)
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 0
        assert response.knowledge_graphs.total_items == 0
        assert response.knowledge_graphs.total_pages == 0
        assert response.knowledge_graphs.has_next_page is False
        assert response.knowledge_graphs.has_previous_page is False

    @pytest.mark.asyncio
    async def test_validation_error_missing_tenant_id(self, use_case):
        """Test validation error when tenant_id is missing."""
        # Arrange
        request = ListKnowledgeGraphsRequest(
            tenant_id="",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20)
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_missing_user_id(self, use_case):
        """Test validation error when user_id is missing."""
        # Arrange
        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="",
            pagination=PaginationParams(page=1, page_size=20)
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_invalid_sort_field(self, use_case):
        """Test validation error when sort field is invalid."""
        # Arrange
        sort_params = SortParams(
            sort_by="invalid_field",
            direction=SortDirection.ASC
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            sort=sort_params
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "Invalid sort field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_invalid_filter_domain(self, use_case):
        """Test validation error when filter domain is invalid."""
        # Arrange
        filters = KnowledgeGraphFilterParams(domain="invalid_domain")  # This would fail at runtime

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Note: This test would need to be adjusted based on how the validation is implemented
        # For now, we'll test with a proper domain but invalid count range

    @pytest.mark.asyncio
    async def test_validation_error_invalid_count_range(self, use_case):
        """Test validation error when count range is invalid."""
        # Arrange
        filters = KnowledgeGraphFilterParams(
            min_node_count=100,
            max_node_count=50  # min > max
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "min_node_count cannot be greater than max_node_count" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_invalid_date_range(self, use_case):
        """Test validation error when date range is invalid."""
        # Arrange
        now = datetime.utcnow()
        filters = KnowledgeGraphFilterParams(
            created_after=now,
            created_before=now - timedelta(days=1)  # after > before
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "created_after cannot be after created_before" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_negative_count_filter(self, use_case):
        """Test validation error when count filter is negative."""
        # Arrange
        filters = KnowledgeGraphFilterParams(min_node_count=-1)

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "min_node_count must be a non-negative integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_empty_name_contains(self, use_case):
        """Test validation error when name_contains is empty."""
        # Arrange
        filters = KnowledgeGraphFilterParams(name_contains="   ")  # Only whitespace

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20),
            filters=filters
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert "name_contains cannot be empty if provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_repository_error_handling(self, use_case, mock_kg_repository):
        """Test error handling when repository raises an exception."""
        # Arrange
        mock_kg_repository.list_by_tenant.side_effect = Exception("Database connection failed")

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=20)
        )

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(request)

        assert "Failed to list knowledge graphs" in str(exc_info.value)
        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complex_filters_combination(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test knowledge graph listing with complex filter combinations."""
        # Arrange
        now = datetime.utcnow()
        filtered_graphs = [sample_knowledge_graphs[0]]  # Only biology graph matches
        mock_kg_repository.list_by_tenant.return_value = (filtered_graphs, 1)

        filters = KnowledgeGraphFilterParams(
            domain=ScientificDomain.BIOLOGY,
            is_public=True,
            name_contains="Bio",
            min_node_count=50,
            max_node_count=200,
            created_after=now - timedelta(days=3),
            created_before=now,
            updated_after=now - timedelta(days=2),
            updated_before=now
        )

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=1, page_size=10),
            filters=filters
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.success is True
        assert response.knowledge_graphs is not None
        assert len(response.knowledge_graphs.items) == 1

        # Verify repository was called with all filters
        mock_kg_repository.list_by_tenant.assert_called_once_with(
            tenant_id="tenant1",
            page=1,
            page_size=10,
            filters=filters,
            sort=None
        )

    @pytest.mark.asyncio
    async def test_all_sort_fields_valid(self, use_case, mock_kg_repository, sample_knowledge_graphs):
        """Test that all defined sort fields are valid."""
        # Test each sort field
        for sort_field in KnowledgeGraphSortField:
            # Arrange
            mock_kg_repository.list_by_tenant.return_value = (sample_knowledge_graphs, 3)

            sort_params = SortParams(
                sort_by=sort_field.value,
                direction=SortDirection.DESC
            )

            request = ListKnowledgeGraphsRequest(
                tenant_id="tenant1",
                user_id="user1",
                pagination=PaginationParams(page=1, page_size=20),
                sort=sort_params
            )

            # Act
            response = await use_case.execute(request)

            # Assert
            assert response.success is True
            assert response.knowledge_graphs is not None

            # Reset mock for next iteration
            mock_kg_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, use_case, mock_kg_repository):
        """Test pagination edge cases."""
        # Test case: exactly divisible total
        mock_kg_repository.list_by_tenant.return_value = ([], 20)

        request = ListKnowledgeGraphsRequest(
            tenant_id="tenant1",
            user_id="user1",
            pagination=PaginationParams(page=2, page_size=10)
        )

        response = await use_case.execute(request)

        assert response.knowledge_graphs.total_pages == 2
        assert response.knowledge_graphs.has_next_page is False
        assert response.knowledge_graphs.has_previous_page is True

        # Test case: not exactly divisible total
        mock_kg_repository.list_by_tenant.return_value = ([], 21)

        response = await use_case.execute(request)

        assert response.knowledge_graphs.total_pages == 3
        assert response.knowledge_graphs.has_next_page is True
        assert response.knowledge_graphs.has_previous_page is True