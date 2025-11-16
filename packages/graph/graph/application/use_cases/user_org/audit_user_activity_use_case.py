"""Use case for auditing user activity."""

from dataclasses import dataclass
from datetime import datetime

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import (
    AuditServicePort,
    AuthorizationServicePort,
    OrganizationRepositoryPort,
    TracingPort,
    UserRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    AuditUserActivityRequestDTO,
    BaseResponseDTO,
    PaginatedResponse,
    UserActivityDTO,
)


@dataclass
class AuditUserActivityResponse(BaseResponseDTO):
    """Response from user activity audit."""

    activities: PaginatedResponse[UserActivityDTO] = None

    def __post_init__(self):
        if self.activities is None:
            self.activities = PaginatedResponse(
                items=[],
                total_items=0,
                total_pages=0,
                page=1,
                page_size=20,
                has_next_page=False,
                has_previous_page=False,
            )


class AuditUserActivityUseCase(
    BaseUseCase[AuditUserActivityRequestDTO, AuditUserActivityResponse]
):
    """Use case for retrieving user activity history with filtering and pagination."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        authorization_service: AuthorizationServicePort,
        audit_service: AuditServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            user_repository: Repository for user operations
            organization_repository: Repository for organization operations
            authorization_service: Service for authorization checks
            audit_service: Service for audit operations
            tracer: Tracing service for observability
        """
        super().__init__()
        self.user_repository = user_repository
        self.organization_repository = organization_repository
        self.audit_service = audit_service
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: AuditUserActivityRequestDTO) -> None:
        """Validate the audit user activity request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate organization_id
        if not request.organization_id or not request.organization_id.strip():
            raise ValidationError(
                message="Organization ID is required and cannot be empty",
                field="organization_id",
            )

        # Validate requesting_user_id
        if not request.requesting_user_id or not request.requesting_user_id.strip():
            raise ValidationError(
                message="Requesting user ID is required and cannot be empty",
                field="requesting_user_id",
            )

        # Validate date range if provided
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise ValidationError(
                    message="Start date cannot be after end date", field="date_range"
                )

        # Validate pagination if provided
        if request.pagination:
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
        self, request: AuditUserActivityRequestDTO
    ) -> AuditUserActivityResponse:
        """Execute the user activity audit.

        Args:
            request: The validated request

        Returns:
            Response containing the user activity history

        Raises:
            NotFoundError: If referenced resources don't exist
            AuthorizationError: If user lacks permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="audit_user_activity",
            tenant_id=request.organization_id,
            user_id=request.requesting_user_id,
        ) as span:
            try:
                # Check if organization exists
                organization = self.organization_repository.get_by_id(
                    request.organization_id
                )
                if not organization:
                    raise NotFoundError(
                        message=f"Organization with ID '{request.organization_id}' not found",
                        resource_type="organization",
                        resource_id=request.organization_id,
                    )

                # Get requesting user
                requesting_user = self.user_repository.get_by_id(
                    request.requesting_user_id
                )
                if not requesting_user:
                    raise NotFoundError(
                        message=f"Requesting user with ID '{request.requesting_user_id}' not found",
                        resource_type="user",
                        resource_id=request.requesting_user_id,
                    )

                # Check authorization - user must have permission to view audit logs
                self.authorization_service.check_permission(
                    user_id=request.requesting_user_id,
                    resource_id=request.organization_id,
                    action="view_audit_logs",
                )

                # Validate that requesting user is in the organization
                if requesting_user.organization_id != request.organization_id:
                    raise AuthorizationError(
                        message="Cannot view audit logs for different organization",
                        user_id=request.requesting_user_id,
                        resource_id=request.organization_id,
                        required_permission="view_audit_logs",
                    )

                # If specific user_id is provided, validate it exists and is in the organization
                if request.user_id:
                    target_user = self.user_repository.get_by_id(request.user_id)
                    if not target_user:
                        raise NotFoundError(
                            message=f"User with ID '{request.user_id}' not found",
                            resource_type="user",
                            resource_id=request.user_id,
                        )

                    if target_user.organization_id != request.organization_id:
                        raise AuthorizationError(
                            message="Cannot view audit logs for users in different organizations",
                            user_id=request.requesting_user_id,
                            resource_id=request.user_id,
                            required_permission="view_audit_logs",
                        )

                # Set default pagination if not provided
                page = request.pagination.page if request.pagination else 1
                page_size = request.pagination.page_size if request.pagination else 20

                # Get user activity from audit service
                activity_records, total_count = self.audit_service.get_user_activity(
                    user_id=request.user_id,
                    organization_id=request.organization_id,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    activity_types=request.activity_types,
                    page=page,
                    page_size=page_size,
                )

                # Convert to DTOs
                activity_dtos = []
                for record in activity_records:
                    activity_dto = UserActivityDTO(
                        id=record.get("id", ""),
                        user_id=record.get("user_id", ""),
                        activity_type=record.get("activity_type", ""),
                        description=record.get("description", ""),
                        resource_id=record.get("resource_id"),
                        resource_type=record.get("resource_type"),
                        metadata=record.get("metadata", {}),
                        timestamp=record.get("timestamp", datetime.utcnow()),
                    )
                    activity_dtos.append(activity_dto)

                # Calculate pagination info
                total_pages = (total_count + page_size - 1) // page_size
                has_next_page = page < total_pages
                has_previous_page = page > 1

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="user_activity_audited",
                    value=len(activity_dtos),
                    tenant_id=request.organization_id,
                    audit_scope="organization" if not request.user_id else "user",
                )

                # Create paginated response
                paginated_activities = PaginatedResponse(
                    items=activity_dtos,
                    total_items=total_count,
                    total_pages=total_pages,
                    page=page,
                    page_size=page_size,
                    has_next_page=has_next_page,
                    has_previous_page=has_previous_page,
                )

                return AuditUserActivityResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    activities=paginated_activities,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="user_activity_audit_errors",
                    value=1,
                    tenant_id=request.organization_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return AuditUserActivityResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to audit user activity: {str(e)}",
                    error_code="USER_ACTIVITY_AUDIT_FAILED",
                ) from e
