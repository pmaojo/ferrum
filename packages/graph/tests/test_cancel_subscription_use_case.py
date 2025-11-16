"""Tests for CancelSubscriptionUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, Subscription, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, NotFoundError, BusinessRuleViolationError, ValidationError
from application.use_cases.subscription.cancel_subscription_use_case import CancelSubscriptionUseCase
from application.use_cases.dto import CancelSubscriptionRequestDTO


class TestCancelSubscriptionUseCase:
    """Test cases for CancelSubscriptionUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.subscription_repository = Mock()
        self.organization_repository = Mock()
        self.billing_adapter = Mock()
        self.authorization_service = Mock()
        self.audit_service = Mock()

        self.use_case = CancelSubscriptionUseCase(
            subscription_repository=self.subscription_repository,
            organization_repository=self.organization_repository,
            billing_adapter=self.billing_adapter,
            authorization_service=self.authorization_service,
            audit_service=self.audit_service
        )

        # Mock organization
        self.organization = Organization.create(
            name="Test Organization",
            subscription_tier=SubscriptionTier.PROFESSIONAL
        )
        self.organization_repository.get_by_id.return_value = self.organization

        # Mock active subscription
        self.subscription = Subscription.create(
            organization_id="org_123",
            tier=SubscriptionTier.PROFESSIONAL,
            billing_cycle="monthly",
            external_subscription_id="ext_sub_123",
            payment_method_id="pm_123"
        )
        self.subscription_repository.get_by_id.return_value = self.subscription

    def test_cancel_subscription_at_period_end_success(self):
        """Test successful subscription cancellation at period end."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancellation_reason="No longer needed",
            cancelled_by_user_id="user_123"
        )

        cancelled_subscription = Mock()
        cancelled_subscription.id = "sub_123"
        cancelled_subscription.organization_id = "org_123"
        cancelled_subscription.external_subscription_id = "ext_sub_123"
        cancelled_subscription.tier = SubscriptionTier.PROFESSIONAL
        cancelled_subscription.billing_cycle = "monthly"
        cancelled_subscription.starts_at = datetime.now()
        cancelled_subscription.expires_at = datetime.now() + timedelta(days=30)
        cancelled_subscription.payment_method_id = "pm_123"
        cancelled_subscription.status = "cancelled"
        cancelled_subscription.created_at = datetime.now()
        cancelled_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = cancelled_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.id == "sub_123"
        assert result.status == "cancelled"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="manage_billing"
        )

        # Verify billing adapter cancellation
        self.billing_adapter.cancel_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            cancel_at_period_end=True
        )

        # Verify subscription update
        self.subscription_repository.update.assert_called_once()

        # Verify organization is NOT updated for period-end cancellation
        self.organization_repository.update.assert_not_called()

        # Verify audit log
        self.audit_service.log_activity.assert_called_once()

    def test_cancel_subscription_immediately_success(self):
        """Test successful immediate subscription cancellation."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=False,
            cancellation_reason="Immediate cancellation needed",
            cancelled_by_user_id="user_123"
        )

        cancelled_subscription = Mock()
        cancelled_subscription.id = "sub_123"
        cancelled_subscription.organization_id = "org_123"
        cancelled_subscription.external_subscription_id = "ext_sub_123"
        cancelled_subscription.tier = SubscriptionTier.PROFESSIONAL
        cancelled_subscription.billing_cycle = "monthly"
        cancelled_subscription.starts_at = datetime.now()
        cancelled_subscription.expires_at = datetime.now()  # Immediate expiration
        cancelled_subscription.payment_method_id = "pm_123"
        cancelled_subscription.status = "cancelled"
        cancelled_subscription.created_at = datetime.now()
        cancelled_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = cancelled_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "cancelled"

        # Verify billing adapter cancellation
        self.billing_adapter.cancel_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            cancel_at_period_end=False
        )

        # Verify organization is downgraded to free tier for immediate cancellation
        self.organization_repository.update.assert_called_once()

        # Verify audit log includes immediate cancellation details
        call_args = self.audit_service.log_activity.call_args
        assert call_args[1]["metadata"]["cancel_at_period_end"] is False

    def test_cancel_subscription_without_external_id(self):
        """Test cancellation of subscription without external billing ID."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        # Mock subscription without external ID (free tier)
        self.subscription.external_subscription_id = None

        cancelled_subscription = Mock()
        cancelled_subscription.id = "sub_123"
        cancelled_subscription.organization_id = "org_123"
        cancelled_subscription.external_subscription_id = None
        cancelled_subscription.tier = SubscriptionTier.FREE
        cancelled_subscription.billing_cycle = "monthly"
        cancelled_subscription.starts_at = datetime.now()
        cancelled_subscription.expires_at = datetime.now() + timedelta(days=30)
        cancelled_subscription.payment_method_id = None
        cancelled_subscription.status = "cancelled"
        cancelled_subscription.created_at = datetime.now()
        cancelled_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = cancelled_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "cancelled"

        # Verify no billing adapter call for subscription without external ID
        self.billing_adapter.cancel_subscription.assert_not_called()

        # Verify subscription is still updated
        self.subscription_repository.update.assert_called_once()

    def test_cancel_subscription_missing_subscription_id(self):
        """Test validation error when subscription ID is missing."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription ID is required" in str(exc_info.value)

    def test_cancel_subscription_missing_user_id(self):
        """Test validation error when cancelled by user ID is missing."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id=""
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Cancelled by user ID is required" in str(exc_info.value)

    def test_cancel_subscription_invalid_cancel_at_period_end(self):
        """Test validation error when cancel_at_period_end is not boolean."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end="invalid",  # Should be boolean
            cancelled_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Cancel at period end must be a boolean value" in str(exc_info.value)

    def test_cancel_subscription_not_found(self):
        """Test error when subscription is not found."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        self.subscription_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription with ID sub_123 not found" in str(exc_info.value)

    def test_cancel_subscription_already_cancelled(self):
        """Test error when subscription is already cancelled."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        # Mock already cancelled subscription
        self.subscription.status = "cancelled"

        # Act & Assert
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription is already cancelled" in str(exc_info.value)

    def test_cancel_subscription_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to manage billing",
            user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_cancel_subscription_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            self.use_case.execute(request)

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_cancel_subscription_billing_adapter_error(self):
        """Test error handling when billing adapter fails."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancelled_by_user_id="user_123"
        )

        self.billing_adapter.cancel_subscription.side_effect = Exception("Billing error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            self.use_case.execute(request)

        assert "Billing error" in str(exc_info.value)

    def test_cancel_subscription_with_reason(self):
        """Test cancellation with specific reason."""
        # Arrange
        request = CancelSubscriptionRequestDTO(
            subscription_id="sub_123",
            cancel_at_period_end=True,
            cancellation_reason="Service not meeting expectations",
            cancelled_by_user_id="user_123"
        )

        cancelled_subscription = Mock()
        cancelled_subscription.id = "sub_123"
        cancelled_subscription.organization_id = "org_123"
        cancelled_subscription.external_subscription_id = "ext_sub_123"
        cancelled_subscription.tier = SubscriptionTier.PROFESSIONAL
        cancelled_subscription.billing_cycle = "monthly"
        cancelled_subscription.starts_at = datetime.now()
        cancelled_subscription.expires_at = datetime.now() + timedelta(days=30)
        cancelled_subscription.payment_method_id = "pm_123"
        cancelled_subscription.status = "cancelled"
        cancelled_subscription.created_at = datetime.now()
        cancelled_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = cancelled_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.status == "cancelled"

        # Verify audit log includes cancellation reason
        call_args = self.audit_service.log_activity.call_args
        assert call_args[1]["metadata"]["cancellation_reason"] == "Service not meeting expectations"