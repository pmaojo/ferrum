"""Use case for updating users."""

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
from application.ports import (
    AuditServicePort,
    AuthorizationServicePort,
    TracingPort,
    UserRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, UpdateUserRequestDTO, UserDTO
from domain.entities import UserRole


@dataclass
class UpdateUserResponse(BaseResponseDTO):
    """Response from user update."""

    user: Optional[UserDTO] = None


class UpdateUserUseCase(BaseUseCase[UpdateUserRequestDTO, UpdateUserResponse]):
    """Use case for updating users with validation and business rules."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        authorization_service: AuthorizationServicePort,
        audit_service: AuditServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            user_repository: Repository for user operations
            authorization_service: Service for authorization checks
            audit_service: Service for audit logging
            tracer: Tracing service for observability
        """
        super().__init__()
        self.user_repository = user_repository
        self.authorization_service = authorization_service
        self.audit_service = audit_service
        self.tracer = tracer

    def _validate_request_internal(self, request: UpdateUserRequestDTO) -> None:
        """Validate the update user request.

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

        # Validate updated_by_user_id
        if not request.updated_by_user_id or not request.updated_by_user_id.strip():
            raise ValidationError(
                message="Updated by user ID is required and cannot be empty",
                field="updated_by_user_id",
            )

        # Validate name if provided
        if request.name is not None:
            if not request.name.strip():
                raise ValidationError(
                    message="Name cannot be empty if provided", field="name"
                )

            if len(request.name) > 255:
                raise ValidationError(
                    message="Name cannot exceed 255 characters", field="name"
                )

        # Validate role if provided
        if request.role is not None:
            valid_roles = [role.value for role in UserRole]
            if request.role not in valid_roles:
                raise ValidationError(
                    message=f"Role must be one of: {', '.join(valid_roles)}",
                    field="role",
                )

        # Validate is_active if provided
        if request.is_active is not None:
            if not isinstance(request.is_active, bool):
                raise ValidationError(
                    message="is_active must be a boolean value", field="is_active"
                )

    async def _execute_internal(
        self, request: UpdateUserRequestDTO
    ) -> UpdateUserResponse:
        """Execute the user update.

        Args:
            request: The validated request

        Returns:
            Response containing the updated user

        Raises:
            BusinessRuleViolationError: If business rules are violated
            NotFoundError: If referenced resources don't exist
            AuthorizationError: If user lacks permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="update_user",
            tenant_id="system",  # We'll get the actual tenant from the user
            user_id=request.updated_by_user_id,
        ) as span:
            try:
                # Get the user to be updated
                user = self.user_repository.get_by_id(request.user_id)
                if not user:
                    raise NotFoundError(
                        message=f"User with ID '{request.user_id}' not found",
                        resource_type="user",
                        resource_id=request.user_id,
                    )

                # Check authorization - user must have permission to manage users in the organization
                # or be updating their own profile (with limited fields)
                if request.updated_by_user_id == request.user_id:
                    # Self-update - only allow name changes
                    if request.role is not None or request.is_active is not None:
                        raise AuthorizationError(
                            message="Users can only update their own name",
                            user_id=request.updated_by_user_id,
                            resource_id=request.user_id,
                            required_permission="self_update_limited",
                        )
                else:
                    # Admin update - check manage_users permission
                    self.authorization_service.check_permission(
                        user_id=request.updated_by_user_id,
                        resource_id=user.organization_id,
                        action="manage_users",
                    )

                # Check if user is active
                if not user.is_active:
                    raise BusinessRuleViolationError(
                        message="Cannot update inactive user",
                        rule_name="active_user_required",
                    )

                # Track changes for audit
                changes = {}

                # Update fields if provided
                if request.name is not None and request.name != user.name:
                    changes["name"] = {"old": user.name, "new": request.name}
                    user.name = request.name

                if request.role is not None and request.role != user.role.value:
                    old_role = user.role.value
                    new_role = UserRole(request.role)
                    changes["role"] = {"old": old_role, "new": request.role}
                    user.update_role(new_role)

                if (
                    request.is_active is not None
                    and request.is_active != user.is_active
                ):
                    changes["is_active"] = {
                        "old": user.is_active,
                        "new": request.is_active,
                    }
                    if request.is_active:
                        user.activate()
                    else:
                        user.deactivate()

                # Only update if there are changes
                if not changes:
                    # No changes, return current user
                    user_dto = UserDTO(
                        id=user.id,
                        email=user.email,
                        name=user.name,
                        organization_id=user.organization_id,
                        role=user.role.value,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                        last_login=user.last_login,
                        is_active=user.is_active,
                    )

                    processing_time = (
                        datetime.utcnow() - start_time
                    ).total_seconds() * 1000
                    return UpdateUserResponse(
                        success=True, processing_time_ms=processing_time, user=user_dto
                    )

                # Save to repository
                updated_user = self.user_repository.update(user)

                # Log audit activity
                self.audit_service.log_activity(
                    user_id=request.updated_by_user_id,
                    activity_type="user_updated",
                    description=f"Updated user '{updated_user.name}' with email '{updated_user.email}'",
                    resource_id=updated_user.id,
                    resource_type="user",
                    metadata={
                        "updated_user_email": updated_user.email,
                        "changes": changes,
                        "organization_id": updated_user.organization_id,
                    },
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="user_updated",
                    value=1,
                    tenant_id=updated_user.organization_id,
                    role=updated_user.role.value,
                )

                # Create response DTO
                user_dto = UserDTO(
                    id=updated_user.id,
                    email=updated_user.email,
                    name=updated_user.name,
                    organization_id=updated_user.organization_id,
                    role=updated_user.role.value,
                    created_at=updated_user.created_at,
                    updated_at=updated_user.updated_at,
                    last_login=updated_user.last_login,
                    is_active=updated_user.is_active,
                )

                return UpdateUserResponse(
                    success=True, processing_time_ms=processing_time, user=user_dto
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="user_update_errors",
                    value=1,
                    tenant_id="system",
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
                    return UpdateUserResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to update user: {str(e)}",
                    error_code="USER_UPDATE_FAILED",
                ) from e
