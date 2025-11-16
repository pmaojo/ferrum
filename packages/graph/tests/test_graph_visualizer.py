"""Tests for GraphVisualizer with D3.js and WebGL optimization."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Dict, List, Any

from domain.entities import Triple, Community, GraphStreamEvent, GraphStreamEventType
from domain.graph_visualizer import GraphVisualizer, VisualizationException


class TestGraphVisualizer:
    """Test suite for GraphVisualizer implementation."""

    @pytest.fixture
    def mock_clustering_port(self):
        """Create mock clustering port for testing."""
        mock = Mock()

        # Setup compute_communities mock
        mock.compute_communities.return_value = [
            Community(
                id="test_kg:1",
                centroid_embedding=[0.1, 0.2, 0.3, 0.4],
                node_ids=["node1", "node2", "node3"],
                size=3,
                tenant_id="test_tenant"
            ),
            Community(
                id="test_kg:2",
                centroid_embedding=[0.5, 0.6, 0.7, 0.8],
                node_ids=["node4", "node5", "node6", "node7"],
                size=4,
                tenant_id="test_tenant"
            )
        ]

        # Setup get_community_subgraph mock
        mock.get_community_subgraph.return_value = [
            Triple(
                subject="node1",
                predicate="relates_to",
                object="node2",
                tenant_id="test_tenant"
            ),
            Triple(
                subject="node2",
                predicate="connects_to",
                object="node3",
                tenant_id="test_tenant"
            )
        ]

        return mock

    @pytest.fixture
    def mock_stream_port(self):
        """Create mock stream port for testing."""
        mock = Mock()
        return mock

    @pytest.fixture
    def mock_tracer_port(self):
        """Create mock tracer port for testing."""
        mock = Mock()
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def visualizer(self, mock_clustering_port, mock_stream_port, mock_tracer_port):
        """Create GraphVisualizer instance for testing."""
        return GraphVisualizer(
            clustering_port=mock_clustering_port,
            stream_port=mock_stream_port,
            tracer=mock_tracer_port,
            viewport_size=(800, 600)
        )

    def test_initialization(self, visualizer, mock_clustering_port):
        """Test GraphVisualizer initialization."""
        assert visualizer.clustering == mock_clustering_port
        assert visualizer.viewport_size == (800, 600)
        assert visualizer.visible_communities == set()
        assert visualizer.visible_nodes == set()
        assert visualizer.visible_edges == set()
        assert visualizer.use_webgl is False

    def test_render_graph_overview(self, visualizer, mock_clustering_port):
        """Test rendering graph overview with communities."""
        result = visualizer.render_graph_overview(
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify clustering port was called correctly
        mock_clustering_port.compute_communities.assert_called_once_with(
            kg_id="test_kg",
            tenant_id="test_tenant",
            algorithm="louvain"
        )

        # Verify response structure
        assert "communities" in result
        assert "layout" in result
        assert "styles" in result
        assert "stats" in result
        assert len(result["communities"]) == 2
        assert result["stats"]["total_nodes"] == 7  # Sum of community sizes
        assert result["stats"]["render_mode"] == "svg"  # Default for small graph

    def test_span_closed_overview(self, visualizer, mock_tracer_port):
        span = MagicMock()
        mock_tracer_port.start_span.return_value = span

        visualizer.render_graph_overview(kg_id="kg", tenant_id="t")

        span.end.assert_called_once()

    def test_render_community_detail(self, visualizer, mock_clustering_port):
        """Test rendering community detail view."""
        result = visualizer.render_community_detail(
            community_id="test_kg:1",
            tenant_id="test_tenant"
        )

        # Verify clustering port was called correctly
        mock_clustering_port.get_community_subgraph.assert_called_once_with(
            community_id="test_kg:1",
            tenant_id="test_tenant"
        )

        # Verify response structure
        assert "nodes" in result
        assert "edges" in result
        assert "layout" in result
        assert "styles" in result
        assert len(result["nodes"]) == 3  # Three nodes from the triples
        assert len(result["edges"]) == 2  # Two edges from the triples

        # Verify visible elements were updated
        assert "test_kg:1" in visualizer.visible_communities
        assert len(visualizer.visible_nodes) == 3
        assert len(visualizer.visible_edges) == 2

    def test_span_closed_community(self, visualizer, mock_tracer_port):
        span = MagicMock()
        mock_tracer_port.start_span.return_value = span

        visualizer.render_community_detail(community_id="c", tenant_id="t")

        span.end.assert_called_once()

    def test_highlight_path(self, visualizer, mock_stream_port):
        """Test path highlighting with streaming."""
        path_nodes = ["node1", "node2", "node3"]

        result = visualizer.highlight_path(
            path_nodes=path_nodes,
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify stream port was called correctly
        assert mock_stream_port.send_event.called
        event_arg = mock_stream_port.send_event.call_args[1]["event"]
        assert isinstance(event_arg, GraphStreamEvent)
        assert event_arg.event_type == GraphStreamEventType.PATH_HIGHLIGHTED
        assert event_arg.data["path_nodes"] == path_nodes

        # Verify response structure
        assert "highlight_id" in result
        assert "path" in result
        assert "styles" in result
        assert result["path"] == path_nodes

    def test_update_viewport(self, visualizer):
        """Test viewport update for culling."""
        result = visualizer.update_viewport(
            x_min=100,
            y_min=100,
            x_max=700,
            y_max=500,
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

        # Verify viewport was updated
        assert visualizer.viewport_bounds["x_min"] == 100
        assert visualizer.viewport_bounds["y_min"] == 100
        assert visualizer.viewport_bounds["x_max"] == 700
        assert visualizer.viewport_bounds["y_max"] == 500

        # Verify response structure
        assert "viewport" in result
        assert "visible_elements" in result

    def test_register_event_handler(self, visualizer):
        """Test event handler registration."""
        mock_handler = Mock()

        visualizer.register_event_handler("node_click", mock_handler)

        assert mock_handler in visualizer.event_handlers["node_click"]

        # Test invalid event type
        with pytest.raises(ValueError):
            visualizer.register_event_handler("invalid_event", mock_handler)

    def test_generate_svg_thumbnail(self, visualizer, mock_clustering_port):
        """Test SVG thumbnail generation."""
        svg = visualizer.generate_svg_thumbnail(
            community_id="test_kg:1",
            tenant_id="test_tenant",
            width=100,
            height=100
        )

        # Verify clustering port was called correctly
        mock_clustering_port.get_community_subgraph.assert_called_with(
            community_id="test_kg:1",
            tenant_id="test_tenant"
        )

        # Verify SVG structure
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')
        assert 'width="100"' in svg
        assert 'height="100"' in svg

    def test_empty_community_response(self, visualizer, mock_clustering_port):
        """Test handling of empty community data."""
        # Setup mock to return empty list
        mock_clustering_port.get_community_subgraph.return_value = []

        result = visualizer.render_community_detail(
            community_id="empty_community",
            tenant_id="test_tenant"
        )

        # Verify empty response structure
        assert "empty" in result
        assert result["empty"] is True
        assert len(result["nodes"]) == 0
        assert len(result["edges"]) == 0

    def test_error_handling(self, visualizer, mock_clustering_port):
        """Test error handling in visualization methods."""
        # Setup mock to raise exception
        mock_clustering_port.compute_communities.side_effect = Exception("Test error")

        # Verify exception is wrapped in VisualizationException
        with pytest.raises(VisualizationException) as excinfo:
            visualizer.render_graph_overview(
                kg_id="test_kg",
                tenant_id="test_tenant"
            )

        assert "Test error" in str(excinfo.value)
        assert excinfo.value.error_code == "VISUALIZATION_OVERVIEW_ERROR"

    def test_viewport_counts_full(self, visualizer):
        """Viewport returns all elements when view covers entire graph."""
        visualizer.render_community_detail(
            community_id="test_kg:1",
            tenant_id="test_tenant",
        )

        visualizer.node_positions = {
            "node1": {"x": 100, "y": 100},
            "node2": {"x": 200, "y": 200},
            "node3": {"x": 300, "y": 300},
        }
        visualizer.community_positions = {"test_kg:1": {"x": 150, "y": 150}}

        result = visualizer.update_viewport(
            x_min=0,
            y_min=0,
            x_max=400,
            y_max=400,
            kg_id="test_kg",
            tenant_id="test_tenant",
        )

        assert result["visible_elements"]["node_count"] == 3
        assert result["visible_elements"]["edge_count"] == 2
        assert result["visible_elements"]["community_count"] == 1

    def test_viewport_counts_partial(self, visualizer):
        """Viewport culling hides off-screen elements."""
        visualizer.render_community_detail(
            community_id="test_kg:1",
            tenant_id="test_tenant",
        )

        visualizer.node_positions = {
            "node1": {"x": 50, "y": 50},
            "node2": {"x": 300, "y": 300},
            "node3": {"x": 500, "y": 500},
        }
        visualizer.community_positions = {"test_kg:1": {"x": 300, "y": 300}}

        result = visualizer.update_viewport(
            x_min=0,
            y_min=0,
            x_max=250,
            y_max=250,
            kg_id="test_kg",
            tenant_id="test_tenant",
        )

        assert result["visible_elements"]["node_count"] == 1
        assert result["visible_elements"]["edge_count"] == 0
        assert result["visible_elements"]["community_count"] == 0

    def test_render_complete_event_overview(self, visualizer):
        handler = Mock()
        visualizer.register_event_handler("render_complete", handler)

        visualizer.render_graph_overview(kg_id="kg", tenant_id="t")

        handler.assert_called_once()

    def test_render_complete_event_community(self, visualizer):
        handler = Mock()
        visualizer.register_event_handler("render_complete", handler)

        visualizer.render_community_detail(community_id="test_kg:1", tenant_id="test_tenant")

        handler.assert_called()

    def test_viewport_counts_none(self, visualizer):
        """No elements visible when viewport outside graph."""
        visualizer.render_community_detail(
            community_id="test_kg:1",
            tenant_id="test_tenant",
        )

        visualizer.node_positions = {
            "node1": {"x": 100, "y": 100},
            "node2": {"x": 200, "y": 200},
            "node3": {"x": 300, "y": 300},
        }
        visualizer.community_positions = {"test_kg:1": {"x": 150, "y": 150}}

        result = visualizer.update_viewport(
            x_min=700,
            y_min=700,
            x_max=800,
            y_max=800,
            kg_id="test_kg",
            tenant_id="test_tenant",
        )

        assert result["visible_elements"]["node_count"] == 0
        assert result["visible_elements"]["edge_count"] == 0
        assert result["visible_elements"]["community_count"] == 0