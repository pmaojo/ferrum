"""Graph visualization service with D3.js and WebGL optimization.

This module implements interactive graph visualization with D3.js and WebGL
for large graph rendering, progressive loading, and real-time updates.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime
import math

from domain.entities import (
    Triple,
    Community,
    GraphStreamEvent,
    GraphStreamEventType,
)
from application.ports import ClusteringPort, GraphStreamPort, TracingPort
from domain.utils.tracing import tracing_span
from domain.utils.viewport import Viewport, visible_counts

# Configure logging
logger = logging.getLogger(__name__)


class VisualizationException(Exception):
    """Base exception for visualization operations."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        self.message = message
        self.error_code = error_code
        self.context = context
        super().__init__(message)


class GraphVisualizer:
    """Service for interactive graph visualization with D3.js and WebGL optimization.

    Implements interactive graph rendering with zoom, filtering, and progressive
    loading for large graphs (>50k nodes) using community-based clustering and
    viewport culling for performance optimization.
    """

    # Constants for visualization settings
    DEFAULT_VIEWPORT_SIZE = (1200, 800)  # Default viewport dimensions
    NODE_RENDER_LIMIT = 5000  # Switch to WebGL when node count exceeds this
    COMMUNITY_PREVIEW_LIMIT = 20  # Number of communities to show in overview

    # Visual style defaults
    DEFAULT_STYLES = {
        "node": {
            "radius": 8,
            "color": "#1f77b4",
            "stroke": "#fff",
            "strokeWidth": 1.5,
            "opacity": 0.8,
        },
        "edge": {"width": 1.5, "color": "#999", "opacity": 0.6, "arrow": True},
        "community": {"color": "#ff7f0e", "opacity": 0.3, "strokeWidth": 2},
        "highlighted": {
            "node": {"color": "#d62728", "radius": 10, "opacity": 1.0},
            "edge": {"color": "#d62728", "width": 3, "opacity": 1.0},
        },
    }

    def __init__(
        self,
        clustering_port: ClusteringPort,
        stream_port: Optional[GraphStreamPort] = None,
        tracer: Optional[TracingPort] = None,
        viewport_size: Tuple[int, int] = DEFAULT_VIEWPORT_SIZE,
        styles: Optional[Dict[str, Any]] = None,
    ):
        """Initialize GraphVisualizer with required dependencies.

        Args:
            clustering_port: Port for community detection and progressive loading
            stream_port: Optional port for real-time graph updates
            tracer: Optional port for performance monitoring
            viewport_size: Initial viewport dimensions as (width, height)
            styles: Optional custom visual styles for graph elements

        Raises:
            VisualizationException: When initialization fails
        """
        self.clustering = clustering_port
        self.stream = stream_port
        self.tracer = tracer
        self.viewport_size = viewport_size
        self.styles = styles or self.DEFAULT_STYLES.copy()

        # State for visualization
        self.visible_communities: Set[str] = set()
        self.visible_nodes: Set[str] = set()
        self.visible_edges: Set[Tuple[str, str]] = set()
        # Track element positions for viewport culling
        self.node_positions: Dict[str, Dict[str, float]] = {}
        self.community_positions: Dict[str, Dict[str, float]] = {}
        self.highlighted_paths: List[List[str]] = []
        self.viewport_bounds: Dict[str, float] = {
            "x_min": 0,
            "x_max": viewport_size[0],
            "y_min": 0,
            "y_max": viewport_size[1],
        }

        # Rendering mode (SVG or WebGL)
        self.use_webgl = False

        # Event handlers for UI callbacks
        self.event_handlers: Dict[str, List[Callable]] = {
            "node_click": [],
            "edge_click": [],
            "community_click": [],
            "viewport_change": [],
            "render_complete": [],
        }

        # Hooks for retrieving modality-specific assets for nodes
        self.asset_hooks: List[
            Callable[[List[str], str, str], Dict[str, Dict[str, Any]]]
        ] = []

        logger.info("GraphVisualizer initialized")

    def render_graph_overview(
        self, *, kg_id: str, tenant_id: str, algorithm: str = "louvain"
    ) -> Dict[str, Any]:
        """Render community-based graph overview for large graph visualization.

        Creates a high-level visualization of the graph using community detection
        to enable progressive loading and exploration of large graphs.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            algorithm: Community detection algorithm (default: "louvain")

        Returns:
            Dictionary with visualization data including:
            - communities: List of community metadata
            - layout: Community layout coordinates
            - styles: Visual styling information
            - stats: Graph statistics (node/edge counts, etc.)

        Raises:
            VisualizationException: When rendering fails
        """
        with tracing_span(
            self.tracer,
            name="visualization.render_overview",
            tenant_id=tenant_id,
            kg_id=kg_id,
            algorithm=algorithm,
        ):
            try:
                logger.info(
                    "Rendering graph overview for kg_id=%s, tenant_id=%s using %s algorithm",
                    kg_id,
                    tenant_id,
                    algorithm,
                )

                # Compute communities using clustering port
                communities = self.clustering.compute_communities(
                    kg_id=kg_id, tenant_id=tenant_id, algorithm=algorithm
                )

                if not communities:
                    logger.warning("No communities found for graph overview")
                    return self._create_empty_visualization_response(
                        kg_id=kg_id, tenant_id=tenant_id
                    )

                # Sort communities by size (descending)
                sorted_communities = sorted(
                    communities, key=lambda c: c.size, reverse=True
                )

                # Limit to preview count for initial rendering
                preview_communities = sorted_communities[: self.COMMUNITY_PREVIEW_LIMIT]

                # Generate 2D layout for communities using their embeddings
                community_layout = self._generate_community_layout(preview_communities)
                # Store positions for viewport culling
                self.community_positions.update(community_layout)

                # Calculate graph statistics
                total_nodes = sum(c.size for c in communities)
                total_communities = len(communities)

                # Determine rendering mode based on node count
                self.use_webgl = total_nodes > self.NODE_RENDER_LIMIT
                render_mode = "webgl" if self.use_webgl else "svg"

                logger.info(
                    f"Generated overview with {len(preview_communities)} communities "
                    f"out of {total_communities} total communities. "
                    f"Rendering mode: {render_mode}"
                )

                # Record metrics if tracer available
                if self.tracer:
                    self.tracer.record_metric(
                        name="visualization.community_count",
                        value=total_communities,
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )
                    self.tracer.record_metric(
                        name="visualization.total_nodes",
                        value=total_nodes,
                        tenant_id=tenant_id,
                        kg_id=kg_id,
                    )

                # Build response with visualization data
                response = {
                    "communities": [
                        {
                            "id": c.id,
                            "size": c.size,
                            "position": community_layout.get(c.id, {"x": 0, "y": 0}),
                            "tenant_id": c.tenant_id,
                        }
                        for c in preview_communities
                    ],
                    "layout": {
                        "type": "force",
                        "width": self.viewport_size[0],
                        "height": self.viewport_size[1],
                    },
                    "styles": self.styles,
                    "stats": {
                        "total_nodes": total_nodes,
                        "total_communities": total_communities,
                        "visible_communities": len(preview_communities),
                        "render_mode": render_mode,
                    },
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                }

                self._emit_event(
                    "render_complete",
                    {"kg_id": kg_id, "tenant_id": tenant_id, "type": "overview"},
                )

                if self.stream:
                    self.stream.send_event(
                        event=GraphStreamEvent(
                            event_type=GraphStreamEventType.RENDER_COMPLETED,
                            data={"type": "overview"},
                            timestamp=datetime.now(),
                            kg_id=kg_id,
                            tenant_id=tenant_id,
                        )
                    )

                return response

            except Exception as e:
                logger.error(
                    "Graph overview rendering failed: %s", str(e), exc_info=True
                )
                raise VisualizationException(
                    message=f"Graph overview rendering failed: {str(e)}",
                    error_code="VISUALIZATION_OVERVIEW_ERROR",
                    context={
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "algorithm": algorithm,
                    },
                ) from e

    def render_community_detail(
        self, *, community_id: str, tenant_id: str, include_neighbors: bool = False
    ) -> Dict[str, Any]:
        """Render detailed view of a specific community with on-demand loading.

        Retrieves and renders the detailed structure of a specific community
        to enable progressive exploration of large graphs.

        Args:
            community_id: Community identifier to render in detail
            tenant_id: Tenant identifier for multi-tenant isolation
            include_neighbors: Whether to include neighboring communities

        Returns:
            Dictionary with detailed visualization data including:
            - nodes: List of node data with positions and attributes
            - edges: List of edge data with source/target and attributes
            - layout: Layout configuration
            - styles: Visual styling information

        Raises:
            VisualizationException: When rendering fails
            ValueError: When community_id is not found
        """
        with tracing_span(
            self.tracer,
            name="visualization.render_community",
            tenant_id=tenant_id,
            community_id=community_id,
            include_neighbors=include_neighbors,
        ):
            try:
                logger.info(
                    "Rendering community detail for community_id=%s, tenant_id=%s, include_neighbors=%s",
                    community_id,
                    tenant_id,
                    include_neighbors,
                )

                # Get community subgraph from clustering port
                triples = self.clustering.get_community_subgraph(
                    community_id=community_id, tenant_id=tenant_id
                )

                if not triples:
                    logger.warning(f"No triples found for community {community_id}")
                    return self._create_empty_community_response(
                        community_id=community_id, tenant_id=tenant_id
                    )

                # Extract nodes and edges from triples
                nodes, edges = self._extract_nodes_and_edges_from_triples(triples)

                # Generate layout for nodes
                node_layout = self._generate_node_layout(nodes)

                # Retrieve modality assets if hooks are registered
                asset_data = self._fetch_node_assets(
                    list(nodes.keys()), community_id, tenant_id
                )
                # Store positions for viewport culling
                self.node_positions.update(node_layout)

                # Update visible elements
                self.visible_communities.add(community_id)
                self.visible_nodes.update(nodes.keys())
                self.visible_edges.update((e["source"], e["target"]) for e in edges)

                # Record metrics if tracer available
                if self.tracer:
                    self.tracer.record_metric(
                        name="visualization.community_node_count",
                        value=len(nodes),
                        tenant_id=tenant_id,
                        community_id=community_id,
                    )
                    self.tracer.record_metric(
                        name="visualization.community_edge_count",
                        value=len(edges),
                        tenant_id=tenant_id,
                        community_id=community_id,
                    )

                logger.info(
                    f"Rendered community {community_id} with {len(nodes)} nodes "
                    f"and {len(edges)} edges"
                )

                # Build response with visualization data
                response = {
                    "nodes": [
                        {
                            "id": node_id,
                            "position": node_layout.get(node_id, {"x": 0, "y": 0}),
                            "attributes": attributes,
                            "community_id": community_id,
                            "assets": asset_data.get(node_id, {}),
                        }
                        for node_id, attributes in nodes.items()
                    ],
                    "edges": [
                        {
                            "source": edge["source"],
                            "target": edge["target"],
                            "type": edge["type"],
                            "attributes": edge.get("attributes", {}),
                        }
                        for edge in edges
                    ],
                    "layout": {
                        "type": "force",
                        "width": self.viewport_size[0],
                        "height": self.viewport_size[1],
                        "charge": -120,
                        "linkDistance": 30,
                    },
                    "styles": self.styles,
                    "community_id": community_id,
                    "tenant_id": tenant_id,
                }

                self._emit_event(
                    "render_complete",
                    {
                        "community_id": community_id,
                        "tenant_id": tenant_id,
                        "type": "community",
                    },
                )

                if self.stream:
                    self.stream.send_event(
                        event=GraphStreamEvent(
                            event_type=GraphStreamEventType.RENDER_COMPLETED,
                            data={"type": "community", "community_id": community_id},
                            timestamp=datetime.now(),
                            kg_id=community_id,
                            tenant_id=tenant_id,
                        )
                    )

                return response

            except ValueError:
                raise  # Invalid community_id
            except Exception as e:
                logger.error(
                    "Community detail rendering failed: %s", str(e), exc_info=True
                )
                raise VisualizationException(
                    message=f"Community detail rendering failed: {str(e)}",
                    error_code="VISUALIZATION_COMMUNITY_ERROR",
                    context={
                        "community_id": community_id,
                        "tenant_id": tenant_id,
                        "include_neighbors": include_neighbors,
                    },
                ) from e

    def highlight_path(
        self,
        *,
        path_nodes: List[str],
        kg_id: str,
        tenant_id: str,
        highlight_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Highlight a path in the graph visualization for query results.

        Highlights a specific path in the graph to visualize query results
        or traversal paths with animated highlighting.

        Args:
            path_nodes: List of node IDs in the path to highlight
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            highlight_id: Optional identifier for the highlight (for updates)

        Returns:
            Dictionary with highlight information including:
            - highlight_id: Unique identifier for this highlight
            - path: List of node IDs in the highlighted path
            - styles: Visual styling for the highlight

        Raises:
            VisualizationException: When highlighting fails
            ValueError: When path is invalid
        """
        if not path_nodes:
            raise ValueError("Path cannot be empty")

        try:
            logger.info(
                f"Highlighting path with {len(path_nodes)} nodes for kg_id={kg_id}, "
                f"tenant_id={tenant_id}"
            )

            # Generate highlight ID if not provided
            if not highlight_id:
                highlight_id = f"highlight_{datetime.now().timestamp()}"

            # Store highlighted path
            self.highlighted_paths.append(path_nodes)

            # Create highlight styles
            highlight_styles = self.styles["highlighted"].copy()

            # Send real-time update if stream port available
            if self.stream:
                event = GraphStreamEvent(
                    event_type=GraphStreamEventType.PATH_HIGHLIGHTED,
                    data={
                        "highlight_id": highlight_id,
                        "path_nodes": path_nodes,
                        "styles": highlight_styles,
                    },
                    timestamp=datetime.now(),
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                )
                self.stream.send_event(event=event)

            # Build response
            response = {
                "highlight_id": highlight_id,
                "path": path_nodes,
                "styles": highlight_styles,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
            }

            return response

        except Exception as e:
            logger.error(f"Path highlighting failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Path highlighting failed: {str(e)}",
                error_code="VISUALIZATION_HIGHLIGHT_ERROR",
                context={
                    "path_length": len(path_nodes),
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                },
            ) from e

    def update_viewport(
        self,
        *,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        kg_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Update viewport bounds for culling and progressive loading.

        Updates the current viewport bounds to enable culling of off-screen
        elements and progressive loading of visible communities.

        Args:
            x_min: Minimum x-coordinate of viewport
            y_min: Minimum y-coordinate of viewport
            x_max: Maximum x-coordinate of viewport
            y_max: Maximum y-coordinate of viewport
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Dictionary with updated viewport information and visible elements

        Raises:
            VisualizationException: When viewport update fails
        """
        try:
            logger.debug(
                f"Updating viewport to ({x_min}, {y_min}) - ({x_max}, {y_max}) "
                f"for kg_id={kg_id}, tenant_id={tenant_id}"
            )

            # Update viewport bounds
            self.viewport_bounds = {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
            }

            # Determine visible elements based on viewport
            visible_elements = self._cull_elements_outside_viewport()

            # Trigger viewport change event handlers
            for handler in self.event_handlers.get("viewport_change", []):
                handler(self.viewport_bounds)

            # Build response
            response = {
                "viewport": self.viewport_bounds,
                "visible_elements": visible_elements,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
            }

            return response

        except Exception as e:
            logger.error(f"Viewport update failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Viewport update failed: {str(e)}",
                error_code="VISUALIZATION_VIEWPORT_ERROR",
                context={
                    "viewport": self.viewport_bounds,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                },
            ) from e

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register event handler for visualization interactions.

        Registers callback functions for various visualization events
        to enable interactive behavior.

        Args:
            event_type: Type of event to handle (node_click, edge_click, etc.)
            handler: Callback function to invoke when event occurs

        Raises:
            ValueError: When event_type is not supported
        """
        if event_type not in self.event_handlers:
            raise ValueError(f"Unsupported event type: {event_type}")

        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type} event")

    def register_asset_hook(
        self,
        hook: Callable[[List[str], str, str], Dict[str, Dict[str, Any]]],
    ) -> None:
        """Register a hook to provide asset metadata for nodes.

        The hook receives a list of node IDs, the community ID and tenant ID,
        and should return a mapping ``node_id -> asset_dict``. Asset dictionaries
        may include keys like ``image_thumbnail`` or ``audio_marker``.
        """

        self.asset_hooks.append(hook)
        logger.debug("Registered asset hook")

    def _fetch_node_assets(
        self, node_ids: List[str], community_id: str, tenant_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch asset metadata for nodes using registered hooks."""

        assets: Dict[str, Dict[str, Any]] = {}
        for hook in self.asset_hooks:
            try:
                data = hook(node_ids, community_id, tenant_id)
                for node_id, meta in data.items():
                    if node_id not in assets:
                        assets[node_id] = {}
                    assets[node_id].update(meta)
            except Exception:  # pragma: no cover - log and continue
                logger.exception("Error in asset hook")

        return assets

    def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Invoke registered handlers for a specific event."""
        for handler in self.event_handlers.get(event_type, []):
            try:
                handler(payload)
            except Exception:  # pragma: no cover - log and continue
                logger.exception("Error in %s handler", event_type)

    def generate_svg_thumbnail(
        self, *, community_id: str, tenant_id: str, width: int = 200, height: int = 200
    ) -> str:
        """Generate SVG thumbnail preview for UI framework node cards.

        Creates a small SVG representation of a community for use in
        UI components like node cards or tooltips.

        Args:
            community_id: Community identifier to render
            tenant_id: Tenant identifier for multi-tenant isolation
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels

        Returns:
            SVG markup as string for embedding in UI

        Raises:
            VisualizationException: When thumbnail generation fails
        """
        try:
            logger.debug(
                f"Generating SVG thumbnail for community_id={community_id}, "
                f"tenant_id={tenant_id}, size={width}x{height}"
            )

            # Get a sample of nodes from the community (limit to 20 for thumbnail)
            triples = self.clustering.get_community_subgraph(
                community_id=community_id, tenant_id=tenant_id
            )

            if not triples:
                # Return empty SVG if no data
                return self._create_empty_svg(width, height)

            # Extract nodes and edges, limiting to a small sample
            nodes, edges = self._extract_nodes_and_edges_from_triples(
                triples, max_elements=20
            )

            # Generate simple force layout for thumbnail
            node_layout = self._generate_node_layout(nodes, width=width, height=height)

            # Retrieve modality assets for nodes if hooks are registered
            asset_data = self._fetch_node_assets(
                list(nodes.keys()), community_id, tenant_id
            )
            for n_id, data in asset_data.items():
                nodes.setdefault(n_id, {}).setdefault("assets", {}).update(data)

            # Generate SVG markup
            svg = self._generate_svg_markup(nodes, edges, node_layout, width, height)

            return svg

        except Exception as e:
            logger.error(f"SVG thumbnail generation failed: {str(e)}", exc_info=True)
            # Return empty SVG on error
            return self._create_empty_svg(width, height)

    def _extract_nodes_and_edges_from_triples(
        self, triples: List[Triple], max_elements: Optional[int] = None
    ) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract nodes and edges from triples for visualization.

        Args:
            triples: List of Triple objects
            max_elements: Optional maximum number of elements to extract

        Returns:
            Tuple of (nodes_dict, edges_list) for visualization
        """
        nodes = {}
        edges = []

        # Limit triples if max_elements specified
        limited_triples = triples
        if max_elements and len(triples) > max_elements:
            limited_triples = triples[:max_elements]

        # Process triples to extract nodes and edges
        for triple in limited_triples:
            # Add subject node if not already present
            if triple.subject not in nodes:
                nodes[triple.subject] = {
                    "label": (
                        triple.subject.split("/")[-1]
                        if "/" in triple.subject
                        else triple.subject
                    ),
                    "type": "entity",
                }

            # Add object node if not already present
            if triple.object not in nodes:
                nodes[triple.object] = {
                    "label": (
                        triple.object.split("/")[-1]
                        if "/" in triple.object
                        else triple.object
                    ),
                    "type": "entity",
                }

            # Add edge
            edges.append(
                {
                    "source": triple.subject,
                    "target": triple.object,
                    "type": triple.predicate,
                    "attributes": {
                        "label": (
                            triple.predicate.split("/")[-1]
                            if "/" in triple.predicate
                            else triple.predicate
                        )
                    },
                }
            )

        return nodes, edges

    def _generate_community_layout(
        self, communities: List[Community]
    ) -> Dict[str, Dict[str, float]]:
        """Generate 2D layout for communities based on embeddings.

        Args:
            communities: List of Community objects

        Returns:
            Dictionary mapping community IDs to position coordinates
        """
        layout = {}

        try:
            # Use PCA to project community embeddings to 2D
            import numpy as np
            from sklearn.decomposition import PCA

            # Extract embeddings
            embeddings = np.array([c.centroid_embedding for c in communities])

            # Apply PCA if we have enough communities
            if len(communities) >= 2:
                pca = PCA(n_components=2)
                positions = pca.fit_transform(embeddings)

                # Scale positions to viewport
                x_scale = self.viewport_size[0] * 0.8
                y_scale = self.viewport_size[1] * 0.8
                x_offset = self.viewport_size[0] * 0.1
                y_offset = self.viewport_size[1] * 0.1

                # Normalize positions
                x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
                y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
                x_range = max(1e-10, x_max - x_min)  # Avoid division by zero
                y_range = max(1e-10, y_max - y_min)

                # Generate layout
                for i, community in enumerate(communities):
                    x = x_offset + (positions[i, 0] - x_min) / x_range * x_scale
                    y = y_offset + (positions[i, 1] - y_min) / y_range * y_scale
                    layout[community.id] = {"x": float(x), "y": float(y)}
            else:
                # For single community, place in center
                for community in communities:
                    layout[community.id] = {
                        "x": self.viewport_size[0] / 2,
                        "y": self.viewport_size[1] / 2,
                    }

        except ImportError:
            logger.warning("PCA dependencies not available, using random layout")
            # Fall back to random layout
            import random

            for community in communities:
                layout[community.id] = {
                    "x": random.uniform(0.1, 0.9) * self.viewport_size[0],
                    "y": random.uniform(0.1, 0.9) * self.viewport_size[1],
                }

        return layout

    def _generate_node_layout(
        self,
        nodes: Dict[str, Dict[str, Any]],
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Generate 2D layout for nodes using force-directed algorithm.

        Args:
            nodes: Dictionary of node data
            width: Optional width constraint
            height: Optional height constraint

        Returns:
            Dictionary mapping node IDs to position coordinates
        """
        layout = {}
        width = width or self.viewport_size[0]
        height = height or self.viewport_size[1]

        try:
            # Use NetworkX for layout if available
            import networkx as nx

            # Create graph
            G = nx.Graph()
            for node_id in nodes:
                G.add_node(node_id)

            # Apply spring layout
            pos = nx.spring_layout(G)

            # Scale positions to viewport
            x_scale = width * 0.8
            y_scale = height * 0.8
            x_offset = width * 0.1
            y_offset = height * 0.1

            # Generate layout
            for node_id, position in pos.items():
                x = x_offset + position[0] * x_scale
                y = y_offset + position[1] * y_scale
                layout[node_id] = {"x": float(x), "y": float(y)}

        except ImportError:
            logger.warning("NetworkX not available, using random layout")
            # Fall back to random layout
            import random

            for node_id in nodes:
                layout[node_id] = {
                    "x": random.uniform(0.1, 0.9) * width,
                    "y": random.uniform(0.1, 0.9) * height,
                }

        return layout

    def _cull_elements_outside_viewport(self) -> Dict[str, int]:
        """Cull elements outside current viewport for performance.

        Returns:
            Dictionary with counts of visible elements
        """
        viewport = Viewport(**self.viewport_bounds)
        node_positions = {
            node_id: self.node_positions.get(node_id)
            for node_id in self.visible_nodes
            if node_id in self.node_positions
        }
        community_positions = {
            c_id: self.community_positions.get(c_id)
            for c_id in self.visible_communities
            if c_id in self.community_positions
        }

        return visible_counts(
            node_positions=node_positions,
            edges=self.visible_edges,
            community_positions=community_positions,
            viewport=viewport,
        )

    def _create_empty_visualization_response(
        self, *, kg_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Create empty visualization response when no data available.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Empty visualization response dictionary
        """
        return {
            "communities": [],
            "layout": {
                "type": "force",
                "width": self.viewport_size[0],
                "height": self.viewport_size[1],
            },
            "styles": self.styles,
            "stats": {
                "total_nodes": 0,
                "total_communities": 0,
                "visible_communities": 0,
                "render_mode": "svg",
            },
            "kg_id": kg_id,
            "tenant_id": tenant_id,
            "empty": True,
        }

    def _create_empty_community_response(
        self, *, community_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Create empty community response when no data available.

        Args:
            community_id: Community identifier
            tenant_id: Tenant identifier

        Returns:
            Empty community response dictionary
        """
        return {
            "nodes": [],
            "edges": [],
            "layout": {
                "type": "force",
                "width": self.viewport_size[0],
                "height": self.viewport_size[1],
            },
            "styles": self.styles,
            "community_id": community_id,
            "tenant_id": tenant_id,
            "empty": True,
        }

    def _create_empty_svg(self, width: int, height: int) -> str:
        """Create empty SVG markup with placeholder text.

        Args:
            width: SVG width
            height: SVG height

        Returns:
            Empty SVG markup as string
        """
        return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#f8f9fa" />
            <text x="50%" y="50%" font-family="Arial" font-size="12" text-anchor="middle">
                No data available
            </text>
        </svg>"""

    def _generate_svg_markup(
        self,
        nodes: Dict[str, Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_layout: Dict[str, Dict[str, float]],
        width: int,
        height: int,
    ) -> str:
        """Generate SVG markup for graph visualization.

        Args:
            nodes: Dictionary of node data
            edges: List of edge data
            node_layout: Dictionary of node positions
            width: SVG width
            height: SVG height

        Returns:
            SVG markup as string
        """
        # Start SVG
        svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n'
        svg += '<rect width="100%" height="100%" fill="#ffffff" />\n'

        # Add edges
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]

            if source_id in node_layout and target_id in node_layout:
                source_pos = node_layout[source_id]
                target_pos = node_layout[target_id]

                # Get edge style
                edge_style = self.styles["edge"]

                # Draw line
                svg += f'<line x1="{source_pos["x"]}" y1="{source_pos["y"]}" '
                svg += f'x2="{target_pos["x"]}" y2="{target_pos["y"]}" '
                svg += f'stroke="{edge_style["color"]}" '
                svg += f'stroke-width="{edge_style["width"]}" '
                svg += f'opacity="{edge_style["opacity"]}" />\n'

                # Add arrow if directed
                if edge_style.get("arrow", False):
                    # Calculate arrow position and rotation
                    dx = target_pos["x"] - source_pos["x"]
                    dy = target_pos["y"] - source_pos["y"]
                    angle = math.atan2(dy, dx) * 180 / math.pi

                    # Draw arrow
                    arrow_x = target_pos["x"] - dx * 0.1
                    arrow_y = target_pos["y"] - dy * 0.1

                    svg += '<polygon points="0,-2 0,2 6,0" '
                    svg += (
                        f'transform="translate({arrow_x},{arrow_y}) rotate({angle})" '
                    )
                    svg += f'fill="{edge_style["color"]}" '
                    svg += f'opacity="{edge_style["opacity"]}" />\n'

        # Add nodes
        for node_id, attributes in nodes.items():
            if node_id in node_layout:
                pos = node_layout[node_id]

                # Get node style
                node_style = self.styles["node"]

                # Draw circle
                svg += f'<circle cx="{pos["x"]}" cy="{pos["y"]}" '
                svg += f'r="{node_style["radius"]}" '
                svg += f'fill="{node_style["color"]}" '
                svg += f'stroke="{node_style["stroke"]}" '
                svg += f'stroke-width="{node_style["strokeWidth"]}" '
                svg += f'opacity="{node_style["opacity"]}" />\n'

                assets = attributes.get("assets", {})
                if thumb := assets.get("image_thumbnail"):
                    svg += (
                        f'<image href="{thumb}" '
                        f'x="{pos["x"] - node_style["radius"]}" '
                        f'y="{pos["y"] - node_style["radius"]}" '
                        'width="16" height="16" />\n'
                    )
                if assets.get("audio_marker"):
                    svg += (
                        f'<circle cx="{pos["x"] + node_style["radius"] + 6}" '
                        f'cy="{pos["y"]}" r="4" fill="#ff6600" />\n'
                    )

                # Add label if space permits
                if width >= 100 and height >= 100:
                    label = attributes.get("label", node_id)
                    if len(label) > 10:
                        label = label[:8] + "..."

                    svg += f'<text x="{pos["x"]}" y="{pos["y"] + node_style["radius"] + 10}" '
                    svg += 'font-family="Arial" font-size="8" text-anchor="middle">'
                    svg += f"{label}</text>\n"

        # Close SVG
        svg += "</svg>"

        return svg
