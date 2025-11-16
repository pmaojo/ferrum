"""Update subscription use case implementation."""

from datetime import datetime

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuditServicePort,
    AuthorizationServicePort,
    BillingAdapterPort,
    OrganizationRepositoryPort,
    SubscriptionRepositoryPort,
    SubscriptionServicePort,
)
from application.use_cases.dto import SubscriptionDTO, UpdateSubscriptionRequestDTO
from domain.entities import Subscription, SubscriptionTier


class UpdateSubscriptionUseCase:
    """Use case for updating an existing subscription."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        billing_adapter: BillingAdapterPort,
        authorization_service: AuthorizationServicePort,
        audit_service: AuditServicePort,
        subscription_service: SubscriptionServicePort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            subscription_repository: Repository for subscription operations
            organization_repository: Repository for organization operations
            billing_adapter: Adapter for external billing system
            authorization_service: Service for authorization checks
            audit_service: Service for audit logging
            subscription_service: Service for subscription business logic
        """
        self.subscription_repository = subscription_repository
        self.organization_repository = organization_repository
        self.billing_adapter = billing_adapter
        self.authorization_service = authorization_service
        self.audit_service = audit_service
        self.subscription_service = subscription_service

    def execute(self, request: UpdateSubscriptionRequestDTO) -> SubscriptionDTO:
        """Execute the update subscription use case.

        Args:
            request: Update subscription request DTO

        Returns:
            Updated subscription DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When subscription update fails
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

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.updated_by_user_id,
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

        # Track changes for audit
        changes = {}
        proration_details = None

        # Update tier if provided
        if request.tier:
            old_tier = subscription.tier.value
            new_tier_enum = self._validate_and_convert_tier(request.tier)

            if new_tier_enum != subscription.tier:
                # Calculate proration for tier change
                days_remaining = (subscription.expires_at - datetime.utcnow()).days
                proration_details = self.subscription_service.calculate_proration(
                    current_tier=old_tier,
                    new_tier=request.tier,
                    billing_cycle=subscription.billing_cycle,
                    days_remaining=days_remaining,
                )

                subscription.update_tier(new_tier_enum)
                changes["tier"] = {"old": old_tier, "new": request.tier}

        # Update billing cycle if provided
        if (
            request.billing_cycle
            and request.billing_cycle != subscription.billing_cycle
        ):
            if request.billing_cycle not in ["monthly", "yearly"]:
                raise ValidationError(
                    message="Billing cycle must be 'monthly' or 'yearly'",
                    field="billing_cycle",
                )

            old_cycle = subscription.billing_cycle
            subscription.billing_cycle = request.billing_cycle
            subscription.updated_at = datetime.utcnow()
            changes["billing_cycle"] = {"old": old_cycle, "new": request.billing_cycle}

        # Update payment method if provided
        if (
            request.payment_method_id
            and request.payment_method_id != subscription.payment_method_id
        ):
            old_payment_method = subscription.payment_method_id
            subscription.payment_method_id = request.payment_method_id
            subscription.updated_at = datetime.utcnow()
            changes["payment_method_id"] = {
                "old": old_payment_method,
                "new": request.payment_method_id,
            }

        # Update external billing system if subscription has external ID
        if subscription.external_subscription_id and changes:
            billing_updates = {}
            if "tier" in changes:
                billing_updates["tier"] = request.tier
            if "billing_cycle" in changes:
                billing_updates["billing_cycle"] = request.billing_cycle
            if "payment_method_id" in changes:
                billing_updates["payment_method_id"] = request.payment_method_id

            if billing_updates:
                self.billing_adapter.update_subscription(
                    external_subscription_id=subscription.external_subscription_id,
                    **billing_updates,
                )

        # Save updated subscription
        updated_subscription = self.subscription_repository.update(subscription)

        # Update organization subscription info if tier changed
        if "tier" in changes:
            organization.update_subscription(subscription.tier, subscription.expires_at)
            self.organization_repository.update(organization)

        # Log audit activity
        if changes:
            self.audit_service.log_activity(
                user_id=request.updated_by_user_id,
                activity_type="subscription_updated",
                description=f"Updated subscription for organization {organization.name}",
                resource_id=subscription.id,
                resource_type="subscription",
                metadata={
                    "organization_id": subscription.organization_id,
                    "changes": changes,
                    "proration_details": proration_details,
                },
            )

        # Return DTO
        return self._to_dto(updated_subscription)

    def _validate_input(self, request: UpdateSubscriptionRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Update subscription request DTO

        Raises:
            ValidationError: When validation fails
        """
        if not request.subscription_id:
            raise ValidationError(
                message="Subscription ID is required", field="subscription_id"
            )

        if not request.updated_by_user_id:
            raise ValidationError(
                message="Updated by user ID is required", field="updated_by_user_id"
            )

        # At least one field must be provided for update
        if not any([request.tier, request.billing_cycle, request.payment_method_id]):
            raise ValidationError(
                message="At least one field must be provided for update",
                field="update_fields",
            )

        # Validate tier if provided
        if request.tier:
            valid_tiers = ["free", "basic", "professional", "enterprise"]
            if request.tier.lower() not in valid_tiers:
                raise ValidationError(
                    message=f"Subscription tier must be one of {valid_tiers}",
                    field="tier",
                )

        # Validate billing cycle if provided
        if request.billing_cycle:
            valid_cycles = ["monthly", "yearly"]
            if request.billing_cycle not in valid_cycles:
                raise ValidationError(
                    message=f"Billing cycle must be one of {valid_cycles}",
                    field="billing_cycle",
                )

    def _validate_and_convert_tier(self, tier: str) -> SubscriptionTier:
        """Validate and convert tier string to enum.

        Args:
            tier: Tier string

        Returns:
            SubscriptionTier enum

        Raises:
            ValidationError: When tier is invalid
        """
        try:
            return SubscriptionTier(tier.lower())
        except ValueError:
            raise ValidationError(
                message=f"Invalid subscription tier: {tier}", field="tier"
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
