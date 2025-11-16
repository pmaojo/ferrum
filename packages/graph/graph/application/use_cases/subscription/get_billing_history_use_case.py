"""Get billing history use case implementation."""

from datetime import datetime, timedelta

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuthorizationServicePort,
    InvoiceRepositoryPort,
    OrganizationRepositoryPort,
    PaymentRepositoryPort,
)
from application.use_cases.dto import (
    BillingHistoryDTO,
    BillingHistoryRequestDTO,
    InvoiceDTO,
    PaginationParams,
    PaymentDTO,
)
from domain.entities import Invoice, Payment


class GetBillingHistoryUseCase:
    """Use case for retrieving billing history for an organization."""

    def __init__(
        self,
        invoice_repository: InvoiceRepositoryPort,
        payment_repository: PaymentRepositoryPort,
        organization_repository: OrganizationRepositoryPort,
        authorization_service: AuthorizationServicePort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            invoice_repository: Repository for invoice operations
            payment_repository: Repository for payment operations
            organization_repository: Repository for organization operations
            authorization_service: Service for authorization checks
        """
        self.invoice_repository = invoice_repository
        self.payment_repository = payment_repository
        self.organization_repository = organization_repository
        self.authorization_service = authorization_service

    def execute(
        self, request: BillingHistoryRequestDTO, user_id: str
    ) -> BillingHistoryDTO:
        """Execute the get billing history use case.

        Args:
            request: Billing history request DTO
            user_id: ID of the user requesting billing history

        Returns:
            Billing history DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            ApplicationError: When billing history retrieval fails
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

        # Set default pagination if not provided
        pagination = request.pagination or PaginationParams(page=1, page_size=20)

        # Set default date range if not provided (last 12 months)
        end_date = request.end_date or datetime.utcnow()
        start_date = request.start_date or (end_date - timedelta(days=365))

        # Get invoices
        invoices, total_invoices = self.invoice_repository.list_by_organization(
            organization_id=request.organization_id,
            start_date=start_date,
            end_date=end_date,
            page=pagination.page,
            page_size=pagination.page_size,
        )

        # Get payments
        payments, total_payments = self.payment_repository.list_by_organization(
            organization_id=request.organization_id,
            start_date=start_date,
            end_date=end_date,
            page=pagination.page,
            page_size=pagination.page_size,
        )

        # Convert to DTOs
        invoice_dtos = [self._invoice_to_dto(invoice) for invoice in invoices]
        payment_dtos = [self._payment_to_dto(payment) for payment in payments]

        # Return billing history DTO
        return BillingHistoryDTO(
            organization_id=request.organization_id,
            invoices=invoice_dtos,
            payments=payment_dtos,
            total_invoices=total_invoices,
            total_payments=total_payments,
        )

    def _validate_input(self, request: BillingHistoryRequestDTO) -> None:
        """Validate the input request.

        Args:
            request: Billing history request DTO

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

        # Validate pagination if provided
        if request.pagination:
            if request.pagination.page < 1:
                raise ValidationError(
                    message="Page must be greater than or equal to 1",
                    field="pagination.page",
                )

            if request.pagination.page_size < 1 or request.pagination.page_size > 100:
                raise ValidationError(
                    message="Page size must be between 1 and 100",
                    field="pagination.page_size",
                )

    def _invoice_to_dto(self, invoice: Invoice) -> InvoiceDTO:
        """Convert invoice entity to DTO.

        Args:
            invoice: Invoice entity

        Returns:
            Invoice DTO
        """
        return InvoiceDTO(
            id=invoice.id,
            organization_id=invoice.organization_id,
            subscription_id=invoice.subscription_id,
            external_invoice_id=invoice.external_invoice_id,
            amount=invoice.amount,
            currency=invoice.currency,
            status=invoice.status,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            created_at=invoice.created_at,
        )

    def _payment_to_dto(self, payment: Payment) -> PaymentDTO:
        """Convert payment entity to DTO.

        Args:
            payment: Payment entity

        Returns:
            Payment DTO
        """
        return PaymentDTO(
            id=payment.id,
            invoice_id=payment.invoice_id,
            external_payment_id=payment.external_payment_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            payment_method=payment.payment_method,
            processed_at=payment.processed_at,
            created_at=payment.created_at,
        )
