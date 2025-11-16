"""Use case for listing knowledge graphs with pagination, filtering, and sorting."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    PaginatedResponse,
    PaginationParams,
    SortParams,
    TenantScopedRequestDTO,
)
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphDTO,
    KnowledgeGraphRepositoryPort,
)
from domain.entities import ScientificDomain


class KnowledgeGraphSortField(str, Enum):
    """Valid sort fields for knowledge graph listing."""

    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NODE_COUNT = "node_count"
    EDGE_COUNT = "edge_count"
    DOMAIN = "domain"


@dataclass
class KnowledgeGraphFilterParams:
    """Filter parameters for knowledge graph listing."""

    domain: Optional[ScientificDomain] = None
    is_public: Optional[bool] = None
    name_contains: Optional[str] = None
    min_node_count: Optional[int] = None
    max_node_count: Optional[int] = None
    min_edge_count: Optional[int] = None
    max_edge_count: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None


@dataclass
class ListKnowledgeGraphsRequest(TenantScopedRequestDTO):
    """Request to list knowledge graphs with pagination, filtering, and sorting."""

    pagination: PaginationParams
    filters: Optional[KnowledgeGraphFilterParams] = None
    sort: Optional[SortParams] = None


@dataclass
class ListKnowledgeGraphsResponse(BaseResponseDTO):
    """Response from knowledge graph listing."""

    knowledge_graphs: Optional[PaginatedResponse[KnowledgeGraphDTO]] = None


class ListKnowledgeGraphsUseCase(
    BaseUseCase[ListKnowledgeGraphsRequest, ListKnowledgeGraphsResponse]
):
    """Use case for listing knowledge graphs with pagination, filtering, and sorting."""

    def __init__(
        self, kg_repository: KnowledgeGraphRepositoryPort, tracer: TracingPort
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.tracer = tracer

    def _validate_request_internal(self, request: ListKnowledgeGraphsRequest) -> None:
        """Validate the list knowledge graphs request.

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

        # Validate pagination parameters (already validated in PaginationParams.__post_init__)
        if not isinstance(request.pagination, PaginationParams):
            raise ValidationError(
                message="Pagination parameters are required", field="pagination"
            )

        # Validate sort parameters if provided
        if request.sort:
            if not isinstance(request.sort, SortParams):
                raise ValidationError(
                    message="Sort parameters must be a valid SortParams object",
                    field="sort",
                )

            if request.sort.sort_by not in [
                field.value for field in KnowledgeGraphSortField
            ]:
                raise ValidationError(
                    message=f"Invalid sort field: {request.sort.sort_by}. Valid fields: {[f.value for f in KnowledgeGraphSortField]}",
                    field="sort.sort_by",
                )

        # Validate filter parameters if provided
        if request.filters:
            self._validate_filters(request.filters)

    def _validate_filters(self, filters: KnowledgeGraphFilterParams) -> None:
        """Validate filter parameters.

        Args:
            filters: Filter parameters to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate domain if provided
        if filters.domain is not None and not isinstance(
            filters.domain, ScientificDomain
        ):
            raise ValidationError(
                message="Domain must be a valid ScientificDomain",
                field="filters.domain",
            )

        # Validate is_public if provided
        if filters.is_public is not None and not isinstance(filters.is_public, bool):
            raise ValidationError(
                message="is_public must be a boolean value", field="filters.is_public"
            )

        # Validate name_contains if provided
        if filters.name_contains is not None:
            if not isinstance(filters.name_contains, str):
                raise ValidationError(
                    message="name_contains must be a string",
                    field="filters.name_contains",
                )
            if len(filters.name_contains.strip()) == 0:
                raise ValidationError(
                    message="name_contains cannot be empty if provided",
                    field="filters.name_contains",
                )

        # Validate count filters
        count_fields = [
            ("min_node_count", filters.min_node_count),
            ("max_node_count", filters.max_node_count),
            ("min_edge_count", filters.min_edge_count),
            ("max_edge_count", filters.max_edge_count),
        ]

        for field_name, value in count_fields:
            if value is not None:
                if not isinstance(value, int) or value < 0:
                    raise ValidationError(
                        message=f"{field_name} must be a non-negative integer",
                        field=f"filters.{field_name}",
                    )

        # Validate count ranges
        if (
            filters.min_node_count is not None
            and filters.max_node_count is not None
            and filters.min_node_count > filters.max_node_count
        ):
            raise ValidationError(
                message="min_node_count cannot be greater than max_node_count",
                field="filters.node_count_range",
            )

        if (
            filters.min_edge_count is not None
            and filters.max_edge_count is not None
            and filters.min_edge_count > filters.max_edge_count
        ):
            raise ValidationError(
                message="min_edge_count cannot be greater than max_edge_count",
                field="filters.edge_count_range",
            )

        # Validate date filters
        date_fields = [
            ("created_after", filters.created_after),
            ("created_before", filters.created_before),
            ("updated_after", filters.updated_after),
            ("updated_before", filters.updated_before),
        ]

        for field_name, value in date_fields:
            if value is not None and not isinstance(value, datetime):
                raise ValidationError(
                    message=f"{field_name} must be a datetime object",
                    field=f"filters.{field_name}",
                )

        # Validate date ranges
        if (
            filters.created_after is not None
            and filters.created_before is not None
            and filters.created_after > filters.created_before
        ):
            raise ValidationError(
                message="created_after cannot be after created_before",
                field="filters.created_date_range",
            )

        if (
            filters.updated_after is not None
            and filters.updated_before is not None
            and filters.updated_after > filters.updated_before
        ):
            raise ValidationError(
                message="updated_after cannot be after updated_before",
                field="filters.updated_date_range",
            )

    async def _execute_internal(
        self, request: ListKnowledgeGraphsRequest
    ) -> ListKnowledgeGraphsResponse:
        """Execute the knowledge graph listing.

        Args:
            request: The validated request

        Returns:
            Response containing the paginated list of knowledge graphs
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="list_knowledge_graphs",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Get knowledge graphs from repository with filters and pagination
                knowledge_graphs, total_count = self.kg_repository.list_by_tenant(
                    tenant_id=request.tenant_id,
                    page=request.pagination.page,
                    page_size=request.pagination.page_size,
                    filters=request.filters,
                    sort=request.sort,
                )

                # Convert to DTOs
                kg_dtos = [
                    KnowledgeGraphDTO(
                        id=kg.id,
                        name=kg.name,
                        description=None,  # Description would come from metadata if available
                        domain=kg.domain.value,
                        ontology_version_id=kg.ontology_version_id,
                        tenant_id=kg.tenant_id,
                        node_count=kg.node_count,
                        edge_count=kg.edge_count,
                        is_public=kg.is_public,
                        created_at=kg.created_at,
                        updated_at=kg.updated_at,
                    )
                    for kg in knowledge_graphs
                ]

                # Calculate pagination metadata
                total_pages = (
                    total_count + request.pagination.page_size - 1
                ) // request.pagination.page_size
                has_next_page = request.pagination.page < total_pages
                has_previous_page = request.pagination.page > 1

                # Create paginated response
                paginated_response = PaginatedResponse[KnowledgeGraphDTO](
                    items=kg_dtos,
                    total_items=total_count,
                    total_pages=total_pages,
                    page=request.pagination.page,
                    page_size=request.pagination.page_size,
                    has_next_page=has_next_page,
                    has_previous_page=has_previous_page,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graphs_listed",
                    value=len(kg_dtos),
                    tenant_id=request.tenant_id,
                    total_count=total_count,
                )

                return ListKnowledgeGraphsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    knowledge_graphs=paginated_response,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="knowledge_graph_listing_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, ValidationError):
                    return ListKnowledgeGraphsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to list knowledge graphs: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_LISTING_FAILED",
                ) from e
