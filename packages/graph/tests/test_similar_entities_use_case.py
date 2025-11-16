"""Tests for SimilarEntitiesUseCase."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime
from typing import List, Dict, Any

from application.use_cases.search.similar_entities_use_case import (
    SimilarEntitiesUseCase,
    SimilarEntitiesConfig,
)
from application.use_cases.dto import (
    SimilarEntitiesRequestDTO,
    SimilarEntitiesResponseDTO,
    SimilarEntityDTO,
    EntityDTO,
    SimilarityExplanationDTO,
)
from application.ports import (
    SimilaritySearchPort,
    AuthorizationPort,
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError


class TestSimilarEntitiesUseCase:
    """Test cases for SimilarEntitiesUseCase."""

    @pytest.fixture
    def mock_similarity_port(self) -> AsyncMock:
        """Create mock similarity search port."""
        return AsyncMock(spec=SimilaritySearchPort)

    @pytest.fixture
    def mock_authorization_port(self) -> AsyncMock:
        """Create mock authorization port."""
        return AsyncMock(spec=AuthorizationPort)

    @pytest.fixture
    def use_case(
        self,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ) -> SimilarEntitiesUseCase:
        """Create SimilarEntitiesUseCase instance."""
        return SimilarEntitiesUseCase(
            similarity_search_port=mock_similarity_port,
            authorization_port=mock_authorization_port,
        )

    @pytest.fixture
    def valid_request(self) -> SimilarEntitiesRequestDTO:
        """Create valid similar entities request."""
        return SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            similarity_algorithm="embedding",
            limit=10,
            threshold=0.7,
            include_explanation=True,
        )

    @pytest.fixture
    def mock_similarity_results(self) -> List[Dict[str, Any]]:
        """Create mock similarity search results."""
        return [
            {
                "entity": {
                    "id": "entity-def",
                    "type": "Person",
                    "label": "John Doe",
                    "properties": {"age": 30, "city": "New York"},
                    "relationship_count": 5,
                    "created_at": datetime(2023, 1, 1, 10, 0, 0),
                    "updated_at": datetime(2023, 1, 1, 11, 0, 0),
                },
                "similarity_score": 0.85,
                "explanation": {
                    "algorithm": "embedding",
                    "factors": {"semantic": 0.8, "structural": 0.9},
                    "description": "High semantic and structural similarity",
                },
            },
            {
                "entity": {
                    "id": "entity-ghi",
                    "type": "Person",
                    "label": "Jane Smith",
                    "properties": {"age": 28, "city": "Boston"},
                    "relationship_count": 3,
                    "created_at": datetime(2023, 1, 1, 9, 0, 0),
                    "updated_at": datetime(2023, 1, 1, 10, 30, 0),
                },
                "similarity_score": 0.75,
                "explanation": {
                    "algorithm": "embedding",
                    "factors": {"semantic": 0.7, "structural": 0.8},
                    "description": "Good semantic and structural similarity",
                },
            },
        ]

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_success_with_explanation(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
        mock_similarity_results: List[Dict[str, Any]],
    ):
        """Test successful execution with explanation."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.return_value = mock_similarity_results

        # Act
        result = await use_case.execute(valid_request)

        # Assert
        assert isinstance(result, SimilarEntitiesResponseDTO)
        assert result.kg_id == valid_request.kg_id
        assert result.tenant_id == valid_request.tenant_id
        assert result.source_entity_id == valid_request.entity_id
        assert result.algorithm_used == valid_request.similarity_algorithm
        assert len(result.similar_entities) == 2
        assert result.processing_time_ms >= 0

        # Check first similar entity
        first_entity = result.similar_entities[0]
        assert first_entity.entity.id == "entity-def"
        assert first_entity.entity.type == "Person"
        assert first_entity.entity.label == "John Doe"
        assert first_entity.similarity_score == 0.85
        assert first_entity.explanation is not None
        assert first_entity.explanation.algorithm == "embedding"
        assert first_entity.explanation.factors == {"semantic": 0.8, "structural": 0.9}

        # Verify port calls
        mock_authorization_port.check_permission.assert_called_once_with(
            valid_request.user_id, valid_request.kg_id, "read"
        )
        mock_similarity_port.find_similar_entities.assert_called_once_with(
            kg_id=valid_request.kg_id,
            tenant_id=valid_request.tenant_id,
            entity_id=valid_request.entity_id,
            similarity_algorithm=valid_request.similarity_algorithm,
            limit=valid_request.limit,
            threshold=valid_request.threshold,
            include_explanation=valid_request.include_explanation,
        )

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_success_without_explanation(
        self,
        use_case: SimilarEntitiesUseCase,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test successful execution without explanation."""
        # Arrange
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            similarity_algorithm="structural",
            limit=5,
            threshold=0.8,
            include_explanation=False,
        )

        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.return_value = [
            {
                "entity": {
                    "id": "entity-def",
                    "type": "Person",
                    "label": "John Doe",
                    "properties": {"age": 30},
                    "relationship_count": 5,
                },
                "similarity_score": 0.85,
            }
        ]

        # Act
        result = await use_case.execute(request)

        # Assert
        assert len(result.similar_entities) == 1
        assert result.similar_entities[0].explanation is None
        assert result.algorithm_used == "structural"

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_authorization_failure(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_authorization_port: AsyncMock,
    ):
        """Test execution with authorization failure."""
        # Arrange
        mock_authorization_port.check_permission.return_value = False

        # Act & Assert
        with pytest.raises(AuthorizationError) as exc_info:
            await use_case.execute(valid_request)

        assert "lacks read permission" in str(exc_info.value)
        assert exc_info.value.user_id == valid_request.user_id
        assert exc_info.value.resource_id == valid_request.kg_id

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_entity_not_found(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test execution when entity is not found."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.side_effect = Exception("Entity not found")

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(valid_request)

        assert "Entity entity-abc not found" in str(exc_info.value)
        assert exc_info.value.resource_type == "entity"
        assert exc_info.value.resource_id == valid_request.entity_id

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_similarity_search_failure(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test execution when similarity search fails."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.side_effect = Exception("Search service unavailable")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Similar entities search failed" in str(exc_info.value)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_execute_empty_results(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test execution with empty results."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.return_value = []

        # Act
        result = await use_case.execute(valid_request)

        # Assert
        assert len(result.similar_entities) == 0
        assert result.kg_id == valid_request.kg_id
        assert result.source_entity_id == valid_request.entity_id

    def test_validate_request_missing_kg_id(self, use_case: SimilarEntitiesUseCase):
        """Test validation with missing knowledge graph ID."""
        request = SimilarEntitiesRequestDTO(
            kg_id="",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_validate_request_missing_tenant_id(self, use_case: SimilarEntitiesUseCase):
        """Test validation with missing tenant ID."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="",
            user_id="user-789",
            entity_id="entity-abc",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Tenant ID is required" in str(exc_info.value)

    def test_validate_request_missing_user_id(self, use_case: SimilarEntitiesUseCase):
        """Test validation with missing user ID."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="",
            entity_id="entity-abc",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "User ID is required" in str(exc_info.value)

    def test_validate_request_missing_entity_id(self, use_case: SimilarEntitiesUseCase):
        """Test validation with missing entity ID."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Entity ID is required" in str(exc_info.value)

    def test_validate_request_invalid_limit_zero(self, use_case: SimilarEntitiesUseCase):
        """Test validation with zero limit."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            limit=0,
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Limit must be greater than 0" in str(exc_info.value)

    def test_validate_request_invalid_limit_too_high(self, use_case: SimilarEntitiesUseCase):
        """Test validation with limit exceeding maximum."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            limit=1000,  # Exceeds default max of 100
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Limit cannot exceed 100" in str(exc_info.value)

    def test_validate_request_invalid_threshold_too_low(self, use_case: SimilarEntitiesUseCase):
        """Test validation with threshold below minimum."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            threshold=-0.1,
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Threshold must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_request_invalid_threshold_too_high(self, use_case: SimilarEntitiesUseCase):
        """Test validation with threshold above maximum."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            threshold=1.1,
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Threshold must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_request_invalid_algorithm(self, use_case: SimilarEntitiesUseCase):
        """Test validation with invalid similarity algorithm."""
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            similarity_algorithm="invalid_algorithm",
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Invalid similarity algorithm: invalid_algorithm" in str(exc_info.value)
        assert "embedding" in str(exc_info.value)
        assert "structural" in str(exc_info.value)
        assert "property" in str(exc_info.value)

    def test_validate_request_valid_algorithms(self, use_case: SimilarEntitiesUseCase):
        """Test validation with all valid algorithms."""
        valid_algorithms = ["embedding", "structural", "property"]

        for algorithm in valid_algorithms:
            request = SimilarEntitiesRequestDTO(
                kg_id="kg-123",
                tenant_id="tenant-456",
                user_id="user-789",
                entity_id="entity-abc",
                similarity_algorithm=algorithm,
            )

            # Should not raise any exception
            use_case.validate_request(request)

    def test_config_customization(
        self,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test use case with custom configuration."""
        # Arrange
        custom_config = SimilarEntitiesConfig(
            max_limit=50,
            default_limit=5,
            min_threshold=0.1,
            max_threshold=0.9,
            valid_algorithms=frozenset(["embedding", "custom_algorithm"]),
        )

        use_case = SimilarEntitiesUseCase(
            similarity_search_port=mock_similarity_port,
            authorization_port=mock_authorization_port,
            config=custom_config,
        )

        # Test custom max limit
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            limit=60,  # Exceeds custom max of 50
        )

        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(request)

        assert "Limit cannot exceed 50" in str(exc_info.value)

        # Test custom algorithm
        request = SimilarEntitiesRequestDTO(
            kg_id="kg-123",
            tenant_id="tenant-456",
            user_id="user-789",
            entity_id="entity-abc",
            similarity_algorithm="custom_algorithm",
        )

        # Should not raise any exception
        use_case.validate_request(request)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_different_similarity_algorithms(
        self,
        use_case: SimilarEntitiesUseCase,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test execution with different similarity algorithms."""
        algorithms = ["embedding", "structural", "property"]

        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.return_value = [
            {
                "entity": {
                    "id": "entity-def",
                    "type": "Person",
                    "label": "John Doe",
                    "properties": {"age": 30},
                    "relationship_count": 5,
                },
                "similarity_score": 0.85,
            }
        ]

        for algorithm in algorithms:
            request = SimilarEntitiesRequestDTO(
                kg_id="kg-123",
                tenant_id="tenant-456",
                user_id="user-789",
                entity_id="entity-abc",
                similarity_algorithm=algorithm,
            )

            result = await use_case.execute(request)
            assert result.algorithm_used == algorithm

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_processing_time_measurement(
        self,
        use_case: SimilarEntitiesUseCase,
        valid_request: SimilarEntitiesRequestDTO,
        mock_similarity_port: AsyncMock,
        mock_authorization_port: AsyncMock,
    ):
        """Test that processing time is measured correctly."""
        # Arrange
        mock_authorization_port.check_permission.return_value = True
        mock_similarity_port.find_similar_entities.return_value = []

        # Act
        result = await use_case.execute(valid_request)

        # Assert
        # Processing time should be a positive number (we can't easily mock time.time())
        assert result.processing_time_ms >= 0
        assert isinstance(result.processing_time_ms, float)