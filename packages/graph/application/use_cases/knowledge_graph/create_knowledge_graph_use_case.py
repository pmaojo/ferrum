"""Use case for creating knowledge graphs."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from application.exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    NotFoundError,
    ValidationError,
)
from application.ports import OntologyValidatorPort, TracingPort
from application.ports.contract import ContractPort
from application.contracts import KGContract
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from application.use_cases.knowledge_graph.metadata_repository import (
    GraphMetadataRepositoryPort,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
)
from domain.entities import KnowledgeGraph, ScientificDomain


@dataclass
class CreateKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to create a new knowledge graph."""

    name: str
    description: Optional[str]
    domain: ScientificDomain
    ontology_version_id: str
    is_public: bool = False
    triplet_batches: Optional[List[List[Tuple[str, str, str]]]] = None


@dataclass
class CreateKnowledgeGraphResponse(BaseResponseDTO):
    """Response from knowledge graph creation."""

    knowledge_graph: Optional["KnowledgeGraphDTO"] = None


@dataclass
class KnowledgeGraphDTO:
    """Knowledge graph data transfer object."""

    id: str
    name: str
    description: Optional[str]
    domain: str
    ontology_version_id: str
    tenant_id: str
    node_count: int
    edge_count: int
    is_public: bool
    created_at: datetime
    updated_at: datetime


# Repository port for knowledge graphs
from abc import abstractmethod
from typing import List, Protocol, Tuple

# Forward declarations for type hints
if False:  # TYPE_CHECKING equivalent
    from application.use_cases.dto import SortParams
    from application.use_cases.knowledge_graph.list_knowledge_graphs_use_case import (
        KnowledgeGraphFilterParams,
    )


class KnowledgeGraphRepositoryPort(Protocol):
    """Port for knowledge graph repository operations."""

    @abstractmethod
    def create(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        """Create a new knowledge graph.

        Args:
            kg: Knowledge graph entity to create

        Returns:
            Created knowledge graph entity

        Raises:
            RepositoryError: When creation fails
        """
        ...

    @abstractmethod
    def update(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        """Update an existing knowledge graph.

        Args:
            kg: Knowledge graph entity to update

        Returns:
            Updated knowledge graph entity

        Raises:
            RepositoryError: When update fails
        """
        ...

    @abstractmethod
    def get_by_id(self, kg_id: str, tenant_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph by ID and tenant.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Knowledge graph entity if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_name(self, name: str, tenant_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph by name and tenant.

        Args:
            name: Knowledge graph name
            tenant_id: Tenant identifier

        Returns:
            Knowledge graph entity if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional["KnowledgeGraphFilterParams"] = None,
        sort: Optional["SortParams"] = None,
    ) -> Tuple[List[KnowledgeGraph], int]:
        """List knowledge graphs for a tenant with pagination, filtering, and sorting.

        Args:
            tenant_id: Tenant identifier
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Optional filter parameters
            sort: Optional sort parameters

        Returns:
            Tuple of (knowledge graphs list, total count)
        """
        ...

    @abstractmethod
    def delete_by_id(self, kg_id: str, tenant_id: str) -> bool:
        """Delete knowledge graph by ID and tenant.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            RepositoryError: When deletion fails
        """
        ...


# Subscription service port
class SubscriptionServicePort(Protocol):
    """Port for subscription service operations."""

    @abstractmethod
    def check_knowledge_graph_limit(self, tenant_id: str) -> None:
        """Check if tenant can create more knowledge graphs.

        Args:
            tenant_id: Tenant identifier

        Raises:
            BusinessRuleViolationError: If limit is exceeded
        """
        ...


class CreateKnowledgeGraphUseCase(
    BaseUseCase[CreateKnowledgeGraphRequest, CreateKnowledgeGraphResponse]
):
    """Use case for creating knowledge graphs with validation and business rules."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        subscription_service: SubscriptionServicePort,
        metadata_repository: GraphMetadataRepositoryPort,
        tracer: TracingPort,
        contract_adapter: ContractPort | None = None,
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            ontology_repository: Repository for ontology operations
            ontology_validator: Service for ontology validation
            subscription_service: Service for subscription limit checking
            metadata_repository: Repository for graph metadata persistence
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.subscription_service = subscription_service
        self.metadata_repository = metadata_repository
        self.tracer = tracer
        self.contract_adapter = contract_adapter

    def _validate_request_internal(self, request: CreateKnowledgeGraphRequest) -> None:
        """Validate the create knowledge graph request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Knowledge graph name is required and cannot be empty",
                field="name",
            )

        if len(request.name) > 255:
            raise ValidationError(
                message="Knowledge graph name cannot exceed 255 characters",
                field="name",
            )

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

        if not isinstance(request.domain, ScientificDomain):
            raise ValidationError(
                message="Domain must be a valid ScientificDomain", field="domain"
            )

        if request.description and len(request.description) > 1000:
            raise ValidationError(
                message="Description cannot exceed 1000 characters", field="description"
            )

    async def _execute_internal(
        self, request: CreateKnowledgeGraphRequest
    ) -> CreateKnowledgeGraphResponse:
        """Execute the knowledge graph creation.

        Args:
            request: The validated request

        Returns:
            Response containing the created knowledge graph

        Raises:
            BusinessRuleViolationError: If business rules are violated
            NotFoundError: If referenced resources don't exist
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="create_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check subscription limits
                self.subscription_service.check_knowledge_graph_limit(request.tenant_id)

                # Check if knowledge graph with same name already exists for tenant
                existing_kg = self.kg_repository.get_by_name(
                    request.name, request.tenant_id
                )
                if existing_kg:
                    raise BusinessRuleViolationError(
                        message=f"Knowledge graph with name '{request.name}' already exists",
                        rule_name="unique_kg_name_per_tenant",
                    )

                # Validate ontology version exists
                ontology_version = self.ontology_repository.get_by_id(
                    request.ontology_version_id,
                    request.tenant_id,
                )
                if not ontology_version:
                    raise NotFoundError(
                        message=(
                            f"Ontology version with ID '{request.ontology_version_id}' not found"
                        ),
                        resource_type="ontology_version",
                        resource_id=request.ontology_version_id,
                    )

                # Create knowledge graph entity
                kg = KnowledgeGraph.create(
                    name=request.name,
                    tenant_id=request.tenant_id,
                    domain=request.domain,
                    ontology_version_id=request.ontology_version_id,
                    is_public=request.is_public,
                )

                # Save to repository
                created_kg = self.kg_repository.create(kg)

                if request.description:
                    self.metadata_repository.save_description(
                        kg_id=created_kg.id,
                        tenant_id=request.tenant_id,
                        description=request.description,
                    )

                # Verify contract after each triplet batch
                if self.contract_adapter and request.triplet_batches:
                    contract = KGContract()
                    for _ in request.triplet_batches:
                        valid, _ = self.contract_adapter.verify(
                            contract,
                            kg_id=created_kg.id,
                            tenant_id=request.tenant_id,
                        )
                        if not valid:
                            self.contract_adapter.repair(
                                contract,
                                kg_id=created_kg.id,
                                tenant_id=request.tenant_id,
                            )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graph_created",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=request.domain.value,
                )

                # Create response DTO
                kg_dto = KnowledgeGraphDTO(
                    id=created_kg.id,
                    name=created_kg.name,
                    description=request.description,
                    domain=created_kg.domain.value,
                    ontology_version_id=created_kg.ontology_version_id,
                    tenant_id=created_kg.tenant_id,
                    node_count=created_kg.node_count,
                    edge_count=created_kg.edge_count,
                    is_public=created_kg.is_public,
                    created_at=created_kg.created_at,
                    updated_at=created_kg.updated_at,
                )

                return CreateKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    knowledge_graph=kg_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="knowledge_graph_creation_errors",
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
                    return CreateKnowledgeGraphResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to create knowledge graph: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_CREATION_FAILED",
                ) from e
