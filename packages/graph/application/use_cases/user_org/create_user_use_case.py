"""Use case for creating users."""

import re
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
    OrganizationRepositoryPort,
    PasswordServicePort,
    TracingPort,
    UserRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, CreateUserRequestDTO, UserDTO
from domain.entities import User, UserRole


@dataclass
class CreateUserResponse(BaseResponseDTO):
    """Response from user creation."""

    user: Optional[UserDTO] = None


class CreateUserUseCase(BaseUseCase[CreateUserRequestDTO, CreateUserResponse]):
    """Use case for creating users with validation and business rules."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        password_service: PasswordServicePort,
        authorization_service: AuthorizationServicePort,
        audit_service: AuditServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            user_repository: Repository for user operations
            organization_repository: Repository for organization operations
            password_service: Service for password hashing
            authorization_service: Service for authorization checks
            audit_service: Service for audit logging
            tracer: Tracing service for observability
        """
        super().__init__()
        self.user_repository = user_repository
        self.organization_repository = organization_repository
        self.password_service = password_service
        self.authorization_service = authorization_service
        self.audit_service = audit_service
        self.tracer = tracer

    def _validate_request_internal(self, request: CreateUserRequestDTO) -> None:
        """Validate the create user request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate email
        if not request.email or not request.email.strip():
            raise ValidationError(
                message="Email is required and cannot be empty", field="email"
            )

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, request.email):
            raise ValidationError(
                message="Email must be in valid format", field="email"
            )

        if len(request.email) > 255:
            raise ValidationError(
                message="Email cannot exceed 255 characters", field="email"
            )

        # Validate name
        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Name is required and cannot be empty", field="name"
            )

        if len(request.name) > 255:
            raise ValidationError(
                message="Name cannot exceed 255 characters", field="name"
            )

        # Validate password
        if not request.password or len(request.password) < 8:
            raise ValidationError(
                message="Password must be at least 8 characters long", field="password"
            )

        if len(request.password) > 128:
            raise ValidationError(
                message="Password cannot exceed 128 characters", field="password"
            )

        # Password complexity validation
        if not re.search(r"[A-Z]", request.password):
            raise ValidationError(
                message="Password must contain at least one uppercase letter",
                field="password",
            )

        if not re.search(r"[a-z]", request.password):
            raise ValidationError(
                message="Password must contain at least one lowercase letter",
                field="password",
            )

        if not re.search(r"\d", request.password):
            raise ValidationError(
                message="Password must contain at least one digit", field="password"
            )

        # Validate organization_id
        if not request.organization_id or not request.organization_id.strip():
            raise ValidationError(
                message="Organization ID is required and cannot be empty",
                field="organization_id",
            )

        # Validate role
        valid_roles = [role.value for role in UserRole]
        if request.role not in valid_roles:
            raise ValidationError(
                message=f"Role must be one of: {', '.join(valid_roles)}", field="role"
            )

        # Validate created_by_user_id
        if not request.created_by_user_id or not request.created_by_user_id.strip():
            raise ValidationError(
                message="Created by user ID is required and cannot be empty",
                field="created_by_user_id",
            )

    async def _execute_internal(
        self, request: CreateUserRequestDTO
    ) -> CreateUserResponse:
        """Execute the user creation.

        Args:
            request: The validated request

        Returns:
            Response containing the created user

        Raises:
            BusinessRuleViolationError: If business rules are violated
            NotFoundError: If referenced resources don't exist
            AuthorizationError: If user lacks permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="create_user",
            tenant_id=request.organization_id,
            user_id=request.created_by_user_id,
        ) as span:
            try:
                # Check authorization - user must have permission to manage users in the organization
                self.authorization_service.check_permission(
                    user_id=request.created_by_user_id,
                    resource_id=request.organization_id,
                    action="manage_users",
                )

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

                # Check if organization is active
                if not organization.is_active:
                    raise BusinessRuleViolationError(
                        message="Cannot create users in inactive organization",
                        rule_name="active_organization_required",
                    )

                # Check if user with same email already exists
                existing_user = self.user_repository.get_by_email(request.email)
                if existing_user:
                    raise BusinessRuleViolationError(
                        message=f"User with email '{request.email}' already exists",
                        rule_name="unique_email",
                    )

                # Hash the password
                password_hash = self.password_service.hash_password(request.password)

                # Create user entity
                user_role = UserRole(request.role)
                user = User.create(
                    email=request.email,
                    name=request.name,
                    password_hash=password_hash,
                    organization_id=request.organization_id,
                    role=user_role,
                )

                # Save to repository
                created_user = self.user_repository.create(user)

                # Log audit activity
                self.audit_service.log_activity(
                    user_id=request.created_by_user_id,
                    activity_type="user_created",
                    description=f"Created user '{created_user.name}' with email '{created_user.email}'",
                    resource_id=created_user.id,
                    resource_type="user",
                    metadata={
                        "created_user_email": created_user.email,
                        "created_user_role": created_user.role.value,
                        "organization_id": created_user.organization_id,
                    },
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="user_created",
                    value=1,
                    tenant_id=request.organization_id,
                    role=created_user.role.value,
                )

                # Create response DTO
                user_dto = UserDTO(
                    id=created_user.id,
                    email=created_user.email,
                    name=created_user.name,
                    organization_id=created_user.organization_id,
                    role=created_user.role.value,
                    created_at=created_user.created_at,
                    updated_at=created_user.updated_at,
                    last_login=created_user.last_login,
                    is_active=created_user.is_active,
                )

                return CreateUserResponse(
                    success=True, processing_time_ms=processing_time, user=user_dto
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="user_creation_errors",
                    value=1,
                    tenant_id=request.organization_id,
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
                    return CreateUserResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to create user: {str(e)}",
                    error_code="USER_CREATION_FAILED",
                ) from e
