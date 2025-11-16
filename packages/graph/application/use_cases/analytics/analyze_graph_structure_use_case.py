"""Use case for analyzing graph structure and calculating metrics."""

import time
from datetime import datetime
from typing import Dict, List, Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import AuthorizationServicePort, GraphAnalyticsPort, TracingPort
from application.use_cases.dto import (
    AnalyzeGraphStructureRequestDTO,
    GraphMetricDTO,
    GraphStructureAnalysisDTO,
)
from application.validators import RequestValidator
from domain.exceptions import AnalyticsError


class AnalyzeGraphStructureUseCase:
    """Use case for analyzing graph structure and calculating various metrics."""

    def __init__(
        self,
        graph_analytics_port: GraphAnalyticsPort,
        authorization_service: AuthorizationServicePort,
        tracing_port: TracingPort,
        request_validator: Optional[RequestValidator] = None,
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
        self.request_validator = request_validator or RequestValidator()

    def execute(
        self, request: AnalyzeGraphStructureRequestDTO
    ) -> GraphStructureAnalysisDTO:
        """Execute graph structure analysis.

        Args:
            request: Request containing analysis parameters

        Returns:
            Graph structure analysis results

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph is not found
            AnalyticsError: When analysis fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="analyze_graph_structure",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
        ):
            # Validate input
            self.request_validator.validate_ids(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                kg_id=request.kg_id,
            )

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # Perform graph structure analysis
                metrics_data = self.graph_analytics_port.analyze_structure(
                    kg_id=request.kg_id, tenant_id=request.tenant_id
                )

                # Convert to DTOs
                metrics = self._convert_metrics_to_dtos(metrics_data)

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.tracing_port.record_metric(
                    name="graph_structure_analysis_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                )

                return GraphStructureAnalysisDTO(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    metrics=metrics,
                    analysis_timestamp=datetime.utcnow(),
                    processing_time_ms=processing_time_ms,
                )

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise AnalyticsError(f"Graph structure analysis failed: {str(e)}")

    def _convert_metrics_to_dtos(
        self, metrics_data: Dict[str, float]
    ) -> List[GraphMetricDTO]:
        """Convert raw metrics data to DTOs.

        Args:
            metrics_data: Dictionary of metric names to values

        Returns:
            List of GraphMetricDTO objects
        """
        metrics = []

        # Define metric categories and descriptions
        metric_definitions = {
            "node_count": {
                "description": "Total number of nodes in the graph",
                "category": "structure",
            },
            "edge_count": {
                "description": "Total number of edges in the graph",
                "category": "structure",
            },
            "density": {
                "description": "Graph density (ratio of actual edges to possible edges)",
                "category": "structure",
            },
            "average_degree": {
                "description": "Average degree of nodes in the graph",
                "category": "structure",
            },
            "clustering_coefficient": {
                "description": "Global clustering coefficient",
                "category": "clustering",
            },
            "diameter": {
                "description": "Graph diameter (longest shortest path)",
                "category": "connectivity",
            },
            "average_path_length": {
                "description": "Average shortest path length between all node pairs",
                "category": "connectivity",
            },
            "connected_components": {
                "description": "Number of connected components",
                "category": "connectivity",
            },
            "largest_component_size": {
                "description": "Size of the largest connected component",
                "category": "connectivity",
            },
            "assortativity": {
                "description": "Degree assortativity coefficient",
                "category": "structure",
            },
            "transitivity": {
                "description": "Graph transitivity (fraction of triangles)",
                "category": "clustering",
            },
        }

        for metric_name, value in metrics_data.items():
            definition = metric_definitions.get(
                metric_name,
                {"description": f"Graph metric: {metric_name}", "category": "other"},
            )

            metrics.append(
                GraphMetricDTO(
                    name=metric_name,
                    value=value,
                    description=definition["description"],
                    category=definition["category"],
                )
            )

        return metrics
