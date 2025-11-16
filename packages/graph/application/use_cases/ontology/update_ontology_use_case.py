"""Use case for updating ontologies with versioning."""

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
from application.ports import OntologyValidatorPort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    OntologyDTO,
    UpdateOntologyRequestDTO,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyParserPort,
    OntologyRepositoryPort,
    SubscriptionServicePort,
)
from domain.entities import OntologyVersion


# Authorization service port
class AuthorizationServicePort:
    """Port for authorization service operations."""

    def check_permission(self, user_id: str, resource_id: str, permission: str) -> None:
        """Check if user has permission for resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            permission: Required permission

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        ...


@dataclass
class UpdateOntologyResponse(BaseResponseDTO):
    """Response from ontology update."""

    ontology: Optional[OntologyDTO] = None


class UpdateOntologyUseCase(
    BaseUseCase[UpdateOntologyRequestDTO, UpdateOntologyResponse]
):
    """Use case for updating ontologies with versioning and parent-child relationship management."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        ontology_parser: OntologyParserPort,
        subscription_service: SubscriptionServicePort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            ontology_validator: Service for ontology validation
            ontology_parser: Service for parsing ontology content
            subscription_service: Service for subscription limit checking
            authorization_service: Service for authorization checks
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.ontology_parser = ontology_parser
        self.subscription_service = subscription_service
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: UpdateOntologyRequestDTO) -> None:
        """Validate the update ontology request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.ontology_id or not request.ontology_id.strip():
            raise ValidationError(
                message="Ontology ID is required and cannot be empty",
                field="ontology_id",
            )

        # At least one field must be provided for update
        if not any([request.name, request.description, request.content]):
            raise ValidationError(
                message="At least one field (name, description, content) must be provided for update",
                field="update_fields",
            )

        # Validate individual fields if provided
        if request.name is not None:
            if not request.name.strip():
                raise ValidationError(
                    message="Name cannot be empty if provided", field="name"
                )

            if len(request.name) > 255:
                raise ValidationError(
                    message="Name cannot exceed 255 characters", field="name"
                )

        if request.description is not None and len(request.description) > 1000:
            raise ValidationError(
                message="Description cannot exceed 1000 characters", field="description"
            )

        if request.content is not None:
            if not request.content.strip():
                raise ValidationError(
                    message="Content cannot be empty if provided", field="content"
                )

        if request.format is not None:
            valid_formats = ["owl", "rdf", "ttl", "json-ld"]
            if request.format not in valid_formats:
                raise ValidationError(
                    message=f"Format must be one of: {', '.join(valid_formats)}",
                    field="format",
                )

    async def _execute_internal(
        self, request: UpdateOntologyRequestDTO
    ) -> UpdateOntologyResponse:
        """Execute the ontology update.

        Args:
            request: The validated request

        Returns:
            Response containing the updated ontology version

        Raises:
            NotFoundError: If ontology doesn't exist
            AuthorizationError: If user doesn't have permission
            BusinessRuleViolationError: If business rules are violated
            ValidationError: If ontology content is invalid
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="update_ontology", tenant_id=request.tenant_id, user_id=request.user_id
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    request.user_id, request.ontology_id, "update"
                )

                # Get existing ontology version
                existing_ontology = self.ontology_repository.get_by_id(
                    request.ontology_id, request.tenant_id
                )
                if not existing_ontology:
                    raise NotFoundError(
                        message=f"Ontology with ID '{request.ontology_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.ontology_id,
                    )

                # Check subscription limits for creating new version
                self.subscription_service.check_ontology_limit(request.tenant_id)

                # Determine what needs to be updated
                needs_new_version = request.content is not None

                if needs_new_version:
                    # Content change requires new version
                    await self._create_new_version(request, existing_ontology)
                else:
                    # Metadata-only update (name, description) - not implemented in this version
                    # as ontology versions are immutable except for content changes
                    raise BusinessRuleViolationError(
                        message="Only content updates are supported, which create new versions",
                        rule_name="ontology_version_immutability",
                    )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_updated",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=existing_ontology.domain.value,
                )

                return UpdateOntologyResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    ontology=self.new_version_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_update_errors",
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
                        BusinessRuleViolationError,
                        NotFoundError,
                        AuthorizationError,
                    ),
                ):
                    return UpdateOntologyResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to update ontology: {str(e)}",
                    error_code="ONTOLOGY_UPDATE_FAILED",
                ) from e

    async def _create_new_version(
        self, request: UpdateOntologyRequestDTO, parent_ontology: OntologyVersion
    ) -> None:
        """Create a new ontology version with updated content.

        Args:
            request: The update request
            parent_ontology: The parent ontology version

        Raises:
            ValidationError: If content validation fails
        """
        # Parse new content into axioms
        format_to_use = request.format or "owl"  # Default to OWL if not specified

        try:
            new_axioms = self.ontology_parser.parse_content(
                request.content, format_to_use
            )
        except Exception as e:
            raise ValidationError(
                message=f"Failed to parse ontology content: {str(e)}", field="content"
            )

        # Create new version as child of existing version
        new_version = OntologyVersion.create_child_version(
            parent=parent_ontology, axioms=new_axioms
        )

        if request.competency_questions:
            new_version.metadata["competency_questions"] = request.competency_questions

        # Validate new version using delta validation
        validation_result = self.ontology_validator.validate_delta(
            new_triples=[],  # Empty triples for ontology-only validation
            existing_version_id=parent_ontology.id,
            tenant_id=request.tenant_id,
        )

        if not validation_result.is_consistent:
            raise ValidationError(
                message=f"Ontology validation failed: {', '.join(validation_result.unsat_classes)}",
                field="content",
                validation_errors=[
                    {
                        "type": "consistency_error",
                        "unsat_classes": validation_result.unsat_classes,
                        "repair_suggestions": validation_result.repair_suggestions,
                    }
                ],
            )

        # Save new version to repository
        created_version = self.ontology_repository.create(new_version)

        # Determine the ontology name to associate with the new version
        name_to_store = request.name
        if not name_to_store:
            name_to_store = (
                self.ontology_repository.get_version_name(
                    parent_ontology.id, request.tenant_id
                )
                or f"Updated version of {parent_ontology.id}"
            )

        # Persist name for the new version
        self.ontology_repository.set_version_name(
            created_version.id,
            name_to_store,
            request.tenant_id,
        )

        # Create response DTO
        self.new_version_dto = OntologyDTO(
            id=created_version.id,
            name=name_to_store,
            description=request.description,
            domain=created_version.domain.value,
            version=f"{parent_ontology.get_version_lineage_depth() + 1}.0.0",
            parent_version_id=created_version.parent_version,
            tenant_id=created_version.tenant_id,
            created_at=created_version.created_at,
            checksum=created_version.checksum,
            axiom_count=len(created_version.axioms),
            competency_questions=request.competency_questions,
        )
