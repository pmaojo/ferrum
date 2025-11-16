"""Tests for CheckSubscriptionLimitsUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, Subscription, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, NotFoundError, ValidationError
from application.use_cases.subscription.check_subscription_limits_use_case import CheckSubscriptionLimitsUseCase
from application.use_cases.dto import CheckSubscriptionLimitsRequestDTO


class TestCheckSubscriptionLimitsUseCase:
    """Test cases for CheckSubscriptionLimitsUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.subscription_repository = Mock()
        self.organization_repository = Mock()
        self.authorization_service = Mock()
        self.subscription_service = Mock()
        self.metrics_repository = Mock()

        self.use_case = CheckSubscriptionLimitsUseCase(
            subscription_repository=self.subscription_repository,
            organization_repository=self.organization_repository,
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

    def test_check_specific_resource_limit_within_limits(self):
        """Test checking specific resource limit that is within limits."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"
        assert result.subscription_tier == "professional"
        assert result.overall_status == "within_limits"
        assert len(result.limits) == 1

        limit = result.limits[0]
        assert limit.resource_type == "knowledge_graphs"
        assert limit.current_usage == 7.0
        assert limit.limit == 10.0
        assert limit.unit == "count"
        assert limit.is_exceeded is False
        assert limit.remaining == 3.0

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="view_billing"
        )

    def test_check_specific_resource_limit_exceeded(self):
        """Test checking specific resource limit that is exceeded."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Mock usage that exceeds limit
        self.metrics_repository.query_range.return_value = [
            (datetime.utcnow(), 15.0)  # Exceeds limit of 10
        ]

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.overall_status == "exceeded_limits"

        limit = result.limits[0]
        assert limit.current_usage == 15.0
        assert limit.limit == 10.0
        assert limit.is_exceeded is True
        assert limit.remaining == 0.0  # Max of 0 and (10 - 15)

    def test_check_specific_resource_limit_with_requested_amount(self):
        """Test checking specific resource limit with requested amount."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs",
            requested_amount=5.0  # Would exceed limit (7 + 5 > 10)
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.overall_status == "exceeded_limits"

        limit = result.limits[0]
        assert limit.current_usage == 7.0  # Current usage unchanged
        assert limit.is_exceeded is True  # But would be exceeded with requested amount

    def test_check_all_limits_success(self):
        """Test checking all resource limits."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123"
            # No resource_type specified, should check all
        )

        # Mock different usage for different resource types
        def mock_query_range(metric, tenant_id, start_time, end_time):
            if metric == "knowledge_graphs_count":
                return [(datetime.utcnow(), 5.0)]
            elif metric == "users_count":
                return [(datetime.utcnow(), 20.0)]
            elif metric == "api_calls_count":
                return [
                    (datetime.utcnow() - timedelta(days=1), 3000.0),
                    (datetime.utcnow(), 2000.0)
                ]
            elif metric == "storage_usage_gb":
                return [(datetime.utcnow(), 75.0)]
            else:
                return []

        self.metrics_repository.query_range.side_effect = mock_query_range

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert len(result.limits) == 4  # All resource types
        assert result.overall_status == "within_limits"

        # Check each resource type
        kg_limit = next(l for l in result.limits if l.resource_type == "knowledge_graphs")
        assert kg_limit.current_usage == 5.0
        assert kg_limit.limit == 10.0

        users_limit = next(l for l in result.limits if l.resource_type == "users")
        assert users_limit.current_usage == 20.0
        assert users_limit.limit == 25.0

        api_limit = next(l for l in result.limits if l.resource_type == "api_calls")
        assert api_limit.current_usage == 5000.0  # Sum of API calls
        assert api_limit.limit == 10000.0
        assert api_limit.unit == "calls"

        storage_limit = next(l for l in result.limits if l.resource_type == "storage_gb")
        assert storage_limit.current_usage == 75.0
        assert storage_limit.limit == 100.0
        assert storage_limit.unit == "GB"

    def test_check_limits_approaching_threshold(self):
        """Test checking limits that are approaching the threshold."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Mock usage at 85% of limit (approaching threshold is 80%)
        self.metrics_repository.query_range.return_value = [
            (datetime.utcnow(), 8.5)  # 85% of 10
        ]

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.overall_status == "approaching_limits"

        limit = result.limits[0]
        assert limit.current_usage == 8.5
        assert limit.is_exceeded is False
        assert limit.remaining == 1.5

    def test_check_limits_unlimited_resource(self):
        """Test checking limits for unlimited resource."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Mock unlimited subscription (no limit)
        self.subscription_service.get_subscription_limits.return_value = {
            "knowledge_graphs": None,  # Unlimited
            "users": 25.0,
            "api_calls_per_month": 10000.0,
            "storage_gb": 100.0
        }

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.overall_status == "within_limits"

        limit = result.limits[0]
        assert limit.current_usage == 7.0
        assert limit.limit is None  # Unlimited
        assert limit.is_exceeded is False
        assert limit.remaining is None  # No limit means no remaining calculation

    def test_check_limits_missing_organization_id(self):
        """Test validation error when organization ID is missing."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="",
            resource_type="knowledge_graphs"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization ID is required" in str(exc_info.value)

    def test_check_limits_invalid_resource_type(self):
        """Test validation error when resource type is invalid."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="invalid_resource"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Invalid resource type" in str(exc_info.value)
        assert "invalid_resource" in str(exc_info.value)

    def test_check_limits_negative_requested_amount(self):
        """Test validation error when requested amount is negative."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs",
            requested_amount=-5.0
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Requested amount must be non-negative" in str(exc_info.value)

    def test_check_limits_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to view billing",
            user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request, user_id="user_123")

    def test_check_limits_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_check_limits_no_subscription(self):
        """Test error when organization has no subscription."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        self.subscription_repository.get_by_organization_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "No subscription found for organization org_123" in str(exc_info.value)

    def test_check_limits_metrics_error_handling(self):
        """Test error handling when metrics retrieval fails."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Mock metrics repository to raise exception
        self.metrics_repository.query_range.side_effect = Exception("Database error")

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        # Should handle error gracefully and return limits with 0 usage
        assert len(result.limits) == 1
        limit = result.limits[0]
        assert limit.current_usage == 0.0  # Should default to 0 when metrics fail
        assert limit.limit == 10.0
        assert limit.is_exceeded is False
        assert limit.remaining == 10.0
        assert result.overall_status == "within_limits"

    def test_check_limits_no_metric_data(self):
        """Test handling when no metric data is available."""
        # Arrange
        request = CheckSubscriptionLimitsRequestDTO(
            organization_id="org_123",
            resource_type="knowledge_graphs"
        )

        # Mock empty metric data
        self.metrics_repository.query_range.return_value = []

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        limit = result.limits[0]
        assert limit.current_usage == 0.0  # Should default to 0 when no data
        assert limit.limit == 10.0
        assert limit.is_exceeded is False
        assert limit.remaining == 10.0