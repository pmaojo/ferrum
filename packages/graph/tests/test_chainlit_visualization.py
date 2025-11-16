"""
End-to-end tests for Chainlit visualization integration.

This module contains tests for the Chainlit visualization components,
including interactive graph visualization and result exploration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from pathlib import Path
import asyncio

from ui_adapters.chainlit.graph_visualization import ChainlitGraphVisualizer


class TestChainlitVisualization(unittest.TestCase):
    """Test cases for Chainlit visualization components."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_graph_visualizer = Mock()

        # Sample query result
        self.sample_result = {
            "results": [
                {
                    "type": "triple",
                    "subject": "entity1",
                    "predicate": "relates_to",
                    "object": "entity2",
                    "tenant_id": "default",
                    "relevance_score": 1.0,
                    "source": "graphrag_triple"
                },
                {
                    "type": "triple",
                    "subject": "entity2",
                    "predicate": "part_of",
                    "object": "entity3",
                    "tenant_id": "default",
                    "relevance_score": 0.9,
                    "source": "graphrag_triple"
                }
            ],
            "explanation": "This query found relationships between entities.",
            "metadata": {
                "execution_time_ms": 150.5,
                "result_count": 2,
                "translated_query": "MATCH (n)-[r]->(m) RETURN n, r, m",
                "error": False
            }
        }

        # Sample community data
        self.sample_community = {
            "nodes": [
                {"id": "entity1", "position": {"x": 100, "y": 100}, "attributes": {"label": "Entity1"}, "community_id": "comm1"},
                {"id": "entity2", "position": {"x": 200, "y": 150}, "attributes": {"label": "Entity2"}, "community_id": "comm1"},
                {"id": "entity3", "position": {"x": 150, "y": 200}, "attributes": {"label": "Entity3"}, "community_id": "comm1"}
            ],
            "edges": [
                {"source": "entity1", "target": "entity2", "type": "relates_to", "attributes": {"label": "relates_to"}},
                {"source": "entity2", "target": "entity3", "type": "part_of", "attributes": {"label": "part_of"}}
            ],
            "community_id": "comm1",
            "tenant_id": "default"
        }

        # Sample overview data
        self.sample_overview = {
            "communities": [
                {"id": "comm1", "size": 25, "position": {"x": 200, "y": 150}, "tenant_id": "default"},
                {"id": "comm2", "size": 18, "position": {"x": 400, "y": 250}, "tenant_id": "default"}
            ],
            "kg_id": "default",
            "tenant_id": "default"
        }

        # Configure mock graph visualizer
        self.mock_graph_visualizer.render_community_detail.return_value = self.sample_community
        self.mock_graph_visualizer.render_graph_overview.return_value = self.sample_overview

    @patch("ui_adapters.chainlit.graph_visualization.cl")
    @patch("ui_adapters.chainlit.graph_visualization.tempfile.NamedTemporaryFile")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="<html><!-- TEMPLATE --></html>")
    def test_visualize_query_results(self, mock_open, mock_tempfile, mock_cl):
        """Test visualization of query results."""
        # Setup mock for tempfile
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.name = "/tmp/mock_visualization.html"
        mock_tempfile.return_value = mock_file

        # Create visualizer
        visualizer = ChainlitGraphVisualizer(self.mock_graph_visualizer)

        # Run the async method using asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            visualizer.visualize_query_results(
                results=self.sample_result,
                question="What entities are related to concept X?",
                kg_id="default",
                tenant_id="default"
            )
        )

        # Verify visualization was generated
        self.assertTrue(mock_tempfile.called)

        # Verify message was sent
        mock_cl.Message.assert_called()
        mock_cl.Message.return_value.send.assert_called_once()

        # Verify iframe was created
        mock_cl.Iframe.assert_called()

    @patch("ui_adapters.chainlit.graph_visualization.cl")
    @patch("ui_adapters.chainlit.graph_visualization.tempfile.NamedTemporaryFile")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="<html><!-- TEMPLATE --></html>")
    def test_visualize_community(self, mock_open, mock_tempfile, mock_cl):
        """Test visualization of community detail."""
        # Setup mock for tempfile
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.name = "/tmp/mock_visualization.html"
        mock_tempfile.return_value = mock_file

        # Create visualizer
        visualizer = ChainlitGraphVisualizer(self.mock_graph_visualizer)

        # Run the async method using asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            visualizer.visualize_community(
                community_id="comm1",
                tenant_id="default",
                title="Test Community"
            )
        )

        # Verify graph visualizer was called
        self.mock_graph_visualizer.render_community_detail.assert_called_once_with(
            community_id="comm1",
            tenant_id="default"
        )

        # Verify visualization was generated
        self.assertTrue(mock_tempfile.called)

        # Verify message was sent
        mock_cl.Message.assert_called()
        mock_cl.Message.return_value.send.assert_called_once()

    @patch("ui_adapters.chainlit.graph_visualization.cl")
    @patch("ui_adapters.chainlit.graph_visualization.tempfile.NamedTemporaryFile")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="<html><!-- TEMPLATE --></html>")
    def test_visualize_graph_overview(self, mock_open, mock_tempfile, mock_cl):
        """Test visualization of graph overview."""
        # Setup mock for tempfile
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.name = "/tmp/mock_visualization.html"
        mock_tempfile.return_value = mock_file

        # Create visualizer
        visualizer = ChainlitGraphVisualizer(self.mock_graph_visualizer)

        # Run the async method using asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            visualizer.visualize_graph_overview(
                kg_id="default",
                tenant_id="default",
                algorithm="louvain",
                title="Test Overview"
            )
        )

        # Verify graph visualizer was called
        self.mock_graph_visualizer.render_graph_overview.assert_called_once_with(
            kg_id="default",
            tenant_id="default",
            algorithm="louvain"
        )

        # Verify visualization was generated
        self.assertTrue(mock_tempfile.called)

        # Verify message was sent
        mock_cl.Message.assert_called()
        mock_cl.Message.return_value.send.assert_called_once()

    def test_extract_path_from_results(self):
        """Test extraction of path nodes from query results."""
        # Create visualizer
        visualizer = ChainlitGraphVisualizer(self.mock_graph_visualizer)

        # Extract path nodes
        path_nodes = visualizer._extract_path_from_results(self.sample_result)

        # Verify extracted nodes
        self.assertEqual(len(path_nodes), 3)
        self.assertIn("entity1", path_nodes)
        self.assertIn("entity2", path_nodes)
        self.assertIn("entity3", path_nodes)

    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="<html><!-- TEMPLATE --></html>")
    def test_generate_visualization_html(self, mock_open):
        """Test generation of visualization HTML."""
        # Create visualizer
        visualizer = ChainlitGraphVisualizer(self.mock_graph_visualizer)

        # Generate HTML
        path_nodes = ["entity1", "entity2", "entity3"]
        html = visualizer._generate_visualization_html(path_nodes, "default", "default")

        # Verify HTML was generated
        self.assertIsNotNone(html)
        self.assertIn("entity1", html)
        self.assertIn("entity2", html)
        self.assertIn("entity3", html)


if __name__ == "__main__":
    unittest.main()