"""Memgraph Lab visualization integration adapter.

This adapter connects the GraphVisualizer with Memgraph Lab interface,
providing real-time graph updates and query execution tracing.
"""

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from application.ports import GraphStreamPort, TracingPort
from domain.entities import GraphStreamEvent, GraphStreamEventType, Triple
from domain.graph_visualizer import GraphVisualizer, VisualizationException

# Configure logging
logger = logging.getLogger(__name__)


class MemgraphLabVisualizationAdapter:
    """Adapter for Memgraph Lab visualization integration.

    Connects GraphVisualizer with Memgraph Lab interface for real-time
    graph updates and query execution tracing.
    """

    def __init__(
        self,
        memgraph_lab_url: str,
        visualizer: GraphVisualizer,
        stream_adapter: Optional[GraphStreamPort] = None,
        tracer: Optional[TracingPort] = None,
        auto_refresh_interval_ms: int = 2000,
        enable_query_tracing: bool = True,
        http_client: Any = requests,
    ):
        """Initialize MemgraphLabVisualizationAdapter.

        Args:
            memgraph_lab_url: URL of Memgraph Lab instance
            visualizer: GraphVisualizer instance
            stream_adapter: Optional GraphStreamPort for real-time updates
            tracer: Optional TracingPort for performance monitoring
            auto_refresh_interval_ms: Interval for automatic refresh in milliseconds
            enable_query_tracing: Whether to enable query execution tracing

        Raises:
            ValueError: When memgraph_lab_url is invalid
            ConnectionError: When connection to Memgraph Lab fails
        """
        if not memgraph_lab_url:
            raise ValueError("memgraph_lab_url cannot be empty")

        self.memgraph_lab_url = memgraph_lab_url.rstrip("/")
        self.visualizer = visualizer
        self.stream_adapter = stream_adapter
        self.tracer = tracer
        self.http = http_client
        self.auto_refresh_interval_ms = auto_refresh_interval_ms
        self.enable_query_tracing = enable_query_tracing

        # Active visualizations by tenant and kg_id
        self.active_visualizations: Dict[str, Dict[str, str]] = (
            {}
        )  # tenant_id -> {kg_id -> view_id}

        # Query execution traces
        self.query_traces: Dict[str, List[Dict[str, Any]]] = (
            {}
        )  # query_id -> trace events

        # Test connection to Memgraph Lab
        self._test_connection()

        # Register event handlers with visualizer
        self._register_event_handlers()

        # Start background tasks
        if auto_refresh_interval_ms > 0:
            self._start_background_tasks()

        logger.info(
            f"MemgraphLabVisualizationAdapter initialized with URL: {memgraph_lab_url}"
        )

    def create_visualization(
        self,
        kg_id: str,
        tenant_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a new visualization in Memgraph Lab.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            name: Optional visualization name
            description: Optional visualization description

        Returns:
            View ID of the created visualization

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
            VisualizationException: When visualization creation fails
        """
        try:
            # Generate default name if not provided
            if not name:
                name = f"Graph {kg_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Create visualization in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views",
                json={
                    "name": name,
                    "description": description or f"Visualization for graph {kg_id}",
                    "metadata": {
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "created_at": datetime.now().isoformat(),
                    },
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            if "id" not in data:
                raise VisualizationException(
                    message="Invalid response from Memgraph Lab",
                    error_code="INVALID_RESPONSE",
                    context={"response": data},
                )

            view_id = data["id"]

            # Store in active visualizations
            if tenant_id not in self.active_visualizations:
                self.active_visualizations[tenant_id] = {}
            self.active_visualizations[tenant_id][kg_id] = view_id

            logger.info(
                f"Created visualization for kg_id={kg_id}, tenant_id={tenant_id}, view_id={view_id}"
            )

            # Initialize visualization with graph overview
            self._initialize_visualization(view_id, kg_id, tenant_id)

            return view_id

        except requests.RequestException as e:
            logger.error(f"Failed to create visualization: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e
        except Exception as e:
            logger.error(f"Visualization creation failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Visualization creation failed: {str(e)}",
                error_code="VISUALIZATION_CREATION_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def update_visualization(self, view_id: str, triples: List[Triple]) -> bool:
        """Update existing visualization with new triples.

        Args:
            view_id: View ID of the visualization
            triples: List of Triple objects to add

        Returns:
            True if update was successful, False otherwise

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
            VisualizationException: When visualization update fails
        """
        try:
            # Convert triples to Memgraph Lab format
            nodes, edges = self._convert_triples_to_memgraph_format(triples)

            # Update visualization in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views/{view_id}/data",
                json={
                    "nodes": nodes,
                    "relationships": edges,
                    "merge": True,  # Merge with existing data
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            logger.info(f"Updated visualization {view_id} with {len(triples)} triples")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to update visualization: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e
        except Exception as e:
            logger.error(f"Visualization update failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Visualization update failed: {str(e)}",
                error_code="VISUALIZATION_UPDATE_ERROR",
                context={"view_id": view_id},
            ) from e

    def highlight_path(
        self, view_id: str, path_nodes: List[str], highlight_id: Optional[str] = None
    ) -> str:
        """Highlight a path in the visualization.

        Args:
            view_id: View ID of the visualization
            path_nodes: List of node IDs in the path
            highlight_id: Optional identifier for the highlight

        Returns:
            Highlight ID

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
            VisualizationException: When path highlighting fails
        """
        try:
            # Generate highlight ID if not provided
            if not highlight_id:
                highlight_id = f"highlight_{uuid.uuid4()}"

            # Highlight path in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views/{view_id}/highlights",
                json={
                    "id": highlight_id,
                    "nodes": path_nodes,
                    "style": {"color": "#d62728", "size": 1.5, "opacity": 1.0},
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            logger.info(
                f"Highlighted path in visualization {view_id} with {len(path_nodes)} nodes"
            )
            return highlight_id

        except requests.RequestException as e:
            logger.error(f"Failed to highlight path: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e
        except Exception as e:
            logger.error(f"Path highlighting failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Path highlighting failed: {str(e)}",
                error_code="PATH_HIGHLIGHT_ERROR",
                context={"view_id": view_id},
            ) from e

    def start_query_trace(self, query: str, kg_id: str, tenant_id: str) -> str:
        """Start tracing a query execution.

        Args:
            query: Query string
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Query trace ID

        Raises:
            VisualizationException: When query tracing fails
        """
        if not self.enable_query_tracing:
            return ""

        try:
            # Generate query ID
            query_id = f"query_{uuid.uuid4()}"

            # Initialize trace
            self.query_traces[query_id] = [
                {
                    "event": "query_start",
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                }
            ]

            # Record metric if tracer available
            if self.tracer:
                self.tracer.record_metric(
                    name="query_trace_started",
                    value=1.0,
                    tenant_id=tenant_id,
                    kg_id=kg_id,
                )

            logger.debug(
                f"Started query trace {query_id} for kg_id={kg_id}, tenant_id={tenant_id}"
            )
            return query_id

        except Exception as e:
            logger.error(f"Query trace start failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Query trace start failed: {str(e)}",
                error_code="QUERY_TRACE_START_ERROR",
                context={"kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def add_trace_event(
        self, query_id: str, event_type: str, data: Dict[str, Any]
    ) -> None:
        """Add event to query execution trace.

        Args:
            query_id: Query trace ID
            event_type: Event type (e.g., "node_visit", "edge_traverse")
            data: Event data

        Raises:
            ValueError: When query_id is invalid
            VisualizationException: When trace event addition fails
        """
        if not self.enable_query_tracing:
            return

        if query_id not in self.query_traces:
            raise ValueError(f"Invalid query_id: {query_id}")

        try:
            # Add event to trace
            self.query_traces[query_id].append(
                {
                    "event": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                }
            )

            logger.debug(f"Added {event_type} event to query trace {query_id}")

        except Exception as e:
            logger.error(f"Trace event addition failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Trace event addition failed: {str(e)}",
                error_code="TRACE_EVENT_ERROR",
                context={"query_id": query_id, "event_type": event_type},
            ) from e

    def end_query_trace(
        self,
        query_id: str,
        result: Optional[Dict[str, Any]] = None,
        view_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """End query execution trace and visualize it.

        Args:
            query_id: Query trace ID
            result: Optional query result
            view_id: Optional view ID for visualization

        Returns:
            Query trace summary

        Raises:
            ValueError: When query_id is invalid
            VisualizationException: When query trace end fails
        """
        if not self.enable_query_tracing:
            return {"query_id": query_id, "events": 0}

        if query_id not in self.query_traces:
            raise ValueError(f"Invalid query_id: {query_id}")

        try:
            # Add end event to trace
            self.query_traces[query_id].append(
                {
                    "event": "query_end",
                    "timestamp": datetime.now().isoformat(),
                    "result": result,
                }
            )

            # Calculate execution time
            start_time = datetime.fromisoformat(
                self.query_traces[query_id][0]["timestamp"]
            )
            end_time = datetime.fromisoformat(
                self.query_traces[query_id][-1]["timestamp"]
            )
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create trace summary
            trace_summary = {
                "query_id": query_id,
                "events": len(self.query_traces[query_id]),
                "execution_time_ms": execution_time_ms,
                "kg_id": self.query_traces[query_id][0].get("kg_id"),
                "tenant_id": self.query_traces[query_id][0].get("tenant_id"),
            }

            # Visualize trace if view_id provided
            if view_id:
                self._visualize_query_trace(query_id, view_id)

            # Record metric if tracer available
            if self.tracer:
                self.tracer.record_metric(
                    name="query_execution_time_ms",
                    value=execution_time_ms,
                    tenant_id=trace_summary["tenant_id"],
                    kg_id=trace_summary["kg_id"],
                    events=trace_summary["events"],
                )

            logger.info(
                f"Ended query trace {query_id} with {trace_summary['events']} events, "
                f"execution time: {execution_time_ms:.2f}ms"
            )

            return trace_summary

        except Exception as e:
            logger.error(f"Query trace end failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Query trace end failed: {str(e)}",
                error_code="QUERY_TRACE_END_ERROR",
                context={"query_id": query_id},
            ) from e

    def get_visualization_url(self, view_id: str) -> str:
        """Get URL for accessing the visualization in Memgraph Lab.

        Args:
            view_id: View ID of the visualization

        Returns:
            URL for accessing the visualization
        """
        return f"{self.memgraph_lab_url}/view/{view_id}"

    def _test_connection(self) -> None:
        """Test connection to Memgraph Lab.

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
        """
        try:
            response = self.http.get(f"{self.memgraph_lab_url}/api/status")
            response.raise_for_status()

            # Check if response indicates Memgraph Lab is ready
            data = response.json()
            if data.get("status") != "ok":
                raise ConnectionError(f"Memgraph Lab is not ready: {data}")

            logger.info("Successfully connected to Memgraph Lab")

        except requests.RequestException as e:
            logger.error(f"Failed to connect to Memgraph Lab: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e

    def _register_event_handlers(self) -> None:
        """Register event handlers with GraphVisualizer."""
        # Register handlers for real-time updates
        self.visualizer.register_event_handler("node_click", self._handle_node_click)
        self.visualizer.register_event_handler("edge_click", self._handle_edge_click)
        self.visualizer.register_event_handler(
            "render_complete", self._handle_render_complete
        )

    def _start_background_tasks(self) -> None:
        """Start background tasks for automatic refresh."""
        # Start refresh thread
        refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        refresh_thread.start()

    def _auto_refresh_loop(self) -> None:
        """Background loop for automatic visualization refresh."""
        while True:
            try:
                # Refresh active visualizations
                for tenant_id, kg_visualizations in self.active_visualizations.items():
                    for kg_id, view_id in kg_visualizations.items():
                        try:
                            self._refresh_visualization(view_id, kg_id, tenant_id)
                        except Exception as e:
                            logger.error(
                                f"Failed to refresh visualization {view_id}: {str(e)}",
                                exc_info=True,
                            )

                # Sleep for refresh interval
                time.sleep(self.auto_refresh_interval_ms / 1000)

            except Exception as e:
                logger.error(f"Error in refresh loop: {str(e)}", exc_info=True)
                time.sleep(5)  # Longer sleep on error

    def _initialize_visualization(
        self, view_id: str, kg_id: str, tenant_id: str
    ) -> None:
        """Initialize visualization with graph overview.

        Args:
            view_id: View ID of the visualization
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Raises:
            VisualizationException: When initialization fails
        """
        try:
            # Get graph overview from visualizer
            overview = self.visualizer.render_graph_overview(
                kg_id=kg_id, tenant_id=tenant_id
            )

            # Convert to Memgraph Lab format
            nodes = []
            for community in overview.get("communities", []):
                nodes.append(
                    {
                        "id": community["id"],
                        "labels": ["Community"],
                        "properties": {
                            "size": community["size"],
                            "tenant_id": community["tenant_id"],
                        },
                        "position": community["position"],
                    }
                )

            # Initialize visualization in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views/{view_id}/data",
                json={
                    "nodes": nodes,
                    "relationships": [],
                    "merge": False,  # Replace existing data
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            # Set visualization style
            self._set_visualization_style(view_id, overview.get("styles", {}))

            logger.info(
                f"Initialized visualization {view_id} with {len(nodes)} communities"
            )

        except Exception as e:
            logger.error(
                f"Visualization initialization failed: {str(e)}", exc_info=True
            )
            raise VisualizationException(
                message=f"Visualization initialization failed: {str(e)}",
                error_code="VISUALIZATION_INIT_ERROR",
                context={"view_id": view_id, "kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def _refresh_visualization(self, view_id: str, kg_id: str, tenant_id: str) -> None:
        """Refresh visualization with latest data.

        Args:
            view_id: View ID of the visualization
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Raises:
            VisualizationException: When refresh fails
        """
        try:
            # Check if there are any pending updates
            # This would typically involve checking for new events
            # or changes since the last refresh

            # For now, just log the refresh attempt
            logger.debug(
                f"Refreshing visualization {view_id} for kg_id={kg_id}, tenant_id={tenant_id}"
            )

        except Exception as e:
            logger.error(f"Visualization refresh failed: {str(e)}", exc_info=True)
            raise VisualizationException(
                message=f"Visualization refresh failed: {str(e)}",
                error_code="VISUALIZATION_REFRESH_ERROR",
                context={"view_id": view_id, "kg_id": kg_id, "tenant_id": tenant_id},
            ) from e

    def _set_visualization_style(self, view_id: str, styles: Dict[str, Any]) -> None:
        """Set visualization style in Memgraph Lab.

        Args:
            view_id: View ID of the visualization
            styles: Style configuration

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
        """
        try:
            # Convert styles to Memgraph Lab format
            memgraph_styles = {
                "node": {
                    "Community": {
                        "color": styles.get("community", {}).get("color", "#ff7f0e"),
                        "size": styles.get("node", {}).get("radius", 8) * 1.5,
                        "opacity": styles.get("community", {}).get("opacity", 0.3),
                    },
                    "Entity": {
                        "color": styles.get("node", {}).get("color", "#1f77b4"),
                        "size": styles.get("node", {}).get("radius", 8),
                        "opacity": styles.get("node", {}).get("opacity", 0.8),
                    },
                },
                "relationship": {
                    "*": {
                        "color": styles.get("edge", {}).get("color", "#999"),
                        "width": styles.get("edge", {}).get("width", 1.5),
                        "opacity": styles.get("edge", {}).get("opacity", 0.6),
                        "arrow": styles.get("edge", {}).get("arrow", True),
                    }
                },
            }

            # Set style in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views/{view_id}/style",
                json=memgraph_styles,
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            logger.debug(f"Set style for visualization {view_id}")

        except requests.RequestException as e:
            logger.error(f"Failed to set visualization style: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e

    def _convert_triples_to_memgraph_format(
        self, triples: List[Triple]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Convert triples to Memgraph Lab format.

        Args:
            triples: List of Triple objects

        Returns:
            Tuple of (nodes, relationships) in Memgraph Lab format
        """
        nodes = {}
        relationships = []

        for triple in triples:
            # Process subject node
            if triple.subject not in nodes:
                nodes[triple.subject] = {
                    "id": triple.subject,
                    "labels": ["Entity"],
                    "properties": {
                        "label": (
                            triple.subject.split("/")[-1]
                            if "/" in triple.subject
                            else triple.subject
                        ),
                        "tenant_id": triple.tenant_id,
                    },
                }

            # Process object node
            if triple.object not in nodes:
                nodes[triple.object] = {
                    "id": triple.object,
                    "labels": ["Entity"],
                    "properties": {
                        "label": (
                            triple.object.split("/")[-1]
                            if "/" in triple.object
                            else triple.object
                        ),
                        "tenant_id": triple.tenant_id,
                    },
                }

            # Process relationship
            relationship_id = f"{triple.subject}_{triple.predicate}_{triple.object}"
            relationships.append(
                {
                    "id": relationship_id,
                    "type": (
                        triple.predicate.split("/")[-1]
                        if "/" in triple.predicate
                        else triple.predicate
                    ),
                    "startNode": triple.subject,
                    "endNode": triple.object,
                    "properties": {"tenant_id": triple.tenant_id},
                }
            )

        return list(nodes.values()), relationships

    def _visualize_query_trace(self, query_id: str, view_id: str) -> None:
        """Visualize query execution trace in Memgraph Lab.

        Args:
            query_id: Query trace ID
            view_id: View ID of the visualization

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
            VisualizationException: When trace visualization fails
        """
        if query_id not in self.query_traces:
            return

        try:
            # Extract path from trace events
            path_nodes = []
            for event in self.query_traces[query_id]:
                if event["event"] == "node_visit" and "node_id" in event.get(
                    "data", {}
                ):
                    path_nodes.append(event["data"]["node_id"])

            if not path_nodes:
                return

            # Highlight path in visualization
            self.highlight_path(
                view_id=view_id, path_nodes=path_nodes, highlight_id=f"trace_{query_id}"
            )

            logger.info(
                f"Visualized query trace {query_id} in view {view_id} with {len(path_nodes)} nodes"
            )

        except Exception as e:
            logger.error(f"Query trace visualization failed: {str(e)}", exc_info=True)
            # Don't raise exception, just log error

    def _handle_node_click(self, event_data: Dict[str, Any]) -> None:
        """Handle node click event from GraphVisualizer.

        Args:
            event_data: Event data
        """
        node_id = event_data.get("id")
        if not node_id:
            return

        # Check if this is a community node
        if event_data.get("type") == "community":
            # Load community detail
            kg_id = event_data.get("kg_id")
            tenant_id = event_data.get("tenant_id")

            if not kg_id or not tenant_id:
                return

            # Get view ID for this kg_id and tenant_id
            view_id = self.active_visualizations.get(tenant_id, {}).get(kg_id)
            if not view_id:
                return

            try:
                # Get community detail from visualizer
                detail = self.visualizer.render_community_detail(
                    community_id=node_id, tenant_id=tenant_id
                )

                # Update visualization with community detail
                self._update_visualization_with_community(view_id, detail)

            except Exception as e:
                logger.error(
                    f"Failed to handle community click: {str(e)}", exc_info=True
                )

    def _handle_edge_click(self, event_data: Dict[str, Any]) -> None:
        """Handle edge click event from GraphVisualizer.

        Args:
            event_data: Event data
        """
        source = event_data.get("source")
        target = event_data.get("target")
        kg_id = event_data.get("kg_id")
        tenant_id = event_data.get("tenant_id")

        if not (source and target and kg_id and tenant_id):
            return

        view_id = self.active_visualizations.get(tenant_id, {}).get(kg_id)
        if not view_id:
            return

        try:
            self.highlight_path(view_id=view_id, path_nodes=[source, target])
        except Exception as e:  # pragma: no cover - log and continue
            logger.error(f"Failed to handle edge click: {str(e)}", exc_info=True)

    def _handle_render_complete(self, event_data: Dict[str, Any]) -> None:
        """Handle render complete event from GraphVisualizer.

        Args:
            event_data: Event data
        """
        if not self.stream_adapter:
            return

        kg_id = event_data.get("kg_id") or event_data.get("community_id")
        tenant_id = event_data.get("tenant_id")
        if not (kg_id and tenant_id):
            return

        try:
            event = GraphStreamEvent(
                event_type=GraphStreamEventType.RENDER_COMPLETED,
                data=event_data,
                timestamp=datetime.now(),
                kg_id=kg_id,
                tenant_id=tenant_id,
            )
            self.stream_adapter.send_event(event=event)
        except Exception as e:  # pragma: no cover - log and continue
            logger.error(f"Failed to handle render completion: {str(e)}", exc_info=True)

    def _update_visualization_with_community(
        self, view_id: str, community_detail: Dict[str, Any]
    ) -> None:
        """Update visualization with community detail.

        Args:
            view_id: View ID of the visualization
            community_detail: Community detail from visualizer

        Raises:
            ConnectionError: When connection to Memgraph Lab fails
        """
        try:
            # Convert nodes and edges to Memgraph Lab format
            nodes = []
            for node in community_detail.get("nodes", []):
                nodes.append(
                    {
                        "id": node["id"],
                        "labels": ["Entity"],
                        "properties": {
                            "label": node.get("attributes", {}).get(
                                "label", node["id"]
                            ),
                            "community_id": community_detail.get("community_id"),
                            "tenant_id": community_detail.get("tenant_id"),
                        },
                        "position": node.get("position", {}),
                    }
                )

            relationships = []
            for edge in community_detail.get("edges", []):
                relationship_id = (
                    f"{edge['source']}_{edge.get('type', 'related')}_{edge['target']}"
                )
                relationships.append(
                    {
                        "id": relationship_id,
                        "type": edge.get("type", "related"),
                        "startNode": edge["source"],
                        "endNode": edge["target"],
                        "properties": {
                            "label": edge.get("attributes", {}).get(
                                "label", edge.get("type", "related")
                            ),
                            "community_id": community_detail.get("community_id"),
                            "tenant_id": community_detail.get("tenant_id"),
                        },
                    }
                )

            # Update visualization in Memgraph Lab
            response = self.http.post(
                f"{self.memgraph_lab_url}/api/views/{view_id}/data",
                json={
                    "nodes": nodes,
                    "relationships": relationships,
                    "merge": True,  # Merge with existing data
                },
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            logger.info(
                f"Updated visualization {view_id} with community detail: "
                f"{len(nodes)} nodes, {len(relationships)} relationships"
            )

        except requests.RequestException as e:
            logger.error(
                f"Failed to update visualization with community: {str(e)}",
                exc_info=True,
            )
            raise ConnectionError(f"Failed to connect to Memgraph Lab: {str(e)}") from e
