"""Use case for deleting knowledge graphs with cascading deletion."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
from application.use_cases.knowledge_graph.update_knowledge_graph_use_case import (
    AuthorizationServicePort,
)


@dataclass
class DeleteKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to delete a knowledge graph."""

    kg_id: str


@dataclass
class DeleteKnowledgeGraphResponse(BaseResponseDTO):
    """Response from knowledge graph deletion."""

    deleted_kg_id: Optional[str] = None
    cascaded_deletions: Optional[dict] = None


# Additional repository ports for cascading deletion
from abc import abstractmethod
from typing import Protocol


class QueryRepositoryPort(Protocol):
    """Port for query repository operations."""

    @abstractmethod
    def delete_by_kg_id(self, kg_id: str, tenant_id: str) -> int:
        """Delete all queries for a knowledge graph.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Number of queries deleted
        """
        ...


class GraphStreamEventRepositoryPort(Protocol):
    """Port for graph stream event repository operations."""

    @abstractmethod
    def delete_by_kg_id(self, kg_id: str, tenant_id: str) -> int:
        """Delete all graph stream events for a knowledge graph.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Number of events deleted
        """
        ...


class CommunityRepositoryPort(Protocol):
    """Port for community repository operations."""

    @abstractmethod
    def delete_by_kg_id(self, kg_id: str, tenant_id: str) -> int:
        """Delete all communities for a knowledge graph.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Number of communities deleted
        """
        ...


class TripleRepositoryPort(Protocol):
    """Port for triple repository operations."""

    @abstractmethod
    def delete_by_kg_id(self, kg_id: str, tenant_id: str) -> int:
        """Delete all triples for a knowledge graph.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Number of triples deleted
        """
        ...


class DeleteKnowledgeGraphUseCase(
    BaseUseCase[DeleteKnowledgeGraphRequest, DeleteKnowledgeGraphResponse]
):
    """Use case for deleting knowledge graphs with cascading deletion of related resources."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        authorization_service: AuthorizationServicePort,
        query_repository: QueryRepositoryPort,
        graph_stream_event_repository: GraphStreamEventRepositoryPort,
        community_repository: CommunityRepositoryPort,
        triple_repository: TripleRepositoryPort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            authorization_service: Service for authorization checks
            query_repository: Repository for query operations
            graph_stream_event_repository: Repository for graph stream event operations
            community_repository: Repository for community operations
            triple_repository: Repository for triple operations
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.authorization_service = authorization_service
        self.query_repository = query_repository
        self.graph_stream_event_repository = graph_stream_event_repository
        self.community_repository = community_repository
        self.triple_repository = triple_repository
        self.tracer = tracer

    def _validate_request_internal(self, request: DeleteKnowledgeGraphRequest) -> None:
        """Validate the delete knowledge graph request.

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

    async def _execute_internal(
        self, request: DeleteKnowledgeGraphRequest
    ) -> DeleteKnowledgeGraphResponse:
        """Execute the knowledge graph deletion with cascading.

        Args:
            request: The validated request

        Returns:
            Response containing deletion results

        Raises:
            NotFoundError: If knowledge graph doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="delete_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    permission="delete",
                )

                # Get existing knowledge graph to verify it exists
                existing_kg = self.kg_repository.get_by_id(
                    request.kg_id, request.tenant_id
                )
                if not existing_kg:
                    raise NotFoundError(
                        message=f"Knowledge graph with ID '{request.kg_id}' not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    )

                # Perform cascading deletion in reverse dependency order
                cascaded_deletions = {}

                # Delete related queries
                deleted_queries = self.query_repository.delete_by_kg_id(
                    request.kg_id, request.tenant_id
                )
                cascaded_deletions["queries"] = deleted_queries

                # Delete related graph stream events
                deleted_events = self.graph_stream_event_repository.delete_by_kg_id(
                    request.kg_id, request.tenant_id
                )
                cascaded_deletions["graph_stream_events"] = deleted_events

                # Delete related communities
                deleted_communities = self.community_repository.delete_by_kg_id(
                    request.kg_id, request.tenant_id
                )
                cascaded_deletions["communities"] = deleted_communities

                # Delete related triples
                deleted_triples = self.triple_repository.delete_by_kg_id(
                    request.kg_id, request.tenant_id
                )
                cascaded_deletions["triples"] = deleted_triples

                # Finally, delete the knowledge graph itself
                success = self.kg_repository.delete_by_id(
                    request.kg_id, request.tenant_id
                )
                if not success:
                    raise ApplicationError(
                        message=f"Failed to delete knowledge graph with ID '{request.kg_id}'",
                        error_code="KNOWLEDGE_GRAPH_DELETION_FAILED",
                    )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graph_deleted",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=existing_kg.domain.value,
                    cascaded_queries=deleted_queries,
                    cascaded_events=deleted_events,
                    cascaded_communities=deleted_communities,
                    cascaded_triples=deleted_triples,
                )

                return DeleteKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    deleted_kg_id=request.kg_id,
                    cascaded_deletions=cascaded_deletions,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="knowledge_graph_deletion_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return DeleteKnowledgeGraphResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to delete knowledge graph: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_DELETION_FAILED",
                ) from e
