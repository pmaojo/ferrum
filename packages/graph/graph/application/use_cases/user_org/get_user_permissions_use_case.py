"""Use case for retrieving user permissions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import AuthorizationServicePort, TracingPort, UserRepositoryPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    GetUserPermissionsRequestDTO,
    UserPermissionsDTO,
)


@dataclass
class GetUserPermissionsResponse(BaseResponseDTO):
    """Response from getting user permissions."""

    permissions: Optional[UserPermissionsDTO] = None


class GetUserPermissionsUseCase(
    BaseUseCase[GetUserPermissionsRequestDTO, GetUserPermissionsResponse]
):
    """Use case for retrieving user permissions with permission calculation logic."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            user_repository: Repository for user operations
            authorization_service: Service for authorization checks and permission calculation
            tracer: Tracing service for observability
        """
        super().__init__()
        self.user_repository = user_repository
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: GetUserPermissionsRequestDTO) -> None:
        """Validate the get user permissions request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        # Validate requesting_user_id
        if not request.requesting_user_id or not request.requesting_user_id.strip():
            raise ValidationError(
                message="Requesting user ID is required and cannot be empty",
                field="requesting_user_id",
            )

    async def _execute_internal(
        self, request: GetUserPermissionsRequestDTO
    ) -> GetUserPermissionsResponse:
        """Execute the user permissions retrieval.

        Args:
            request: The validated request

        Returns:
            Response containing the user permissions

        Raises:
            NotFoundError: If referenced resources don't exist
            AuthorizationError: If user lacks permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="get_user_permissions",
            tenant_id="system",  # We'll get the actual tenant from the user
            user_id=request.requesting_user_id,
        ) as span:
            try:
                # Get the user whose permissions are being requested
                user = self.user_repository.get_by_id(request.user_id)
                if not user:
                    raise NotFoundError(
                        message=f"User with ID '{request.user_id}' not found",
                        resource_type="user",
                        resource_id=request.user_id,
                    )

                # Get the requesting user
                requesting_user = self.user_repository.get_by_id(
                    request.requesting_user_id
                )
                if not requesting_user:
                    raise NotFoundError(
                        message=f"Requesting user with ID '{request.requesting_user_id}' not found",
                        resource_type="user",
                        resource_id=request.requesting_user_id,
                    )

                # Check authorization - user must have permission to view permissions
                # Users can always view their own permissions
                # Admins can view permissions of users in their organization
                if request.user_id != request.requesting_user_id:
                    # Different user - check if requesting user can view permissions
                    if user.organization_id != requesting_user.organization_id:
                        raise AuthorizationError(
                            message="Cannot view permissions of users in different organizations",
                            user_id=request.requesting_user_id,
                            resource_id=request.user_id,
                            required_permission="view_user_permissions",
                        )

                    # Check if requesting user has permission to view user permissions
                    self.authorization_service.check_permission(
                        user_id=request.requesting_user_id,
                        resource_id=user.organization_id,
                        action="view_user_permissions",
                    )

                # Get user permissions from authorization service
                general_permissions = self.authorization_service.get_user_permissions(
                    user_id=request.user_id, resource_id=None
                )

                # Get resource-specific permissions if resource_id is provided
                resource_permissions = {}
                if request.resource_id:
                    resource_specific_permissions = (
                        self.authorization_service.get_user_permissions(
                            user_id=request.user_id, resource_id=request.resource_id
                        )
                    )
                    resource_permissions[request.resource_id] = (
                        resource_specific_permissions
                    )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="user_permissions_retrieved",
                    value=1,
                    tenant_id=user.organization_id,
                    user_role=user.role.value,
                )

                # Create response DTO
                permissions_dto = UserPermissionsDTO(
                    user_id=user.id,
                    organization_id=user.organization_id,
                    role=user.role.value,
                    permissions=general_permissions,
                    resource_permissions=resource_permissions,
                )

                return GetUserPermissionsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    permissions=permissions_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="user_permissions_retrieval_errors",
                    value=1,
                    tenant_id="system",
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return GetUserPermissionsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to retrieve user permissions: {str(e)}",
                    error_code="USER_PERMISSIONS_RETRIEVAL_FAILED",
                ) from e
