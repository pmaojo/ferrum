"""Use case for creating ontologies."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol

from application.exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    NotFoundError,
    ValidationError,
)
from application.ports import OntologyValidatorPort, TracingPort
from application.ports.owl import OwlAxiomGeneratorPort
from application.ports.contract import ContractPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    CreateOntologyRequestDTO,
    OntologyDTO,
)
from domain.entities import OntologyVersion, ScientificDomain


# Repository port for ontologies
class OntologyRepositoryPort(Protocol):
    """Port for ontology repository operations."""

    def create(self, ontology: OntologyVersion) -> OntologyVersion:
        """Create a new ontology version.

        Args:
            ontology: Ontology version entity to create

        Returns:
            Created ontology version entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    def get_by_id(self, ontology_id: str, tenant_id: str) -> Optional[OntologyVersion]:
        """Get ontology version by ID and tenant.

        Args:
            ontology_id: Ontology version identifier
            tenant_id: Tenant identifier

        Returns:
            Ontology version entity if found, None otherwise
        """
        ...

    def get_by_name_and_domain(
        self, name: str, domain: ScientificDomain, tenant_id: str
    ) -> Optional[OntologyVersion]:
        """Get latest ontology version by name, domain and tenant.

        Args:
            name: Ontology name
            domain: Scientific domain
            tenant_id: Tenant identifier

        Returns:
            Latest ontology version entity if found, None otherwise
        """
        ...

    def list_versions(self, name: str, tenant_id: str) -> List[OntologyVersion]:
        """List all versions of an ontology.

        Args:
            name: Ontology name
            tenant_id: Tenant identifier

        Returns:
            List of ontology versions ordered by creation date
        """
        ...

    def set_version_name(self, version_id: str, name: str, tenant_id: str) -> None:
        """Persist the ontology name for the given version.

        Args:
            version_id: Ontology version identifier
            name: Human readable ontology name
            tenant_id: Tenant identifier
        """
        ...

    def get_version_name(self, version_id: str, tenant_id: str) -> Optional[str]:
        """Retrieve the ontology name for a specific version.

        Args:
            version_id: Ontology version identifier
            tenant_id: Tenant identifier

        Returns:
            Ontology name if stored, ``None`` otherwise
        """
        ...


# Subscription service port
class SubscriptionServicePort(Protocol):
    """Port for subscription service operations."""

    def check_ontology_limit(self, tenant_id: str) -> None:
        """Check if tenant can create more ontologies.

        Args:
            tenant_id: Tenant identifier

        Raises:
            BusinessRuleViolationError: If limit is exceeded
        """
        ...


# Ontology content parser port
class OntologyParserPort(Protocol):
    """Port for parsing ontology content."""

    def parse_content(self, content: str, format: str) -> List[str]:
        """Parse ontology content into axioms.

        Args:
            content: Raw ontology content
            format: Content format (owl, rdf, ttl, json-ld)

        Returns:
            List of axioms in Manchester syntax

        Raises:
            ValidationError: If content cannot be parsed
        """
        ...

    def detect_format(self, content: str) -> str:
        """Detect the format of ontology content.

        Args:
            content: Raw ontology content

        Returns:
            Detected format string

        Raises:
            ValidationError: If format cannot be detected
        """
        ...


@dataclass
class CreateOntologyResponse(BaseResponseDTO):
    """Response from ontology creation."""

    ontology: Optional[OntologyDTO] = None


class CreateOntologyUseCase(
    BaseUseCase[CreateOntologyRequestDTO, CreateOntologyResponse]
):
    """Use case for creating ontologies with validation and business rules."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        ontology_parser: OntologyParserPort,
        subscription_service: SubscriptionServicePort,
        tracer: TracingPort,
        axiom_generator: Optional[OwlAxiomGeneratorPort] = None,
        contract_adapter: Optional[ContractPort] = None,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            ontology_validator: Service for ontology validation
            ontology_parser: Service for parsing ontology content
            subscription_service: Service for subscription limit checking
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.ontology_parser = ontology_parser
        self.subscription_service = subscription_service
        self.tracer = tracer
        self.axiom_generator = axiom_generator
        self.contract_adapter = contract_adapter

    def _validate_request_internal(self, request: CreateOntologyRequestDTO) -> None:
        """Validate the create ontology request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Ontology name is required and cannot be empty", field="name"
            )

        if len(request.name) > 255:
            raise ValidationError(
                message="Ontology name cannot exceed 255 characters", field="name"
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if (
            (not request.content or not request.content.strip())
            and not request.competency_questions
        ):
            raise ValidationError(
                message="Ontology content is required and cannot be empty",
                field="content",
            )

        if not request.domain or not request.domain.strip():
            raise ValidationError(
                message="Domain is required and cannot be empty", field="domain"
            )

        # Validate domain is a valid ScientificDomain value
        try:
            ScientificDomain(request.domain)
        except ValueError:
            valid_domains = [d.value for d in ScientificDomain]
            raise ValidationError(
                message=f"Domain must be one of: {', '.join(valid_domains)}",
                field="domain",
            )

        if not request.format or not request.format.strip():
            raise ValidationError(
                message="Format is required and cannot be empty", field="format"
            )

        # Validate format
        valid_formats = ["owl", "rdf", "ttl", "json-ld"]
        if request.format not in valid_formats:
            raise ValidationError(
                message=f"Format must be one of: {', '.join(valid_formats)}",
                field="format",
            )

        if request.description and len(request.description) > 1000:
            raise ValidationError(
                message="Description cannot exceed 1000 characters", field="description"
            )

    async def _execute_internal(
        self, request: CreateOntologyRequestDTO
    ) -> CreateOntologyResponse:
        """Execute the ontology creation.

        Args:
            request: The validated request

        Returns:
            Response containing the created ontology

        Raises:
            BusinessRuleViolationError: If business rules are violated
            NotFoundError: If referenced resources don't exist
            ValidationError: If ontology content is invalid
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="create_ontology", tenant_id=request.tenant_id, user_id=request.user_id
        ) as span:
            try:
                # Check subscription limits
                self.subscription_service.check_ontology_limit(request.tenant_id)

                # Convert domain string to enum
                domain = ScientificDomain(request.domain)

                # Check if ontology with same name and domain already exists for tenant
                existing_ontology = self.ontology_repository.get_by_name_and_domain(
                    request.name, domain, request.tenant_id
                )
                if existing_ontology:
                    raise BusinessRuleViolationError(
                        message=f"Ontology with name '{request.name}' and domain '{request.domain}' already exists",
                        rule_name="unique_ontology_name_domain_per_tenant",
                    )

                # Validate parent version if provided
                parent_version = None
                if request.parent_version_id:
                    parent_version = self.ontology_repository.get_by_id(
                        request.parent_version_id, request.tenant_id
                    )
                    if not parent_version:
                        raise NotFoundError(
                            message=f"Parent ontology version with ID '{request.parent_version_id}' not found",
                            resource_type="ontology_version",
                            resource_id=request.parent_version_id,
                        )

                    # Validate parent has same domain
                    if parent_version.domain != domain:
                        raise BusinessRuleViolationError(
                            message="Child ontology must have same domain as parent",
                            rule_name="ontology_domain_inheritance",
                        )

                # Generate or parse ontology content into axioms
                cq_ids: List[str] = []
                if request.competency_questions and self.axiom_generator:
                    axioms: List[str] = []
                    for cq in request.competency_questions:
                        question = cq.get("question") or cq.get("text") or ""
                        axioms.extend(
                            self.axiom_generator.generate_axioms(
                                text=question, tenant_id=request.tenant_id
                            )
                        )
                        if cid := cq.get("id"):
                            cq_ids.append(cid)
                else:
                    try:
                        axioms = self.ontology_parser.parse_content(
                            request.content, request.format
                        )
                    except Exception as e:
                        raise ValidationError(
                            message=f"Failed to parse ontology content: {str(e)}",
                            field="content",
                        )

                # Validate ontology content
                if parent_version:
                    # Create child version
                    ontology = OntologyVersion.create_child_version(
                        parent=parent_version, axioms=axioms
                    )
                else:
                    # Create root version
                    ontology = OntologyVersion.create(
                        tenant_id=request.tenant_id, domain=domain, axioms=axioms
                    )

                if request.competency_questions:
                    ontology.metadata["competency_questions"] = request.competency_questions
                if cq_ids:
                    ontology.metadata["competency_question_ids"] = cq_ids

                # Run contract verification if provided
                if request.contract and self.contract_adapter:
                    is_valid, details = self.contract_adapter.verify(
                        request.contract, kg_id=ontology.id, tenant_id=request.tenant_id
                    )
                    if not is_valid and request.competency_questions and self.axiom_generator:
                        for detail in details:
                            failing_id = detail.get("cq_id")
                            if failing_id:
                                cq = next(
                                    (
                                        c
                                        for c in request.competency_questions
                                        if c.get("id") == failing_id
                                    ),
                                    None,
                                )
                                if cq:
                                    axioms.extend(
                                        self.axiom_generator.generate_axioms(
                                            text=cq.get("question") or "",
                                            tenant_id=request.tenant_id,
                                        )
                                    )
                        # Rebuild ontology with additional axioms
                        if parent_version:
                            ontology = OntologyVersion.create_child_version(
                                parent=parent_version, axioms=axioms
                            )
                        else:
                            ontology = OntologyVersion.create(
                                tenant_id=request.tenant_id,
                                domain=domain,
                                axioms=axioms,
                            )
                        if request.competency_questions:
                            ontology.metadata["competency_questions"] = request.competency_questions
                        if cq_ids:
                            ontology.metadata["competency_question_ids"] = cq_ids
                        is_valid, _ = self.contract_adapter.verify(
                            request.contract, kg_id=ontology.id, tenant_id=request.tenant_id
                        )
                        if not is_valid:
                            raise ValidationError(
                                message="Contract verification failed",
                                field="contract",
                            )

                # Validate ontology consistency
                validation_result = self.ontology_validator.validate(
                    triples=[],  # Empty triples for ontology-only validation
                    ontology_version_id=ontology.id,
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

                # Save to repository
                created_ontology = self.ontology_repository.create(ontology)
                # Persist ontology name for this version
                self.ontology_repository.set_version_name(
                    created_ontology.id,
                    request.name,
                    request.tenant_id,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_created",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=request.domain,
                )

                # Create response DTO
                ontology_dto = OntologyDTO(
                    id=created_ontology.id,
                    name=request.name,
                    description=request.description,
                    domain=created_ontology.domain.value,
                    version=(
                        "1.0.0"
                        if not parent_version
                        else f"{parent_version.get_version_lineage_depth() + 1}.0.0"
                    ),
                    parent_version_id=created_ontology.parent_version,
                    tenant_id=created_ontology.tenant_id,
                    created_at=created_ontology.created_at,
                    checksum=created_ontology.checksum,
                    axiom_count=len(created_ontology.axioms),
                    competency_questions=request.competency_questions,
                )

                return CreateOntologyResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    ontology=ontology_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_creation_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(
                    e, (ValidationError, BusinessRuleViolationError, NotFoundError)
                ):
                    return CreateOntologyResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to create ontology: {str(e)}",
                    error_code="ONTOLOGY_CREATION_FAILED",
                ) from e
