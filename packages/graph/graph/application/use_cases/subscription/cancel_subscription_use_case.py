"""Cancel subscription use case implementation."""

from datetime import datetime

from application.exceptions import (
    BusinessRuleViolationError,
    NotFoundError,
    ValidationError,
)
from application.ports import (
    AuditServicePort,
    AuthorizationServicePort,
    BillingAdapterPort,
    OrganizationRepositoryPort,
    SubscriptionRepositoryPort,
)
from application.use_cases.dto import CancelSubscriptionRequestDTO, SubscriptionDTO
from domain.entities import Subscription, SubscriptionTier


class CancelSubscriptionUseCase:
    """Use case for cancelling a subscription."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        billing_adapter: BillingAdapterPort,
        authorization_service: AuthorizationServicePort,
        audit_service: AuditServicePort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            subscription_repository: Repository for subscription operations
            organization_repository: Repository for organization operations
            billing_adapter: Adapter for external billing system
            authorization_service: Service for authorization checks
            audit_service: Service for audit logging
        """
        self.subscription_repository = subscription_repository
        self.organization_repository = organization_repository
        self.billing_adapter = billing_adapter
        self.authorization_service = authorization_service
        self.audit_service = audit_service

    def execute(self, request: CancelSubscriptionRequestDTO) -> SubscriptionDTO:
        """Execute the cancel subscription use case.

        Args:
            request: Cancel subscription request DTO

        Returns:
            Cancelled subscription DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When subscription cancellation fails
        """
        # Validate input
        self._validate_input(request)

        # Get existing subscription
        subscription = self.subscription_repository.get_by_id(request.subscription_id)
        if not subscription:
            raise NotFoundError(
                message=f"Subscription with ID {request.subscription_id} not found",
                resource_type="subscription",
                resource_id=request.subscription_id,
            )

        # Check if subscription is already cancelled
        if subscription.status == "cancelled":
            raise BusinessRuleViolationError(
                message="Subscription is already cancelled",
                rule_name="subscription_not_already_cancelled",
            )

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.cancelled_by_user_id,
            resource_id=subscription.organization_id,
            action="manage_billing",
        )

        # Get organization
        organization = self.organization_repository.get_by_id(
            subscription.organization_id
        )
        if not organization:
            raise NotFoundError(
                message=f"Organization with ID {subscription.organization_id} not found",
                resource_type="organization",
                resource_id=subscription.organization_id,
            )

        # Cancel subscription in external billing system if it has external ID
        if subscription.external_subscription_id:
            self.billing_adapter.cancel_subscription(
                external_subscription_id=subscription.external_subscription_id,
                cancel_at_period_end=request.cancel_at_period_end,
            )

        # Update subscription status
        subscription.cancel(cancel_at_period_end=request.cancel_at_period_end)

        # If immediate cancellation, downgrade organization to free tier
        if not request.cancel_at_period_end:
            organization.update_subscription(SubscriptionTier.FREE, None)
            self.organization_repository.update(organization)

        # Save updated subscription
        updated_subscription = self.subscription_repository.update(subscription)

        # Log audit activity
        self.audit_service.log_activity(
            user_id=request.cancelled_by_user_id,
            activity_type="subscription_cancelled",
            description=f"Cancelled subscription for organization {organization.name}",
            resource_id=subscription.id,
            resource_type="subscription",
            metadata={
                "organization_id": subscription.organization_id,
                "tier": subscription.tier.value,
                "cancel_at_period_end": request.cancel_at_period_end,
                "cancellation_reason": request.cancellation_reason,
                "cancelled_at": datetime.utcnow().isoformat(),
            },
        )

        # Return DTO
        return self._to_dto(updated_subscription)

    def _validate_input(self, request: CancelSubscriptionRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Cancel subscription request DTO

        Raises:
            ValidationError: When validation fails
        """
        if not request.subscription_id:
            raise ValidationError(
                message="Subscription ID is required", field="subscription_id"
            )

        if not request.cancelled_by_user_id:
            raise ValidationError(
                message="Cancelled by user ID is required", field="cancelled_by_user_id"
            )

        # Validate cancel_at_period_end is boolean
        if not isinstance(request.cancel_at_period_end, bool):
            raise ValidationError(
                message="Cancel at period end must be a boolean value",
                field="cancel_at_period_end",
            )

    def _to_dto(self, subscription: Subscription) -> SubscriptionDTO:
        """Convert subscription entity to DTO.

        Args:
            subscription: Subscription entity

        Returns:
            Subscription DTO
        """
        return SubscriptionDTO(
            id=subscription.id,
            organization_id=subscription.organization_id,
            external_subscription_id=subscription.external_subscription_id,
            tier=subscription.tier.value,
            billing_cycle=subscription.billing_cycle,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            payment_method_id=subscription.payment_method_id,
            status=subscription.status,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
