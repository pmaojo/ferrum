"""Use case for creating organizations."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    ValidationError,
)
from application.ports import (
    AuditServicePort,
    OrganizationRepositoryPort,
    PasswordServicePort,
    TracingPort,
    UserRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    CreateOrganizationRequestDTO,
    OrganizationDTO,
    UserDTO,
)
from domain.entities import Organization, SubscriptionTier, User, UserRole


@dataclass
class CreateOrganizationResponse(BaseResponseDTO):
    """Response from organization creation."""

    organization: Optional[OrganizationDTO] = None
    admin_user: Optional[UserDTO] = None


class CreateOrganizationUseCase(
    BaseUseCase[CreateOrganizationRequestDTO, CreateOrganizationResponse]
):
    """Use case for creating organizations with tenant isolation setup."""

    def __init__(
        self,
        organization_repository: OrganizationRepositoryPort,
        user_repository: UserRepositoryPort,
        password_service: PasswordServicePort,
        audit_service: AuditServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            organization_repository: Repository for organization operations
            user_repository: Repository for user operations
            password_service: Service for password hashing
            audit_service: Service for audit logging
            tracer: Tracing service for observability
        """
        super().__init__()
        self.organization_repository = organization_repository
        self.user_repository = user_repository
        self.password_service = password_service
        self.audit_service = audit_service
        self.tracer = tracer

    def _validate_request_internal(self, request: CreateOrganizationRequestDTO) -> None:
        """Validate the create organization request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate organization name
        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Organization name is required and cannot be empty",
                field="name",
            )

        if len(request.name) > 255:
            raise ValidationError(
                message="Organization name cannot exceed 255 characters", field="name"
            )

        # Validate subscription tier
        valid_tiers = [tier.value for tier in SubscriptionTier]
        if request.subscription_tier not in valid_tiers:
            raise ValidationError(
                message=f"Subscription tier must be one of: {', '.join(valid_tiers)}",
                field="subscription_tier",
            )

        # Validate admin user details if provided
        if request.admin_email:
            # Basic email format validation
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, request.admin_email):
                raise ValidationError(
                    message="Admin email must be in valid format", field="admin_email"
                )

            if len(request.admin_email) > 255:
                raise ValidationError(
                    message="Admin email cannot exceed 255 characters",
                    field="admin_email",
                )

        if request.admin_name:
            if len(request.admin_name) > 255:
                raise ValidationError(
                    message="Admin name cannot exceed 255 characters",
                    field="admin_name",
                )

        if request.admin_password:
            if len(request.admin_password) < 8:
                raise ValidationError(
                    message="Admin password must be at least 8 characters long",
                    field="admin_password",
                )

            if len(request.admin_password) > 128:
                raise ValidationError(
                    message="Admin password cannot exceed 128 characters",
                    field="admin_password",
                )

            # Password complexity validation
            if not re.search(r"[A-Z]", request.admin_password):
                raise ValidationError(
                    message="Admin password must contain at least one uppercase letter",
                    field="admin_password",
                )

            if not re.search(r"[a-z]", request.admin_password):
                raise ValidationError(
                    message="Admin password must contain at least one lowercase letter",
                    field="admin_password",
                )

            if not re.search(r"\d", request.admin_password):
                raise ValidationError(
                    message="Admin password must contain at least one digit",
                    field="admin_password",
                )

        # If admin details are provided, all must be provided
        admin_fields = [request.admin_email, request.admin_name, request.admin_password]
        if any(admin_fields) and not all(admin_fields):
            raise ValidationError(
                message="If admin details are provided, admin_email, admin_name, and admin_password are all required",
                field="admin_details",
            )

    async def _execute_internal(
        self, request: CreateOrganizationRequestDTO
    ) -> CreateOrganizationResponse:
        """Execute the organization creation.

        Args:
            request: The validated request

        Returns:
            Response containing the created organization and admin user

        Raises:
            BusinessRuleViolationError: If business rules are violated
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="create_organization",
            tenant_id="system",  # System-level operation
            user_id="system",
        ) as span:
            try:
                # Check if organization with same name already exists
                existing_org = self.organization_repository.get_by_name(request.name)
                if existing_org:
                    raise BusinessRuleViolationError(
                        message=f"Organization with name '{request.name}' already exists",
                        rule_name="unique_organization_name",
                    )

                # Check if admin email already exists (if provided)
                admin_user = None
                if request.admin_email:
                    existing_user = self.user_repository.get_by_email(
                        request.admin_email
                    )
                    if existing_user:
                        raise BusinessRuleViolationError(
                            message=f"User with email '{request.admin_email}' already exists",
                            rule_name="unique_email",
                        )

                # Create organization entity
                subscription_tier = SubscriptionTier(request.subscription_tier)
                organization = Organization.create(
                    name=request.name, subscription_tier=subscription_tier
                )

                # Save organization to repository
                created_org = self.organization_repository.create(organization)

                # Create admin user if details provided
                if (
                    request.admin_email
                    and request.admin_name
                    and request.admin_password
                ):
                    # Hash the password
                    password_hash = self.password_service.hash_password(
                        request.admin_password
                    )

                    # Create admin user entity
                    admin_user = User.create(
                        email=request.admin_email,
                        name=request.admin_name,
                        password_hash=password_hash,
                        organization_id=created_org.id,
                        role=UserRole.ADMIN,
                    )

                    # Save admin user to repository
                    created_admin = self.user_repository.create(admin_user)

                    # Log admin user creation
                    self.audit_service.log_activity(
                        user_id="system",
                        activity_type="admin_user_created",
                        description=f"Created admin user '{created_admin.name}' for organization '{created_org.name}'",
                        resource_id=created_admin.id,
                        resource_type="user",
                        metadata={
                            "admin_user_email": created_admin.email,
                            "organization_id": created_org.id,
                            "organization_name": created_org.name,
                        },
                    )

                    admin_user = created_admin

                # Log organization creation
                self.audit_service.log_activity(
                    user_id="system",
                    activity_type="organization_created",
                    description=f"Created organization '{created_org.name}' with subscription tier '{created_org.subscription_tier.value}'",
                    resource_id=created_org.id,
                    resource_type="organization",
                    metadata={
                        "organization_name": created_org.name,
                        "subscription_tier": created_org.subscription_tier.value,
                        "admin_user_created": admin_user is not None,
                    },
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="organization_created",
                    value=1,
                    tenant_id=created_org.id,
                    subscription_tier=created_org.subscription_tier.value,
                )

                # Create response DTOs
                org_dto = OrganizationDTO(
                    id=created_org.id,
                    name=created_org.name,
                    subscription_tier=created_org.subscription_tier.value,
                    subscription_expires_at=created_org.subscription_expires_at,
                    created_at=created_org.created_at,
                    updated_at=created_org.updated_at,
                    is_active=created_org.is_active,
                )

                admin_user_dto = None
                if admin_user:
                    admin_user_dto = UserDTO(
                        id=admin_user.id,
                        email=admin_user.email,
                        name=admin_user.name,
                        organization_id=admin_user.organization_id,
                        role=admin_user.role.value,
                        created_at=admin_user.created_at,
                        updated_at=admin_user.updated_at,
                        last_login=admin_user.last_login,
                        is_active=admin_user.is_active,
                    )

                return CreateOrganizationResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    organization=org_dto,
                    admin_user=admin_user_dto,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="organization_creation_errors",
                    value=1,
                    tenant_id="system",
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, BusinessRuleViolationError)):
                    return CreateOrganizationResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to create organization: {str(e)}",
                    error_code="ORGANIZATION_CREATION_FAILED",
                ) from e
