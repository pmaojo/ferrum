"""Use case for listing ontology versions."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    ListOntologyVersionsRequestDTO,
    OntologyVersionDTO,
    PaginatedResponse,
    PaginationParams,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
)
from application.use_cases.ontology.update_ontology_use_case import (
    AuthorizationServicePort,
)
from domain.entities import OntologyVersion, ScientificDomain


# Extended repository port for listing operations
class ExtendedOntologyRepositoryPort(OntologyRepositoryPort):
    """Extended ontology repository port with listing capabilities."""

    def list_versions_by_tenant(
        self,
        tenant_id: str,
        ontology_name: Optional[str] = None,
        domain: Optional[ScientificDomain] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OntologyVersion], int]:
        """List ontology versions for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier
            ontology_name: Optional ontology name filter
            domain: Optional domain filter
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            Tuple of (ontology versions list, total count)
        """
        ...

    def get_latest_version_by_name_and_domain(
        self, name: str, domain: ScientificDomain, tenant_id: str
    ) -> Optional[OntologyVersion]:
        """Get the latest version of an ontology by name and domain.

        Args:
            name: Ontology name
            domain: Scientific domain
            tenant_id: Tenant identifier

        Returns:
            Latest ontology version if found, None otherwise
        """
        ...


@dataclass
class ListOntologyVersionsResponse(BaseResponseDTO):
    """Response from listing ontology versions."""

    versions: Optional[PaginatedResponse[OntologyVersionDTO]] = None


class ListOntologyVersionsUseCase(
    BaseUseCase[ListOntologyVersionsRequestDTO, ListOntologyVersionsResponse]
):
    """Use case for listing ontology versions with version history retrieval."""

    def __init__(
        self,
        ontology_repository: ExtendedOntologyRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            authorization_service: Service for authorization checks
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(
        self, request: ListOntologyVersionsRequestDTO
    ) -> None:
        """Validate the list ontology versions request.

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

        # Validate domain if provided
        if request.domain:
            try:
                ScientificDomain(request.domain)
            except ValueError:
                valid_domains = [d.value for d in ScientificDomain]
                raise ValidationError(
                    message=f"Domain must be one of: {', '.join(valid_domains)}",
                    field="domain",
                )

        # Validate ontology name if provided
        if request.ontology_name is not None:
            if not request.ontology_name.strip():
                raise ValidationError(
                    message="Ontology name cannot be empty if provided",
                    field="ontology_name",
                )

            if len(request.ontology_name) > 255:
                raise ValidationError(
                    message="Ontology name cannot exceed 255 characters",
                    field="ontology_name",
                )

        # Validate pagination if provided
        if request.pagination:
            # Ensure page and page size are within acceptable ranges
            if request.pagination.page < 1:
                raise ValidationError(
                    message="Page must be greater than or equal to 1",
                    field="pagination.page",
                )

            if request.pagination.page_size < 1 or request.pagination.page_size > 100:
                raise ValidationError(
                    message="Page size must be between 1 and 100",
                    field="pagination.page_size",
                )

    async def _execute_internal(
        self, request: ListOntologyVersionsRequestDTO
    ) -> ListOntologyVersionsResponse:
        """Execute the ontology versions listing.

        Args:
            request: The validated request

        Returns:
            Response containing the paginated list of ontology versions

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="list_ontology_versions",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check authorization - user needs read access to tenant ontologies
                self.authorization_service.check_permission(
                    request.user_id, request.tenant_id, "read_ontologies"
                )

                # Set up pagination parameters
                pagination = request.pagination or PaginationParams()

                # Convert domain string to enum if provided
                domain_filter = None
                if request.domain:
                    domain_filter = ScientificDomain(request.domain)

                # Get ontology versions from repository
                versions, total_count = (
                    self.ontology_repository.list_versions_by_tenant(
                        tenant_id=request.tenant_id,
                        ontology_name=request.ontology_name,
                        domain=domain_filter,
                        page=pagination.page,
                        page_size=pagination.page_size,
                    )
                )

                # Determine which versions are latest for their respective ontologies
                latest_versions = self._identify_latest_versions(
                    versions, request.tenant_id
                )

                # Convert to DTOs
                version_dtos = [
                    self._create_version_dto(version, version.id in latest_versions)
                    for version in versions
                ]

                # Calculate pagination info
                total_pages = (
                    total_count + pagination.page_size - 1
                ) // pagination.page_size
                has_next_page = pagination.page < total_pages
                has_previous_page = pagination.page > 1

                # Create paginated response
                paginated_response = PaginatedResponse[OntologyVersionDTO](
                    items=version_dtos,
                    total_items=total_count,
                    total_pages=total_pages,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    has_next_page=has_next_page,
                    has_previous_page=has_previous_page,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_versions_listed",
                    value=len(version_dtos),
                    tenant_id=request.tenant_id,
                    total_count=total_count,
                )

                return ListOntologyVersionsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    versions=paginated_response,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_versions_listing_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return ListOntologyVersionsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to list ontology versions: {str(e)}",
                    error_code="ONTOLOGY_VERSIONS_LISTING_FAILED",
                ) from e

    def _identify_latest_versions(
        self, versions: List[OntologyVersion], tenant_id: str
    ) -> set:
        """Identify which versions are the latest for their respective ontologies.

        Args:
            versions: List of ontology versions
            tenant_id: Tenant identifier

        Returns:
            Set of version IDs that are the latest versions
        """
        latest_versions = set()

        # Group versions by ontology name and domain
        ontology_groups = {}
        for version in versions:
            ontology_name = self.ontology_repository.get_version_name(
                version.id, tenant_id
            )
            ontology_key = (ontology_name, version.domain)

            if ontology_key not in ontology_groups:
                ontology_groups[ontology_key] = []
            ontology_groups[ontology_key].append(version)

        # Find the latest version in each group (most recent created_at)
        for group_versions in ontology_groups.values():
            if group_versions:
                latest_version = max(group_versions, key=lambda v: v.created_at)
                latest_versions.add(latest_version.id)

        return latest_versions

    def _create_version_dto(
        self, version: OntologyVersion, is_latest: bool
    ) -> OntologyVersionDTO:
        """Create an OntologyVersionDTO from an OntologyVersion entity.

        Args:
            version: The ontology version entity
            is_latest: Whether this is the latest version

        Returns:
            OntologyVersionDTO
        """
        # Generate version string based on lineage depth
        version_string = f"{version.get_version_lineage_depth() + 1}.0.0"

        # Retrieve stored ontology name
        ontology_name = (
            self.ontology_repository.get_version_name(version.id, version.tenant_id)
            or f"{version.domain.value.title()} Ontology"
        )

        return OntologyVersionDTO(
            id=version.id,
            ontology_name=ontology_name,
            version=version_string,
            parent_version_id=version.parent_version,
            domain=version.domain.value,
            tenant_id=version.tenant_id,
            created_at=version.created_at,
            checksum=version.checksum,
            axiom_count=len(version.axioms),
            is_latest=is_latest,
            competency_questions=version.metadata.get("competency_questions"),
        )


class ListOntologyVersionsByNameUseCase(
    BaseUseCase[ListOntologyVersionsRequestDTO, ListOntologyVersionsResponse]
):
    """Specialized use case for listing versions of a specific ontology by name."""

    def __init__(
        self,
        ontology_repository: ExtendedOntologyRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies."""
        super().__init__()
        self.ontology_repository = ontology_repository
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(
        self, request: ListOntologyVersionsRequestDTO
    ) -> None:
        """Validate the request - ontology name is required for this use case."""
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.ontology_name or not request.ontology_name.strip():
            raise ValidationError(
                message="Ontology name is required for version history listing",
                field="ontology_name",
            )

        if len(request.ontology_name) > 255:
            raise ValidationError(
                message="Ontology name cannot exceed 255 characters",
                field="ontology_name",
            )

    async def _execute_internal(
        self, request: ListOntologyVersionsRequestDTO
    ) -> ListOntologyVersionsResponse:
        """Execute the ontology version history listing for a specific ontology."""
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="list_ontology_versions_by_name",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            ontology_name=request.ontology_name,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    request.user_id, request.tenant_id, "read_ontologies"
                )

                # Get all versions of the specific ontology
                versions = self.ontology_repository.list_versions(
                    name=request.ontology_name, tenant_id=request.tenant_id
                )

                # Sort by creation date (newest first)
                versions.sort(key=lambda v: v.created_at, reverse=True)

                # Apply pagination
                pagination = request.pagination or PaginationParams()
                start_idx = (pagination.page - 1) * pagination.page_size
                end_idx = start_idx + pagination.page_size
                paginated_versions = versions[start_idx:end_idx]

                # Convert to DTOs (first version is latest)
                version_dtos = [
                    self._create_version_dto(version, i == 0)
                    for i, version in enumerate(paginated_versions)
                ]

                # Calculate pagination info
                total_count = len(versions)
                total_pages = (
                    total_count + pagination.page_size - 1
                ) // pagination.page_size
                has_next_page = pagination.page < total_pages
                has_previous_page = pagination.page > 1

                # Create paginated response
                paginated_response = PaginatedResponse[OntologyVersionDTO](
                    items=version_dtos,
                    total_items=total_count,
                    total_pages=total_pages,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    has_next_page=has_next_page,
                    has_previous_page=has_previous_page,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_version_history_listed",
                    value=len(version_dtos),
                    tenant_id=request.tenant_id,
                    ontology_name=request.ontology_name,
                    total_versions=total_count,
                )

                return ListOntologyVersionsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    versions=paginated_response,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_version_history_listing_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return ListOntologyVersionsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to list ontology version history: {str(e)}",
                    error_code="ONTOLOGY_VERSION_HISTORY_LISTING_FAILED",
                ) from e

    def _create_version_dto(
        self, version: OntologyVersion, is_latest: bool
    ) -> OntologyVersionDTO:
        """Create an OntologyVersionDTO from an OntologyVersion entity."""
        version_string = f"{version.get_version_lineage_depth() + 1}.0.0"

        ontology_name = (
            self.ontology_repository.get_version_name(version.id, version.tenant_id)
            or "Ontology"
        )

        return OntologyVersionDTO(
            id=version.id,
            ontology_name=ontology_name,
            version=version_string,
            parent_version_id=version.parent_version,
            domain=version.domain.value,
            tenant_id=version.tenant_id,
            created_at=version.created_at,
            checksum=version.checksum,
            axiom_count=len(version.axioms),
            is_latest=is_latest,
            competency_questions=version.metadata.get("competency_questions"),
        )
