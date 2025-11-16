"""Tests for DetectCommunitiesUseCase."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from application.ports import TracingPort

from application.use_cases.analytics.detect_communities_use_case import DetectCommunitiesUseCase
from application.use_cases.dto import (
    DetectCommunitiesRequestDTO,
    CommunitiesAnalysisDTO,
    CommunityDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import ClusteringError
from domain.entities import Community


class TestDetectCommunitiesUseCase:
    """Test cases for DetectCommunitiesUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.clustering_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)

        # Mock tracing context manager
        self.tracing_port.start_span.return_value.__enter__ = Mock(return_value=None)
        self.tracing_port.start_span.return_value.__exit__ = Mock(return_value=False)

        self.use_case = DetectCommunitiesUseCase(
            clustering_port=self.clustering_port,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port
        )

    def test_execute_successful_community_detection(self):
        """Test successful community detection."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain",
            min_community_size=3,
            resolution=1.0
        )

        mock_communities = [
            Community(
                id="comm-1",
                centroid_embedding=[0.1, 0.2, 0.3],
                node_ids=["node-1", "node-2", "node-3", "node-4"],
                size=4,
                tenant_id="tenant-123"
            ),
            Community(
                id="comm-2",
                centroid_embedding=[0.4, 0.5, 0.6],
                node_ids=["node-5", "node-6", "node-7"],
                size=3,
                tenant_id="tenant-123"
            ),
            Community(
                id="comm-3",
                centroid_embedding=[0.7, 0.8, 0.9],
                node_ids=["node-8", "node-9"],
                size=2,
                tenant_id="tenant-123"
            )
        ]

        self.clustering_port.compute_communities.return_value = mock_communities

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, CommunitiesAnalysisDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert result.algorithm == "louvain"
        assert result.total_communities == 2  # Only communities with size >= 3
        assert len(result.communities) == 2
        assert result.modularity > 0
        assert result.coverage > 0
        assert result.processing_time_ms > 0
        assert isinstance(result.analysis_timestamp, datetime)

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify clustering port was called
        self.clustering_port.compute_communities.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            algorithm="louvain"
        )

        # Verify metrics were recorded
        assert self.tracing_port.record_metric.call_count == 2

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            algorithm="louvain"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_unsupported_algorithm(self):
        """Test execution with unsupported algorithm."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="unsupported_algorithm"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Unsupported algorithm" in str(exc_info.value)

    def test_execute_with_invalid_min_community_size(self):
        """Test execution with invalid minimum community size."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain",
            min_community_size=0  # Invalid size
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Minimum community size must be at least 1" in str(exc_info.value)

    def test_execute_with_invalid_resolution(self):
        """Test execution with invalid resolution parameter."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain",
            resolution=0.0  # Invalid resolution
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Resolution parameter must be positive" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User does not have permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_clustering_failure(self):
        """Test execution when clustering port fails."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain"
        )

        self.clustering_port.compute_communities.side_effect = Exception(
            "Clustering failed"
        )

        # Act & Assert
        with pytest.raises(ClusteringError) as exc_info:
            self.use_case.execute(request)

        assert "Community detection failed" in str(exc_info.value)

    def test_execute_with_empty_communities(self):
        """Test execution with no communities detected."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain"
        )

        self.clustering_port.compute_communities.return_value = []

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, CommunitiesAnalysisDTO)
        assert result.total_communities == 0
        assert len(result.communities) == 0
        assert result.modularity == 0.0
        assert result.coverage == 0.0

    def test_execute_with_small_communities_filtered(self):
        """Test execution where small communities are filtered out."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain",
            min_community_size=5  # High threshold
        )

        mock_communities = [
            Community(
                id="comm-1",
                centroid_embedding=[0.1, 0.2, 0.3],
                node_ids=["node-1", "node-2", "node-3"],
                size=3,
                tenant_id="tenant-123"
            ),
            Community(
                id="comm-2",
                centroid_embedding=[0.4, 0.5, 0.6],
                node_ids=["node-4", "node-5"],
                size=2,
                tenant_id="tenant-123"
            )
        ]

        self.clustering_port.compute_communities.return_value = mock_communities

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.total_communities == 0  # All communities filtered out
        assert len(result.communities) == 0

    def test_convert_communities_to_dtos(self):
        """Test conversion of Community entities to DTOs."""
        # Arrange
        communities = [
            Community(
                id="comm-1",
                centroid_embedding=[0.1, 0.2, 0.3],
                node_ids=["node-1", "node-2", "node-3"],
                size=3,
                tenant_id="tenant-123"
            )
        ]

        # Act
        result = self.use_case._convert_communities_to_dtos(communities, "louvain")

        # Assert
        assert len(result) == 1
        community_dto = result[0]
        assert isinstance(community_dto, CommunityDTO)
        assert community_dto.id == "comm-1"
        assert community_dto.size == 3
        assert community_dto.node_ids == ["node-1", "node-2", "node-3"]
        assert community_dto.centroid_node_id == "node-1"  # First node as heuristic
        assert community_dto.modularity_score >= 0
        assert community_dto.internal_edges > 0
        assert community_dto.external_edges >= 0

    def test_find_centroid_node(self):
        """Test finding centroid node in community."""
        # Arrange
        community = Community(
            id="comm-1",
            centroid_embedding=[0.8, 0.1, 0.9],
            node_ids=["node-1", "node-2", "node-3"],
            size=3,
            tenant_id="tenant-123"
        )

        # Act
        result = self.use_case._find_centroid_node(community)

        # Assert
        assert result == "node-3"

    def test_find_centroid_node_different_centroid(self):
        """Ensure centroid node changes with centroid embedding."""
        community = Community(
            id="comm-2",
            centroid_embedding=[0.1, 0.2, 0.3],
            node_ids=["node-1", "node-2", "node-3"],
            size=3,
            tenant_id="tenant-123",
        )

        result = self.use_case._find_centroid_node(community)

        assert result == "node-1"

    def test_find_centroid_node_empty_community(self):
        """Test finding centroid node in empty community."""
        # Arrange
        community = Community(
            id="comm-1",
            centroid_embedding=[0.1, 0.2, 0.3],
            node_ids=[],
            size=0,
            tenant_id="tenant-123"
        )

        # Act
        result = self.use_case._find_centroid_node(community)

        # Assert
        assert result == ""

    def test_calculate_community_modularity(self):
        """Test calculation of community modularity."""
        # Arrange
        community = Community(
            id="comm-1",
            centroid_embedding=[0.1, 0.2, 0.3],
            node_ids=["node-1", "node-2", "node-3"],
            size=3,
            tenant_id="tenant-123"
        )

        # Act
        result = self.use_case._calculate_community_modularity(community)

        # Assert
        assert 0.0 <= result <= 0.8
        assert isinstance(result, float)

    def test_calculate_overall_metrics(self):
        """Test calculation of overall modularity and coverage metrics."""
        # Arrange
        community_dtos = [
            CommunityDTO(
                id="comm-1",
                size=4,
                node_ids=["node-1", "node-2", "node-3", "node-4"],
                centroid_node_id="node-1",
                modularity_score=0.5,
                internal_edges=6,
                external_edges=2
            ),
            CommunityDTO(
                id="comm-2",
                size=3,
                node_ids=["node-5", "node-6", "node-7"],
                centroid_node_id="node-5",
                modularity_score=0.3,
                internal_edges=3,
                external_edges=1
            )
        ]

        all_communities = [
            Community(
                id="comm-1",
                centroid_embedding=[0.1, 0.2, 0.3],
                node_ids=["node-1", "node-2", "node-3", "node-4"],
                size=4,
                tenant_id="tenant-123"
            ),
            Community(
                id="comm-2",
                centroid_embedding=[0.4, 0.5, 0.6],
                node_ids=["node-5", "node-6", "node-7"],
                size=3,
                tenant_id="tenant-123"
            ),
            Community(
                id="comm-3",
                centroid_embedding=[0.7, 0.8, 0.9],
                node_ids=["node-8"],
                size=1,
                tenant_id="tenant-123"
            )
        ]

        # Act
        modularity, coverage = self.use_case._calculate_overall_metrics(
            community_dtos, all_communities
        )

        # Assert
        assert 0.0 <= modularity <= 1.0
        assert 0.0 <= coverage <= 1.0
        assert coverage == 7/8  # 7 nodes in filtered communities out of 8 total

    def test_calculate_overall_metrics_empty(self):
        """Test calculation of overall metrics with empty communities."""
        # Act
        modularity, coverage = self.use_case._calculate_overall_metrics([], [])

        # Assert
        assert modularity == 0.0
        assert coverage == 0.0

    def test_supported_algorithms_validation(self):
        """Test that all supported algorithms are accepted."""
        supported_algorithms = ["louvain", "leiden", "label_propagation", "infomap"]

        for algorithm in supported_algorithms:
            request = DetectCommunitiesRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                kg_id="kg-789",
                algorithm=algorithm
            )

            # Should not raise ValidationError
            self.use_case._validate_request(request)

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = DetectCommunitiesRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            algorithm="louvain"
        )

        self.clustering_port.compute_communities.return_value = []

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="detect_communities",
            tenant_id="tenant-123",
            kg_id="kg-789",
            algorithm="louvain"
        )