"""Use case for calculating node centrality measures in knowledge graphs."""

import time
from datetime import datetime
from typing import Dict, List

from application.exceptions import NotFoundError, ValidationError
from application.ports import AuthorizationServicePort, GraphAnalyticsPort, TracingPort
from application.use_cases.dto import (
    CentralityAnalysisDTO,
    GetNodeCentralityRequestDTO,
    NodeCentralityDTO,
)
from domain.exceptions import AnalyticsError


class GetNodeCentralityUseCase:
    """Use case for calculating various centrality measures for nodes in knowledge graphs."""

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

    def execute(self, request: GetNodeCentralityRequestDTO) -> CentralityAnalysisDTO:
        """Execute node centrality calculation.

        Args:
            request: Request containing centrality calculation parameters

        Returns:
            Centrality analysis results

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph is not found
            AnalyticsError: When centrality calculation fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="get_node_centrality",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            centrality_types=",".join(request.centrality_types or []),
        ):
            # Validate input
            self._validate_request(request)

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # Calculate centrality measures
                centrality_data = self.graph_analytics_port.calculate_centrality(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    centrality_types=request.centrality_types,
                    node_ids=request.node_ids,
                )

                # Convert to DTOs and apply limit
                node_centralities = self._convert_centrality_to_dtos(
                    centrality_data=centrality_data,
                    centrality_types=request.centrality_types,
                    limit=request.limit,
                )

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.tracing_port.record_metric(
                    name="centrality_calculation_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                self.tracing_port.record_metric(
                    name="nodes_centrality_calculated",
                    value=len(node_centralities),
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                return CentralityAnalysisDTO(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    centrality_types=request.centrality_types,
                    node_centralities=node_centralities,
                    total_nodes_analyzed=len(node_centralities),
                    analysis_timestamp=datetime.utcnow(),
                    processing_time_ms=processing_time_ms,
                )

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise AnalyticsError(f"Node centrality calculation failed: {str(e)}")

    def _validate_request(self, request: GetNodeCentralityRequestDTO) -> None:
        """Validate the centrality calculation request.

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

        # Set default centrality types if not provided
        if not request.centrality_types:
            request.centrality_types = ["degree", "betweenness", "closeness"]

        # Validate centrality types
        supported_types = [
            "betweenness",
            "closeness",
            "degree",
            "eigenvector",
            "pagerank",
        ]

        for centrality_type in request.centrality_types:
            if centrality_type not in supported_types:
                raise ValidationError(
                    message=(
                        f"Unsupported centrality type: {centrality_type}. "
                        f"Supported types: {', '.join(supported_types)}"
                    ),
                    field="centrality_types",
                )

        # Validate limit
        if request.limit < 1:
            raise ValidationError(message="Limit must be at least 1", field="limit")

        if request.limit > 10000:
            raise ValidationError(
                message="Limit cannot exceed 10000 to prevent performance issues",
                field="limit",
            )

        # Validate node_ids if provided
        if request.node_ids is not None:
            if not isinstance(request.node_ids, list):
                raise ValidationError(
                    message="Node IDs must be a list", field="node_ids"
                )

            if len(request.node_ids) == 0:
                raise ValidationError(
                    message="Node IDs list cannot be empty when provided",
                    field="node_ids",
                )

            if len(request.node_ids) > 1000:
                raise ValidationError(
                    message="Cannot specify more than 1000 node IDs", field="node_ids"
                )

    def _convert_centrality_to_dtos(
        self,
        centrality_data: Dict[str, Dict[str, float]],
        centrality_types: List[str],
        limit: int,
    ) -> List[NodeCentralityDTO]:
        """Convert centrality data to DTOs.

        Args:
            centrality_data: Dictionary mapping node IDs to centrality measures
            centrality_types: List of centrality types that were calculated
            limit: Maximum number of nodes to return

        Returns:
            List of NodeCentralityDTO objects, sorted by highest centrality
        """
        node_centralities = []

        for node_id, centrality_measures in centrality_data.items():
            # Extract node type from centrality data or use default
            node_type = centrality_measures.get("node_type", "unknown")

            # Create DTO with centrality measures
            node_centrality = NodeCentralityDTO(
                node_id=node_id,
                node_type=node_type,
                betweenness_centrality=centrality_measures.get("betweenness"),
                closeness_centrality=centrality_measures.get("closeness"),
                degree_centrality=centrality_measures.get("degree"),
                eigenvector_centrality=centrality_measures.get("eigenvector"),
                pagerank=centrality_measures.get("pagerank"),
            )

            node_centralities.append(node_centrality)

        # Sort by the first centrality type in descending order
        if centrality_types and node_centralities:
            primary_centrality = centrality_types[0]
            node_centralities.sort(
                key=lambda x: self._get_centrality_value(x, primary_centrality),
                reverse=True,
            )

        # Apply limit
        return node_centralities[:limit]

    def _get_centrality_value(
        self, node_centrality: NodeCentralityDTO, centrality_type: str
    ) -> float:
        """Get centrality value for sorting.

        Args:
            node_centrality: Node centrality DTO
            centrality_type: Type of centrality to get

        Returns:
            Centrality value or 0.0 if not available
        """
        centrality_map = {
            "betweenness": node_centrality.betweenness_centrality,
            "closeness": node_centrality.closeness_centrality,
            "degree": node_centrality.degree_centrality,
            "eigenvector": node_centrality.eigenvector_centrality,
            "pagerank": node_centrality.pagerank,
        }

        value = centrality_map.get(centrality_type)
        return value if value is not None else 0.0
