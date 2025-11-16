"""Use case for finding shortest paths between nodes in knowledge graphs."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import AuthorizationServicePort, GraphAnalyticsPort, TracingPort
from application.use_cases.dto import (
    FindShortestPathRequestDTO,
    PathEdgeDTO,
    PathNodeDTO,
    ShortestPathDTO,
)
from domain.exceptions import AnalyticsError


class FindShortestPathUseCase:
    """Use case for finding shortest paths between nodes in knowledge graphs."""

    def __init__(
        self,
        graph_analytics_port: GraphAnalyticsPort,
        authorization_service: AuthorizationServicePort,
        tracing_port: TracingPort,
    ):
        """Initialize the use case with required ports.

        Args:
            graph_analytics_port: Port for graph analytics operations
            authorization_service: Port for authorization checks
            tracing_port: Port for observability tracing
        """
        self.graph_analytics_port = graph_analytics_port
        self.authorization_service = authorization_service
        self.tracing_port = tracing_port

    def execute(self, request: FindShortestPathRequestDTO) -> Optional[ShortestPathDTO]:
        """Execute shortest path finding.

        Args:
            request: Request containing path finding parameters

        Returns:
            Shortest path result or None if no path exists

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph or nodes are not found
            AnalyticsError: When path finding fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="find_shortest_path",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            source_node=request.source_node_id,
            target_node=request.target_node_id,
        ):
            # Validate input
            self._validate_request(request)

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # Find shortest path
                path_data = self.graph_analytics_port.find_shortest_path(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    source_node_id=request.source_node_id,
                    target_node_id=request.target_node_id,
                    max_depth=request.max_depth,
                    weight_property=request.weight_property,
                )

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.tracing_port.record_metric(
                    name="shortest_path_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                if path_data is None:
                    # No path found
                    self.tracing_port.record_metric(
                        name="shortest_path_found",
                        value=0,
                        tenant_id=request.tenant_id,
                        kg_id=request.kg_id,
                    )
                    return None

                # Convert to DTO
                path_dto = self._convert_path_to_dto(
                    path_data=path_data,
                    request=request,
                    processing_time_ms=processing_time_ms,
                )

                # Record success metrics
                self.tracing_port.record_metric(
                    name="shortest_path_found",
                    value=1,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                self.tracing_port.record_metric(
                    name="shortest_path_length",
                    value=path_dto.path_length,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                return path_dto

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise AnalyticsError(f"Shortest path finding failed: {str(e)}")

    def _validate_request(self, request: FindShortestPathRequestDTO) -> None:
        """Validate the shortest path request.

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

        if not request.source_node_id:
            raise ValidationError(
                message="Source node ID is required", field="source_node_id"
            )

        if not request.target_node_id:
            raise ValidationError(
                message="Target node ID is required", field="target_node_id"
            )

        if request.source_node_id == request.target_node_id:
            raise ValidationError(
                message="Source and target nodes cannot be the same",
                field="target_node_id",
            )

        if request.max_depth < 1:
            raise ValidationError(
                message="Maximum depth must be at least 1", field="max_depth"
            )

        if request.max_depth > 50:
            raise ValidationError(
                message="Maximum depth cannot exceed 50 to prevent performance issues",
                field="max_depth",
            )

    def _convert_path_to_dto(
        self,
        path_data: Dict[str, Any],
        request: FindShortestPathRequestDTO,
        processing_time_ms: float,
    ) -> ShortestPathDTO:
        """Convert path data to DTO.

        Args:
            path_data: Raw path data from analytics port
            request: Original request
            processing_time_ms: Processing time in milliseconds

        Returns:
            ShortestPathDTO object
        """
        # Extract nodes and edges from path data
        nodes = self._extract_path_nodes(path_data.get("nodes", []))
        edges = self._extract_path_edges(path_data.get("edges", []))

        # Calculate path length and total weight
        path_length = len(nodes) - 1 if len(nodes) > 1 else 0
        total_weight = path_data.get("total_weight")

        return ShortestPathDTO(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            source_node_id=request.source_node_id,
            target_node_id=request.target_node_id,
            path_length=path_length,
            total_weight=total_weight,
            nodes=nodes,
            edges=edges,
            analysis_timestamp=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
        )

    def _extract_path_nodes(
        self, nodes_data: List[Dict[str, Any]]
    ) -> List[PathNodeDTO]:
        """Extract path nodes from raw data.

        Args:
            nodes_data: Raw nodes data

        Returns:
            List of PathNodeDTO objects
        """
        nodes = []

        for node_data in nodes_data:
            node = PathNodeDTO(
                node_id=node_data.get("id", ""),
                node_type=node_data.get("type", "unknown"),
                properties=node_data.get("properties", {}),
            )
            nodes.append(node)

        return nodes

    def _extract_path_edges(
        self, edges_data: List[Dict[str, Any]]
    ) -> List[PathEdgeDTO]:
        """Extract path edges from raw data.

        Args:
            edges_data: Raw edges data

        Returns:
            List of PathEdgeDTO objects
        """
        edges = []

        for edge_data in edges_data:
            edge = PathEdgeDTO(
                source_node_id=edge_data.get("source", ""),
                target_node_id=edge_data.get("target", ""),
                relationship_type=edge_data.get("type", "unknown"),
                properties=edge_data.get("properties", {}),
                weight=edge_data.get("weight"),
            )
            edges.append(edge)

        return edges
