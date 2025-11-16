"""Use case for managing team members."""

from dataclasses import dataclass
from datetime import datetime
from typing import List

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
    TracingPort,
    UserRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    ManageTeamMembersRequestDTO,
    UserDTO,
)
from domain.entities import User


@dataclass
class ManageTeamMembersResponse(BaseResponseDTO):
    """Response from team member management."""

    affected_users: List[UserDTO] = None
    action_performed: str = ""

    def __post_init__(self):
        if self.affected_users is None:
            self.affected_users = []


class ManageTeamMembersUseCase(
    BaseUseCase[ManageTeamMembersRequestDTO, ManageTeamMembersResponse]
):
    """Use case for managing team members with add/remove functionality."""

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
            audit_service: Service for audit logging
            tracer: Tracing service for observability
        """
        super().__init__()
        self.user_repository = user_repository
        self.organization_repository = organization_repository
        self.authorization_service = authorization_service
        self.audit_service = audit_service
        self.tracer = tracer

    def _validate_request_internal(self, request: ManageTeamMembersRequestDTO) -> None:
        """Validate the manage team members request.

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

        # Validate action
        valid_actions = ["add", "remove"]
        if request.action not in valid_actions:
            raise ValidationError(
                message=f"Action must be one of: {', '.join(valid_actions)}",
                field="action",
            )

        # Validate user_ids
        if not request.user_ids or len(request.user_ids) == 0:
            raise ValidationError(
                message="At least one user ID must be provided", field="user_ids"
            )

        # Check for duplicate user IDs
        if len(request.user_ids) != len(set(request.user_ids)):
            raise ValidationError(
                message="Duplicate user IDs are not allowed", field="user_ids"
            )

        # Validate each user ID
        for user_id in request.user_ids:
            if not user_id or not user_id.strip():
                raise ValidationError(
                    message="User IDs cannot be empty", field="user_ids"
                )

        # Validate manager_user_id
        if not request.manager_user_id or not request.manager_user_id.strip():
            raise ValidationError(
                message="Manager user ID is required and cannot be empty",
                field="manager_user_id",
            )

    async def _execute_internal(
        self, request: ManageTeamMembersRequestDTO
    ) -> ManageTeamMembersResponse:
        """Execute the team member management.

        Args:
            request: The validated request

        Returns:
            Response containing the affected users

        Raises:
            BusinessRuleViolationError: If business rules are violated
            NotFoundError: If referenced resources don't exist
            AuthorizationError: If user lacks permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="manage_team_members",
            tenant_id=request.organization_id,
            user_id=request.manager_user_id,
        ) as span:
            try:
                # Check authorization - user must have permission to manage users in the organization
                self.authorization_service.check_permission(
                    user_id=request.manager_user_id,
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
                        message="Cannot manage team members in inactive organization",
                        rule_name="active_organization_required",
                    )

                # Get all users to be affected
                affected_users = []
                not_found_users = []

                for user_id in request.user_ids:
                    user = self.user_repository.get_by_id(user_id)
                    if not user:
                        not_found_users.append(user_id)
                    else:
                        affected_users.append(user)

                # If any users not found, report error
                if not_found_users:
                    raise NotFoundError(
                        message=f"Users not found: {', '.join(not_found_users)}",
                        resource_type="user",
                        resource_id=", ".join(not_found_users),
                    )

                # Process based on action
                if request.action == "add":
                    result_users = await self._add_users_to_organization(
                        affected_users, organization, request.manager_user_id
                    )
                elif request.action == "remove":
                    result_users = await self._remove_users_from_organization(
                        affected_users, organization, request.manager_user_id
                    )
                else:
                    # This should not happen due to validation, but just in case
                    raise ValidationError(
                        message=f"Invalid action: {request.action}", field="action"
                    )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name=f"team_members_{request.action}",
                    value=len(result_users),
                    tenant_id=request.organization_id,
                    action=request.action,
                )

                # Create response DTOs
                user_dtos = [
                    UserDTO(
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
                    for user in result_users
                ]

                return ManageTeamMembersResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    affected_users=user_dtos,
                    action_performed=request.action,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="team_management_errors",
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
                    return ManageTeamMembersResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                        action_performed=request.action,
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to manage team members: {str(e)}",
                    error_code="TEAM_MANAGEMENT_FAILED",
                ) from e

    async def _add_users_to_organization(
        self, users: List[User], organization, manager_user_id: str
    ) -> List[User]:
        """Add users to the organization.

        Args:
            users: List of users to add
            organization: Target organization
            manager_user_id: ID of user performing the action

        Returns:
            List of users that were successfully added

        Raises:
            BusinessRuleViolationError: If business rules are violated
        """
        added_users = []

        for user in users:
            # Check if user is already in the organization
            if user.organization_id == organization.id:
                # User is already in the organization, skip
                continue

            # Check if user is active
            if not user.is_active:
                raise BusinessRuleViolationError(
                    message=f"Cannot add inactive user '{user.name}' to organization",
                    rule_name="active_user_required",
                )

            # Update user's organization
            user.organization_id = organization.id
            user.updated_at = datetime.utcnow()

            # Save updated user
            updated_user = self.user_repository.update(user)
            added_users.append(updated_user)

            # Log audit activity
            self.audit_service.log_activity(
                user_id=manager_user_id,
                activity_type="user_added_to_organization",
                description=f"Added user '{user.name}' to organization '{organization.name}'",
                resource_id=user.id,
                resource_type="user",
                metadata={
                    "user_email": user.email,
                    "organization_id": organization.id,
                    "organization_name": organization.name,
                    "action": "add",
                },
            )

        return added_users

    async def _remove_users_from_organization(
        self, users: List[User], organization, manager_user_id: str
    ) -> List[User]:
        """Remove users from the organization.

        Args:
            users: List of users to remove
            organization: Source organization
            manager_user_id: ID of user performing the action

        Returns:
            List of users that were successfully removed

        Raises:
            BusinessRuleViolationError: If business rules are violated
        """
        removed_users = []

        for user in users:
            # Check if user is in the organization
            if user.organization_id != organization.id:
                # User is not in the organization, skip
                continue

            # Check if user is trying to remove themselves
            if user.id == manager_user_id:
                raise BusinessRuleViolationError(
                    message="Users cannot remove themselves from the organization",
                    rule_name="no_self_removal",
                )

            # Deactivate user instead of changing organization
            # This maintains data integrity and audit trail
            user.deactivate()

            # Save updated user
            updated_user = self.user_repository.update(user)
            removed_users.append(updated_user)

            # Log audit activity
            self.audit_service.log_activity(
                user_id=manager_user_id,
                activity_type="user_removed_from_organization",
                description=f"Removed user '{user.name}' from organization '{organization.name}'",
                resource_id=user.id,
                resource_type="user",
                metadata={
                    "user_email": user.email,
                    "organization_id": organization.id,
                    "organization_name": organization.name,
                    "action": "remove",
                },
            )

        return removed_users
