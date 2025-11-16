"""Check subscription limits use case implementation."""

from datetime import datetime, timedelta
from typing import List, Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuthorizationServicePort,
    MetricsRepositoryPort,
    OrganizationRepositoryPort,
    SubscriptionRepositoryPort,
    SubscriptionServicePort,
)
from application.use_cases.dto import (
    CheckSubscriptionLimitsRequestDTO,
    SubscriptionLimitDTO,
    SubscriptionLimitsDTO,
)


class CheckSubscriptionLimitsUseCase:
    """Use case for checking subscription limits for an organization."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        authorization_service: AuthorizationServicePort,
        subscription_service: SubscriptionServicePort,
        metrics_repository: MetricsRepositoryPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            subscription_repository: Repository for subscription operations
            organization_repository: Repository for organization operations
            authorization_service: Service for authorization checks
            subscription_service: Service for subscription business logic
            metrics_repository: Repository for metrics data
        """
        self.subscription_repository = subscription_repository
        self.organization_repository = organization_repository
        self.authorization_service = authorization_service
        self.subscription_service = subscription_service
        self.metrics_repository = metrics_repository

    def execute(
        self, request: CheckSubscriptionLimitsRequestDTO, user_id: str
    ) -> SubscriptionLimitsDTO:
        """Execute the check subscription limits use case.

        Args:
            request: Check subscription limits request DTO
            user_id: ID of the user requesting limit check

        Returns:
            Subscription limits DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When limit check fails
        """
        # Validate input
        self._validate_input(request)

        # Check authorization
        self.authorization_service.check_permission(
            user_id=user_id, resource_id=request.organization_id, action="view_billing"
        )

        # Check if organization exists
        organization = self.organization_repository.get_by_id(request.organization_id)
        if not organization:
            raise NotFoundError(
                message=f"Organization with ID {request.organization_id} not found",
                resource_type="organization",
                resource_id=request.organization_id,
            )

        # Get current subscription
        subscription = self.subscription_repository.get_by_organization_id(
            request.organization_id
        )
        if not subscription:
            raise NotFoundError(
                message=f"No subscription found for organization {request.organization_id}",
                resource_type="subscription",
                resource_id=request.organization_id,
            )

        # Get subscription limits
        subscription_limits = self.subscription_service.get_subscription_limits(
            subscription.tier.value
        )

        # Check specific resource type or all limits
        if request.resource_type:
            # Check specific resource type
            limit_dto = self._check_resource_limit(
                organization_id=request.organization_id,
                resource_type=request.resource_type,
                requested_amount=request.requested_amount,
                subscription_limits=subscription_limits,
            )
            limits = [limit_dto] if limit_dto else []
        else:
            # Check all resource types
            limits = self._check_all_limits(
                organization_id=request.organization_id,
                subscription_limits=subscription_limits,
            )

        # Determine overall status
        overall_status = self._determine_overall_status(limits)

        # Return DTO
        return SubscriptionLimitsDTO(
            organization_id=request.organization_id,
            subscription_tier=subscription.tier.value,
            limits=limits,
            overall_status=overall_status,
        )

    def _validate_input(self, request: CheckSubscriptionLimitsRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Check subscription limits request DTO

        Raises:
            ValidationError: When validation fails
        """
        if not request.organization_id:
            raise ValidationError(
                message="Organization ID is required", field="organization_id"
            )

        # Validate resource type if provided
        if request.resource_type:
            valid_types = ["knowledge_graphs", "users", "api_calls", "storage_gb"]
            if request.resource_type not in valid_types:
                raise ValidationError(
                    message=(
                        f"Invalid resource type: {request.resource_type}. Valid types: {valid_types}"
                    ),
                    field="resource_type",
                )

        # Validate requested amount if provided
        if request.requested_amount is not None:
            if request.requested_amount < 0:
                raise ValidationError(
                    message="Requested amount must be non-negative",
                    field="requested_amount",
                )

    def _check_resource_limit(
        self,
        organization_id: str,
        resource_type: str,
        requested_amount: Optional[float],
        subscription_limits: dict,
    ) -> Optional[SubscriptionLimitDTO]:
        """Check limit for a specific resource type.

        Args:
            organization_id: Organization identifier
            resource_type: Type of resource to check
            requested_amount: Optional amount being requested
            subscription_limits: Subscription limits dictionary

        Returns:
            Subscription limit DTO or None if resource type not supported
        """
        try:
            current_usage = self._get_current_usage(organization_id, resource_type)
            limit = subscription_limits.get(self._get_limit_key(resource_type))

            # Calculate if limit would be exceeded with requested amount
            projected_usage = current_usage
            if requested_amount is not None:
                projected_usage += requested_amount

            is_exceeded = limit is not None and projected_usage > limit
            remaining = None
            if limit is not None:
                remaining = max(0, limit - current_usage)

            return SubscriptionLimitDTO(
                resource_type=resource_type,
                current_usage=current_usage,
                limit=limit,
                unit=self._get_unit(resource_type),
                is_exceeded=is_exceeded,
                remaining=remaining,
            )
        except Exception:
            # Log error but don't fail the entire request
            return None

    def _check_all_limits(
        self, organization_id: str, subscription_limits: dict
    ) -> List[SubscriptionLimitDTO]:
        """Check limits for all resource types.

        Args:
            organization_id: Organization identifier
            subscription_limits: Subscription limits dictionary

        Returns:
            List of subscription limit DTOs
        """
        resource_types = ["knowledge_graphs", "users", "api_calls", "storage_gb"]
        limits = []

        for resource_type in resource_types:
            limit_dto = self._check_resource_limit(
                organization_id=organization_id,
                resource_type=resource_type,
                requested_amount=None,
                subscription_limits=subscription_limits,
            )
            if limit_dto:
                limits.append(limit_dto)

        return limits

    def _get_current_usage(self, organization_id: str, resource_type: str) -> float:
        """Get current usage for a resource type.

        Args:
            organization_id: Organization identifier
            resource_type: Type of resource

        Returns:
            Current usage value
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)  # Last 30 days

        if resource_type == "knowledge_graphs":
            metric_name = "knowledge_graphs_count"
        elif resource_type == "users":
            metric_name = "users_count"
        elif resource_type == "api_calls":
            metric_name = "api_calls_count"
        elif resource_type == "storage_gb":
            metric_name = "storage_usage_gb"
        else:
            return 0.0

        try:
            metric_data = self.metrics_repository.query_range(
                metric=metric_name,
                tenant_id=organization_id,
                start_time=start_time,
                end_time=end_time,
            )

            if resource_type == "api_calls":
                # Sum API calls over the period
                return sum(data_point[1] for data_point in metric_data)
            else:
                # Get latest value for other metrics
                return metric_data[-1][1] if metric_data else 0.0
        except Exception:
            return 0.0

    def _get_limit_key(self, resource_type: str) -> str:
        """Get the limit key for a resource type.

        Args:
            resource_type: Type of resource

        Returns:
            Limit key for subscription limits dictionary
        """
        if resource_type == "api_calls":
            return "api_calls_per_month"
        else:
            return resource_type

    def _get_unit(self, resource_type: str) -> str:
        """Get the unit for a resource type.

        Args:
            resource_type: Type of resource

        Returns:
            Unit string
        """
        if resource_type == "storage_gb":
            return "GB"
        elif resource_type == "api_calls":
            return "calls"
        else:
            return "count"

    def _determine_overall_status(self, limits: List[SubscriptionLimitDTO]) -> str:
        """Determine overall status based on individual limits.

        Args:
            limits: List of subscription limit DTOs

        Returns:
            Overall status string
        """
        if not limits:
            return "within_limits"

        # Check if any limits are exceeded
        if any(limit.is_exceeded for limit in limits):
            return "exceeded_limits"

        # Check if any limits are approaching (>80% usage)
        approaching_threshold = 0.8
        for limit in limits:
            if limit.limit is not None and limit.current_usage > (
                limit.limit * approaching_threshold
            ):
                return "approaching_limits"

        return "within_limits"
