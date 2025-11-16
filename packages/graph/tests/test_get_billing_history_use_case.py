"""Tests for GetBillingHistoryUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from domain.entities import Organization, Invoice, Payment, SubscriptionTier
from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.use_cases.subscription.get_billing_history_use_case import GetBillingHistoryUseCase
from application.use_cases.dto import BillingHistoryRequestDTO, PaginationParams


class TestGetBillingHistoryUseCase:
    """Test cases for GetBillingHistoryUseCase."""

    def setup_method(self):
        """Set up test dependencies."""
        self.invoice_repository = Mock()
        self.payment_repository = Mock()
        self.organization_repository = Mock()
        self.authorization_service = Mock()

        self.use_case = GetBillingHistoryUseCase(
            invoice_repository=self.invoice_repository,
            payment_repository=self.payment_repository,
            organization_repository=self.organization_repository,
            authorization_service=self.authorization_service
        )

        # Mock organization
        self.organization = Organization.create(
            name="Test Organization",
            subscription_tier=SubscriptionTier.PROFESSIONAL
        )
        self.organization_repository.get_by_id.return_value = self.organization

        # Mock invoices
        self.invoices = [
            Invoice.create(
                organization_id="org_123",
                subscription_id="sub_123",
                amount=99.99,
                currency="USD"
            ),
            Invoice.create(
                organization_id="org_123",
                subscription_id="sub_123",
                amount=199.99,
                currency="USD"
            )
        ]
        self.invoice_repository.list_by_organization.return_value = (self.invoices, 2)

        # Mock payments
        self.payments = [
            Payment.create(
                invoice_id="inv_123",
                amount=99.99,
                payment_method="credit_card"
            ),
            Payment.create(
                invoice_id="inv_456",
                amount=199.99,
                payment_method="credit_card"
            )
        ]
        self.payment_repository.list_by_organization.return_value = (self.payments, 2)

    def test_get_billing_history_success(self):
        """Test successful billing history retrieval."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"
        assert len(result.invoices) == 2
        assert len(result.payments) == 2
        assert result.total_invoices == 2
        assert result.total_payments == 2

        # Check invoice DTOs
        assert result.invoices[0].organization_id == "org_123"
        assert result.invoices[0].amount == 99.99
        assert result.invoices[0].currency == "USD"
        assert result.invoices[1].amount == 199.99

        # Check payment DTOs
        assert result.payments[0].amount == 99.99
        assert result.payments[0].payment_method == "credit_card"
        assert result.payments[1].amount == 199.99

        # Verify authorization check
        self.authorization_service.check_permission.assert_called_once_with(
            user_id="user_123",
            resource_id="org_123",
            action="view_billing"
        )

        # Verify organization lookup
        self.organization_repository.get_by_id.assert_called_once_with("org_123")

        # Verify repository calls with default date range (last 12 months)
        self.invoice_repository.list_by_organization.assert_called_once()
        self.payment_repository.list_by_organization.assert_called_once()

    def test_get_billing_history_with_date_range(self):
        """Test billing history retrieval with specific date range."""
        # Arrange
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        request = BillingHistoryRequestDTO(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"

        # Verify repository calls with specified date range
        self.invoice_repository.list_by_organization.assert_called_once_with(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=20
        )

        self.payment_repository.list_by_organization.assert_called_once_with(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=20
        )

    def test_get_billing_history_with_pagination(self):
        """Test billing history retrieval with pagination."""
        # Arrange
        pagination = PaginationParams(page=2, page_size=10)
        request = BillingHistoryRequestDTO(
            organization_id="org_123",
            pagination=pagination
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"

        # Verify repository calls with pagination
        self.invoice_repository.list_by_organization.assert_called_once()
        call_args = self.invoice_repository.list_by_organization.call_args
        assert call_args[1]["page"] == 2
        assert call_args[1]["page_size"] == 10

        self.payment_repository.list_by_organization.assert_called_once()
        call_args = self.payment_repository.list_by_organization.call_args
        assert call_args[1]["page"] == 2
        assert call_args[1]["page_size"] == 10

    def test_get_billing_history_empty_results(self):
        """Test billing history retrieval with no invoices or payments."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        # Mock empty results
        self.invoice_repository.list_by_organization.return_value = ([], 0)
        self.payment_repository.list_by_organization.return_value = ([], 0)

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        assert result.organization_id == "org_123"
        assert len(result.invoices) == 0
        assert len(result.payments) == 0
        assert result.total_invoices == 0
        assert result.total_payments == 0

    def test_get_billing_history_missing_organization_id(self):
        """Test validation error when organization ID is missing."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id=""
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization ID is required" in str(exc_info.value)

    def test_get_billing_history_invalid_date_range(self):
        """Test validation error when start date is after end date."""
        # Arrange
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(days=1)  # End before start

        request = BillingHistoryRequestDTO(
            organization_id="org_123",
            start_date=start_date,
            end_date=end_date
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Start date must be before end date" in str(exc_info.value)

    def test_get_billing_history_invalid_pagination_page(self):
        """Test validation error when pagination page is invalid."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            pagination = PaginationParams(page=0, page_size=20)  # This will raise ValueError

        assert "Page must be greater than or equal to 1" in str(exc_info.value)

    def test_get_billing_history_invalid_pagination_page_size(self):
        """Test validation error when pagination page size is invalid."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            pagination = PaginationParams(page=1, page_size=101)  # This will raise ValueError

        assert "Page size must be less than or equal to 100" in str(exc_info.value)

    def test_get_billing_history_authorization_error(self):
        """Test authorization error when user lacks permission."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        self.authorization_service.check_permission.side_effect = AuthorizationError(
            "User lacks permission to view billing"
        )

        # Act & Assert
        with pytest.raises(AuthorizationError):
            self.use_case.execute(request, user_id="user_123")

    def test_get_billing_history_organization_not_found(self):
        """Test error when organization is not found."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        self.organization_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ApplicationError) as exc_info:
            self.use_case.execute(request, user_id="user_123")

        assert "Organization with ID org_123 not found" in str(exc_info.value)

    def test_get_billing_history_invoice_dto_conversion(self):
        """Test proper conversion of invoice entity to DTO."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        # Create invoice with all fields
        invoice = Invoice.create(
            organization_id="org_123",
            subscription_id="sub_123",
            amount=149.99,
            currency="EUR",
            external_invoice_id="ext_inv_123"
        )
        invoice.mark_paid()  # Set paid_at timestamp

        self.invoice_repository.list_by_organization.return_value = ([invoice], 1)

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        invoice_dto = result.invoices[0]
        assert invoice_dto.id == invoice.id
        assert invoice_dto.organization_id == "org_123"
        assert invoice_dto.subscription_id == "sub_123"
        assert invoice_dto.external_invoice_id == "ext_inv_123"
        assert invoice_dto.amount == 149.99
        assert invoice_dto.currency == "EUR"
        assert invoice_dto.status == "paid"
        assert invoice_dto.paid_at is not None
        assert invoice_dto.created_at == invoice.created_at

    def test_get_billing_history_payment_dto_conversion(self):
        """Test proper conversion of payment entity to DTO."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        # Create payment with all fields
        payment = Payment.create(
            invoice_id="inv_123",
            amount=149.99,
            payment_method="bank_transfer",
            currency="EUR",
            external_payment_id="ext_pay_123"
        )
        payment.mark_succeeded()  # Set processed_at timestamp

        self.payment_repository.list_by_organization.return_value = ([payment], 1)

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        payment_dto = result.payments[0]
        assert payment_dto.id == payment.id
        assert payment_dto.invoice_id == "inv_123"
        assert payment_dto.external_payment_id == "ext_pay_123"
        assert payment_dto.amount == 149.99
        assert payment_dto.currency == "EUR"
        assert payment_dto.status == "succeeded"
        assert payment_dto.payment_method == "bank_transfer"
        assert payment_dto.processed_at is not None
        assert payment_dto.created_at == payment.created_at

    def test_get_billing_history_default_pagination(self):
        """Test that default pagination is used when not provided."""
        # Arrange
        request = BillingHistoryRequestDTO(
            organization_id="org_123"
        )

        # Act
        result = self.use_case.execute(request, user_id="user_123")

        # Assert
        # Verify default pagination was used (page=1, page_size=20)
        call_args = self.invoice_repository.list_by_organization.call_args
        assert call_args[1]["page"] == 1
        assert call_args[1]["page_size"] == 20