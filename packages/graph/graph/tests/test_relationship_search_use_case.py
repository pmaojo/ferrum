"""Tests for relationship search use case."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from application.use_cases.search.relationship_search_use_case import RelationshipSearchUseCase
from application.use_cases.dto import (
    RelationshipSearchRequestDTO,
    RelationshipSearchResponseDTO,
    PaginationParams,
)
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
)


class TestRelationshipSearchUseCase:
    """Test cases for RelationshipSearchUseCase."""

    @pytest.fixture
    def relationship_search_port(self):
        """Mock relationship search port."""
        return Mock()

    @pytest.fixture
    def authorization_port(self):
        """Mock authorization port."""
        return Mock()

    @pytest.fixture
    def use_case(self, relationship_search_port, authorization_port):
        """Create use case instance."""
        return RelationshipSearchUseCase(
            relationship_search_port=relationship_search_port,
            authorization_port=authorization_port,
        )

    @pytest.fixture
    def valid_request(self):
        """Create valid relationship search request."""
        return RelationshipSearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-2",
            relationship_types=["WORKS_FOR", "COLLABORATES_WITH"],
            property_filters={"strength": {"gte": 0.5}, "verified": True},
            pagination=PaginationParams(page=1, page_size=20),
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, valid_request, relationship_search_port, authorization_port):
        """Test successful relationship search execution."""
        # Arrange
        authorization_port.check_permission.return_value = True

        mock_relationships = [
            {
                "id": "rel-1",
                "source_node_id": "node-1",
                "target_node_id": "node-2",
                "relationship_type": "WORKS_FOR",
                "properties": {"strength": 0.8, "verified": True},
                "source_node_label": "John Doe",
                "target_node_label": "AI Corp",
                "weight": 0.8,
            },
            {
                "id": "rel-2",
                "source_node_id": "node-1",
                "target_node_id": "node-3",
                "relationship_type": "COLLABORATES_WITH",
                "properties": {"strength": 0.6},
                "source_node_label": "John Doe",
                "target_node_label": "Jane Smith",
            },
        ]
        relationship_search_port.search_relationships.return_value = (mock_relationships, 15)

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, RelationshipSearchResponseDTO)
        assert response.kg_id == valid_request.kg_id
        assert response.tenant_id == valid_request.tenant_id
        assert len(response.relationships) == 2
        assert response.total_relationships == 15
        assert response.pattern_matched is None
        assert response.processing_time_ms > 0
        assert isinstance(response.search_timestamp, datetime)

        # Check first relationship
        first_rel = response.relationships[0]
        assert first_rel.id == "rel-1"
        assert first_rel.source_node_id == "node-1"
        assert first_rel.target_node_id == "node-2"
        assert first_rel.relationship_type == "WORKS_FOR"
        assert first_rel.source_node_label == "John Doe"
        assert first_rel.target_node_label == "AI Corp"
        assert first_rel.weight == 0.8

        # Check second relationship
        second_rel = response.relationships[1]
        assert second_rel.id == "rel-2"
        assert second_rel.weight is None

        # Verify port calls
        authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )
        relationship_search_port.search_relationships.assert_called_once_with(
            kg_id=valid_request.kg_id,
            tenant_id=valid_request.tenant_id,
            source_node_id=valid_request.source_node_id,
            target_node_id=valid_request.target_node_id,
            relationship_types=valid_request.relationship_types,
            pattern=valid_request.pattern,
            property_filters=valid_request.property_filters,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_execute_with_pattern(self, use_case, relationship_search_port, authorization_port):
        """Test relationship search with pattern matching."""
        # Arrange
        request = RelationshipSearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            pattern="(a:Person)-[r:WORKS_FOR]->(b:Organization)",
        )
        authorization_port.check_permission.return_value = True
        relationship_search_port.search_relationships.return_value = ([], 0)

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.pattern_matched == request.pattern
        relationship_search_port.search_relationships.assert_called_once_with(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            source_node_id=None,
            target_node_id=None,
            relationship_types=None,
            pattern=request.pattern,
            property_filters=None,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_execute_with_defaults(self, use_case, relationship_search_port, authorization_port):
        """Test relationship search with default pagination."""
        # Arrange
        request = RelationshipSearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            relationship_types=["KNOWS"],
        )
        authorization_port.check_permission.return_value = True
        relationship_search_port.search_relationships.return_value = ([], 0)

        # Act
        response = await use_case.execute(request)

        # Assert
        relationship_search_port.search_relationships.assert_called_once_with(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            source_node_id=None,
            target_node_id=None,
            relationship_types=request.relationship_types,
            pattern=None,
            property_filters=None,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_execute_authorization_failure(self, use_case, valid_request, authorization_port):
        """Test relationship search with authorization failure."""
        # Arrange
        authorization_port.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            await use_case.execute(valid_request)

        assert "lacks read permission" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_knowledge_graph_not_found(self, use_case, valid_request, relationship_search_port, authorization_port):
        """Test relationship search when knowledge graph is not found."""
        # Arrange
        authorization_port.check_permission.return_value = True
        relationship_search_port.search_relationships.side_effect = Exception("Knowledge graph not found")

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_search_error(self, use_case, valid_request, relationship_search_port, authorization_port):
        """Test relationship search with search error."""
        # Arrange
        authorization_port.check_permission.return_value = True
        relationship_search_port.search_relationships.side_effect = Exception("Search service unavailable")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Relationship search failed" in str(exc_info.value)

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

    def test_validate_request_invalid_source_node_id(self, use_case, valid_request):
        """Test validation with invalid source node ID."""
        valid_request.source_node_id = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "source_node_id must be a non-empty string" in str(exc_info.value)

    def test_validate_request_invalid_target_node_id(self, use_case, valid_request):
        """Test validation with invalid target node ID."""
        valid_request.target_node_id = "   "

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "target_node_id must be a non-empty string" in str(exc_info.value)

    def test_validate_request_invalid_relationship_types_not_list(self, use_case, valid_request):
        """Test validation with invalid relationship types (not a list)."""
        valid_request.relationship_types = "WORKS_FOR"

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "relationship_types must be a list" in str(exc_info.value)

    def test_validate_request_invalid_relationship_types_non_string(self, use_case, valid_request):
        """Test validation with invalid relationship types (non-string elements)."""
        valid_request.relationship_types = ["WORKS_FOR", 123]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "All relationship types must be strings" in str(exc_info.value)

    def test_validate_request_empty_relationship_types(self, use_case, valid_request):
        """Test validation with empty relationship types list."""
        valid_request.relationship_types = []

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "relationship_types cannot be empty if provided" in str(exc_info.value)

    def test_validate_request_invalid_pattern_empty(self, use_case, valid_request):
        """Test validation with empty pattern."""
        valid_request.pattern = ""
        valid_request.source_node_id = None
        valid_request.target_node_id = None
        valid_request.relationship_types = None
        valid_request.property_filters = None

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "pattern must be a non-empty string" in str(exc_info.value)

    def test_validate_request_invalid_pattern_format(self, use_case, valid_request):
        """Test validation with invalid pattern format."""
        valid_request.pattern = "invalid pattern"
        valid_request.source_node_id = None
        valid_request.target_node_id = None
        valid_request.relationship_types = None

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "pattern should be a valid Cypher-like pattern" in str(exc_info.value)

    def test_validate_request_pattern_with_conflicting_params(self, use_case, valid_request):
        """Test validation with pattern and conflicting parameters."""
        valid_request.pattern = "(a)-[r]->(b)"
        # source_node_id is already set in valid_request

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "pattern cannot be used together with" in str(exc_info.value)

    def test_validate_request_invalid_property_filters_not_dict(self, use_case, valid_request):
        """Test validation with invalid property filters (not a dict)."""
        valid_request.property_filters = ["strength", "0.5"]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "property_filters must be a dictionary" in str(exc_info.value)

    def test_validate_request_invalid_filter_operator(self, use_case, valid_request):
        """Test validation with invalid filter operator."""
        valid_request.property_filters = {"strength": {"invalid_op": 0.5}}

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Invalid filter operator 'invalid_op'" in str(exc_info.value)

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

    def test_validate_request_no_search_criteria(self, use_case, valid_request):
        """Test validation with no search criteria provided."""
        valid_request.source_node_id = None
        valid_request.target_node_id = None
        valid_request.relationship_types = None
        valid_request.pattern = None
        valid_request.property_filters = None

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "At least one search criterion must be provided" in str(exc_info.value)

    def test_validate_request_valid_patterns(self, use_case):
        """Test validation with valid Cypher patterns."""
        valid_patterns = [
            "(a)-[r]->(b)",
            "(a:Person)-[:WORKS_FOR]->(b:Organization)",
            "MATCH (a)-[r]->(b) RETURN a, r, b",
            "(a {name: 'John'})-[r:KNOWS {since: 2020}]->(b)",
        ]

        for pattern in valid_patterns:
            request = RelationshipSearchRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                kg_id="kg-789",
                pattern=pattern,
            )

            # Should not raise any exception
            use_case._validate_request_internal(request)

    def test_validate_request_valid_property_filters(self, use_case, valid_request):
        """Test validation with valid property filters."""
        valid_request.property_filters = {
            "strength": 0.8,
            "weight": {"gte": 0.5, "lt": 1.0},
            "tags": {"in": ["important", "verified"]},
            "description": {"contains": "collaboration"},
            "active": {"exists": True},
        }

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)

    def test_validate_request_valid_minimal(self, use_case):
        """Test validation with minimal valid request."""
        request = RelationshipSearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
        )

        # Should not raise any exception
        use_case._validate_request_internal(request)