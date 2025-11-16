"""Tests for GetNodeCentralityUseCase."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from application.ports import TracingPort

from application.use_cases.analytics.get_node_centrality_use_case import GetNodeCentralityUseCase
from application.use_cases.dto import (
    GetNodeCentralityRequestDTO,
    CentralityAnalysisDTO,
    NodeCentralityDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import AnalyticsError


class TestGetNodeCentralityUseCase:
    """Test cases for GetNodeCentralityUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph_analytics_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)

        # Mock tracing context manager
        self.tracing_port.start_span.return_value.__enter__ = Mock()
        self.tracing_port.start_span.return_value.__exit__ = Mock()

        self.use_case = GetNodeCentralityUseCase(
            graph_analytics_port=self.graph_analytics_port,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port
        )

    def test_execute_successful_centrality_calculation(self):
        """Test successful node centrality calculation."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            node_ids=["node-1", "node-2", "node-3"],
            centrality_types=["degree", "betweenness", "pagerank"],
            limit=100
        )

        mock_centrality_data = {
            "node-1": {
                "node_type": "Person",
                "degree": 0.8,
                "betweenness": 0.6,
                "pagerank": 0.15
            },
            "node-2": {
                "node_type": "Organization",
                "degree": 0.5,
                "betweenness": 0.3,
                "pagerank": 0.10
            },
            "node-3": {
                "node_type": "Person",
                "degree": 0.9,
                "betweenness": 0.7,
                "pagerank": 0.20
            }
        }

        self.graph_analytics_port.calculate_centrality.return_value = mock_centrality_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, CentralityAnalysisDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert result.centrality_types == ["degree", "betweenness", "pagerank"]
        assert result.total_nodes_analyzed == 3
        assert len(result.node_centralities) == 3
        assert result.processing_time_ms > 0
        assert isinstance(result.analysis_timestamp, datetime)

        # Verify nodes are sorted by degree centrality (first centrality type)
        assert result.node_centralities[0].node_id == "node-3"  # Highest degree (0.9)
        assert result.node_centralities[1].node_id == "node-1"  # Second highest (0.8)
        assert result.node_centralities[2].node_id == "node-2"  # Lowest (0.5)

        # Verify centrality values
        node1_centrality = next(n for n in result.node_centralities if n.node_id == "node-1")
        assert node1_centrality.degree_centrality == 0.8
        assert node1_centrality.betweenness_centrality == 0.6
        assert node1_centrality.pagerank == 0.15
        assert node1_centrality.closeness_centrality is None  # Not calculated
        assert node1_centrality.eigenvector_centrality is None  # Not calculated

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify analytics port was called
        self.graph_analytics_port.calculate_centrality.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            centrality_types=["degree", "betweenness", "pagerank"],
            node_ids=["node-1", "node-2", "node-3"]
        )

        # Verify metrics were recorded
        assert self.tracing_port.record_metric.call_count == 2

    def test_execute_with_default_centrality_types(self):
        """Test execution with default centrality types when none provided."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=None  # Will use defaults
        )

        mock_centrality_data = {
            "node-1": {
                "node_type": "Person",
                "degree": 0.8,
                "betweenness": 0.6,
                "closeness": 0.4
            }
        }

        self.graph_analytics_port.calculate_centrality.return_value = mock_centrality_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.centrality_types == ["degree", "betweenness", "closeness"]

        # Verify analytics port was called with defaults
        self.graph_analytics_port.calculate_centrality.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            centrality_types=["degree", "betweenness", "closeness"],
            node_ids=None
        )

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            centrality_types=["degree"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_unsupported_centrality_type(self):
        """Test execution with unsupported centrality type."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree", "unsupported_centrality"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Unsupported centrality type" in str(exc_info.value)

    def test_execute_with_invalid_limit_too_small(self):
        """Test execution with limit too small."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"],
            limit=0  # Invalid limit
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Limit must be at least 1" in str(exc_info.value)

    def test_execute_with_invalid_limit_too_large(self):
        """Test execution with limit too large."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"],
            limit=20000  # Too large
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Limit cannot exceed 10000" in str(exc_info.value)

    def test_execute_with_empty_node_ids_list(self):
        """Test execution with empty node IDs list."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            node_ids=[],  # Empty list
            centrality_types=["degree"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Node IDs list cannot be empty when provided" in str(exc_info.value)

    def test_execute_with_too_many_node_ids(self):
        """Test execution with too many node IDs."""
        # Arrange
        node_ids = [f"node-{i}" for i in range(1001)]  # Too many nodes
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            node_ids=node_ids,
            centrality_types=["degree"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Cannot specify more than 1000 node IDs" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"]
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User does not have permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_analytics_failure(self):
        """Test execution when analytics port fails."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"]
        )

        self.graph_analytics_port.calculate_centrality.side_effect = Exception(
            "Centrality calculation failed"
        )

        # Act & Assert
        with pytest.raises(AnalyticsError) as exc_info:
            self.use_case.execute(request)

        assert "Node centrality calculation failed" in str(exc_info.value)

    def test_execute_with_limit_applied(self):
        """Test execution with limit applied to results."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"],
            limit=2  # Limit to 2 results
        )

        mock_centrality_data = {
            "node-1": {"node_type": "Person", "degree": 0.8},
            "node-2": {"node_type": "Person", "degree": 0.5},
            "node-3": {"node_type": "Person", "degree": 0.9}
        }

        self.graph_analytics_port.calculate_centrality.return_value = mock_centrality_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert len(result.node_centralities) == 2  # Limited to 2
        assert result.total_nodes_analyzed == 2
        # Should return top 2 by degree centrality
        assert result.node_centralities[0].node_id == "node-3"  # 0.9
        assert result.node_centralities[1].node_id == "node-1"  # 0.8

    def test_convert_centrality_to_dtos(self):
        """Test conversion of centrality data to DTOs."""
        # Arrange
        centrality_data = {
            "node-1": {
                "node_type": "Person",
                "degree": 0.8,
                "betweenness": 0.6,
                "pagerank": 0.15
            },
            "node-2": {
                "node_type": "Organization",
                "degree": 0.5,
                "betweenness": 0.3
                # Missing pagerank
            }
        }

        centrality_types = ["degree", "betweenness", "pagerank"]

        # Act
        result = self.use_case._convert_centrality_to_dtos(
            centrality_data, centrality_types, 100
        )

        # Assert
        assert len(result) == 2

        # Check sorting by degree (first centrality type)
        assert result[0].node_id == "node-1"  # Higher degree
        assert result[1].node_id == "node-2"  # Lower degree

        # Check node-1 values
        node1 = result[0]
        assert node1.node_type == "Person"
        assert node1.degree_centrality == 0.8
        assert node1.betweenness_centrality == 0.6
        assert node1.pagerank == 0.15
        assert node1.closeness_centrality is None
        assert node1.eigenvector_centrality is None

        # Check node-2 values
        node2 = result[1]
        assert node2.node_type == "Organization"
        assert node2.degree_centrality == 0.5
        assert node2.betweenness_centrality == 0.3
        assert node2.pagerank is None  # Missing in data

    def test_get_centrality_value(self):
        """Test getting centrality value for sorting."""
        # Arrange
        node_centrality = NodeCentralityDTO(
            node_id="node-1",
            node_type="Person",
            degree_centrality=0.8,
            betweenness_centrality=0.6,
            closeness_centrality=None,
            eigenvector_centrality=0.4,
            pagerank=0.15
        )

        # Act & Assert
        assert self.use_case._get_centrality_value(node_centrality, "degree") == 0.8
        assert self.use_case._get_centrality_value(node_centrality, "betweenness") == 0.6
        assert self.use_case._get_centrality_value(node_centrality, "closeness") == 0.0  # None -> 0.0
        assert self.use_case._get_centrality_value(node_centrality, "eigenvector") == 0.4
        assert self.use_case._get_centrality_value(node_centrality, "pagerank") == 0.15
        assert self.use_case._get_centrality_value(node_centrality, "unknown") == 0.0

    def test_execute_with_empty_centrality_data(self):
        """Test execution with empty centrality data."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree"]
        )

        self.graph_analytics_port.calculate_centrality.return_value = {}

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, CentralityAnalysisDTO)
        assert result.total_nodes_analyzed == 0
        assert len(result.node_centralities) == 0

    def test_supported_centrality_types_validation(self):
        """Test that all supported centrality types are accepted."""
        supported_types = ["betweenness", "closeness", "degree", "eigenvector", "pagerank"]

        for centrality_type in supported_types:
            request = GetNodeCentralityRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                kg_id="kg-789",
                centrality_types=[centrality_type]
            )

            # Should not raise ValidationError
            self.use_case._validate_request(request)

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = GetNodeCentralityRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            centrality_types=["degree", "betweenness"]
        )

        self.graph_analytics_port.calculate_centrality.return_value = {}

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="get_node_centrality",
            tenant_id="tenant-123",
            kg_id="kg-789",
            centrality_types="degree,betweenness"
        )

    def test_convert_centrality_missing_node_type(self):
        """Test conversion when node_type is missing from centrality data."""
        # Arrange
        centrality_data = {
            "node-1": {
                # Missing node_type
                "degree": 0.8
            }
        }

        # Act
        result = self.use_case._convert_centrality_to_dtos(
            centrality_data, ["degree"], 100
        )

        # Assert
        assert len(result) == 1
        assert result[0].node_type == "unknown"  # Default value