"""Tests for CreateSubscriptionUseCase."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.use_cases.subscription.create_subscription_use_case import CreateSubscriptionUseCase
from application.use_cases.dto import CreateSubscriptionRequestDTO


class TestCreateSubscriptionUseCase:
    """Test cases for CreateSubscriptionUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.subscription_repository = Mock()
        self.organization_repository = Mock()
        self.billing_adapter = Mock()
        self.authorization_service = Mock()
        self.audit_service = Mock()

        self.use_case = CreateSubscriptionUseCase(
            subscription_repository=self.subscription_repository,
            organization_repository=self.organization_repository,
            billing_adapter=self.billing_adapter,
            authorization_service=self.authorization_service,
            audit_service=self.audit_service
        )

        # Mock organization
        self.organization = Organization.create(
            name="Test Organization",
            subscription_tier=SubscriptionTier.FREE
        )
        self.organization_repository.get_by_id.return_value = self.organization

        # Mock billing adapter response
        self.billing_adapter.create_subscription.return_value = {
            "subscription_id": "ext_sub_123"
        }

    def test_create_free_subscription_success(self):
        """Test successful creation of free subscription."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="free",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        self.subscription_repository.get_by_organization_id.return_value = None

        # Mock created subscription
        created_subscription = Mock()
        created_subscription.id = "sub_123"
        created_subscription.organization_id = "org_123"
        created_subscription.external_subscription_id = None
        created_subscription.tier = SubscriptionTier.FREE
        created_subscription.billing_cycle = "monthly"
        created_subscription.starts_at = datetime.now()
        created_subscription.expires_at = datetime.now()
        created_subscription.payment_method_id = None
        created_subscription.status = "active"
        created_subscription.created_at = datetime.now()
        created_subscription.updated_at = datetime.now()

        self.subscription_repository.create.return_value = created_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.id == "sub_123"
        assert result.organization_id == "org_123"
        assert result.tier == "free"
        assert result.billing_cycle == "monthly"
        assert result.status == "active"

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="manage_billing"
        )

        # Verify organization lookup
        self.organization_repository.get_by_id.assert_called_once_with("org_123")

        # Verify no billing adapter call for free tier
        self.billing_adapter.create_subscription.assert_not_called()

        # Verify subscription creation
        self.subscription_repository.create.assert_called_once()

        # Verify organization update
        self.organization_repository.update.assert_called_once()

        # Verify audit log
        self.audit_service.log_activity.assert_called_once()

    def test_create_paid_subscription_success(self):
        """Test successful creation of paid subscription."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="professional",
            billing_cycle="monthly",
            payment_method_id="pm_123",
            created_by_user_id="user_123"
        )

        self.subscription_repository.get_by_organization_id.return_value = None

        # Mock created subscription
        created_subscription = Mock()
        created_subscription.id = "sub_123"
        created_subscription.organization_id = "org_123"
        created_subscription.external_subscription_id = "ext_sub_123"
        created_subscription.tier = SubscriptionTier.PROFESSIONAL
        created_subscription.billing_cycle = "monthly"
        created_subscription.starts_at = datetime.now()
        created_subscription.expires_at = datetime.now()
        created_subscription.payment_method_id = "pm_123"
        created_subscription.status = "active"
        created_subscription.created_at = datetime.now()
        created_subscription.updated_at = datetime.now()

        self.subscription_repository.create.return_value = created_subscription

        # Act
        result = self.use_case.execute(request)

        # Assert
        assert result.id == "sub_123"
        assert result.organization_id == "org_123"
        assert result.tier == "professional"
        assert result.external_subscription_id == "ext_sub_123"
        assert result.payment_method_id == "pm_123"

        # Verify billing adapter call for paid tier
        self.billing_adapter.create_subscription.assert_called_once_with(
            organization_id="org_123",
            tier="professional",
            billing_cycle="monthly",
            payment_method_id="pm_123"
        )

    def test_create_subscription_missing_organization_id(self):
        """Test validation error when organization ID is missing."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="",
            tier="basic",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Organization ID is required" in str(exc_info.value)

    def test_create_subscription_invalid_tier(self):
        """Test validation error when tier is invalid."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="invalid_tier",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Subscription tier must be one of" in str(exc_info.value)

    def test_create_subscription_invalid_billing_cycle(self):
        """Test validation error when billing cycle is invalid."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="invalid_cycle",
            created_by_user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Billing cycle must be one of" in str(exc_info.value)

    def test_create_subscription_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            message="User lacks permission to manage billing",
            user_id="user_123"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request)

    def test_create_subscription_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            self.use_case.execute(request)

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_create_subscription_existing_active_subscription(self):
        """Test error when organization already has active subscription."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        # Mock existing active subscription
        existing_subscription = Mock()
        existing_subscription.is_active.return_value = True
        self.subscription_repository.get_by_organization_id.return_value = existing_subscription

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            self.use_case.execute(request)

        assert "Organization already has an active subscription" in str(exc_info.value)

    def test_create_paid_subscription_missing_payment_method(self):
        """Test validation error when payment method is missing for paid tier."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="monthly",
            created_by_user_id="user_123"
        )

        self.subscription_repository.get_by_organization_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request)

        assert "Payment method ID is required for paid tiers" in str(exc_info.value)

    def test_create_subscription_billing_adapter_error(self):
        """Test error handling when billing adapter fails."""
        # Arrange
        request = CreateSubscriptionRequestDTO(
            organization_id="org_123",
            tier="basic",
            billing_cycle="monthly",
            payment_method_id="pm_123",
            created_by_user_id="user_123"
        )

        self.subscription_repository.get_by_organization_id.return_value = None
        self.billing_adapter.create_subscription.side_effect = Exception("Billing error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            self.use_case.execute(request)

        assert "Billing error" in str(exc_info.value)