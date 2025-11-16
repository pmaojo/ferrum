"""Get usage metrics use case implementation."""

from datetime import datetime, timedelta
from typing import Optional

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuthorizationServicePort,
    BillingAdapterPort,
    MetricsRepositoryPort,
    OrganizationRepositoryPort,
    SubscriptionRepositoryPort,
    SubscriptionServicePort,
)
from application.use_cases.dto import (
    UsageMetricDTO,
    UsageMetricsDTO,
    UsageMetricsRequestDTO,
)


class GetUsageMetricsUseCase:
    """Use case for retrieving usage metrics for an organization."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        billing_adapter: BillingAdapterPort,
        authorization_service: AuthorizationServicePort,
        subscription_service: SubscriptionServicePort,
        metrics_repository: MetricsRepositoryPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            subscription_repository: Repository for subscription operations
            organization_repository: Repository for organization operations
            billing_adapter: Adapter for external billing system
            authorization_service: Service for authorization checks
            subscription_service: Service for subscription business logic
            metrics_repository: Repository for metrics data
        """
        self.subscription_repository = subscription_repository
        self.organization_repository = organization_repository
        self.billing_adapter = billing_adapter
        self.authorization_service = authorization_service
        self.subscription_service = subscription_service
        self.metrics_repository = metrics_repository

    def execute(self, request: UsageMetricsRequestDTO, user_id: str) -> UsageMetricsDTO:
        """Execute the get usage metrics use case.

        Args:
            request: Usage metrics request DTO
            user_id: ID of the user requesting metrics

        Returns:
            Usage metrics DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When metrics retrieval fails
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

        # Set default date range if not provided
        end_date = request.end_date or datetime.utcnow()
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Get subscription limits
        subscription_limits = self.subscription_service.get_subscription_limits(
            subscription.tier.value
        )

        # Collect usage metrics
        metrics = []

        # Get requested metric types or default to all
        metric_types = request.metric_types or [
            "knowledge_graphs",
            "users",
            "api_calls",
            "storage_gb",
        ]

        for metric_type in metric_types:
            metric = self._get_usage_metric(
                organization_id=request.organization_id,
                metric_type=metric_type,
                start_date=start_date,
                end_date=end_date,
                subscription_limits=subscription_limits,
            )
            if metric:
                metrics.append(metric)

        # Return DTO
        return UsageMetricsDTO(
            organization_id=request.organization_id,
            subscription_tier=subscription.tier.value,
            metrics=metrics,
            period_start=start_date,
            period_end=end_date,
        )

    def _validate_input(self, request: UsageMetricsRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Usage metrics request DTO

        Raises:
            ValidationError: When validation fails
        """
        if not request.organization_id:
            raise ValidationError(
                message="Organization ID is required", field="organization_id"
            )

        # Validate date range if provided
        if request.start_date and request.end_date:
            if request.start_date >= request.end_date:
                raise ValidationError(
                    message="Start date must be before end date", field="date_range"
                )

        # Validate metric types if provided
        if request.metric_types:
            valid_metrics = ["knowledge_graphs", "users", "api_calls", "storage_gb"]
            invalid_metrics = [
                m for m in request.metric_types if m not in valid_metrics
            ]
            if invalid_metrics:
                raise ValidationError(
                    message=(
                        f"Invalid metric types: {invalid_metrics}. Valid types: {valid_metrics}"
                    ),
                    field="metric_types",
                )

    def _get_usage_metric(
        self,
        organization_id: str,
        metric_type: str,
        start_date: datetime,
        end_date: datetime,
        subscription_limits: dict,
    ) -> Optional[UsageMetricDTO]:
        """Get usage metric for a specific type.

        Args:
            organization_id: Organization identifier
            metric_type: Type of metric to retrieve
            start_date: Start date for metric period
            end_date: End date for metric period
            subscription_limits: Subscription limits dictionary

        Returns:
            Usage metric DTO or None if metric not available
        """
        try:
            if metric_type == "knowledge_graphs":
                return self._get_knowledge_graphs_metric(
                    organization_id, start_date, end_date, subscription_limits
                )
            elif metric_type == "users":
                return self._get_users_metric(
                    organization_id, start_date, end_date, subscription_limits
                )
            elif metric_type == "api_calls":
                return self._get_api_calls_metric(
                    organization_id, start_date, end_date, subscription_limits
                )
            elif metric_type == "storage_gb":
                return self._get_storage_metric(
                    organization_id, start_date, end_date, subscription_limits
                )
            else:
                return None
        except Exception:
            # Log error but don't fail the entire request
            # In a real implementation, you'd use proper logging
            return None

    def _get_knowledge_graphs_metric(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        subscription_limits: dict,
    ) -> UsageMetricDTO:
        """Get knowledge graphs usage metric."""
        # Query metrics repository for knowledge graph count
        metric_data = self.metrics_repository.query_range(
            metric="knowledge_graphs_count",
            tenant_id=organization_id,
            start_time=start_date,
            end_time=end_date,
        )

        # Get current value (latest data point)
        current_value = metric_data[-1][1] if metric_data else 0.0

        # Get limit from subscription
        limit_value = subscription_limits.get("knowledge_graphs")

        return UsageMetricDTO(
            metric_type="knowledge_graphs",
            current_value=current_value,
            limit_value=limit_value,
            unit="count",
            period_start=start_date,
            period_end=end_date,
        )

    def _get_users_metric(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        subscription_limits: dict,
    ) -> UsageMetricDTO:
        """Get users usage metric."""
        # Query metrics repository for user count
        metric_data = self.metrics_repository.query_range(
            metric="users_count",
            tenant_id=organization_id,
            start_time=start_date,
            end_time=end_date,
        )

        # Get current value (latest data point)
        current_value = metric_data[-1][1] if metric_data else 0.0

        # Get limit from subscription
        limit_value = subscription_limits.get("users")

        return UsageMetricDTO(
            metric_type="users",
            current_value=current_value,
            limit_value=limit_value,
            unit="count",
            period_start=start_date,
            period_end=end_date,
        )

    def _get_api_calls_metric(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        subscription_limits: dict,
    ) -> UsageMetricDTO:
        """Get API calls usage metric."""
        # Query metrics repository for API call count
        metric_data = self.metrics_repository.query_range(
            metric="api_calls_count",
            tenant_id=organization_id,
            start_time=start_date,
            end_time=end_date,
        )

        # Sum all API calls in the period
        current_value = sum(data_point[1] for data_point in metric_data)

        # Get limit from subscription (monthly limit)
        limit_value = subscription_limits.get("api_calls_per_month")

        return UsageMetricDTO(
            metric_type="api_calls",
            current_value=current_value,
            limit_value=limit_value,
            unit="calls",
            period_start=start_date,
            period_end=end_date,
        )

    def _get_storage_metric(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        subscription_limits: dict,
    ) -> UsageMetricDTO:
        """Get storage usage metric."""
        # Query metrics repository for storage usage
        metric_data = self.metrics_repository.query_range(
            metric="storage_usage_gb",
            tenant_id=organization_id,
            start_time=start_date,
            end_time=end_date,
        )

        # Get current value (latest data point)
        current_value = metric_data[-1][1] if metric_data else 0.0

        # Get limit from subscription
        limit_value = subscription_limits.get("storage_gb")

        return UsageMetricDTO(
            metric_type="storage_gb",
            current_value=current_value,
            limit_value=limit_value,
            unit="GB",
            period_start=start_date,
            period_end=end_date,
        )
