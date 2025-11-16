"""Tests for GetUsageMetricsUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, Subscription, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, NotFoundError, ValidationError
from application.use_cases.subscription.get_usage_metrics_use_case import GetUsageMetricsUseCase
from application.use_cases.dto import UsageMetricsRequestDTO


class TestGetUsageMetricsUseCase:
    """Test cases for GetUsageMetricsUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.subscription_repository = Mock()
        self.organization_repository = Mock()
        self.billing_adapter = Mock()
        self.authorization_service = Mock()
        self.subscription_service = Mock()
        self.metrics_repository = Mock()

        self.use_case = GetUsageMetricsUseCase(
            subscription_repository=self.subscription_repository,
            organization_repository=self.organization_repository,
            billing_adapter=self.billing_adapter,
            authorization_service=self.authorization_service,
            subscription_service=self.subscription_service,
            metrics_repository=self.metrics_repository
        )

        # Mock organization
        self.organization = Organization.create(
            name="Test Organization",
            subscription_tier=SubscriptionTier.PROFESSIONAL
        )
        self.organization_repository.get_by_id.return_value = self.organization

        # Mock subscription
        self.subscription = Subscription.create(
            organization_id="org_123",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_cycle="monthly"
        )
        self.subscription_repository.get_by_organization_id.return_value = self.subscription

        # Mock subscription limits
        self.subscription_service.get_subscription_limits.return_value = {
            "knowledge_graphs": 10.0,
            "users": 25.0,
            "api_calls_per_month": 10000.0,
            "storage_gb": 100.0
        }

        # Mock metrics data
        now = datetime.utcnow()
        self.metrics_repository.query_range.return_value = [
            (now - timedelta(days=1), 5.0),
            (now, 7.0)
        ]

    def test_get_usage_metrics_success(self):
        """Test successful usage metrics retrieval."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs", "users"]
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"
        assert result.subscription_tier == "professional"
        assert len(result.metrics) == 2

        # Check knowledge graphs metric
        kg_metric = next(m for m in result.metrics if m.metric_type == "knowledge_graphs")
        assert kg_metric.current_value == 7.0
        assert kg_metric.limit_value == 10.0
        assert kg_metric.unit == "count"

        # Check users metric
        users_metric = next(m for m in result.metrics if m.metric_type == "users")
        assert users_metric.current_value == 7.0
        assert users_metric.limit_value == 25.0
        assert users_metric.unit == "count"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="view_billing"
        )

        # Verify organization lookup
        self.organization_repository.get_by_id.assert_called_once_with("org_123")

        # Verify subscription lookup
        self.subscription_repository.get_by_organization_id.assert_called_once_with("org_123")

        # Verify subscription limits lookup
        self.subscription_service.get_subscription_limits.assert_called_once_with("professional")

    def test_get_usage_metrics_all_types_success(self):
        """Test successful usage metrics retrieval for all metric types."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123"
            # No metric_types specified, should get all
        )

        # Mock different metric data for different types
        def mock_query_range(metric, tenant_id, start_time, end_time):
            if metric == "api_calls_count":
                # Return multiple data points for API calls (should be summed)
                return [
                    (datetime.utcnow() - timedelta(days=2), 1000.0),
                    (datetime.utcnow() - timedelta(days=1), 1500.0),
                    (datetime.utcnow(), 2000.0)
                ]
            else:
                # Return single latest value for other metrics
                return [(datetime.utcnow(), 7.0)]

        self.metrics_repository.query_range.side_effect = mock_query_range

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert len(result.metrics) == 4  # All metric types

        # Check API calls metric (should be summed)
        api_metric = next(m for m in result.metrics if m.metric_type == "api_calls")
        assert api_metric.current_value == 4500.0  # Sum of all API calls
        assert api_metric.limit_value == 10000.0
        assert api_metric.unit == "calls"

        # Check storage metric
        storage_metric = next(m for m in result.metrics if m.metric_type == "storage_gb")
        assert storage_metric.current_value == 7.0
        assert storage_metric.limit_value == 100.0
        assert storage_metric.unit == "GB"

    def test_get_usage_metrics_with_date_range(self):
        """Test usage metrics retrieval with specific date range."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date,
            metric_types=["knowledge_graphs"]
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.period_start == start_date
        assert result.period_end == end_date

        # Verify metrics repository was called with correct date range
        self.metrics_repository.query_range.assert_called_with(
            metric="knowledge_graphs_count",
            tenant_id="org_123",
            start_time=start_date,
            end_time=end_date
        )

    def test_get_usage_metrics_missing_organization_id(self):
        """Test validation error when organization ID is missing."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="",
            metric_types=["knowledge_graphs"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization ID is required" in str(exc_info.value)

    def test_get_usage_metrics_invalid_date_range(self):
        """Test validation error when start date is after end date."""
        # Arrange
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(days=1)  # End before start

        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date,
            metric_types=["knowledge_graphs"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Start date must be before end date" in str(exc_info.value)

    def test_get_usage_metrics_invalid_metric_types(self):
        """Test validation error when invalid metric types are provided."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["invalid_metric", "another_invalid"]
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Invalid metric types" in str(exc_info.value)
        assert "invalid_metric" in str(exc_info.value)
        assert "another_invalid" in str(exc_info.value)

    def test_get_usage_metrics_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs"]
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to view billing"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request, user_id="user_123")

    def test_get_usage_metrics_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs"]
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_get_usage_metrics_no_subscription(self):
        """Test error when organization has no subscription."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs"]
        )

        self.subscription_repository.get_by_organization_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "No subscription found for organization org_123" in str(exc_info.value)

    def test_get_usage_metrics_no_metric_data(self):
        """Test handling when no metric data is available."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs"]
        )

        # Mock empty metric data
        self.metrics_repository.query_range.return_value = []

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert len(result.metrics) == 1
        kg_metric = result.metrics[0]
        assert kg_metric.current_value == 0.0  # Should default to 0 when no data
        assert kg_metric.limit_value == 10.0

    def test_get_usage_metrics_metric_error_handling(self):
        """Test error handling when individual metric retrieval fails."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs", "users"]
        )

        # Mock metrics repository to raise exception for one metric
        def mock_query_range(metric, tenant_id, start_time, end_time):
            if metric == "knowledge_graphs_count":
                raise Exception("Database error")
            else:
                return [(datetime.utcnow(), 5.0)]

        self.metrics_repository.query_range.side_effect = mock_query_range

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        # Should only return metrics that succeeded (users), not the failed one
        assert len(result.metrics) == 1
        assert result.metrics[0].metric_type == "users"

    def test_get_usage_metrics_default_date_range(self):
        """Test that default date range is used when not provided."""
        # Arrange
        request = UsageMetricsRequestDTO(
            organization_id="org_123",
            metric_types=["knowledge_graphs"]
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        # Should use 30-day default range
        assert result.period_end is not None
        assert result.period_start is not None
        assert (result.period_end - result.period_start).days == 30