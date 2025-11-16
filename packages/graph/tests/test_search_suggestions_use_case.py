"""Tests for search suggestions use case."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from application.use_cases.search.search_suggestions_use_case import SearchSuggestionsUseCase
from application.use_cases.dto import SearchSuggestionsRequestDTO, SearchSuggestionsResponseDTO
from application.exceptions import ValidationError, NotFoundError, AuthorizationError


class TestSearchSuggestionsUseCase:
    """Test cases for SearchSuggestionsUseCase."""

    @pytest.fixture
    def search_suggestions_port(self):
        """Mock search suggestions port."""
        return Mock()

    @pytest.fixture
    def authorization_port(self):
        """Mock authorization port."""
        return Mock()

    @pytest.fixture
    def use_case(self, search_suggestions_port, authorization_port):
        """Create use case instance."""
        return SearchSuggestionsUseCase(
            search_suggestions_port=search_suggestions_port,
            authorization_port=authorization_port,
        )

    @pytest.fixture
    def valid_request(self):
        """Create valid search suggestions request."""
        return SearchSuggestionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            partial_query="artif",
            suggestion_types=["entities", "relationships"],
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, valid_request, search_suggestions_port, authorization_port):
        """Test successful search suggestions execution."""
        # Arrange
        authorization_port.check_permission.return_value = True

        mock_suggestions = [
            {
                "text": "artificial intelligence",
                "type": "entities",
                "score": 0.95,
                "metadata": {"node_count": 15, "category": "concept"},
            },
            {
                "text": "artificial neural network",
                "type": "entities",
                "score": 0.88,
                "metadata": {"node_count": 8},
            },
            {
                "text": "creates_artificial",
                "type": "relationships",
                "score": 0.75,
                "metadata": {"edge_count": 3},
            },
        ]
        search_suggestions_port.get_suggestions.return_value = mock_suggestions

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, SearchSuggestionsResponseDTO)
        assert response.kg_id == valid_request.kg_id
        assert response.tenant_id == valid_request.tenant_id
        assert response.partial_query == valid_request.partial_query
        assert len(response.suggestions) == 3
        assert response.total_suggestions == 3
        assert response.processing_time_ms > 0

        # Check first suggestion
        first_suggestion = response.suggestions[0]
        assert first_suggestion.text == "artificial intelligence"
        assert first_suggestion.type == "entities"
        assert first_suggestion.score == 0.95
        assert first_suggestion.metadata["node_count"] == 15
        assert first_suggestion.metadata["category"] == "concept"

        # Check second suggestion
        second_suggestion = response.suggestions[1]
        assert second_suggestion.text == "artificial neural network"
        assert second_suggestion.type == "entities"
        assert second_suggestion.score == 0.88
        assert "node_count" in second_suggestion.metadata

        # Check third suggestion
        third_suggestion = response.suggestions[2]
        assert third_suggestion.text == "creates_artificial"
        assert third_suggestion.type == "relationships"
        assert third_suggestion.score == 0.75

        # Verify port calls
        authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )
        search_suggestions_port.get_suggestions.assert_called_once_with(
            kg_id=valid_request.kg_id,
            tenant_id=valid_request.tenant_id,
            partial_query=valid_request.partial_query,
            suggestion_types=valid_request.suggestion_types,
            limit=valid_request.limit,
        )

    @pytest.mark.asyncio
    async def test_execute_empty_suggestions(self, use_case, valid_request, search_suggestions_port, authorization_port):
        """Test search suggestions with no results."""
        # Arrange
        authorization_port.check_permission.return_value = True
        search_suggestions_port.get_suggestions.return_value = []

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert isinstance(response, SearchSuggestionsResponseDTO)
        assert len(response.suggestions) == 0
        assert response.total_suggestions == 0

    @pytest.mark.asyncio
    async def test_execute_single_suggestion_type(self, use_case, valid_request, search_suggestions_port, authorization_port):
        """Test search suggestions with single suggestion type."""
        # Arrange
        valid_request.suggestion_types = ["properties"]
        authorization_port.check_permission.return_value = True

        mock_suggestions = [
            {
                "text": "artificial_property",
                "type": "properties",
                "score": 0.9,
                "metadata": {"property_type": "string"},
            }
        ]
        search_suggestions_port.get_suggestions.return_value = mock_suggestions

        # Act
        response = await use_case.execute(valid_request)

        # Assert
        assert len(response.suggestions) == 1
        suggestion = response.suggestions[0]
        assert suggestion.type == "properties"
        assert suggestion.text == "artificial_property"

    @pytest.mark.asyncio
    async def test_execute_authorization_failure(self, use_case, valid_request, authorization_port):
        """Test search suggestions with authorization failure."""
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
    async def test_execute_knowledge_graph_not_found(self, use_case, valid_request, search_suggestions_port, authorization_port):
        """Test search suggestions when knowledge graph is not found."""
        # Arrange
        authorization_port.check_permission.return_value = True
        search_suggestions_port.get_suggestions.side_effect = Exception("Knowledge graph not found")

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_suggestions_error(self, use_case, valid_request, search_suggestions_port, authorization_port):
        """Test search suggestions with suggestions service error."""
        # Arrange
        authorization_port.check_permission.return_value = True
        search_suggestions_port.get_suggestions.side_effect = Exception("Suggestions service unavailable")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Search suggestions failed" in str(exc_info.value)

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

    def test_validate_request_empty_partial_query(self, use_case, valid_request):
        """Test validation with empty partial query."""
        valid_request.partial_query = ""

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Partial query is required" in str(exc_info.value)

    def test_validate_request_whitespace_partial_query(self, use_case, valid_request):
        """Test validation with whitespace-only partial query."""
        valid_request.partial_query = "   "

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Partial query is required" in str(exc_info.value)

    def test_validate_request_partial_query_too_long(self, use_case, valid_request):
        """Test validation with partial query exceeding maximum length."""
        valid_request.partial_query = "a" * 101  # Exceeds max length of 100

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "cannot exceed 100 characters" in str(exc_info.value)

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
        valid_request.limit = 51  # Exceeds max limit of 50

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Limit cannot exceed 50" in str(exc_info.value)

    def test_validate_request_suggestion_types_not_list(self, use_case, valid_request):
        """Test validation with suggestion_types not being a list."""
        valid_request.suggestion_types = "entities"

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "suggestion_types must be a list" in str(exc_info.value)

    def test_validate_request_empty_suggestion_types(self, use_case, valid_request):
        """Test validation with empty suggestion_types list."""
        valid_request.suggestion_types = []

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "At least one suggestion type must be specified" in str(exc_info.value)

    def test_validate_request_invalid_suggestion_types(self, use_case, valid_request):
        """Test validation with invalid suggestion types."""
        valid_request.suggestion_types = ["entities", "invalid_type", "relationships"]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "Invalid suggestion types: ['invalid_type']" in str(exc_info.value)
        assert "Valid types are: ['entities', 'properties', 'relationships']" in str(exc_info.value)

    def test_validate_request_non_string_suggestion_types(self, use_case, valid_request):
        """Test validation with non-string suggestion types."""
        valid_request.suggestion_types = ["entities", 123]

        with pytest.raises(ValidationError) as exc_info:
            use_case._validate_request_internal(valid_request)

        assert "All suggestion types must be strings" in str(exc_info.value)

    def test_validate_request_valid_edge_cases(self, use_case, valid_request):
        """Test validation with valid edge cases."""
        # Test minimum valid values
        valid_request.partial_query = "a"  # Minimum length
        valid_request.limit = 1
        valid_request.suggestion_types = ["entities"]

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)

        # Test maximum valid values
        valid_request.partial_query = "a" * 100  # Maximum length
        valid_request.limit = 50  # Maximum limit
        valid_request.suggestion_types = ["entities", "relationships", "properties"]

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)

    def test_validate_request_all_valid_suggestion_types(self, use_case, valid_request):
        """Test validation with all valid suggestion types."""
        valid_request.suggestion_types = ["entities", "relationships", "properties"]

        # Should not raise any exception
        use_case._validate_request_internal(valid_request)