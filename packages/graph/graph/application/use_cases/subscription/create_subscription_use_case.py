"""Create subscription use case implementation."""

from application.exceptions import ApplicationError, ValidationError
from application.ports import (
    AuditServicePort,
    AuthorizationServicePort,
    BillingAdapterPort,
    OrganizationRepositoryPort,
    SubscriptionRepositoryPort,
)
from application.use_cases.dto import CreateSubscriptionRequestDTO, SubscriptionDTO
from domain.entities import Subscription, SubscriptionTier


class CreateSubscriptionUseCase:
    """Use case for creating a new subscription."""

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

    def execute(self, request: CreateSubscriptionRequestDTO) -> SubscriptionDTO:
        """Execute the create subscription use case.

        Args:
            request: Create subscription request DTO

        Returns:
            Created subscription DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When subscription creation fails
        """
        # Validate input
        self._validate_input(request)

        # Check authorization
        self.authorization_service.check_permission(
            user_id=request.created_by_user_id,
            resource_id=request.organization_id,
            action="manage_billing",
        )

        # Check if organization exists
        organization = self.organization_repository.get_by_id(request.organization_id)
        if not organization:
            raise ApplicationError(
                message=f"Organization with ID {request.organization_id} not found",
                error_code="ORGANIZATION_NOT_FOUND",
            )

        # Check if organization already has an active subscription
        existing_subscription = self.subscription_repository.get_by_organization_id(
            request.organization_id
        )
        if existing_subscription and existing_subscription.is_active():
            raise ApplicationError(
                message="Organization already has an active subscription",
                error_code="ACTIVE_SUBSCRIPTION_EXISTS",
            )

        # Convert tier string to enum
        try:
            tier_enum = SubscriptionTier(request.tier.lower())
        except ValueError:
            raise ValidationError(
                message=f"Invalid subscription tier: {request.tier}", field="tier"
            )

        # Process payment with billing adapter if not free tier
        external_subscription_id = None
        if tier_enum != SubscriptionTier.FREE:
            if not request.payment_method_id:
                raise ValidationError(
                    message="Payment method ID is required for paid tiers",
                    field="payment_method_id",
                )

            billing_result = self.billing_adapter.create_subscription(
                organization_id=request.organization_id,
                tier=request.tier,
                billing_cycle=request.billing_cycle,
                payment_method_id=request.payment_method_id,
            )
            external_subscription_id = billing_result.get("subscription_id")

        # Create subscription entity
        subscription = Subscription.create(
            organization_id=request.organization_id,
            tier=tier_enum,
            billing_cycle=request.billing_cycle,
            external_subscription_id=external_subscription_id,
            payment_method_id=request.payment_method_id,
        )

        # Save to repository
        created_subscription = self.subscription_repository.create(subscription)

        # Update organization with new subscription tier
        organization.update_subscription(tier_enum, created_subscription.expires_at)
        self.organization_repository.update(organization)

        # Log audit activity
        self.audit_service.log_activity(
            user_id=request.created_by_user_id,
            activity_type="subscription_created",
            description=f"Created {request.tier} subscription for organization {organization.name}",
            resource_id=created_subscription.id,
            resource_type="subscription",
            metadata={
                "organization_id": request.organization_id,
                "tier": request.tier,
                "billing_cycle": request.billing_cycle,
            },
        )

        # Return DTO
        return self._to_dto(created_subscription)

    def _validate_input(self, request: CreateSubscriptionRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Create subscription request DTO

        Raises:
            ValidationError: When validation fails
        """
        if not request.organization_id:
            raise ValidationError(
                message="Organization ID is required", field="organization_id"
            )

        if not request.tier:
            raise ValidationError(message="Subscription tier is required", field="tier")

        valid_tiers = ["free", "basic", "professional", "enterprise"]
        if request.tier.lower() not in valid_tiers:
            raise ValidationError(
                message=f"Subscription tier must be one of {valid_tiers}", field="tier"
            )

        valid_cycles = ["monthly", "yearly"]
        if request.billing_cycle not in valid_cycles:
            raise ValidationError(
                message=f"Billing cycle must be one of {valid_cycles}",
                field="billing_cycle",
            )

        if not request.created_by_user_id:
            raise ValidationError(
                message="Created by user ID is required", field="created_by_user_id"
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
