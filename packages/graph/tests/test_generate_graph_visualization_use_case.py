"""Tests for GenerateGraphVisualizationUseCase."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from application.ports import TracingPort

from application.use_cases.visualization.generate_graph_visualization_use_case import GenerateGraphVisualizationUseCase
from application.use_cases.dto import (
    GenerateGraphVisualizationRequestDTO,
    GraphVisualizationDTO,
    VisualizationNodeDTO,
    VisualizationEdgeDTO
)
from application.exceptions import ValidationError, NotFoundError, AuthorizationError
from domain.exceptions import VisualizationError


class TestGenerateGraphVisualizationUseCase:
    """Test cases for GenerateGraphVisualizationUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph_visualization_port = Mock()
        self.authorization_service = Mock()
        self.tracing_port = Mock(spec=TracingPort)
        self.layout_repository = Mock()

        # Mock tracing context manager
        self.tracing_port.start_span.return_value.__enter__ = Mock()
        self.tracing_port.start_span.return_value.__exit__ = Mock()

        self.use_case = GenerateGraphVisualizationUseCase(
            graph_visualization_port=self.graph_visualization_port,
            layout_repository=self.layout_repository,
            authorization_service=self.authorization_service,
            tracing_port=self.tracing_port,
        )

    def test_execute_successful_visualization_generation(self):
        """Test successful graph visualization generation."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed",
            node_limit=1000,
            include_labels=True,
            include_communities=True,
            filter_by_node_types=["Person", "Organization"],
            filter_by_relationship_types=["WORKS_FOR", "KNOWS"]
        )

        mock_layout_data = {
            "nodes": [
                {
                    "id": "node-1",
                    "type": "Person",
                    "x": 10.0,
                    "y": 20.0,
                    "size": 15.0,
                    "color": "#e74c3c",
                    "properties": {"name": "Alice", "age": 30},
                    "community_id": "comm-1"
                },
                {
                    "id": "node-2",
                    "type": "Organization",
                    "x": 50.0,
                    "y": 60.0,
                    "size": 20.0,
                    "color": "#2ecc71",
                    "properties": {"name": "Company Inc."}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "node-1",
                    "target": "node-2",
                    "type": "WORKS_FOR",
                    "weight": 1.0,
                    "color": "#34495e",
                    "properties": {"since": "2020"}
                }
            ]
        }

        self.graph_visualization_port.generate_layout.return_value = mock_layout_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert isinstance(result, GraphVisualizationDTO)
        assert result.kg_id == "kg-789"
        assert result.tenant_id == "tenant-123"
        assert result.layout_algorithm == "force_directed"
        assert result.total_nodes == 2
        assert result.total_edges == 1
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.processing_time_ms > 0
        assert isinstance(result.analysis_timestamp, datetime)

        # Verify node details
        node1 = result.nodes[0]
        assert node1.id == "node-1"
        assert node1.node_type == "Person"
        assert node1.x == 10.0
        assert node1.y == 20.0
        assert node1.size == 15.0
        assert node1.color == "#e74c3c"
        assert node1.label == "Alice"  # From name property
        assert node1.community_id == "comm-1"
        assert node1.properties["age"] == 30

        # Verify edge details
        edge1 = result.edges[0]
        assert edge1.id == "edge-1"
        assert edge1.source_id == "node-1"
        assert edge1.target_id == "node-2"
        assert edge1.relationship_type == "WORKS_FOR"
        assert edge1.weight == 1.0
        assert edge1.color == "#34495e"
        assert "Works For" in edge1.label

        # Verify viewport bounds
        assert "min_x" in result.viewport_bounds
        assert "max_x" in result.viewport_bounds
        assert "min_y" in result.viewport_bounds
        assert "max_y" in result.viewport_bounds

        # Verify authorization was checked
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user-456",
            resource_id="kg-789",
            action="read"
        )

        # Verify visualization port was called with filters
        expected_filters = {
            "node_types": ["Person", "Organization"],
            "relationship_types": ["WORKS_FOR", "KNOWS"]
        }

        self.graph_visualization_port.generate_layout.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            algorithm="force_directed",
            node_limit=1000,
            include_communities=True,
            filters=expected_filters
        )

        # Verify metrics were recorded
        assert self.tracing_port.record_metric.call_count == 3

    def test_execute_with_missing_kg_id(self):
        """Test execution with missing knowledge graph ID."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="",  # Empty kg_id
            layout_algorithm="force_directed"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Knowledge graph ID is required" in str(exc_info.value)

    def test_execute_with_unsupported_algorithm(self):
        """Test execution with unsupported layout algorithm."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="unsupported_algorithm"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Unsupported layout algorithm" in str(exc_info.value)

    def test_execute_with_invalid_node_limit_too_small(self):
        """Test execution with node limit too small."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed",
            node_limit=0  # Invalid limit
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Node limit must be at least 1" in str(exc_info.value)

    def test_execute_with_invalid_node_limit_too_large(self):
        """Test execution with node limit too large."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed",
            node_limit=20000  # Too large
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Node limit cannot exceed 10000" in str(exc_info.value)

    def test_execute_with_authorization_failure(self):
        """Test execution when authorization fails."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User does not have permission to read knowledge graph"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_execute_with_visualization_failure(self):
        """Test execution when visualization port fails."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed"
        )

        self.graph_visualization_port.generate_layout.side_effect = Exception(
            "Visualization generation failed"
        )

        # Act & Assert
        with pytest.raises(VisualizationError) as exc_info:
            self.use_case.execute(request)

        assert "Graph visualization generation failed" in str(exc_info.value)

    def test_execute_without_filters(self):
        """Test execution without node or relationship type filters."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="circular",
            filter_by_node_types=None,
            filter_by_relationship_types=None
        )

        mock_layout_data = {"nodes": [], "edges": []}
        self.graph_visualization_port.generate_layout.return_value = mock_layout_data

        # Act
        result = self.use_case.execute(request)

        # Assert
        # Verify visualization port was called with empty filters
        self.graph_visualization_port.generate_layout.assert_called_once_with(
            kg_id="kg-789",
            tenant_id="tenant-123",
            algorithm="circular",
            node_limit=1000,  # Default
            include_communities=False,  # Default
            filters={}
        )

    def test_execute_uses_existing_layout(self):
        """Return cached layout when available."""
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-001",
            layout_algorithm="force_directed",
        )

        mock_layout = {"nodes": [1], "edges": []}
        self.layout_repository.get_layout.return_value = mock_layout

        result = self.use_case.execute(request)

        assert result.total_nodes == 1
        self.layout_repository.get_layout.assert_called_once_with(
            visualization_id="viz-001", tenant_id="tenant-123"
        )
        self.graph_visualization_port.generate_layout.assert_not_called()

    def test_execute_generates_layout_when_missing(self):
        """Generate new layout when repository has none."""
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            visualization_id="viz-999",
            layout_algorithm="force_directed",
        )

        self.layout_repository.get_layout.return_value = None
        mock_layout = {"nodes": [], "edges": []}
        self.graph_visualization_port.generate_layout.return_value = mock_layout

        result = self.use_case.execute(request)

        assert result.total_nodes == 0
        self.layout_repository.get_layout.assert_called_once_with(
            visualization_id="viz-999", tenant_id="tenant-123"
        )
        self.graph_visualization_port.generate_layout.assert_called_once()

    def test_generate_node_label_with_name_property(self):
        """Test node label generation with name property."""
        # Act
        result = self.use_case._generate_node_label(
            node_id="node-123",
            node_type="Person",
            properties={"name": "Alice Smith", "age": 30}
        )

        # Assert
        assert result == "Alice Smith"

    def test_generate_node_label_with_title_property(self):
        """Test node label generation with title property."""
        # Act
        result = self.use_case._generate_node_label(
            node_id="node-123",
            node_type="Document",
            properties={"title": "Research Paper", "year": 2023}
        )

        # Assert
        assert result == "Research Paper"

    def test_generate_node_label_fallback(self):
        """Test node label generation fallback to type and ID."""
        # Act
        result = self.use_case._generate_node_label(
            node_id="very-long-node-identifier-123456789",
            node_type="Entity",
            properties={"description": "Some entity"}
        )

        # Assert
        assert result == "Entity:23456789"  # Last 8 characters of ID

    def test_generate_node_label_short_id(self):
        """Test node label generation with short ID."""
        # Act
        result = self.use_case._generate_node_label(
            node_id="node-1",
            node_type="Person",
            properties={}
        )

        # Assert
        assert result == "Person:node-1"  # Full ID when short

    def test_generate_edge_label_basic(self):
        """Test edge label generation with basic relationship type."""
        # Act
        result = self.use_case._generate_edge_label(
            relationship_type="WORKS_FOR",
            properties={"since": "2020"}
        )

        # Assert
        assert result == "Works For"

    def test_generate_edge_label_with_weight(self):
        """Test edge label generation with weight property."""
        # Act
        result = self.use_case._generate_edge_label(
            relationship_type="SIMILAR_TO",
            properties={"weight": 0.85, "confidence": "high"}
        )

        # Assert
        assert result == "Similar To (0.85)"

    def test_calculate_viewport_bounds_empty_nodes(self):
        """Test viewport bounds calculation with empty nodes list."""
        # Act
        result = self.use_case._calculate_viewport_bounds([])

        # Assert
        expected = {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0}
        assert result == expected

    def test_calculate_viewport_bounds_single_node(self):
        """Test viewport bounds calculation with single node."""
        # Arrange
        nodes = [
            VisualizationNodeDTO(
                id="node-1",
                label="Test",
                node_type="Person",
                x=50.0,
                y=100.0,
                size=10.0,
                color="#000000",
                properties={}
            )
        ]

        # Act
        result = self.use_case._calculate_viewport_bounds(nodes)

        # Assert
        assert result["min_x"] == 40.0  # 50 - 10 (minimum padding)
        assert result["max_x"] == 60.0  # 50 + 10
        assert result["min_y"] == 90.0  # 100 - 10
        assert result["max_y"] == 110.0  # 100 + 10

    def test_calculate_viewport_bounds_multiple_nodes(self):
        """Test viewport bounds calculation with multiple nodes."""
        # Arrange
        nodes = [
            VisualizationNodeDTO(
                id="node-1", label="Test1", node_type="Person",
                x=0.0, y=0.0, size=10.0, color="#000000", properties={}
            ),
            VisualizationNodeDTO(
                id="node-2", label="Test2", node_type="Person",
                x=100.0, y=200.0, size=10.0, color="#000000", properties={}
            )
        ]

        # Act
        result = self.use_case._calculate_viewport_bounds(nodes)

        # Assert
        # X range: 100, padding: 10 (10% of 100)
        assert result["min_x"] == -10.0  # 0 - 10
        assert result["max_x"] == 110.0  # 100 + 10

        # Y range: 200, padding: 20 (10% of 200)
        assert result["min_y"] == -20.0  # 0 - 20
        assert result["max_y"] == 220.0  # 200 + 20

    def test_extract_visualization_nodes_without_labels(self):
        """Test node extraction without labels."""
        # Arrange
        nodes_data = [
            {
                "id": "node-1",
                "type": "Person",
                "x": 10.0,
                "y": 20.0,
                "properties": {"name": "Alice"}
            }
        ]

        # Act
        result = self.use_case._extract_visualization_nodes(nodes_data, include_labels=False)

        # Assert
        assert len(result) == 1
        assert result[0].label == ""  # No label when include_labels=False

    def test_extract_visualization_nodes_missing_fields(self):
        """Test node extraction with missing fields."""
        # Arrange
        nodes_data = [
            {
                "id": "node-1"
                # Missing other fields
            }
        ]

        # Act
        result = self.use_case._extract_visualization_nodes(nodes_data, include_labels=True)

        # Assert
        assert len(result) == 1
        node = result[0]
        assert node.id == "node-1"
        assert node.node_type == "unknown"
        assert node.x == 0.0
        assert node.y == 0.0
        assert node.size == 10.0
        assert node.color == "#3498db"
        assert node.properties == {}
        assert node.community_id is None

    def test_extract_visualization_edges_missing_fields(self):
        """Test edge extraction with missing fields."""
        # Arrange
        edges_data = [
            {
                "source": "node-1",
                "target": "node-2"
                # Missing other fields
            }
        ]

        # Act
        result = self.use_case._extract_visualization_edges(edges_data)

        # Assert
        assert len(result) == 1
        edge = result[0]
        assert edge.id == ""
        assert edge.source_id == "node-1"
        assert edge.target_id == "node-2"
        assert edge.relationship_type == "unknown"
        assert edge.weight is None
        assert edge.color == "#95a5a6"
        assert edge.properties == {}

    def test_supported_algorithms_validation(self):
        """Test that all supported algorithms are accepted."""
        supported_algorithms = [
            "force_directed", "circular", "hierarchical", "spring",
            "grid", "random", "fruchterman_reingold"
        ]

        for algorithm in supported_algorithms:
            request = GenerateGraphVisualizationRequestDTO(
                tenant_id="tenant-123",
                user_id="user-456",
                kg_id="kg-789",
                layout_algorithm=algorithm
            )

            # Should not raise ValidationError
            self.use_case._validate_request(request)

    def test_prepare_filters_empty(self):
        """Test filter preparation with no filters."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed",
            filter_by_node_types=None,
            filter_by_relationship_types=None
        )

        # Act
        result = self.use_case._prepare_filters(request)

        # Assert
        assert result == {}

    def test_prepare_filters_with_values(self):
        """Test filter preparation with filter values."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="force_directed",
            filter_by_node_types=["Person", "Organization"],
            filter_by_relationship_types=["WORKS_FOR"]
        )

        # Act
        result = self.use_case._prepare_filters(request)

        # Assert
        expected = {
            "node_types": ["Person", "Organization"],
            "relationship_types": ["WORKS_FOR"]
        }
        assert result == expected

    def test_tracing_span_creation(self):
        """Test that tracing span is created correctly."""
        # Arrange
        request = GenerateGraphVisualizationRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            kg_id="kg-789",
            layout_algorithm="circular"
        )

        self.graph_visualization_port.generate_layout.return_value = {"nodes": [], "edges": []}

        # Act
        self.use_case.execute(request)

        # Assert
        self.tracing_port.start_span.assert_called_once_with(
            name="generate_graph_visualization",
            tenant_id="tenant-123",
            kg_id="kg-789",
            layout_algorithm="circular"
        )