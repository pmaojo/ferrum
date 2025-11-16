"""Use case for validating ontologies."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import OntologyValidatorPort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    OntologyValidationResultDTO,
    ValidateOntologyRequestDTO,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
)
from application.use_cases.ontology.update_ontology_use_case import (
    AuthorizationServicePort,
)
from domain.entities import Triple


@dataclass
class ValidateOntologyResponse(BaseResponseDTO):
    """Response from ontology validation."""

    validation_result: Optional[OntologyValidationResultDTO] = None


class ValidateOntologyUseCase(
    BaseUseCase[ValidateOntologyRequestDTO, ValidateOntologyResponse]
):
    """Use case for validating ontologies with consistency checking."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            ontology_validator: Service for ontology validation
            authorization_service: Service for authorization checks
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: ValidateOntologyRequestDTO) -> None:
        """Validate the validate ontology request.

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

        if not request.ontology_version_id or not request.ontology_version_id.strip():
            raise ValidationError(
                message="Ontology version ID is required and cannot be empty",
                field="ontology_version_id",
            )

        # Validate triples format if provided
        if request.triples:
            if not isinstance(request.triples, list):
                raise ValidationError(message="Triples must be a list", field="triples")

            for i, triple_dict in enumerate(request.triples):
                if not isinstance(triple_dict, dict):
                    raise ValidationError(
                        message=f"Triple at index {i} must be a dictionary",
                        field="triples",
                    )

                required_keys = ["subject", "predicate", "object"]
                for key in required_keys:
                    if key not in triple_dict:
                        raise ValidationError(
                            message=f"Triple at index {i} missing required key: {key}",
                            field="triples",
                        )

                    if (
                        not isinstance(triple_dict[key], str)
                        or not triple_dict[key].strip()
                    ):
                        raise ValidationError(
                            message=f"Triple at index {i} key '{key}' must be a non-empty string",
                            field="triples",
                        )

    async def _execute_internal(
        self, request: ValidateOntologyRequestDTO
    ) -> ValidateOntologyResponse:
        """Execute the ontology validation.

        Args:
            request: The validated request

        Returns:
            Response containing the validation results

        Raises:
            NotFoundError: If ontology version doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="validate_ontology",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    request.user_id, request.ontology_version_id, "read"
                )

                # Get ontology version
                ontology_version = self.ontology_repository.get_by_id(
                    request.ontology_version_id, request.tenant_id
                )
                if not ontology_version:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.ontology_version_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.ontology_version_id,
                    )

                # Convert triple dictionaries to Triple objects if provided
                triples = []
                if request.triples:
                    triples = [
                        Triple(
                            subject=triple_dict["subject"],
                            predicate=triple_dict["predicate"],
                            object=triple_dict["object"],
                            tenant_id=request.tenant_id,
                        )
                        for triple_dict in request.triples
                    ]

                # Perform validation
                validation_result = self.ontology_validator.validate(
                    triples=triples, ontology_version_id=request.ontology_version_id
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_validated",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=ontology_version.domain.value,
                    is_consistent=validation_result.is_consistent,
                )

                # Create validation errors list for response
                validation_errors = []
                if not validation_result.is_consistent:
                    validation_errors.extend(
                        [
                            f"Unsatisfiable class: {cls}"
                            for cls in validation_result.unsat_classes
                        ]
                    )

                # Create response DTO
                validation_result_dto = OntologyValidationResultDTO(
                    is_consistent=validation_result.is_consistent,
                    unsat_classes=validation_result.unsat_classes,
                    repair_suggestions=validation_result.repair_suggestions,
                    validation_errors=validation_errors,
                    processing_time_ms=processing_time,
                )

                return ValidateOntologyResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    validation_result=validation_result_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_validation_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return ValidateOntologyResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to validate ontology: {str(e)}",
                    error_code="ONTOLOGY_VALIDATION_FAILED",
                ) from e


class ValidateOntologyConsistencyUseCase(
    BaseUseCase[ValidateOntologyRequestDTO, ValidateOntologyResponse]
):
    """Specialized use case for ontology consistency checking without triples."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies."""
        super().__init__()
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: ValidateOntologyRequestDTO) -> None:
        """Validate the request - same as parent but triples are ignored."""
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.ontology_version_id or not request.ontology_version_id.strip():
            raise ValidationError(
                message="Ontology version ID is required and cannot be empty",
                field="ontology_version_id",
            )

    async def _execute_internal(
        self, request: ValidateOntologyRequestDTO
    ) -> ValidateOntologyResponse:
        """Execute ontology-only consistency validation.

        This method validates the ontology axioms for internal consistency
        without considering any external triples.
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="validate_ontology_consistency",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    request.user_id, request.ontology_version_id, "read"
                )

                # Get ontology version
                ontology_version = self.ontology_repository.get_by_id(
                    request.ontology_version_id, request.tenant_id
                )
                if not ontology_version:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.ontology_version_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.ontology_version_id,
                    )

                # Perform consistency validation with empty triples (ontology-only)
                validation_result = self.ontology_validator.validate(
                    triples=[],  # Empty triples for ontology-only validation
                    ontology_version_id=request.ontology_version_id,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_consistency_validated",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=ontology_version.domain.value,
                    is_consistent=validation_result.is_consistent,
                )

                # Create validation errors list for response
                validation_errors = []
                if not validation_result.is_consistent:
                    validation_errors.extend(
                        [
                            f"Inconsistent ontology: {cls}"
                            for cls in validation_result.unsat_classes
                        ]
                    )
                    validation_errors.append("Ontology contains contradictory axioms")

                # Create response DTO
                validation_result_dto = OntologyValidationResultDTO(
                    is_consistent=validation_result.is_consistent,
                    unsat_classes=validation_result.unsat_classes,
                    repair_suggestions=validation_result.repair_suggestions,
                    validation_errors=validation_errors,
                    processing_time_ms=processing_time,
                )

                return ValidateOntologyResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    validation_result=validation_result_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_consistency_validation_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return ValidateOntologyResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to validate ontology consistency: {str(e)}",
                    error_code="ONTOLOGY_CONSISTENCY_VALIDATION_FAILED",
                ) from e
