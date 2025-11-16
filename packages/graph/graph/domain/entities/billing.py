import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set
from ..exceptions import ValidationError, VersioningException

class SubscriptionTier(Enum):
    """Subscription tiers for organizations."""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
class Subscription:
    """Subscription entity for billing management."""

    id: str
    organization_id: str
    external_subscription_id: Optional[str]
    tier: SubscriptionTier
    billing_cycle: str  # monthly, yearly
    starts_at: datetime
    expires_at: datetime
    payment_method_id: Optional[str]
    status: str  # active, cancelled, expired, past_due
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate the subscription after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the subscription entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Subscription ID must be a non-empty string", param="id"
            )

        # Validate organization_id - must be non-empty string
        if not self.organization_id or not isinstance(self.organization_id, str):
            raise ValidationError(
                message="Organization ID must be a non-empty string",
                param="organization_id",
            )

        # Validate tier - must be a valid SubscriptionTier
        if not isinstance(self.tier, SubscriptionTier):
            raise ValidationError(
                message="Subscription tier must be a valid SubscriptionTier",
                param="tier",
            )

        # Validate billing_cycle
        if self.billing_cycle not in ["monthly", "yearly"]:
            raise ValidationError(
                message="Billing cycle must be 'monthly' or 'yearly'",
                param="billing_cycle",
            )

        # Validate status
        valid_statuses = ["active", "cancelled", "expired", "past_due"]
        if self.status not in valid_statuses:
            raise ValidationError(
                message=f"Status must be one of {valid_statuses}", param="status"
            )

        # Validate timestamps
        if not isinstance(self.starts_at, datetime):
            raise ValidationError(
                message="Starts at must be a datetime object", param="starts_at"
            )

        if not isinstance(self.expires_at, datetime):
            raise ValidationError(
                message="Expires at must be a datetime object", param="expires_at"
            )

        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                message="Updated at must be a datetime object", param="updated_at"
            )

        # Validate expires_at is after starts_at
        if self.expires_at <= self.starts_at:
            raise ValidationError(
                message="Expires at must be after starts at", param="expires_at"
            )

        # Validate updated_at is not before created_at
        if self.updated_at < self.created_at:
            raise ValidationError(
                message="Updated at cannot be before created at", param="updated_at"
            )

    @classmethod
    def create(
        cls,
        organization_id: str,
        tier: SubscriptionTier,
        billing_cycle: str = "monthly",
        external_subscription_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
    ) -> "Subscription":
        """Create a new subscription with auto-generated ID and timestamps.

        Args:
            organization_id: Organization ID the subscription belongs to
            tier: Subscription tier
            billing_cycle: Billing cycle (monthly or yearly)
            external_subscription_id: External billing system subscription ID
            payment_method_id: Payment method identifier

        Returns:
            A new Subscription instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        subscription_id = str(uuid.uuid4())

        # Calculate expiration based on billing cycle
        if billing_cycle == "yearly":
            expires_at = now.replace(year=now.year + 1)
        else:  # monthly
            if now.month == 12:
                expires_at = now.replace(year=now.year + 1, month=1)
            else:
                expires_at = now.replace(month=now.month + 1)

        return cls(
            id=subscription_id,
            organization_id=organization_id,
            external_subscription_id=external_subscription_id,
            tier=tier,
            billing_cycle=billing_cycle,
            starts_at=now,
            expires_at=expires_at,
            payment_method_id=payment_method_id,
            status="active",
            created_at=now,
            updated_at=now,
        )

    def update_tier(self, tier: SubscriptionTier) -> None:
        """Update the subscription tier.

        Args:
            tier: New subscription tier

        Raises:
            ValidationError: If tier is invalid
        """
        if not isinstance(tier, SubscriptionTier):
            raise ValidationError(
                message="Subscription tier must be a valid SubscriptionTier",
                param="tier",
            )

        self.tier = tier
        self.updated_at = datetime.utcnow()

    def cancel(self, cancel_at_period_end: bool = True) -> None:
        """Cancel the subscription.

        Args:
            cancel_at_period_end: Whether to cancel at the end of the current period
        """
        if cancel_at_period_end:
            self.status = "cancelled"
        else:
            self.status = "cancelled"
            self.expires_at = datetime.utcnow()

        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if the subscription is currently active."""
        return self.status == "active" and datetime.utcnow() < self.expires_at

    def is_expired(self) -> bool:
        """Check if the subscription has expired."""
        return datetime.utcnow() >= self.expires_at


class Invoice:
    """Invoice entity for billing management."""

    id: str
    organization_id: str
    subscription_id: str
    external_invoice_id: Optional[str]
    amount: float
    currency: str
    status: str  # draft, open, paid, void, uncollectible
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    created_at: datetime

    def __post_init__(self):
        """Validate the invoice after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the invoice entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Invoice ID must be a non-empty string", param="id"
            )

        # Validate organization_id - must be non-empty string
        if not self.organization_id or not isinstance(self.organization_id, str):
            raise ValidationError(
                message="Organization ID must be a non-empty string",
                param="organization_id",
            )

        # Validate subscription_id - must be non-empty string
        if not self.subscription_id or not isinstance(self.subscription_id, str):
            raise ValidationError(
                message="Subscription ID must be a non-empty string",
                param="subscription_id",
            )

        # Validate amount - must be positive number
        if not isinstance(self.amount, (int, float)) or self.amount < 0:
            raise ValidationError(
                message="Amount must be a non-negative number", param="amount"
            )

        # Validate currency - must be non-empty string
        if not self.currency or not isinstance(self.currency, str):
            raise ValidationError(
                message="Currency must be a non-empty string", param="currency"
            )

        # Validate status
        valid_statuses = ["draft", "open", "paid", "void", "uncollectible"]
        if self.status not in valid_statuses:
            raise ValidationError(
                message=f"Status must be one of {valid_statuses}", param="status"
            )

        # Validate timestamps
        if not isinstance(self.invoice_date, datetime):
            raise ValidationError(
                message="Invoice date must be a datetime object", param="invoice_date"
            )

        if not isinstance(self.due_date, datetime):
            raise ValidationError(
                message="Due date must be a datetime object", param="due_date"
            )

        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if self.paid_at is not None and not isinstance(self.paid_at, datetime):
            raise ValidationError(
                message="Paid at must be a datetime object or None", param="paid_at"
            )

        # Validate due_date is not before invoice_date
        if self.due_date < self.invoice_date:
            raise ValidationError(
                message="Due date cannot be before invoice date", param="due_date"
            )

    @classmethod
    def create(
        cls,
        organization_id: str,
        subscription_id: str,
        amount: float,
        currency: str = "USD",
        external_invoice_id: Optional[str] = None,
    ) -> "Invoice":
        """Create a new invoice with auto-generated ID and timestamps.

        Args:
            organization_id: Organization ID the invoice belongs to
            subscription_id: Subscription ID the invoice is for
            amount: Invoice amount
            currency: Currency code (default: USD)
            external_invoice_id: External billing system invoice ID

        Returns:
            A new Invoice instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        invoice_id = str(uuid.uuid4())
        due_date = now + timedelta(days=30)  # 30 days from now

        return cls(
            id=invoice_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            external_invoice_id=external_invoice_id,
            amount=amount,
            currency=currency,
            status="open",
            invoice_date=now,
            due_date=due_date,
            paid_at=None,
            created_at=now,
        )

    def mark_paid(self) -> None:
        """Mark the invoice as paid."""
        self.status = "paid"
        self.paid_at = datetime.utcnow()

    def void(self) -> None:
        """Void the invoice."""
        self.status = "void"


@dataclass
class Payment:
    """Payment entity for billing management."""

    id: str
    invoice_id: str
    external_payment_id: Optional[str]
    amount: float
    currency: str
    status: str  # pending, succeeded, failed, cancelled
    payment_method: str
    processed_at: Optional[datetime]
    created_at: datetime

    def __post_init__(self):
        """Validate the payment after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the payment entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Payment ID must be a non-empty string", param="id"
            )

        # Validate invoice_id - must be non-empty string
        if not self.invoice_id or not isinstance(self.invoice_id, str):
            raise ValidationError(
                message="Invoice ID must be a non-empty string", param="invoice_id"
            )

        # Validate amount - must be positive number
        if not isinstance(self.amount, (int, float)) or self.amount < 0:
            raise ValidationError(
                message="Amount must be a non-negative number", param="amount"
            )

        # Validate currency - must be non-empty string
        if not self.currency or not isinstance(self.currency, str):
            raise ValidationError(
                message="Currency must be a non-empty string", param="currency"
            )

        # Validate status
        valid_statuses = ["pending", "succeeded", "failed", "cancelled"]
        if self.status not in valid_statuses:
            raise ValidationError(
                message=f"Status must be one of {valid_statuses}", param="status"
            )

        # Validate payment_method - must be non-empty string
        if not self.payment_method or not isinstance(self.payment_method, str):
            raise ValidationError(
                message="Payment method must be a non-empty string",
                param="payment_method",
            )

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if self.processed_at is not None and not isinstance(
            self.processed_at, datetime
        ):
            raise ValidationError(
                message="Processed at must be a datetime object or None",
                param="processed_at",
            )

    @classmethod
    def create(
        cls,
        invoice_id: str,
        amount: float,
        payment_method: str,
        currency: str = "USD",
        external_payment_id: Optional[str] = None,
    ) -> "Payment":
        """Create a new payment with auto-generated ID and timestamps.

        Args:
            invoice_id: Invoice ID the payment is for
            amount: Payment amount
            payment_method: Payment method used
            currency: Currency code (default: USD)
            external_payment_id: External payment processor payment ID

        Returns:
            A new Payment instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        payment_id = str(uuid.uuid4())

        return cls(
            id=payment_id,
            invoice_id=invoice_id,
            external_payment_id=external_payment_id,
            amount=amount,
            currency=currency,
            status="pending",
            payment_method=payment_method,
            processed_at=None,
            created_at=now,
        )

    def mark_succeeded(self) -> None:
        """Mark the payment as succeeded."""
        self.status = "succeeded"
        self.processed_at = datetime.utcnow()

    def mark_failed(self) -> None:
        """Mark the payment as failed."""
        self.status = "failed"
        self.processed_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the payment."""
        self.status = "cancelled"
        self.processed_at = datetime.utcnow()

