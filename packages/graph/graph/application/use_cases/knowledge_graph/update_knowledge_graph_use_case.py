"""Use case for updating knowledge graphs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    BusinessRuleViolationError,
    NotFoundError,
    ValidationError,
)
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphDTO,
    KnowledgeGraphRepositoryPort,
)
from application.use_cases.knowledge_graph.metadata_repository import (
    GraphMetadataRepositoryPort,
)


@dataclass
class UpdateKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to update an existing knowledge graph."""

    kg_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


@dataclass
class UpdateKnowledgeGraphResponse(BaseResponseDTO):
    """Response from knowledge graph update."""

    knowledge_graph: Optional[KnowledgeGraphDTO] = None


# Authorization service port
from abc import abstractmethod
from typing import Protocol


class AuthorizationServicePort(Protocol):
    """Port for authorization service operations."""

    @abstractmethod
    def check_permission(self, user_id: str, resource_id: str, permission: str) -> None:
        """Check if user has permission for a resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            permission: Permission to check

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        ...


class UpdateKnowledgeGraphUseCase(
    BaseUseCase[UpdateKnowledgeGraphRequest, UpdateKnowledgeGraphResponse]
):
    """Use case for updating knowledge graphs with validation and authorization."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        authorization_service: AuthorizationServicePort,
        metadata_repository: GraphMetadataRepositoryPort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            authorization_service: Service for authorization checks
            metadata_repository: Repository for graph metadata persistence
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.authorization_service = authorization_service
        self.metadata_repository = metadata_repository
        self.tracer = tracer

    def _validate_request_internal(self, request: UpdateKnowledgeGraphRequest) -> None:
        """Validate the update knowledge graph request.

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

        # Validate name if provided
        if request.name is not None:
            if not request.name.strip():
                raise ValidationError(
                    message="Knowledge graph name cannot be empty if provided",
                    field="name",
                )

            if len(request.name) > 255:
                raise ValidationError(
                    message="Knowledge graph name cannot exceed 255 characters",
                    field="name",
                )

        # Validate description if provided
        if request.description is not None and len(request.description) > 1000:
            raise ValidationError(
                message="Description cannot exceed 1000 characters", field="description"
            )

        # Check that at least one field is being updated
        if (
            request.name is None
            and request.description is None
            and request.is_public is None
        ):
            raise ValidationError(
                message="At least one field must be provided for update",
                field="update_fields",
            )

    async def _execute_internal(
        self, request: UpdateKnowledgeGraphRequest
    ) -> UpdateKnowledgeGraphResponse:
        """Execute the knowledge graph update.

        Args:
            request: The validated request

        Returns:
            Response containing the updated knowledge graph

        Raises:
            NotFoundError: If knowledge graph doesn't exist
            AuthorizationError: If user doesn't have permission
            BusinessRuleViolationError: If business rules are violated
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="update_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    user_id=request.user_id,
                    resource_id=request.kg_id,
                    permission="update",
                )

                # Get existing knowledge graph
                existing_kg = self.kg_repository.get_by_id(
                    request.kg_id, request.tenant_id
                )
                if not existing_kg:
                    raise NotFoundError(
                        message=f"Knowledge graph with ID '{request.kg_id}' not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    )

                # Check if name is being changed and if new name already exists
                if request.name and request.name != existing_kg.name:
                    existing_with_name = self.kg_repository.get_by_name(
                        request.name, request.tenant_id
                    )
                    if existing_with_name and existing_with_name.id != request.kg_id:
                        raise BusinessRuleViolationError(
                            message=f"Knowledge graph with name '{request.name}' already exists",
                            rule_name="unique_kg_name_per_tenant",
                        )

                # Update the knowledge graph
                updated = False

                if request.name and request.name != existing_kg.name:
                    existing_kg.name = request.name
                    updated = True

                if request.description is not None:
                    self.metadata_repository.save_description(
                        kg_id=request.kg_id,
                        tenant_id=request.tenant_id,
                        description=request.description,
                    )
                    updated = True

                if (
                    request.is_public is not None
                    and request.is_public != existing_kg.is_public
                ):
                    existing_kg.set_public(request.is_public)
                    updated = True

                if updated:
                    existing_kg.updated_at = datetime.utcnow()
                    updated_kg = self.kg_repository.update(existing_kg)
                else:
                    updated_kg = existing_kg

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graph_updated",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=updated_kg.domain.value,
                )

                # Create response DTO
                kg_dto = KnowledgeGraphDTO(
                    id=updated_kg.id,
                    name=updated_kg.name,
                    description=request.description,  # Use the provided description
                    domain=updated_kg.domain.value,
                    ontology_version_id=updated_kg.ontology_version_id,
                    tenant_id=updated_kg.tenant_id,
                    node_count=updated_kg.node_count,
                    edge_count=updated_kg.edge_count,
                    is_public=updated_kg.is_public,
                    created_at=updated_kg.created_at,
                    updated_at=updated_kg.updated_at,
                )

                return UpdateKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    knowledge_graph=kg_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="knowledge_graph_update_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(
                    e,
                    (
                        ValidationError,
                        NotFoundError,
                        AuthorizationError,
                        BusinessRuleViolationError,
                    ),
                ):
                    return UpdateKnowledgeGraphResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to update knowledge graph: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_UPDATE_FAILED",
                ) from e
