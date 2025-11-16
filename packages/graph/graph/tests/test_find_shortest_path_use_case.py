"""Tests for FindShortestPathUseCase."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from application.ports import TracingPort

from application.use_cases.analytics.find_shortest_path_use_case import FindShortestPathUseCase
from application.use_cases.dto import (
    FindShortestPathRequestDTO,
    ShortestPathDTO,
    PathNodeDTO,
    PathEdgeDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import AnalyticsError


class TestFindShortestPathUseCase:
    """Test cases for FindShortestPathUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph_analytics_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)

        # Mock tracing context manager properly
        mock_span = Mock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        self.tracing_port.start_span.return_value = mock_span

        self.use_case = FindShortestPathUseCase(
            graph_analytics_port=self.graph_analytics_port,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port
        )

    def test_execute_successful_path_finding(self):
        """Test successful shortest path finding."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=10,
            weight_property="weight"
        )

        mock_path_data = {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "Person",
                    "properties": {"name": "Alice"}
                },
                {
                    "id": "node-2",
                    "type": "Organization",
                    "properties": {"name": "Company"}
                },
                {
                    "id": "node-3",
                    "type": "Person",
                    "properties": {"name": "Bob"}
                }
            ],
            "edges": [
                {
                    "source": "node-1",
                    "target": "node-2",
                    "type": "WORKS_FOR",
                    "properties": {"since": "2020"},
                    "weight": 1.0
                },
                {
                    "source": "node-2",
                    "target": "node-3",
                    "type": "EMPLOYS",
                    "properties": {"role": "manager"},
                    "weight": 1.5
                }
            ],
            "total_weight": 2.5
        }

        self.graph_analytics_port.find_shortest_path.return_value = mock_path_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, ShortestPathDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert result.source_node_id == "node-1"
        assert result.target_node_id == "node-3"
        assert result.path_length == 2
        assert result.total_weight == 2.5
        assert len(result.nodes) == 3
        assert len(result.edges) == 2
        assert result.processing_time_ms > 0
        assert isinstance(result.analysis_timestamp, datetime)

        # Verify node details
        assert result.nodes[0].node_id == "node-1"
        assert result.nodes[0].node_type == "Person"
        assert result.nodes[0].properties["name"] == "Alice"

        # Verify edge details
        assert result.edges[0].source_node_id == "node-1"
        assert result.edges[0].target_node_id == "node-2"
        assert result.edges[0].relationship_type == "WORKS_FOR"
        assert result.edges[0].weight == 1.0

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify analytics port was called
        self.graph_analytics_port.find_shortest_path.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=10,
            weight_property="weight"
        )

        # Verify metrics were recorded
        assert self.tracing_port.record_metric.call_count == 3

    def test_execute_no_path_found(self):
        """Test execution when no path exists between nodes."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        self.graph_analytics_port.find_shortest_path.return_value = None

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result is None

        # Verify metrics were recorded for no path found
        assert self.tracing_port.record_metric.call_count == 2

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            source_node_id="node-1",
            target_node_id="node-3"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_missing_source_node(self):
        """Test execution with missing source node ID."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="",  # Empty source_node_id
            target_node_id="node-3"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Source node ID is required" in str(exc_info.value)

    def test_execute_with_missing_target_node(self):
        """Test execution with missing target node ID."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id=""  # Empty target_node_id
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Target node ID is required" in str(exc_info.value)

    def test_execute_with_same_source_and_target(self):
        """Test execution with same source and target nodes."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-1"  # Same as source
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Source and target nodes cannot be the same" in str(exc_info.value)

    def test_execute_with_invalid_max_depth_too_small(self):
        """Test execution with max depth too small."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=0  # Invalid depth
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Maximum depth must be at least 1" in str(exc_info.value)

    def test_execute_with_invalid_max_depth_too_large(self):
        """Test execution with max depth too large."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=100  # Too large
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Maximum depth cannot exceed 50" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="User does not have permission to read knowledge graph",
            user_id="user-456",
            resource_type="knowledge_graph",
            resource_id="kg-789",
            required_permission="read"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_analytics_failure(self):
        """Test execution when analytics port fails."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        self.graph_analytics_port.find_shortest_path.side_effect = Exception(
            "Path finding failed"
        )

        # Act & Assert
        with pytest.raises(AnalyticsError) as exc_info:
            self.use_case.execute(request)

        assert "Shortest path finding failed" in str(exc_info.value)

    def test_extract_path_nodes(self):
        """Test extraction of path nodes from raw data."""
        # Arrange
        nodes_data = [
            {
                "id": "node-1",
                "type": "Person",
                "properties": {"name": "Alice", "age": 30}
            },
            {
                "id": "node-2",
                "type": "Organization",
                "properties": {"name": "Company"}
            }
        ]

        # Act
        result = self.use_case._extract_path_nodes(nodes_data)

        # Assert
        assert len(result) == 2

        node1 = result[0]
        assert isinstance(node1, PathNodeDTO)
        assert node1.node_id == "node-1"
        assert node1.node_type == "Person"
        assert node1.properties["name"] == "Alice"
        assert node1.properties["age"] == 30

        node2 = result[1]
        assert node2.node_id == "node-2"
        assert node2.node_type == "Organization"
        assert node2.properties["name"] == "Company"

    def test_extract_path_edges(self):
        """Test extraction of path edges from raw data."""
        # Arrange
        edges_data = [
            {
                "source": "node-1",
                "target": "node-2",
                "type": "WORKS_FOR",
                "properties": {"since": "2020"},
                "weight": 1.0
            },
            {
                "source": "node-2",
                "target": "node-3",
                "type": "EMPLOYS",
                "properties": {"role": "manager"}
                # No weight property
            }
        ]

        # Act
        result = self.use_case._extract_path_edges(edges_data)

        # Assert
        assert len(result) == 2

        edge1 = result[0]
        assert isinstance(edge1, PathEdgeDTO)
        assert edge1.source_node_id == "node-1"
        assert edge1.target_node_id == "node-2"
        assert edge1.relationship_type == "WORKS_FOR"
        assert edge1.properties["since"] == "2020"
        assert edge1.weight == 1.0

        edge2 = result[1]
        assert edge2.source_node_id == "node-2"
        assert edge2.target_node_id == "node-3"
        assert edge2.relationship_type == "EMPLOYS"
        assert edge2.properties["role"] == "manager"
        assert edge2.weight is None

    def test_extract_path_nodes_empty(self):
        """Test extraction of path nodes with empty data."""
        # Act
        result = self.use_case._extract_path_nodes([])

        # Assert
        assert result == []

    def test_extract_path_edges_empty(self):
        """Test extraction of path edges with empty data."""
        # Act
        result = self.use_case._extract_path_edges([])

        # Assert
        assert result == []

    def test_extract_path_nodes_missing_fields(self):
        """Test extraction of path nodes with missing fields."""
        # Arrange
        nodes_data = [
            {
                "id": "node-1"
                # Missing type and properties
            },
            {
                "type": "Person"
                # Missing id and properties
            }
        ]

        # Act
        result = self.use_case._extract_path_nodes(nodes_data)

        # Assert
        assert len(result) == 2

        node1 = result[0]
        assert node1.node_id == "node-1"
        assert node1.node_type == "unknown"
        assert node1.properties == {}

        node2 = result[1]
        assert node2.node_id == ""
        assert node2.node_type == "Person"
        assert node2.properties == {}

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        self.graph_analytics_port.find_shortest_path.return_value = None

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="find_shortest_path",
            tenant_id="tenant-123",
            kg_id="kg-789",
            source_node="node-1",
            target_node="node-3"
        )

    def test_convert_path_to_dto_single_node(self):
        """Test conversion of path data with single node (no edges)."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-1"  # Same node (hypothetically)
        )

        path_data = {
            "nodes": [{"id": "node-1", "type": "Person", "properties": {}}],
            "edges": [],
            "total_weight": 0.0
        }

        # Act
        result = self.use_case._convert_path_to_dto(path_data, request, 100.0)

        # Assert
        assert result.path_length == 0  # Single node = 0 edges
        assert len(result.nodes) == 1
        assert len(result.edges) == 0
        assert result.total_weight == 0.0

    def test_execute_with_weighted_path(self):
        """Test execution with weighted edges."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3",
            weight_property="distance"
        )

        mock_path_data = {
            "nodes": [
                {"id": "node-1", "type": "City", "properties": {"name": "New York"}},
                {"id": "node-2", "type": "City", "properties": {"name": "Chicago"}},
                {"id": "node-3", "type": "City", "properties": {"name": "Los Angeles"}}
            ],
            "edges": [
                {
                    "source": "node-1",
                    "target": "node-2",
                    "type": "CONNECTED_TO",
                    "properties": {"distance": 790},
                    "weight": 790.0
                },
                {
                    "source": "node-2",
                    "target": "node-3",
                    "type": "CONNECTED_TO",
                    "properties": {"distance": 2015},
                    "weight": 2015.0
                }
            ],
            "total_weight": 2805.0
        }

        self.graph_analytics_port.find_shortest_path.return_value = mock_path_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result is not None
        assert result.total_weight == 2805.0
        assert result.path_length == 2
        assert len(result.edges) == 2
        assert result.edges[0].weight == 790.0
        assert result.edges[1].weight == 2015.0

        # Verify weight property was passed to analytics port
        self.graph_analytics_port.find_shortest_path.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=10,
            weight_property="distance"
        )

    def test_execute_with_complex_path(self):
        """Test execution with a longer, more complex path."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="person-1",
            target_node_id="person-5",
            max_depth=20
        )

        mock_path_data = {
            "nodes": [
                {"id": "person-1", "type": "Person", "properties": {"name": "Alice"}},
                {"id": "org-1", "type": "Organization", "properties": {"name": "Company A"}},
                {"id": "person-2", "type": "Person", "properties": {"name": "Bob"}},
                {"id": "org-2", "type": "Organization", "properties": {"name": "Company B"}},
                {"id": "person-5", "type": "Person", "properties": {"name": "Eve"}}
            ],
            "edges": [
                {
                    "source": "person-1",
                    "target": "org-1",
                    "type": "WORKS_FOR",
                    "properties": {"role": "engineer"},
                    "weight": 1.0
                },
                {
                    "source": "org-1",
                    "target": "person-2",
                    "type": "EMPLOYS",
                    "properties": {"role": "manager"},
                    "weight": 1.0
                },
                {
                    "source": "person-2",
                    "target": "org-2",
                    "type": "WORKS_FOR",
                    "properties": {"role": "consultant"},
                    "weight": 1.0
                },
                {
                    "source": "org-2",
                    "target": "person-5",
                    "type": "EMPLOYS",
                    "properties": {"role": "director"},
                    "weight": 1.0
                }
            ],
            "total_weight": 4.0
        }

        self.graph_analytics_port.find_shortest_path.return_value = mock_path_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result is not None
        assert result.path_length == 4
        assert result.total_weight == 4.0
        assert len(result.nodes) == 5
        assert len(result.edges) == 4

        # Verify node sequence
        assert result.nodes[0].node_id == "person-1"
        assert result.nodes[1].node_id == "org-1"
        assert result.nodes[2].node_id == "person-2"
        assert result.nodes[3].node_id == "org-2"
        assert result.nodes[4].node_id == "person-5"

        # Verify edge sequence
        assert result.edges[0].source_node_id == "person-1"
        assert result.edges[0].target_node_id == "org-1"
        assert result.edges[3].source_node_id == "org-2"
        assert result.edges[3].target_node_id == "person-5"

    def test_execute_with_custom_max_depth(self):
        """Test execution with custom maximum depth setting."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=5
        )

        self.graph_analytics_port.find_shortest_path.return_value = None

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result is None

        # Verify max_depth was passed correctly
        self.graph_analytics_port.find_shortest_path.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            source_node_id="node-1",
            target_node_id="node-3",
            max_depth=5,
            weight_property=None
        )

    def test_execute_with_missing_tenant_id(self):
        """Test execution with missing tenant ID."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="",  # Empty tenant_id
            user_id="user-456",
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Tenant ID is required" in str(exc_info.value)

    def test_execute_with_missing_user_id(self):
        """Test execution with missing user ID."""
        # Arrange
        request = FindShortestPathRequestDTO(
            tenant_id="tenant-123",
            user_id="",  # Empty user_id
            kg_id="kg-789",
            source_node_id="node-1",
            target_node_id="node-3"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "User ID is required" in str(exc_info.value)