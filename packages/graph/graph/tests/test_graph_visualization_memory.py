"""Memory profiling tests for graph visualization with progressive rendering.

This test suite measures memory usage during graph visualization with different
rendering strategies and viewport culling.
"""

import logging
import random
import sys
import time
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

# Import memory_profiler if available
try:
    from memory_profiler import profile as memory_profile
except ImportError:
    # Create a no-op decorator if memory_profiler is not available
    def memory_profile(func):
        return func


from domain.entities import Community, GraphStreamEvent, GraphStreamEventType, Triple
from domain.graph_visualizer import GraphVisualizer


class TestGraphVisualizationMemory:
    """Memory profiling tests for graph visualization."""

    @pytest.fixture
    def mock_clustering_port(self):
        """Create mock clustering port with large graph data."""
        mock = Mock()

        # Generate large number of communities
        communities = []
        for i in range(50):
            # Each community has random number of nodes
            node_count = random.randint(100, 500)
            node_ids = [f"node_{i}_{j}" for j in range(node_count)]

            communities.append(
                Community(
                    id=f"test_kg:{i}",
                    centroid_embedding=[random.random() for _ in range(10)],
                    node_ids=node_ids,
                    size=len(node_ids),
                    tenant_id="test_tenant",
                )
            )

        mock.compute_communities.return_value = communities

        # Setup get_community_subgraph to return large number of triples
        def get_subgraph(*, community_id, tenant_id):
            community_index = int(community_id.split(":")[-1])
            node_count = communities[community_index].size

            # Generate triples for this community
            triples = []
            for j in range(node_count):
                node_id = f"node_{community_index}_{j}"

                # Each node connects to ~5 other nodes
                for _ in range(min(5, node_count - j - 1)):
                    target_j = j + random.randint(1, min(20, node_count - j - 1))
                    target_id = f"node_{community_index}_{target_j}"

                    triples.append(
                        Triple(
                            subject=node_id,
                            predicate="connects_to",
                            object=target_id,
                            tenant_id=tenant_id,
                        )
                    )

                # Add node properties
                triples.append(
                    Triple(
                        subject=node_id,
                        predicate="has_value",
                        object=f"value_{random.randint(1, 100)}",
                        tenant_id=tenant_id,
                    )
                )

            return triples

        mock.get_community_subgraph.side_effect = get_subgraph

        return mock

    @pytest.fixture
    def mock_stream_port(self):
        """Create mock stream port for testing."""
        return Mock()

    @pytest.fixture
    def mock_tracer_port(self):
        """Create mock tracer port for testing."""
        return Mock()

    @pytest.fixture
    def visualizer(self, mock_clustering_port, mock_stream_port, mock_tracer_port):
        """Create GraphVisualizer instance for testing."""
        return GraphVisualizer(
            clustering_port=mock_clustering_port,
            stream_port=mock_stream_port,
            tracer=mock_tracer_port,
            viewport_size=(1920, 1080),
        )

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_render_graph_overview_memory(self, visualizer):
        """Test memory usage when rendering graph overview."""
        # Measure memory usage for graph overview rendering
        result = visualizer.render_graph_overview(
            kg_id="test_kg", tenant_id="test_tenant"
        )

        # Basic assertions to ensure the function worked
        assert "communities" in result
        assert "layout" in result
        assert "styles" in result
        assert "stats" in result
        assert len(result["communities"]) == 50

        # Force garbage collection to get accurate memory measurements
        import gc

        gc.collect()

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_render_community_detail_memory(self, visualizer, mock_clustering_port):
        """Test memory usage when rendering community detail."""
        # Get a large community
        communities = mock_clustering_port.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant"
        )

        # Find the largest community
        largest_community = max(communities, key=lambda c: c.size)

        # Measure memory usage for community detail rendering
        result = visualizer.render_community_detail(
            community_id=largest_community.id, tenant_id="test_tenant"
        )

        # Basic assertions to ensure the function worked
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) > 0
        assert len(result["edges"]) > 0

        # Force garbage collection
        import gc

        gc.collect()

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_viewport_culling_memory(self, visualizer, mock_clustering_port):
        """Test memory usage with viewport culling."""
        # First load a large community
        communities = mock_clustering_port.compute_communities(
            kg_id="test_kg", tenant_id="test_tenant"
        )
        largest_community = max(communities, key=lambda c: c.size)

        visualizer.render_community_detail(
            community_id=largest_community.id, tenant_id="test_tenant"
        )

        # Now measure memory usage with viewport culling
        result = visualizer.update_viewport(
            x_min=100,
            y_min=100,
            x_max=500,
            y_max=400,
            kg_id="test_kg",
            tenant_id="test_tenant",
        )

        # Basic assertions
        assert "viewport" in result
        assert "visible_elements" in result

        # The number of visible elements should be less than total elements
        assert result["visible_elements"]["node_count"] < largest_community.size

        # Force garbage collection
        import gc

        gc.collect()

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_webgl_vs_svg_memory(self, visualizer, mock_clustering_port):
        """Compare memory usage between WebGL and SVG rendering."""
        # First test with SVG rendering (default)
        visualizer.use_webgl = False

        svg_start_time = time.time()
        svg_result = visualizer.render_graph_overview(
            kg_id="test_kg", tenant_id="test_tenant"
        )
        svg_time = time.time() - svg_start_time

        # Force garbage collection
        import gc

        gc.collect()

        # Now test with WebGL rendering
        visualizer.use_webgl = True

        webgl_start_time = time.time()
        webgl_result = visualizer.render_graph_overview(
            kg_id="test_kg", tenant_id="test_tenant"
        )
        webgl_time = time.time() - webgl_start_time

        # Basic assertions
        assert svg_result["stats"]["render_mode"] == "svg"
        assert webgl_result["stats"]["render_mode"] == "webgl"

        # Print performance comparison using logging
        logger = logging.getLogger(__name__)
        logger.info("SVG rendering time: %.4fs", svg_time)
        logger.info("WebGL rendering time: %.4fs", webgl_time)
        logger.info("WebGL speedup: %.2fx", svg_time / webgl_time)

        # Force garbage collection
        gc.collect()

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_progressive_loading_memory(self, visualizer, mock_clustering_port):
        """Test memory usage with progressive loading strategy."""
        # First load overview (communities only)
        overview_result = visualizer.render_graph_overview(
            kg_id="test_kg", tenant_id="test_tenant"
        )

        # Get first few communities
        community_ids = [c["id"] for c in overview_result["communities"][:3]]

        # Progressively load each community and measure memory
        for community_id in community_ids:
            # Load community detail
            detail_result = visualizer.render_community_detail(
                community_id=community_id, tenant_id="test_tenant"
            )

            # Basic assertions
            assert "nodes" in detail_result
            assert "edges" in detail_result
            assert len(detail_result["nodes"]) > 0

            # Force garbage collection between communities
            import gc

            gc.collect()

    @pytest.mark.skipif(
        sys.platform != "linux", reason="Memory profiling most accurate on Linux"
    )
    @memory_profile
    def test_real_time_updates_memory(self, visualizer, mock_stream_port):
        """Test memory usage with real-time graph updates."""
        # Setup initial graph state
        visualizer.render_graph_overview(kg_id="test_kg", tenant_id="test_tenant")

        # Simulate stream of graph updates
        for i in range(100):
            # Create node added event
            node_event = GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={
                    "node_id": f"new_node_{i}",
                    "properties": {"name": f"Node {i}", "type": "TestNode"},
                },
                timestamp=time.time(),
                kg_id="test_kg",
                tenant_id="test_tenant",
            )

            # Process event
            visualizer._process_stream_event(node_event)

            # Create edge added event
            if i > 0:
                edge_event = GraphStreamEvent(
                    event_type=GraphStreamEventType.EDGE_ADDED,
                    data={
                        "source_id": f"new_node_{i-1}",
                        "target_id": f"new_node_{i}",
                        "type": "connects_to",
                    },
                    timestamp=time.time(),
                    kg_id="test_kg",
                    tenant_id="test_tenant",
                )

                # Process event
                visualizer._process_stream_event(edge_event)

        # Force garbage collection
        import gc

        gc.collect()

        # Verify node and edge counts
        assert len(visualizer.visible_nodes) >= 100
        assert len(visualizer.visible_edges) >= 99


if __name__ == "__main__":
    pytest.main(["-v", __file__])
