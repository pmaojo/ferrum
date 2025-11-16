"""Use case for generating graph visualizations with various layout algorithms."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuthorizationServicePort,
    GraphVisualizationPort,
    TracingPort,
    VisualizationLayoutRepositoryPort,
)
from application.use_cases.dto import (
    GenerateGraphVisualizationRequestDTO,
    GraphVisualizationDTO,
    VisualizationEdgeDTO,
    VisualizationNodeDTO,
)
from domain.exceptions import VisualizationError


class GenerateGraphVisualizationUseCase:
    """Use case for generating graph visualizations with layout algorithms."""

    def __init__(
        self,
        graph_visualization_port: GraphVisualizationPort,
        layout_repository: VisualizationLayoutRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracing_port: TracingPort,
    ):
        """Initialize the use case with required ports.

        Args:
            graph_visualization_port: Port for graph visualization operations
            layout_repository: Repository for stored visualization layouts
            authorization_service: Port for authorization checks
            tracing_port: Port for observability tracing
        """
        self.graph_visualization_port = graph_visualization_port
        self.layout_repository = layout_repository
        self.authorization_service = authorization_service
        self.tracing_port = tracing_port

    def execute(
        self, request: GenerateGraphVisualizationRequestDTO
    ) -> GraphVisualizationDTO:
        """Execute graph visualization generation.

        Args:
            request: Request containing visualization parameters

        Returns:
            Graph visualization results

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph is not found
            VisualizationError: When visualization generation fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="generate_graph_visualization",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            layout_algorithm=request.layout_algorithm,
        ):
            # Validate input
            self._validate_request(request)

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # Prepare filters
                filters = self._prepare_filters(request)

                layout_data: Optional[Dict[str, Any]] = None
                if request.visualization_id:
                    layout_data = self.layout_repository.get_layout(
                        visualization_id=request.visualization_id,
                        tenant_id=request.tenant_id,
                    )

                if layout_data is None:
                    layout_data = self.graph_visualization_port.generate_layout(
                        kg_id=request.kg_id,
                        tenant_id=request.tenant_id,
                        algorithm=request.layout_algorithm,
                        node_limit=request.node_limit,
                        include_communities=request.include_communities,
                        filters=filters,
                    )

                # Convert to DTO
                visualization_dto = self._convert_layout_to_dto(
                    layout_data=layout_data, request=request
                )

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000
                visualization_dto.processing_time_ms = processing_time_ms

                # Record metrics
                self.tracing_port.record_metric(
                    name="visualization_generation_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                    layout_algorithm=request.layout_algorithm,
                )

                self.tracing_port.record_metric(
                    name="visualization_nodes_count",
                    value=visualization_dto.total_nodes,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                self.tracing_port.record_metric(
                    name="visualization_edges_count",
                    value=visualization_dto.total_edges,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                return visualization_dto

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise VisualizationError(
                    f"Graph visualization generation failed: {str(e)}"
                )

    def _validate_request(self, request: GenerateGraphVisualizationRequestDTO) -> None:
        """Validate the visualization request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: When validation fails
        """
        if not request.kg_id:
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )

        if not request.tenant_id:
            raise ValidationError(message="Tenant ID is required", field="tenant_id")

        if not request.user_id:
            raise ValidationError(message="User ID is required", field="user_id")

        # Validate layout algorithm
        supported_algorithms = [
            "force_directed",
            "circular",
            "hierarchical",
            "spring",
            "grid",
            "random",
            "fruchterman_reingold",
        ]

        if request.layout_algorithm not in supported_algorithms:
            raise ValidationError(
                message=(
                    f"Unsupported layout algorithm: {request.layout_algorithm}. "
                    f"Supported algorithms: {', '.join(supported_algorithms)}"
                ),
                field="layout_algorithm",
            )

        # Validate node limit
        if request.node_limit < 1:
            raise ValidationError(
                message="Node limit must be at least 1", field="node_limit"
            )

        if request.node_limit > 10000:
            raise ValidationError(
                message="Node limit cannot exceed 10000 to prevent performance issues",
                field="node_limit",
            )

        # Validate filter lists if provided
        if request.filter_by_node_types is not None:
            if not isinstance(request.filter_by_node_types, list):
                raise ValidationError(
                    message="Node type filters must be a list",
                    field="filter_by_node_types",
                )

        if request.filter_by_relationship_types is not None:
            if not isinstance(request.filter_by_relationship_types, list):
                raise ValidationError(
                    message="Relationship type filters must be a list",
                    field="filter_by_relationship_types",
                )

    def _prepare_filters(
        self, request: GenerateGraphVisualizationRequestDTO
    ) -> Dict[str, Any]:
        """Prepare filters for the visualization port.

        Args:
            request: Visualization request

        Returns:
            Dictionary of filters
        """
        filters = {}

        if request.filter_by_node_types:
            filters["node_types"] = request.filter_by_node_types

        if request.filter_by_relationship_types:
            filters["relationship_types"] = request.filter_by_relationship_types

        return filters

    def _convert_layout_to_dto(
        self, layout_data: Dict[str, Any], request: GenerateGraphVisualizationRequestDTO
    ) -> GraphVisualizationDTO:
        """Convert layout data to visualization DTO.

        Args:
            layout_data: Raw layout data from visualization port
            request: Original request

        Returns:
            GraphVisualizationDTO object
        """
        # Extract nodes and edges
        nodes = self._extract_visualization_nodes(
            layout_data.get("nodes", []), request.include_labels
        )

        edges = self._extract_visualization_edges(layout_data.get("edges", []))

        # Calculate viewport bounds
        viewport_bounds = self._calculate_viewport_bounds(nodes)

        return GraphVisualizationDTO(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            layout_algorithm=request.layout_algorithm,
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            viewport_bounds=viewport_bounds,
            analysis_timestamp=datetime.utcnow(),
            processing_time_ms=0.0,  # Will be set by caller
        )

    def _extract_visualization_nodes(
        self, nodes_data: List[Dict[str, Any]], include_labels: bool
    ) -> List[VisualizationNodeDTO]:
        """Extract visualization nodes from layout data.

        Args:
            nodes_data: Raw nodes data
            include_labels: Whether to include node labels

        Returns:
            List of VisualizationNodeDTO objects
        """
        nodes = []

        for node_data in nodes_data:
            # Extract basic properties
            node_id = node_data.get("id", "")
            node_type = node_data.get("type", "unknown")
            properties = node_data.get("properties", {})

            # Extract position
            x = float(node_data.get("x", 0.0))
            y = float(node_data.get("y", 0.0))

            # Extract visual properties
            size = float(node_data.get("size", 10.0))
            color = node_data.get("color", "#3498db")

            # Generate label
            label = ""
            if include_labels:
                label = self._generate_node_label(node_id, node_type, properties)

            # Extract community information if available
            community_id = node_data.get("community_id")

            node = VisualizationNodeDTO(
                id=node_id,
                label=label,
                node_type=node_type,
                x=x,
                y=y,
                size=size,
                color=color,
                properties=properties,
                community_id=community_id,
            )

            nodes.append(node)

        return nodes

    def _extract_visualization_edges(
        self, edges_data: List[Dict[str, Any]]
    ) -> List[VisualizationEdgeDTO]:
        """Extract visualization edges from layout data.

        Args:
            edges_data: Raw edges data

        Returns:
            List of VisualizationEdgeDTO objects
        """
        edges = []

        for edge_data in edges_data:
            # Extract basic properties
            edge_id = edge_data.get("id", "")
            source_id = edge_data.get("source", "")
            target_id = edge_data.get("target", "")
            relationship_type = edge_data.get("type", "unknown")
            properties = edge_data.get("properties", {})

            # Extract visual properties
            weight = edge_data.get("weight")
            color = edge_data.get("color", "#95a5a6")

            # Generate label
            label = self._generate_edge_label(relationship_type, properties)

            edge = VisualizationEdgeDTO(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                label=label,
                relationship_type=relationship_type,
                weight=weight,
                color=color,
                properties=properties,
            )

            edges.append(edge)

        return edges

    def _generate_node_label(
        self, node_id: str, node_type: str, properties: Dict[str, Any]
    ) -> str:
        """Generate a display label for a node.

        Args:
            node_id: Node identifier
            node_type: Node type
            properties: Node properties

        Returns:
            Generated label string
        """
        # Try common label properties
        label_candidates = ["name", "title", "label", "id"]

        for candidate in label_candidates:
            if candidate in properties:
                return str(properties[candidate])

        # Fallback to node type and truncated ID
        short_id = node_id[-8:] if len(node_id) > 8 else node_id
        return f"{node_type}:{short_id}"

    def _generate_edge_label(
        self, relationship_type: str, properties: Dict[str, Any]
    ) -> str:
        """Generate a display label for an edge.

        Args:
            relationship_type: Relationship type
            properties: Edge properties

        Returns:
            Generated label string
        """
        # Use relationship type as base label
        label = relationship_type.replace("_", " ").title()

        # Add weight if available
        if "weight" in properties:
            weight = properties["weight"]
            if isinstance(weight, (int, float)):
                label += f" ({weight:.2f})"

        return label

    def _calculate_viewport_bounds(
        self, nodes: List[VisualizationNodeDTO]
    ) -> Dict[str, float]:
        """Calculate viewport bounds for the visualization.

        Args:
            nodes: List of visualization nodes

        Returns:
            Dictionary with min_x, max_x, min_y, max_y bounds
        """
        if not nodes:
            return {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0}

        x_coords = [node.x for node in nodes]
        y_coords = [node.y for node in nodes]

        # Add padding (10% of range)
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)

        x_padding = max(x_range * 0.1, 10.0)  # Minimum 10 units padding
        y_padding = max(y_range * 0.1, 10.0)

        return {
            "min_x": min(x_coords) - x_padding,
            "max_x": max(x_coords) + x_padding,
            "min_y": min(y_coords) - y_padding,
            "max_y": max(y_coords) + y_padding,
        }
