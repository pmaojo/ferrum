"""Tests for FacetedSearchUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from application.use_cases.search.faceted_search_use_case import FacetedSearchUseCase
from application.use_cases.dto import (
    FacetedSearchRequestDTO,
    FacetedSearchResponseDTO,
    PaginationParams,
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError


class TestFacetedSearchUseCase:
    """Test cases for FacetedSearchUseCase."""

    @pytest.fixture
    def mock_faceted_search_port(self):
        """Create mock faceted search port."""
        return Mock()

    @pytest.fixture
    def mock_authorization_port(self):
        """Create mock authorization port."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_faceted_search_port, mock_authorization_port):
        """Create FacetedSearchUseCase instance."""
        return FacetedSearchUseCase(
            faceted_search_port=mock_faceted_search_port,
            authorization_port=mock_authorization_port,
        )

    @pytest.fixture
    def valid_request(self):
        """Create valid faceted search request."""
        return FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            query="test query",
            selected_facets={"type": ["Person", "Organization"]},
            facet_fields=["type", "domain", "status"],
            pagination=PaginationParams(page=1, page_size=20),
        )

    @pytest.fixture
    def mock_search_result(self):
        """Create mock search result from port."""
        return {
            "results": [
                {
                    "node_id": "node-1",
                    "node_type": "Person",
                    "label": "John Doe",
                    "properties": {"name": "John Doe", "age": 30},
                    "score": 0.95,
                    "snippet": "John Doe is a software engineer..."
                },
                {
                    "node_id": "node-2",
                    "node_type": "Organization",
                    "label": "Acme Corp",
                    "properties": {"name": "Acme Corp", "industry": "Technology"},
                    "score": 0.87,
                }
            ],
            "facets": [
                {
                    "field": "type",
                    "label": "Entity Type",
                    "values": [
                        {"value": "Person", "count": 15},
                        {"value": "Organization", "count": 8},
                        {"value": "Location", "count": 3}
                    ]
                },
                {
                    "field": "domain",
                    "label": "Domain",
                    "values": [
                        {"value": "Technology", "count": 12},
                        {"value": "Healthcare", "count": 7},
                        {"value": "Finance", "count": 7}
                    ]
                }
            ],
            "total_results": 26
        }

    @pytest.mark.asyncio
    async def test_successful_faceted_search(
        self, use_case, valid_request, mock_faceted_search_port,
        mock_authorization_port, mock_search_result
    ):
        """Test successful faceted search execution."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.return_value = mock_search_result

        # Act
        result = await use_case.execute(valid_request)

        # Assert
        assert isinstance(result, FacetedSearchResponseDTO)
        assert result.kg_id == "kg-123"
        assert result.tenant_id == "tenant-456"
        assert result.query == "test query"
        assert len(result.results) == 2
        assert len(result.facets) == 2
        assert result.total_results == 26
        assert result.applied_filters == {"type": ["Person", "Organization"]}
        assert result.processing_time_ms > 0
        assert isinstance(result.search_timestamp, datetime)

        # Verify search results
        assert result.results[0].node_id == "node-1"
        assert result.results[0].node_type == "Person"
        assert result.results[0].label == "John Doe"
        assert result.results[0].score == 0.95
        assert result.results[0].snippet == "John Doe is a software engineer..."

        assert result.results[1].node_id == "node-2"
        assert result.results[1].node_type == "Organization"
        assert result.results[1].label == "Acme Corp"
        assert result.results[1].score == 0.87
        assert result.results[1].snippet is None

        # Verify facets
        type_facet = result.facets[0]
        assert type_facet.field == "type"
        assert type_facet.label == "Entity Type"
        assert len(type_facet.values) == 3
        assert type_facet.values[0].value == "Person"
        assert type_facet.values[0].count == 15
        assert type_facet.values[0].selected is True  # Selected in request
        assert type_facet.values[2].selected is False  # Not selected

        # Verify port calls
        mock_authorization_port.check_permission.assert_called_once_with(
            "user-789", "kg-123", "read"
        )
        mock_faceted_search_port.search_with_facets.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-456",
            query="test query",
            selected_facets={"type": ["Person", "Organization"]},
            facet_fields=["type", "domain", "status"],
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_faceted_search_without_query(
        self, use_case, mock_faceted_search_port, mock_authorization_port, mock_search_result
    ):
        """Test faceted search without text query (browse mode)."""
        # Arrange
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            query=None,
            selected_facets={"type": ["Person"]},
            facet_fields=["type", "domain"],
        )
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.return_value = mock_search_result

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.query is None
        mock_faceted_search_port.search_with_facets.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-456",
            query=None,
            selected_facets={"type": ["Person"]},
            facet_fields=["type", "domain"],
            page=1,  # Default pagination
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_faceted_search_with_default_pagination(
        self, use_case, mock_faceted_search_port, mock_authorization_port, mock_search_result
    ):
        """Test faceted search with default pagination when not provided."""
        # Arrange
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            query="test",
            pagination=None,  # No pagination provided
        )
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.return_value = mock_search_result

        # Act
        result = await use_case.execute(request)

        # Assert
        mock_faceted_search_port.search_with_facets.assert_called_once_with(
            kg_id="kg-123",
            tenant_id="tenant-456",
            query="test",
            selected_facets={},
            facet_fields=None,
            page=1,  # Default
            page_size=20,  # Default
        )

    @pytest.mark.asyncio
    async def test_authorization_failure(
        self, use_case, valid_request, mock_authorization_port
    ):
        """Test faceted search with authorization failure."""
        # Arrange
        mock_authorization_port.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            await use_case.execute(valid_request)

        assert "lacks read permission" in str(exc_info.value)
        assert "user-789" in str(exc_info.value)
        assert "kg-123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_knowledge_graph_not_found(
        self, use_case, valid_request, mock_faceted_search_port, mock_authorization_port
    ):
        """Test faceted search when knowledge graph is not found."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.side_effect = Exception("Knowledge graph not found")

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "Knowledge graph kg-123 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_port_failure(
        self, use_case, valid_request, mock_faceted_search_port, mock_authorization_port
    ):
        """Test faceted search with search port failure."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.side_effect = Exception("Search service unavailable")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Faceted search failed" in str(exc_info.value)
        assert "Search service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self, use_case, valid_request, mock_faceted_search_port, mock_authorization_port
    ):
        """Test faceted search with empty results."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.return_value = {
            "results": [],
            "facets": [
                {
                    "field": "type",
                    "label": "Entity Type",
                    "values": [
                        {"value": "Person", "count": 0},
                        {"value": "Organization", "count": 0}
                    ]
                }
            ],
            "total_results": 0
        }

        # Act
        result = await use_case.execute(valid_request)

        # Assert
        assert len(result.results) == 0
        assert result.total_results == 0
        assert len(result.facets) == 1
        assert result.facets[0].values[0].count == 0

    def test_validate_request_missing_kg_id(self, use_case):
        """Test validation with missing knowledge graph ID."""
        request = FacetedSearchRequestDTO(
            kg_id="",
            tenant_id="tenant-456",
            user_id="user-789",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_validate_request_missing_tenant_id(self, use_case):
        """Test validation with missing tenant ID."""
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="",
            user_id="user-789",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Tenant ID is required" in str(exc_info.value)

    def test_validate_request_missing_user_id(self, use_case):
        """Test validation with missing user ID."""
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "User ID is required" in str(exc_info.value)

    def test_validate_request_invalid_pagination(self, use_case):
        """Test validation with invalid pagination parameters."""
        # Test invalid page - this will fail at DTO creation level
        with pytest.raises(ValueError) as exc_info:
            PaginationParams(page=0, page_size=20)

        assert "Page must be greater than or equal to 1" in str(exc_info.value)

        # Test invalid page size - this will fail at DTO creation level
        with pytest.raises(ValueError) as exc_info:
            PaginationParams(page=1, page_size=0)

        assert "Page size must be greater than or equal to 1" in str(exc_info.value)

        # Test page size too large - this will fail at DTO creation level
        with pytest.raises(ValueError) as exc_info:
            PaginationParams(page=1, page_size=1001)

        assert "Page size must be less than or equal to 100" in str(exc_info.value)

        # Test use case validation with valid pagination but invalid page in use case logic
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            pagination=PaginationParams(page=1, page_size=20),
        )

        # Manually set invalid page to test use case validation
        request.pagination.page = 0

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Page must be greater than 0" in str(exc_info.value)

    def test_validate_request_invalid_selected_facets(self, use_case):
        """Test validation with invalid selected facets."""
        # Test non-dict selected facets
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            selected_facets="invalid",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Selected facets must be a dictionary" in str(exc_info.value)

        # Test non-string field names
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            selected_facets={123: ["value"]},
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Facet field names must be strings" in str(exc_info.value)

        # Test non-list values
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            selected_facets={"field": "not_a_list"},
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Facet values for field 'field' must be a list" in str(exc_info.value)

        # Test non-string values in list
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            selected_facets={"field": ["valid", 123]},
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "All facet values for field 'field' must be strings" in str(exc_info.value)

    def test_validate_request_invalid_facet_fields(self, use_case):
        """Test validation with invalid facet fields."""
        # Test non-list facet fields
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            facet_fields="invalid",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Facet fields must be a list" in str(exc_info.value)

        # Test non-string facet fields
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            facet_fields=["valid", 123],
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "All facet fields must be strings" in str(exc_info.value)

        # Test too many facet fields
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            facet_fields=[f"field_{i}" for i in range(51)],
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(request)

        assert "Cannot request more than 50 facet fields" in str(exc_info.value)

    def test_is_facet_value_selected(self, use_case):
        """Test facet value selection checking."""
        selected_facets = {
            "type": ["Person", "Organization"],
            "domain": ["Technology"]
        }

        # Test selected values
        assert use_case._is_facet_value_selected("type", "Person", selected_facets) is True
        assert use_case._is_facet_value_selected("type", "Organization", selected_facets) is True
        assert use_case._is_facet_value_selected("domain", "Technology", selected_facets) is True

        # Test non-selected values
        assert use_case._is_facet_value_selected("type", "Location", selected_facets) is False
        assert use_case._is_facet_value_selected("domain", "Healthcare", selected_facets) is False
        assert use_case._is_facet_value_selected("status", "Active", selected_facets) is False

    @pytest.mark.asyncio
    async def test_faceted_search_with_complex_facets(
        self, use_case, mock_faceted_search_port, mock_authorization_port
    ):
        """Test faceted search with complex facet structure."""
        # Arrange
        request = FacetedSearchRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            query="complex search",
            selected_facets={
                "type": ["Person", "Organization"],
                "domain": ["Technology", "Healthcare"],
                "status": ["Active"]
            },
            facet_fields=["type", "domain", "status", "location", "industry"],
        )

        complex_search_result = {
            "results": [
                {
                    "node_id": "node-1",
                    "node_type": "Person",
                    "label": "Jane Smith",
                    "properties": {"name": "Jane Smith", "title": "CTO"},
                    "score": 0.92,
                }
            ],
            "facets": [
                {
                    "field": "type",
                    "label": "Entity Type",
                    "values": [
                        {"value": "Person", "count": 25},
                        {"value": "Organization", "count": 15},
                        {"value": "Location", "count": 5}
                    ]
                },
                {
                    "field": "domain",
                    "values": [
                        {"value": "Technology", "count": 20},
                        {"value": "Healthcare", "count": 15},
                        {"value": "Finance", "count": 10}
                    ]
                },
                {
                    "field": "status",
                    "values": [
                        {"value": "Active", "count": 35},
                        {"value": "Inactive", "count": 10}
                    ]
                }
            ],
            "total_results": 45
        }

        mock_authorization_port.check_permission.return_value = True
        mock_faceted_search_port.search_with_facets.return_value = complex_search_result

        # Act
        result = await use_case.execute(request)

        # Assert
        assert len(result.facets) == 3
        assert result.applied_filters == {
            "type": ["Person", "Organization"],
            "domain": ["Technology", "Healthcare"],
            "status": ["Active"]
        }

        # Check facet selection states
        type_facet = next(f for f in result.facets if f.field == "type")
        person_value = next(v for v in type_facet.values if v.value == "Person")
        location_value = next(v for v in type_facet.values if v.value == "Location")

        assert person_value.selected is True
        assert location_value.selected is False