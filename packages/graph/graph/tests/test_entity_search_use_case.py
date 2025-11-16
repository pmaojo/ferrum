"""Tests for entity search use case."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from application.use_cases.search.entity_search_use_case import EntitySearchUseCase
from application.use_cases.dto import (
    EntitySearchRequestDTO,
    EntitySearchResponseDTO,
    PaginationParams,
    SortParams,
    SortDirection,
)
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
)


class TestEntitySearchUseCase:
    """Test cases for EntitySearchUseCase."""

    @pytest.fixture
    def entity_search_port(self):
        """Mock entity search port."""
        return Mock()

    @pytest.fixture
    def authorization_port(self):
        """Mock authorization port."""
        return Mock()

    @pytest.fixture
    def use_case(self, entity_search_port, authorization_port):
        """Create use case instance."""
        return EntitySearchUseCase(
            entity_search_port=entity_search_port,
            authorization_port=authorization_port,
        )

    @pytest.fixture
    def valid_request(self):
        """Create valid entity search request."""
        return EntitySearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            entity_types=["Person", "Organization"],
            property_filters={"status": "active", "category": {"in": ["tech", "finance"]}},
            text_query="artificial intelligence",
            pagination=PaginationParams(page=1, page_size=20),
            sort=SortParams(sort_by="created_at", direction=SortDirection.DESC),
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, valid_request, entity_search_port, authorization_port):
        """Test successful entity search execution."""
        # Arrange
        authorization_port.check_permission.return_value = True

        mock_entities = [
            {
                "id": "entity-1",
                "type": "Person",
                "label": "John Doe",
                "properties": {"name": "John Doe", "role": "AI Researcher"},
                "relationship_count": 5,
                "created_at": datetime(2023, 1, 1),
                "updated_at": datetime(2023, 6, 1),
            },
            {
                "id": "entity-2",
                "type": "Organization",
                "label": "AI Corp",
                "properties": {"name": "AI Corp", "industry": "Technology"},
                "relationship_count": 12,
                "created_at": datetime(2023, 2, 1),
            },
        ]
        entity_search_port.search_entities.return_value = (mock_entities, 25)

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, EntitySearchResponseDTO)
        assert response.kg_id == valid_request.kg_id
        assert response.tenant_id == valid_request.tenant_id
        assert len(response.entities) == 2
        assert response.total_entities == 25
        assert response.processing_time_ms > 0
        assert isinstance(response.search_timestamp, datetime)

        # Check filters applied
        assert "entity_types" in response.filters_applied
        assert "property_filters" in response.filters_applied
        assert "text_query" in response.filters_applied

        # Check first entity
        first_entity = response.entities[0]
        assert first_entity.id == "entity-1"
        assert first_entity.type == "Person"
        assert first_entity.label == "John Doe"
        assert first_entity.relationship_count == 5
        assert first_entity.created_at == datetime(2023, 1, 1)
        assert first_entity.updated_at == datetime(2023, 6, 1)

        # Check second entity
        second_entity = response.entities[1]
        assert second_entity.id == "entity-2"
        assert second_entity.updated_at is None

        # Verify port calls
        authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )
        entity_search_port.search_entities.assert_called_once_with(
            kg_id=valid_request.kg_id,
            tenant_id=valid_request.tenant_id,
            entity_types=valid_request.entity_types,
            property_filters=valid_request.property_filters,
            text_query=valid_request.text_query,
            page=1,
            page_size=20,
            sort_by="created_at",
            sort_direction="desc",
        )

    @pytest.mark.asyncio
    async def test_execute_with_defaults(self, use_case, entity_search_port, authorization_port):
        """Test entity search with default pagination and sorting."""
        # Arrange
        request = EntitySearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            entity_types=["Person"],
        )
        authorization_port.check_permission.return_value = True
        entity_search_port.search_entities.return_value = ([], 0)

        # Act
        response = await use_case.execute(request)

        # Assert
        entity_search_port.search_entities.assert_called_once_with(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            entity_types=request.entity_types,
            property_filters=None,
            text_query=None,
            page=1,
            page_size=20,
            sort_by=None,
            sort_direction="asc",
        )

    @pytest.mark.asyncio
    async def test_execute_authorization_failure(self, use_case, valid_request, authorization_port):
        """Test entity search with authorization failure."""
        # Arrange
        authorization_port.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            await use_case.execute(valid_request)

        assert "lacks read permission" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_knowledge_graph_not_found(self, use_case, valid_request, entity_search_port, authorization_port):
        """Test entity search when knowledge graph is not found."""
        # Arrange
        authorization_port.check_permission.return_value = True
        entity_search_port.search_entities.side_effect = Exception("Knowledge graph not found")

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_search_error(self, use_case, valid_request, entity_search_port, authorization_port):
        """Test entity search with search error."""
        # Arrange
        authorization_port.check_permission.return_value = True
        entity_search_port.search_entities.side_effect = Exception("Search service unavailable")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Entity search failed" in str(exc_info.value)

    def test_validate_request_missing_kg_id(self, use_case, valid_request):
        """Test validation with missing knowledge graph ID."""
        valid_request.kg_id = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_validate_request_missing_tenant_id(self, use_case, valid_request):
        """Test validation with missing tenant ID."""
        valid_request.tenant_id = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Tenant ID is required" in str(exc_info.value)

    def test_validate_request_missing_user_id(self, use_case, valid_request):
        """Test validation with missing user ID."""
        valid_request.user_id = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "User ID is required" in str(exc_info.value)

    def test_validate_request_invalid_entity_types_not_list(self, use_case, valid_request):
        """Test validation with invalid entity types (not a list)."""
        valid_request.entity_types = "Person"

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "entity_types must be a list" in str(exc_info.value)

    def test_validate_request_invalid_entity_types_non_string(self, use_case, valid_request):
        """Test validation with invalid entity types (non-string elements)."""
        valid_request.entity_types = ["Person", 123]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "All entity types must be strings" in str(exc_info.value)

    def test_validate_request_empty_entity_types(self, use_case, valid_request):
        """Test validation with empty entity types list."""
        valid_request.entity_types = []

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "entity_types cannot be empty if provided" in str(exc_info.value)

    def test_validate_request_invalid_property_filters_not_dict(self, use_case, valid_request):
        """Test validation with invalid property filters (not a dict)."""
        valid_request.property_filters = ["status", "active"]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "property_filters must be a dictionary" in str(exc_info.value)

    def test_validate_request_invalid_filter_operator(self, use_case, valid_request):
        """Test validation with invalid filter operator."""
        valid_request.property_filters = {"status": {"invalid_op": "active"}}

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Invalid filter operator 'invalid_op'" in str(exc_info.value)

    def test_validate_request_invalid_text_query_not_string(self, use_case, valid_request):
        """Test validation with invalid text query (not a string)."""
        valid_request.text_query = 123

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "text_query must be a string" in str(exc_info.value)

    def test_validate_request_empty_text_query(self, use_case, valid_request):
        """Test validation with empty text query."""
        valid_request.text_query = "   "

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "text_query cannot be empty if provided" in str(exc_info.value)

    def test_validate_request_invalid_pagination_page(self, use_case, valid_request):
        """Test validation with invalid pagination page."""
        valid_request.pagination = PaginationParams(page=0, page_size=20)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Page must be greater than or equal to 1" in str(exc_info.value)

    def test_validate_request_invalid_pagination_page_size(self, use_case, valid_request):
        """Test validation with invalid pagination page size."""
        valid_request.pagination = PaginationParams(page=1, page_size=0)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Page size must be greater than or equal to 1" in str(exc_info.value)

    def test_validate_request_pagination_page_size_too_large(self, use_case, valid_request):
        """Test validation with page size exceeding maximum."""
        valid_request.pagination = PaginationParams(page=1, page_size=1001)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Page size cannot exceed 1000" in str(exc_info.value)

    def test_validate_request_invalid_sort_field(self, use_case, valid_request):
        """Test validation with invalid sort field."""
        valid_request.sort = SortParams(sort_by="invalid_field", direction=SortDirection.ASC)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Invalid sort field 'invalid_field'" in str(exc_info.value)

    def test_validate_request_empty_sort_by(self, use_case, valid_request):
        """Test validation with empty sort_by field."""
        valid_request.sort = SortParams(sort_by="", direction=SortDirection.ASC)

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "sort_by is required when sort is provided" in str(exc_info.value)

    def test_validate_request_no_search_criteria(self, use_case, valid_request):
        """Test validation with no search criteria provided."""
        valid_request.entity_types = None
        valid_request.property_filters = None
        valid_request.text_query = None

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "At least one search criterion must be provided" in str(exc_info.value)

    def test_validate_request_valid_property_filters(self, use_case, valid_request):
        """Test validation with valid property filters."""
        valid_request.property_filters = {
            "status": "active",
            "age": {"gte": 18, "lt": 65},
            "tags": {"in": ["tech", "ai"]},
            "description": {"contains": "machine learning"},
            "verified": {"exists": True},
        }

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)

    def test_validate_request_valid_minimal(self, use_case):
        """Test validation with minimal valid request."""
        request = EntitySearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            entity_types=["Person"],
        )

        # Should not raise any exception
        use_case._validate_request_internal(request)