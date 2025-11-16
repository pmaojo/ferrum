"""
Graph visualization components for Chainlit UI.

This module provides interactive graph visualization components for displaying
GraphRAG query results in the Chainlit UI.
"""

import logging
import json
import tempfile
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import os

try:  # Optional Chainlit dependency
    import chainlit as cl
    from chainlit.element import Element
except Exception:  # pragma: no cover - fallback stubs
    from infrastructure.stubs import chainlit as cl
    Element = object  # type: ignore

from domain.entities import Triple
from domain.graph_visualizer import GraphVisualizer

# Configure logging
logger = logging.getLogger(__name__)


class ChainlitGraphVisualizer:
    """Graph visualization component for Chainlit UI.

    This class provides methods for generating interactive graph visualizations
    for display in the Chainlit UI.
    """

    def __init__(
        self,
        graph_visualizer: GraphVisualizer,
        template_path: Optional[str] = None,
        width: int = 800,
        height: int = 600,
        cl_module: Optional[Any] = None,
    ):
        """Initialize Chainlit graph visualizer.

        Args:
            graph_visualizer: Domain graph visualizer service
            template_path: Optional path to HTML template
            width: Visualization width in pixels
            height: Visualization height in pixels
        """
        self.graph_visualizer = graph_visualizer
        self.width = width
        self.height = height
        self._cl = cl_module or cl

        # Use default template if not provided
        if template_path:
            self.template_path = Path(template_path)
        else:
            self.template_path = Path(__file__).parent.parent / "visualization_demo.html"

        # Verify template exists
        if not self.template_path.exists():
            logger.warning(f"Visualization template not found at {self.template_path}")

        # Register callback for graph exploration
        self._cl.action_callback("explore_graph")(self._on_explore_graph)

    async def visualize_query_results(
        self,
        results: Dict[str, Any],
        question: str,
        kg_id: str,
        tenant_id: str
    ) -> Optional[Any]:
        """Generate and display visualization for query results.

        Args:
            results: Query result dictionary
            question: Original natural language query
            kg_id: Knowledge graph ID
            tenant_id: Tenant ID

        Returns:
            Chainlit message with visualization or None if visualization failed
        """
        try:
            # Extract path to highlight if available
            path_nodes = self._extract_path_from_results(results)

            if not path_nodes:
                logger.info("No path nodes found in results for visualization")
                return None

            # Generate HTML visualization
            html_content = self._generate_visualization_html(path_nodes, kg_id, tenant_id)

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(html_content)
                temp_path = f.name

            # Create interactive elements
            elements = [
                self._cl.Iframe(path=temp_path, display="inline", height=self.height)
            ]

            # Add exploration controls if available
            if len(path_nodes) > 3:
                elements.append(
                    self._cl.Text(
                        name="graph_data",
                        content=json.dumps({
                            "path_nodes": path_nodes,
                            "kg_id": kg_id,
                            "tenant_id": tenant_id
                        }),
                        display="none"
                    )
                )

                # Add interactive buttons
                elements.append(
                    self._cl.Button(
                        name="explore_graph",
                        content="Explore Graph",
                        action_name="explore_graph"
                    )
                )

            # Send visualization message
            message = self._cl.Message(
                content=f"Graph visualization for: '{question}'",
                elements=elements
            )

            await message.send()
            return message

        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
            return None

    async def visualize_community(
        self,
        community_id: str,
        tenant_id: str,
        title: str = "Community Visualization"
    ) -> Optional[Any]:
        """Generate and display visualization for a community.

        Args:
            community_id: Community identifier
            tenant_id: Tenant identifier
            title: Visualization title

        Returns:
            Chainlit message with visualization or None if visualization failed
        """
        try:
            # Get community detail from graph visualizer
            community_data = self.graph_visualizer.render_community_detail(
                community_id=community_id,
                tenant_id=tenant_id
            )

            # Generate HTML visualization
            html_content = self._generate_community_html(community_data)

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(html_content)
                temp_path = f.name

            # Send visualization message
            message = self._cl.Message(
                content=title,
                elements=[
                    self._cl.Iframe(path=temp_path, display="inline", height=self.height)
                ]
            )

            await message.send()
            return message

        except Exception as e:
            logger.error(f"Error generating community visualization: {str(e)}", exc_info=True)
            return None

    async def visualize_graph_overview(
        self,
        kg_id: str,
        tenant_id: str,
        algorithm: str = "louvain",
        title: str = "Knowledge Graph Overview"
    ) -> Optional[Any]:
        """Generate and display visualization for graph overview.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            algorithm: Community detection algorithm
            title: Visualization title

        Returns:
            Chainlit message with visualization or None if visualization failed
        """
        try:
            # Get graph overview from graph visualizer
            overview_data = self.graph_visualizer.render_graph_overview(
                kg_id=kg_id,
                tenant_id=tenant_id,
                algorithm=algorithm
            )

            # Generate HTML visualization
            html_content = self._generate_overview_html(overview_data)

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(html_content)
                temp_path = f.name

            # Send visualization message
            message = self._cl.Message(
                content=title,
                elements=[
                    self._cl.Iframe(path=temp_path, display="inline", height=self.height)
                ]
            )

            await message.send()
            return message

        except Exception as e:
            logger.error(f"Error generating graph overview: {str(e)}", exc_info=True)
            return None

    def _extract_path_from_results(self, results: Dict[str, Any]) -> List[str]:
        """Extract path nodes from query results.

        Args:
            results: Query result dictionary

        Returns:
            List of node IDs forming a path
        """
        path_nodes = []

        # Extract nodes from results
        result_items = results.get("results", [])

        if isinstance(result_items, list):
            # Handle structured results
            for item in result_items:
                if isinstance(item, dict):
                    if item.get("type") == "triple":
                        # Add subject and object from triple
                        if item.get("subject") and item.get("subject") not in path_nodes:
                            path_nodes.append(item.get("subject"))
                        if item.get("object") and item.get("object") not in path_nodes:
                            path_nodes.append(item.get("object"))

        return path_nodes

    def _generate_visualization_html(
        self,
        path_nodes: List[str],
        kg_id: str,
        tenant_id: str
    ) -> str:
        """Generate HTML visualization for query results.

        Args:
            path_nodes: List of node IDs to highlight
            kg_id: Knowledge graph ID
            tenant_id: Tenant ID

        Returns:
            HTML content as string
        """
        # Read the visualization template
        with open(self.template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Modify the template to include our path nodes
        path_nodes_json = json.dumps(path_nodes)

        # Insert path nodes into the sampleHighlight object
        html_content = html_content.replace(
            '"path": ["node1", "node2", "node3", "node5"]',
            f'"path": {path_nodes_json}'
        )

        if path_nodes_json not in html_content:
            html_content += (
                f'<script id="graph-data" type="application/json">{path_nodes_json}</script>'
            )

        # Add custom title
        html_content = html_content.replace(
            "<title>GraphRAG Visualization Demo</title>",
            f"<title>GraphRAG Query Results - {kg_id}</title>"
        )

        # Add tenant ID as data attribute
        html_content = html_content.replace(
            "<body>",
            f'<body data-tenant-id="{tenant_id}" data-kg-id="{kg_id}">'
        )

        # Add responsive sizing
        html_content = html_content.replace(
            "width: 100%;",
            "width: 100%; max-width: 100%;"
        )

        return html_content

    def _generate_community_html(self, community_data: Dict[str, Any]) -> str:
        """Generate HTML visualization for community detail.

        Args:
            community_data: Community detail data from graph visualizer

        Returns:
            HTML content as string
        """
        # Read the visualization template
        with open(self.template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Replace sample community data with actual data
        community_json = json.dumps(community_data)

        # Insert community data
        html_content = html_content.replace(
            "const sampleCommunity = {",
            f"const sampleCommunity = {community_json}; const originalCommunity = {{"
        )

        # Add custom title
        html_content = html_content.replace(
            "<title>GraphRAG Visualization Demo</title>",
            f"<title>Community Detail - {community_data.get('community_id', 'Unknown')}</title>"
        )

        # Add responsive sizing
        html_content = html_content.replace(
            "width: 100%;",
            "width: 100%; max-width: 100%;"
        )

        return html_content

    def _generate_overview_html(self, overview_data: Dict[str, Any]) -> str:
        """Generate HTML visualization for graph overview.

        Args:
            overview_data: Graph overview data from graph visualizer

        Returns:
            HTML content as string
        """
        # Read the visualization template
        with open(self.template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Replace sample overview data with actual data
        overview_json = json.dumps(overview_data)

        # Insert overview data
        html_content = html_content.replace(
            "const sampleOverview = {",
            f"const sampleOverview = {overview_json}; const originalOverview = {{"
        )

        # Add custom title
        html_content = html_content.replace(
            "<title>GraphRAG Visualization Demo</title>",
            f"<title>Knowledge Graph Overview - {overview_data.get('kg_id', 'Unknown')}</title>"
        )

        # Add responsive sizing
        html_content = html_content.replace(
            "width: 100%;",
            "width: 100%; max-width: 100%;"
        )

        return html_content

    async def _on_explore_graph(self, action: Any) -> None:
        """Handle explore graph button click."""
        try:
            graph_data_element = next(
                (e for e in action.message.elements if e.name == "graph_data"),
                None,
            )

            if not graph_data_element:
                await self._cl.Message(content="Graph data not found").send()
                return

            graph_data = json.loads(graph_data_element.content)

            await self._cl.Message(
                content=f"Exploring graph with {len(graph_data['path_nodes'])} nodes"
            ).send()
        except Exception as e:
            logger.error("Error handling explore action: %s", str(e), exc_info=True)
            await self._cl.Message(content=f"Error exploring graph: {str(e)}").send()

