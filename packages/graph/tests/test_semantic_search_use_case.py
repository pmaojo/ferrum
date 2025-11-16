"""Tests for semantic search use case."""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from application.use_cases.dto import (
    SemanticSearchRequestDTO,
    SemanticSearchResponseDTO,
)
from application.use_cases.search.semantic_search_use_case import SemanticSearchUseCase
from application.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)


class TestSemanticSearchUseCase:
    """Test cases for SemanticSearchUseCase."""

    @pytest.fixture
    def semantic_search_port(self):
        """Mock semantic search port."""
        return Mock()

    @pytest.fixture
    def authorization_port(self):
        """Mock authorization port."""
        return Mock()

    @pytest.fixture
    def use_case(self, semantic_search_port, authorization_port):
        """Create use case instance."""
        return SemanticSearchUseCase(
            semantic_search_port=semantic_search_port,
            authorization_port=authorization_port,
        )

    @pytest.fixture
    def valid_request(self):
        """Create valid semantic search request."""
        return SemanticSearchRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            query="artificial intelligence",
            limit=10,
            threshold=0.7,
            include_properties=True,
            filter_by_node_types=["Concept", "Entity"],
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self, use_case, valid_request, semantic_search_port, authorization_port
    ):
        """Test successful semantic search execution."""
        # Arrange
        authorization_port.check_permission.return_value = True

        mock_results = [
            {
                "node_id": "node-1",
                "node_type": "Concept",
                "label": "Artificial Intelligence",
                "properties": {"definition": "Machine intelligence"},
                "score": 0.95,
                "snippet": "AI is the simulation of human intelligence...",
            },
            {
                "node_id": "node-2",
                "node_type": "Entity",
                "label": "Machine Learning",
                "properties": {"category": "AI Subfield"},
                "score": 0.85,
            },
        ]
        semantic_search_port.search.return_value = mock_results

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, SemanticSearchResponseDTO)
        assert response.kg_id == valid_request.kg_id
        assert response.tenant_id == valid_request.tenant_id
        assert response.query == valid_request.query
        assert len(response.results) == 2
        assert response.total_results == 2
        assert response.processing_time_ms > 0
        assert isinstance(response.search_timestamp, datetime)

        # Check first result
        first_result = response.results[0]
        assert first_result.node_id == "node-1"
        assert first_result.node_type == "Concept"
        assert first_result.label == "Artificial Intelligence"
        assert first_result.score == 0.95
        assert first_result.snippet == "AI is the simulation of human intelligence..."
        assert "definition" in first_result.properties

        # Check second result
        second_result = response.results[1]
        assert second_result.node_id == "node-2"
        assert second_result.snippet is None

        # Verify port calls
        authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )
        semantic_search_port.search.assert_called_once_with(
            kg_id=valid_request.kg_id,
            tenant_id=valid_request.tenant_id,
            query=valid_request.query,
            limit=valid_request.limit,
            threshold=valid_request.threshold,
            filter_by_node_types=valid_request.filter_by_node_types,
        )

    @pytest.mark.asyncio
    async def test_execute_without_properties(
        self, use_case, valid_request, semantic_search_port, authorization_port
    ):
        """Test semantic search without including properties."""
        # Arrange
        valid_request.include_properties = False
        authorization_port.check_permission.return_value = True

        mock_results = [
            {
                "node_id": "node-1",
                "node_type": "Concept",
                "label": "AI",
                "properties": {"definition": "Should not be included"},
                "score": 0.9,
            }
        ]
        semantic_search_port.search.return_value = mock_results

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert len(response.results) == 1
        result = response.results[0]
        assert result.properties == {}

    @pytest.mark.asyncio
    async def test_execute_authorization_failure(
        self, use_case, valid_request, authorization_port
    ):
        """Test semantic search with authorization failure."""
        # Arrange
        authorization_port.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            await use_case.execute(valid_request)

        assert "lacks read permission" in str(exc_info.value)
        authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )

    @pytest.mark.asyncio
    async def test_execute_knowledge_graph_not_found(
        self, use_case, valid_request, semantic_search_port, authorization_port, caplog
    ):
        """Test semantic search when knowledge graph is not found."""
        # Arrange
        authorization_port.check_permission.return_value = True
        semantic_search_port.search.side_effect = Exception("Knowledge graph not found")

        caplog.set_level(logging.ERROR)

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "not found" in str(exc_info.value)
        assert any(
            "Knowledge graph not found" in record.getMessage()
            and f"tenant_id={valid_request.tenant_id}" in record.getMessage()
            and "request_id=" in record.getMessage()
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_execute_search_error(
        self, use_case, valid_request, semantic_search_port, authorization_port
    ):
        """Test semantic search with search error."""
        # Arrange
        authorization_port.check_permission.return_value = True
        semantic_search_port.search.side_effect = Exception(
            "Search service unavailable"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Semantic search failed" in str(exc_info.value)

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

    def test_validate_request_empty_query(self, use_case, valid_request):
        """Test validation with empty query."""
        valid_request.query = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Search query is required" in str(exc_info.value)

    def test_validate_request_whitespace_query(self, use_case, valid_request):
        """Test validation with whitespace-only query."""
        valid_request.query = "   "

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Search query is required" in str(exc_info.value)

    def test_validate_request_invalid_limit_zero(self, use_case, valid_request):
        """Test validation with zero limit."""
        valid_request.limit = 0

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Limit must be greater than 0" in str(exc_info.value)

    def test_validate_request_invalid_limit_negative(self, use_case, valid_request):
        """Test validation with negative limit."""
        valid_request.limit = -5

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Limit must be greater than 0" in str(exc_info.value)

    def test_validate_request_limit_too_large(self, use_case, valid_request):
        """Test validation with limit exceeding maximum."""
        valid_request.limit = 1001

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Limit cannot exceed 1000" in str(exc_info.value)

    def test_validate_request_invalid_threshold_negative(self, use_case, valid_request):
        """Test validation with negative threshold."""
        valid_request.threshold = -0.1

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Threshold must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_request_invalid_threshold_too_large(
        self, use_case, valid_request
    ):
        """Test validation with threshold greater than 1.0."""
        valid_request.threshold = 1.1

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Threshold must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_request_invalid_node_types_not_list(
        self, use_case, valid_request
    ):
        """Test validation with invalid node types (not a list)."""
        valid_request.filter_by_node_types = "Concept"

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "filter_by_node_types must be a list" in str(exc_info.value)

    def test_validate_request_invalid_node_types_non_string(
        self, use_case, valid_request
    ):
        """Test validation with invalid node types (non-string elements)."""
        valid_request.filter_by_node_types = ["Concept", 123]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "All node types in filter must be strings" in str(exc_info.value)

    def test_validate_request_valid_edge_cases(self, use_case, valid_request):
        """Test validation with valid edge cases."""
        # Test minimum valid values
        valid_request.limit = 1
        valid_request.threshold = 0.0
        valid_request.filter_by_node_types = None

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)

        # Test maximum valid values
        valid_request.limit = 1000
        valid_request.threshold = 1.0
        valid_request.filter_by_node_types = []

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)
