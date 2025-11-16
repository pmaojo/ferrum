"""Use case for detecting communities in knowledge graphs."""

import time
from datetime import datetime
from typing import List, Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import AuthorizationServicePort, ClusteringPort, TracingPort
from application.use_cases.dto import (
    CommunitiesAnalysisDTO,
    CommunityDTO,
    DetectCommunitiesRequestDTO,
)
from application.validators import RequestValidator
from domain.entities import Community
from domain.exceptions import ClusteringError


class DetectCommunitiesUseCase:
    """Use case for detecting communities in knowledge graphs using various algorithms."""

    def __init__(
        self,
        clustering_port: ClusteringPort,
        authorization_service: AuthorizationServicePort,
        tracing_port: TracingPort,
        request_validator: Optional[RequestValidator] = None,
    ):
        """Initialize the use case with required ports.

        Args:
            clustering_port: Port for clustering operations
            authorization_service: Port for authorization checks
            tracing_port: Port for observability tracing
        """
        self.clustering_port = clustering_port
        self.authorization_service = authorization_service
        self.tracing_port = tracing_port
        self.request_validator = request_validator or RequestValidator()

    def execute(self, request: DetectCommunitiesRequestDTO) -> CommunitiesAnalysisDTO:
        """Execute community detection analysis.

        Args:
            request: Request containing community detection parameters

        Returns:
            Communities analysis results

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph is not found
            ClusteringError: When community detection fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="detect_communities",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            algorithm=request.algorithm,
        ):
            # Validate input
            self.request_validator.validate_ids(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                kg_id=request.kg_id,
            )
            self._validate_request(request)

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # Perform community detection
                communities = self.clustering_port.compute_communities(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    algorithm=request.algorithm,
                )

                # Filter communities by minimum size
                filtered_communities = [
                    c for c in communities if c.size >= request.min_community_size
                ]

                # Convert to DTOs and calculate additional metrics
                community_dtos = self._convert_communities_to_dtos(
                    filtered_communities, request.algorithm
                )

                # Calculate overall metrics
                modularity, coverage = self._calculate_overall_metrics(
                    community_dtos, communities
                )

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.tracing_port.record_metric(
                    name="community_detection_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                    algorithm=request.algorithm,
                )

                self.tracing_port.record_metric(
                    name="communities_detected_count",
                    value=len(community_dtos),
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                    algorithm=request.algorithm,
                )

                return CommunitiesAnalysisDTO(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    algorithm=request.algorithm,
                    communities=community_dtos,
                    total_communities=len(community_dtos),
                    modularity=modularity,
                    coverage=coverage,
                    analysis_timestamp=datetime.utcnow(),
                    processing_time_ms=processing_time_ms,
                )

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise ClusteringError(f"Community detection failed: {str(e)}")

    def _validate_request(self, request: DetectCommunitiesRequestDTO) -> None:
        """Validate the community detection request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: When validation fails
        """

        # Validate algorithm
        supported_algorithms = ["louvain", "leiden", "label_propagation", "infomap"]
        if request.algorithm not in supported_algorithms:
            raise ValidationError(
                message=(
                    f"Unsupported algorithm: {request.algorithm}. "
                    f"Supported algorithms: {', '.join(supported_algorithms)}"
                ),
                field="algorithm",
            )

        # Validate min_community_size
        if request.min_community_size < 1:
            raise ValidationError(
                message="Minimum community size must be at least 1",
                field="min_community_size",
            )

        # Validate resolution parameter
        if request.resolution <= 0:
            raise ValidationError(
                message="Resolution parameter must be positive", field="resolution"
            )

    def _convert_communities_to_dtos(
        self, communities: List[Community], algorithm: str
    ) -> List[CommunityDTO]:
        """Convert Community entities to DTOs with additional metrics.

        Args:
            communities: List of Community entities
            algorithm: Algorithm used for detection

        Returns:
            List of CommunityDTO objects
        """
        community_dtos = []

        for community in communities:
            # Calculate centroid node (node closest to centroid embedding)
            centroid_node_id = self._find_centroid_node(community)

            # Estimate internal/external edges (simplified calculation)
            internal_edges = max(1, int(community.size * 1.5))  # Rough estimate
            external_edges = max(0, int(community.size * 0.5))  # Rough estimate

            # Calculate modularity score for this community (simplified)
            modularity_score = self._calculate_community_modularity(community)

            community_dtos.append(
                CommunityDTO(
                    id=community.id,
                    size=community.size,
                    node_ids=community.node_ids,
                    centroid_node_id=centroid_node_id,
                    modularity_score=modularity_score,
                    internal_edges=internal_edges,
                    external_edges=external_edges,
                )
            )

        return community_dtos

    def _find_centroid_node(self, community: Community) -> str:
        """Find the node closest to the community centroid using Euclidean distance.

        The current implementation derives deterministic embeddings from each
        node identifier to avoid external dependencies. Distances are calculated
        using efficient NumPy vector operations to scale to large communities.

        Args:
            community: Community entity

        Returns:
            Node ID of the centroid node or an empty string if the community has
            no nodes.
        """
        if not community.node_ids:
            return ""

        import hashlib

        import numpy as np

        centroid = np.array(community.centroid_embedding, dtype=float)
        dim = len(centroid)

        def _embedding(node_id: str) -> list[float]:
            digest = hashlib.sha256(node_id.encode()).digest()
            values = [b / 255 for b in digest[:dim]]
            if len(values) < dim:
                values.extend([0.0] * (dim - len(values)))
            return values

        embeddings = np.array([_embedding(node_id) for node_id in community.node_ids])
        distances = np.linalg.norm(embeddings - centroid, axis=1)
        closest_index = int(np.argmin(distances))
        return community.node_ids[closest_index]

    def _calculate_community_modularity(self, community: Community) -> float:
        """Calculate modularity score for a single community.

        Args:
            community: Community entity

        Returns:
            Modularity score (simplified calculation)
        """
        # Simplified modularity calculation
        # In a real implementation, this would use the actual graph structure
        if community.size <= 1:
            return 0.0

        # Rough estimate based on community size
        return min(0.8, community.size / 100.0)

    def _calculate_overall_metrics(
        self, community_dtos: List[CommunityDTO], all_communities: List[Community]
    ) -> tuple[float, float]:
        """Calculate overall modularity and coverage metrics.

        Args:
            community_dtos: Filtered community DTOs
            all_communities: All detected communities

        Returns:
            Tuple of (modularity, coverage)
        """
        if not community_dtos:
            return 0.0, 0.0

        # Calculate overall modularity (weighted average)
        total_nodes = sum(c.size for c in community_dtos)
        if total_nodes == 0:
            modularity = 0.0
        else:
            weighted_modularity = sum(
                c.modularity_score * c.size for c in community_dtos
            )
            modularity = weighted_modularity / total_nodes

        # Calculate coverage (fraction of nodes in communities)
        total_graph_nodes = sum(c.size for c in all_communities)
        if total_graph_nodes == 0:
            coverage = 0.0
        else:
            coverage = total_nodes / total_graph_nodes

        return modularity, coverage
