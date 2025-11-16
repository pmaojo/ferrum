"""
Unit tests for Chainlit UI adapter.

This module contains tests for the Chainlit UI adapter implementation,
including the GraphRAG tool and visualization integration.
"""
import importlib
import pytest

try:
    _cl = importlib.import_module("chainlit")
    getattr(_cl, "Action")
except Exception:  # pragma: no cover - optional dependency
    pytest.skip("chainlit package not available", allow_module_level=True)

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from pathlib import Path

from ui_adapters.chainlit.graphrag_tool import ChainlitGraphRAGAdapter


class TestChainlitAdapter(unittest.TestCase):
    """Test cases for Chainlit UI adapter."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_query_service = Mock()
        self.mock_graph_retriever = Mock()
        self.mock_query_translator = Mock()
        self.mock_graph_visualizer = Mock()
        self.mock_response_generator = Mock()

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

        # Configure mock query service
        self.mock_query_service.execute_natural_language_query.return_value = self.sample_result

    @patch("ui_adapters.chainlit.graphrag_tool.cl")
    def test_adapter_initialization(self, mock_cl):
        """Test adapter initialization and tool registration."""
        # Initialize adapter
        adapter = ChainlitGraphRAGAdapter(
            query_service=self.mock_query_service,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            graph_visualizer=self.mock_graph_visualizer,
            response_generator=self.mock_response_generator
        )

        # Verify tool registration
        mock_cl.tool.assert_called_once()

    @patch("ui_adapters.chainlit.graphrag_tool.cl")
    def test_graphrag_tool_execution(self, mock_cl):
        """Test GraphRAG tool execution with query."""
        # Initialize adapter
        adapter = ChainlitGraphRAGAdapter(
            query_service=self.mock_query_service,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            graph_visualizer=self.mock_graph_visualizer,
            response_generator=self.mock_response_generator
        )

        # Get the registered tool function
        tool_decorator = mock_cl.tool.return_value
        tool_func = tool_decorator.call_args[0][0]

        # Execute tool function
        question = "What entities are related to concept X?"
        result = tool_func(question)

        # Verify query service was called
        self.mock_query_service.execute_natural_language_query.assert_called_once_with(
            question=question,
            kg_id="default",
            tenant_id="default",
            user_id="chainlit_user",
            include_explanation=True
        )

        # Verify result formatting
        self.assertIn("Results for:", result)
        self.assertIn("Explanation", result)
        self.assertIn("This query found relationships between entities.", result)
        self.assertIn("entity1 → relates_to → entity2", result)
        self.assertIn("entity2 → part_of → entity3", result)
        self.assertIn("Query executed in 150.50ms with 2 results", result)

    @patch("ui_adapters.chainlit.graphrag_tool.cl")
    @patch("ui_adapters.chainlit.graphrag_tool.tempfile.NamedTemporaryFile")
    @patch("ui_adapters.chainlit.graphrag_tool.Path")
    def test_visualization_generation(self, mock_path, mock_tempfile, mock_cl):
        """Test visualization generation for query results."""
        # Setup mock for Path
        mock_path_instance = Mock()
        mock_path_instance.parent.parent = Path("/mock/path")
        mock_path.return_value = mock_path_instance

        # Setup mock for tempfile
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.name = "/tmp/mock_visualization.html"
        mock_tempfile.return_value = mock_file

        # Setup mock for open
        mock_open = unittest.mock.mock_open(read_data="<html><!-- TEMPLATE --></html>")

        # Initialize adapter
        adapter = ChainlitGraphRAGAdapter(
            query_service=self.mock_query_service,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            graph_visualizer=self.mock_graph_visualizer,
            response_generator=self.mock_response_generator
        )

        # Get the registered tool function
        tool_decorator = mock_cl.tool.return_value
        tool_func = tool_decorator.call_args[0][0]

        # Execute tool function with patched open
        with patch("builtins.open", mock_open):
            question = "What entities are related to concept X?"
            result = tool_func(question)

        # Verify visualization was generated
        self.assertTrue(mock_tempfile.called)

        # Verify message was sent
        mock_cl.Message.assert_called()

    @patch("ui_adapters.chainlit.graphrag_tool.cl")
    def test_error_handling(self, mock_cl):
        """Test error handling in GraphRAG tool."""
        # Configure mock to raise exception
        self.mock_query_service.execute_natural_language_query.side_effect = Exception("Test error")

        # Initialize adapter
        adapter = ChainlitGraphRAGAdapter(
            query_service=self.mock_query_service,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            graph_visualizer=self.mock_graph_visualizer,
            response_generator=self.mock_response_generator
        )

        # Get the registered tool function
        tool_decorator = mock_cl.tool.return_value
        tool_func = tool_decorator.call_args[0][0]

        # Execute tool function
        question = "What entities are related to concept X?"
        result = tool_func(question)

        # Verify error message
        self.assertIn("Error processing query: Test error", result)


if __name__ == "__main__":
    unittest.main()