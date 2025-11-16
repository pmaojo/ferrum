"""Use case for retrieving detailed knowledge graph information with statistics."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)
from application.use_cases.knowledge_graph.metadata_repository import (
    GraphMetadataRepositoryPort,
)
from application.use_cases.knowledge_graph.update_knowledge_graph_use_case import (
    AuthorizationServicePort,
)


@dataclass
class KnowledgeGraphStatisticsDTO:
    """Statistics for a knowledge graph."""

    node_count: int
    edge_count: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]
    avg_node_degree: float
    max_node_degree: int
    min_node_degree: int
    connected_components: int
    density: float
    clustering_coefficient: Optional[float] = None
    diameter: Optional[int] = None


@dataclass
class KnowledgeGraphDetailsDTO:
    """Detailed knowledge graph information."""

    id: str
    name: str
    description: Optional[str]
    domain: str
    ontology_version_id: str
    tenant_id: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    statistics: KnowledgeGraphStatisticsDTO
    metadata: Dict[str, Any]


@dataclass
class GetKnowledgeGraphDetailsRequest(TenantScopedRequestDTO):
    """Request to get detailed knowledge graph information."""

    kg_id: str
    include_advanced_stats: bool = False


@dataclass
class GetKnowledgeGraphDetailsResponse(BaseResponseDTO):
    """Response from knowledge graph details retrieval."""

    knowledge_graph: Optional[KnowledgeGraphDetailsDTO] = None


# Statistics service port
from abc import abstractmethod
from typing import Protocol


class GraphStatisticsServicePort(Protocol):
    """Port for graph statistics service operations."""

    @abstractmethod
    def calculate_basic_statistics(
        self, kg_id: str, tenant_id: str
    ) -> KnowledgeGraphStatisticsDTO:
        """Calculate basic graph statistics.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Basic statistics for the knowledge graph
        """
        ...

    @abstractmethod
    def calculate_advanced_statistics(
        self, kg_id: str, tenant_id: str
    ) -> KnowledgeGraphStatisticsDTO:
        """Calculate advanced graph statistics including clustering and diameter.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Advanced statistics for the knowledge graph
        """
        ...


# Metadata repository port
class GraphMetadataServicePort(GraphMetadataRepositoryPort, Protocol):
    """Deprecated alias for GraphMetadataRepositoryPort."""


class GetKnowledgeGraphDetailsUseCase(
    BaseUseCase[GetKnowledgeGraphDetailsRequest, GetKnowledgeGraphDetailsResponse]
):
    """Use case for retrieving detailed knowledge graph information with statistics."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        authorization_service: AuthorizationServicePort,
        statistics_service: GraphStatisticsServicePort,
        metadata_repository: GraphMetadataRepositoryPort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            authorization_service: Service for authorization checks
            statistics_service: Service for calculating graph statistics
            metadata_repository: Repository for graph metadata persistence
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.authorization_service = authorization_service
        self.statistics_service = statistics_service
        self.metadata_repository = metadata_repository
        self.tracer = tracer

    def _validate_request_internal(
        self, request: GetKnowledgeGraphDetailsRequest
    ) -> None:
        """Validate the get knowledge graph details request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required and cannot be empty",
                field="kg_id",
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not isinstance(request.include_advanced_stats, bool):
            raise ValidationError(
                message="include_advanced_stats must be a boolean value",
                field="include_advanced_stats",
            )

    async def _execute_internal(
        self, request: GetKnowledgeGraphDetailsRequest
    ) -> GetKnowledgeGraphDetailsResponse:
        """Execute the knowledge graph details retrieval.

        Args:
            request: The validated request

        Returns:
            Response containing detailed knowledge graph information

        Raises:
            NotFoundError: If knowledge graph doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="get_knowledge_graph_details",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    permission="read",
                )

                # Get knowledge graph
                kg = self.kg_repository.get_by_id(request.kg_id, request.tenant_id)
                if not kg:
                    raise NotFoundError(
                        message=f"Knowledge graph with ID '{request.kg_id}' not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    )

                # Calculate statistics
                if request.include_advanced_stats:
                    statistics = self.statistics_service.calculate_advanced_statistics(
                        kg_id=request.kg_id, tenant_id=request.tenant_id
                    )
                else:
                    statistics = self.statistics_service.calculate_basic_statistics(
                        kg_id=request.kg_id, tenant_id=request.tenant_id
                    )

                # Get metadata
                metadata = self.metadata_repository.get_metadata(
                    kg_id=request.kg_id, tenant_id=request.tenant_id
                )

                # Create detailed DTO
                kg_details = KnowledgeGraphDetailsDTO(
                    id=kg.id,
                    name=kg.name,
                    description=metadata.get("description"),
                    domain=kg.domain.value,
                    ontology_version_id=kg.ontology_version_id,
                    tenant_id=kg.tenant_id,
                    is_public=kg.is_public,
                    created_at=kg.created_at,
                    updated_at=kg.updated_at,
                    statistics=statistics,
                    metadata=metadata,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graph_details_retrieved",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=kg.domain.value,
                    include_advanced_stats=request.include_advanced_stats,
                )

                return GetKnowledgeGraphDetailsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    knowledge_graph=kg_details,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="knowledge_graph_details_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return GetKnowledgeGraphDetailsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to get knowledge graph details: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_DETAILS_FAILED",
                ) from e
