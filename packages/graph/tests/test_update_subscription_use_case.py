"""Tests for UpdateSubscriptionUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, Subscription, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, NotFoundError, ValidationError
from application.use_cases.subscription.update_subscription_use_case import UpdateSubscriptionUseCase
from application.use_cases.dto import UpdateSubscriptionRequestDTO


class TestUpdateSubscriptionUseCase:
    """Test cases for UpdateSubscriptionUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.subscription_repository = Mock()
        self.organization_repository = Mock()
        self.billing_adapter = Mock()
        self.authorization_service = Mock()
        self.audit_service = Mock()
        self.subscription_service = Mock()

        self.use_case = UpdateSubscriptionUseCase(
            subscription_repository=self.subscription_repository,
            organization_repository=self.organization_repository,
            billing_adapter=self.billing_adapter,
            authorization_service=self.authorization_service,
            audit_service=self.audit_service,
            subscription_service=self.subscription_service
        )

        # Mock organization
        self.organization = Organization.create(
            name="Test Organization",
            subscription_tier=SubscriptionTier.BASIC
        )
        self.organization_repository.get_by_id.return_value = self.organization

        # Mock subscription
        self.subscription = Subscription.create(
            organization_id="org_123",
            tier=SubscriptionTier.BASIC,
            billing_cycle="monthly",
            external_subscription_id="ext_sub_123",
            payment_method_id="pm_123"
        )
        self.subscription_repository.get_by_id.return_value = self.subscription

        # Mock proration calculation
        self.subscription_service.calculate_proration.return_value = {
            "proration_amount": 15.50,
            "credit_amount": 5.00,
            "next_invoice_amount": 25.00
        }

    def test_update_subscription_tier_success(self):
        """Test successful subscription tier update."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        updated_subscription = Mock()
        updated_subscription.id = "sub_123"
        updated_subscription.organization_id = "org_123"
        updated_subscription.external_subscription_id = "ext_sub_123"
        updated_subscription.tier = SubscriptionTier.PROFESSIONAL
        updated_subscription.billing_cycle = "monthly"
        updated_subscription.starts_at = datetime.now()
        updated_subscription.expires_at = datetime.now() + timedelta(days=30)
        updated_subscription.payment_method_id = "pm_123"
        updated_subscription.status = "active"
        updated_subscription.created_at = datetime.now()
        updated_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = updated_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.id == "sub_123"
        assert result.tier == "professional"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="manage_billing"
        )

        # Verify proration calculation
        self.subscription_service.calculate_proration.assert_called_once()

        # Verify billing adapter update
        self.billing_adapter.update_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            tier="professional"
        )

        # Verify subscription update
        self.subscription_repository.update.assert_called_once()

        # Verify organization update
        self.organization_repository.update.assert_called_once()

        # Verify audit log
        self.audit_service.log_activity.assert_called_once()

    def test_update_subscription_billing_cycle_success(self):
        """Test successful billing cycle update."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            billing_cycle="yearly",
            updated_by_user_id="user_123"
        )

        updated_subscription = Mock()
        updated_subscription.id = "sub_123"
        updated_subscription.organization_id = "org_123"
        updated_subscription.external_subscription_id = "ext_sub_123"
        updated_subscription.tier = SubscriptionTier.BASIC
        updated_subscription.billing_cycle = "yearly"
        updated_subscription.starts_at = datetime.now()
        updated_subscription.expires_at = datetime.now() + timedelta(days=365)
        updated_subscription.payment_method_id = "pm_123"
        updated_subscription.status = "active"
        updated_subscription.created_at = datetime.now()
        updated_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = updated_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.billing_cycle == "yearly"

        # Verify billing adapter update
        self.billing_adapter.update_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            billing_cycle="yearly"
        )

    def test_update_subscription_payment_method_success(self):
        """Test successful payment method update."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            payment_method_id="pm_456",
            updated_by_user_id="user_123"
        )

        updated_subscription = Mock()
        updated_subscription.id = "sub_123"
        updated_subscription.organization_id = "org_123"
        updated_subscription.external_subscription_id = "ext_sub_123"
        updated_subscription.tier = SubscriptionTier.BASIC
        updated_subscription.billing_cycle = "monthly"
        updated_subscription.starts_at = datetime.now()
        updated_subscription.expires_at = datetime.now() + timedelta(days=30)
        updated_subscription.payment_method_id = "pm_456"
        updated_subscription.status = "active"
        updated_subscription.created_at = datetime.now()
        updated_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = updated_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.payment_method_id == "pm_456"

        # Verify billing adapter update
        self.billing_adapter.update_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            payment_method_id="pm_456"
        )

    def test_update_subscription_multiple_fields_success(self):
        """Test successful update of multiple fields."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="enterprise",
            billing_cycle="yearly",
            payment_method_id="pm_789",
            updated_by_user_id="user_123"
        )

        updated_subscription = Mock()
        updated_subscription.id = "sub_123"
        updated_subscription.organization_id = "org_123"
        updated_subscription.external_subscription_id = "ext_sub_123"
        updated_subscription.tier = SubscriptionTier.ENTERPRISE
        updated_subscription.billing_cycle = "yearly"
        updated_subscription.starts_at = datetime.now()
        updated_subscription.expires_at = datetime.now() + timedelta(days=365)
        updated_subscription.payment_method_id = "pm_789"
        updated_subscription.status = "active"
        updated_subscription.created_at = datetime.now()
        updated_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = updated_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.tier == "enterprise"
        assert result.billing_cycle == "yearly"
        assert result.payment_method_id == "pm_789"

        # Verify billing adapter update with all fields
        self.billing_adapter.update_subscription.assert_called_once_with(
            external_subscription_id="ext_sub_123",
            tier="enterprise",
            billing_cycle="yearly",
            payment_method_id="pm_789"
        )

    def test_update_subscription_missing_subscription_id(self):
        """Test validation error when subscription ID is missing."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="",
            tier="professional",
            updated_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription ID is required" in str(exc_info.value)

    def test_update_subscription_no_fields_provided(self):
        """Test validation error when no fields are provided for update."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            updated_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "At least one field must be provided for update" in str(exc_info.value)

    def test_update_subscription_invalid_tier(self):
        """Test validation error when tier is invalid."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="invalid_tier",
            updated_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription tier must be one of" in str(exc_info.value)

    def test_update_subscription_invalid_billing_cycle(self):
        """Test validation error when billing cycle is invalid."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            billing_cycle="invalid_cycle",
            updated_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Billing cycle must be one of" in str(exc_info.value)

    def test_update_subscription_not_found(self):
        """Test error when subscription is not found."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        self.subscription_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription with ID sub_123 not found" in str(exc_info.value)

    def test_update_subscription_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to manage billing"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_update_subscription_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            self.use_case.execute(request)

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_update_subscription_no_external_id(self):
        """Test update when subscription has no external ID."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        # Mock subscription without external ID (free tier)
        self.subscription.external_subscription_id = None

        updated_subscription = Mock()
        updated_subscription.id = "sub_123"
        updated_subscription.organization_id = "org_123"
        updated_subscription.external_subscription_id = None
        updated_subscription.tier = SubscriptionTier.PROFESSIONAL
        updated_subscription.billing_cycle = "monthly"
        updated_subscription.starts_at = datetime.now()
        updated_subscription.expires_at = datetime.now() + timedelta(days=30)
        updated_subscription.payment_method_id = None
        updated_subscription.status = "active"
        updated_subscription.created_at = datetime.now()
        updated_subscription.updated_at = datetime.now()

        self.subscription_repository.update.return_value = updated_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.tier == "professional"

        # Verify no billing adapter call for subscription without external ID
        self.billing_adapter.update_subscription.assert_not_called()

    def test_update_subscription_billing_adapter_error(self):
        """Test error handling when billing adapter fails."""
        # Arrange
        request = UpdateSubscriptionRequestDTO(
            subscription_id="sub_123",
            tier="professional",
            updated_by_user_id="user_123"
        )

        self.billing_adapter.update_subscription.side_effect = Exception("Billing error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            self.use_case.execute(request)

        assert "Billing error" in str(exc_info.value)