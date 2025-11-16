import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set
from ..exceptions import ValidationError, VersioningException
from .billing import SubscriptionTier

class UserRole(Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

@dataclass
class User:
    """User entity with authentication and authorization."""

    id: str
    email: str
    name: str
    password_hash: str
    organization_id: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    def __post_init__(self):
        """Validate the user after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the user entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="User ID must be a non-empty string", param="id"
            )

        # Validate email - must be non-empty string with basic format
        if not self.email or not isinstance(self.email, str):
            raise ValidationError(
                message="Email must be a non-empty string", param="email"
            )

        # Basic email format validation
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise ValidationError(
                message="Email must be in valid format", param="email"
            )

        # Validate name - must be non-empty string
        if not self.name or not isinstance(self.name, str):
            raise ValidationError(
                message="Name must be a non-empty string", param="name"
            )

        # Validate password_hash - must be non-empty string
        if not self.password_hash or not isinstance(self.password_hash, str):
            raise ValidationError(
                message="Password hash must be a non-empty string",
                param="password_hash",
            )

        # Validate organization_id - must be non-empty string
        if not self.organization_id or not isinstance(self.organization_id, str):
            raise ValidationError(
                message="Organization ID must be a non-empty string",
                param="organization_id",
            )

        # Validate role - must be a valid UserRole
        if not isinstance(self.role, UserRole):
            raise ValidationError(message="Role must be a valid UserRole", param="role")

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                message="Updated at must be a datetime object", param="updated_at"
            )

        if self.last_login is not None and not isinstance(self.last_login, datetime):
            raise ValidationError(
                message="Last login must be a datetime object or None",
                param="last_login",
            )

        # Validate is_active - must be boolean
        if not isinstance(self.is_active, bool):
            raise ValidationError(
                message="is_active must be a boolean value", param="is_active"
            )

        # Validate updated_at is not before created_at
        if self.updated_at < self.created_at:
            raise ValidationError(
                message="Updated at cannot be before created at", param="updated_at"
            )

    @classmethod
    def create(
        cls,
        email: str,
        name: str,
        password_hash: str,
        organization_id: str,
        role: UserRole = UserRole.VIEWER,
    ) -> "User":
        """Create a new user with auto-generated ID and timestamps.

        Args:
            email: User email address
            name: User full name
            password_hash: Hashed password
            organization_id: Organization ID the user belongs to
            role: User role (default: VIEWER)

        Returns:
            A new User instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        user_id = str(uuid.uuid4())

        return cls(
            id=user_id,
            email=email,
            name=name,
            password_hash=password_hash,
            organization_id=organization_id,
            role=role,
            created_at=now,
            updated_at=now,
            last_login=None,
            is_active=True,
        )

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

@dataclass
class GraphAccessPolicy:
    """Access policy defining permissions for a user over a knowledge graph."""

    kg_id: str
    tenant_id: str
    user_id: str
    role: UserRole
    permissions: List[str]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.kg_id or not isinstance(self.kg_id, str):
            raise ValidationError(message="Knowledge graph ID must be a non-empty string", param="kg_id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValidationError(message="User ID must be a non-empty string", param="user_id")
        if not isinstance(self.role, UserRole):
            raise ValidationError(message="Role must be a valid UserRole", param="role")
        if not isinstance(self.permissions, list) or not all(isinstance(p, str) for p in self.permissions):
            raise ValidationError(message="Permissions must be a list of strings", param="permissions")

    def update_role(self, role: UserRole) -> None:
        """Update the user role.

        Args:
            role: New user role

        Raises:
            ValidationError: If role is invalid
        """
        if not isinstance(role, UserRole):
            raise ValidationError(message="Role must be a valid UserRole", param="role")

        self.role = role
        self.updated_at = datetime.utcnow()


class Organization:
    """Organization entity for multi-tenancy."""

    id: str
    name: str
    subscription_tier: SubscriptionTier
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    def __post_init__(self):
        """Validate the organization after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate the organization entity.

        Raises:
            ValidationError: If any validation fails
        """
        # Validate id - must be non-empty string
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(
                message="Organization ID must be a non-empty string", param="id"
            )

        # Validate name - must be non-empty string
        if not self.name or not isinstance(self.name, str):
            raise ValidationError(
                message="Organization name must be a non-empty string", param="name"
            )

        # Validate subscription_tier - must be a valid SubscriptionTier
        if not isinstance(self.subscription_tier, SubscriptionTier):
            raise ValidationError(
                message="Subscription tier must be a valid SubscriptionTier",
                param="subscription_tier",
            )

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                message="Created at must be a datetime object", param="created_at"
            )

        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                message="Updated at must be a datetime object", param="updated_at"
            )

        if self.subscription_expires_at is not None and not isinstance(
            self.subscription_expires_at, datetime
        ):
            raise ValidationError(
                message="Subscription expires at must be a datetime object or None",
                param="subscription_expires_at",
            )

        # Validate is_active - must be boolean
        if not isinstance(self.is_active, bool):
            raise ValidationError(
                message="is_active must be a boolean value", param="is_active"
            )

        # Validate updated_at is not before created_at
        if self.updated_at < self.created_at:
            raise ValidationError(
                message="Updated at cannot be before created at", param="updated_at"
            )

    @classmethod
    def create(
        cls, name: str, subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> "Organization":
        """Create a new organization with auto-generated ID and timestamps.

        Args:
            name: Organization name
            subscription_tier: Subscription tier (default: FREE)

        Returns:
            A new Organization instance

        Raises:
            ValidationError: If any parameter is invalid
        """
        now = datetime.utcnow()
        org_id = str(uuid.uuid4())

        return cls(
            id=org_id,
            name=name,
            subscription_tier=subscription_tier,
            subscription_expires_at=None,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

    def update_subscription(
        self, tier: SubscriptionTier, expires_at: Optional[datetime] = None
    ) -> None:
        """Update the subscription tier and expiration.

        Args:
            tier: New subscription tier
            expires_at: Optional expiration date

        Raises:
            ValidationError: If tier is invalid
        """
        if not isinstance(tier, SubscriptionTier):
            raise ValidationError(
                message="Subscription tier must be a valid SubscriptionTier",
                param="subscription_tier",
            )

        self.subscription_tier = tier
        self.subscription_expires_at = expires_at
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the organization."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the organization."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
class APIKeyStatus(Enum):
    """Status of API keys."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class APIKey:
    """API Key entity for external integrations."""

    id: str
    tenant_id: str
    key_hash: str
    name: str
    scopes: List[str]
    status: APIKeyStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    usage_count: int = 0
    rate_limit: Optional[int] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the API key entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="API key ID must be a non-empty string", param="id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.key_hash or not isinstance(self.key_hash, str):
            raise ValidationError(message="Key hash must be a non-empty string", param="key_hash")
        if not self.name or not isinstance(self.name, str):
            raise ValidationError(message="Name must be a non-empty string", param="name")
        if not isinstance(self.scopes, list):
            raise ValidationError(message="Scopes must be a list", param="scopes")
        if not isinstance(self.status, APIKeyStatus):
            raise ValidationError(message="Status must be a valid APIKeyStatus", param="status")

    @classmethod
    def create(
        cls,
        tenant_id: str,
        key_hash: str,
        name: str,
        scopes: List[str],
        created_by: str,
        expires_at: Optional[datetime] = None,
        rate_limit: Optional[int] = None,
    ) -> "APIKey":
        """Create a new API key."""
        now = datetime.utcnow()
        key_id = str(uuid.uuid4())

        return cls(
            id=key_id,
            tenant_id=tenant_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes,
            status=APIKeyStatus.ACTIVE,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            last_used_at=None,
            expires_at=expires_at,
            usage_count=0,
            rate_limit=rate_limit,
        )

    def record_usage(self) -> None:
        """Record usage of this API key."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def is_valid(self) -> bool:
        """Check if the API key is valid and not expired."""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


@dataclass
class AuditLog:
    """Audit log entity for tracking system activities."""

    id: str
    tenant_id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate the audit log entity."""
        if not self.id or not isinstance(self.id, str):
            raise ValidationError(message="Audit log ID must be a non-empty string", param="id")
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValidationError(message="Tenant ID must be a non-empty string", param="tenant_id")
        if not self.action or not isinstance(self.action, str):
            raise ValidationError(message="Action must be a non-empty string", param="action")
        if not self.resource_type or not isinstance(self.resource_type, str):
            raise ValidationError(message="Resource type must be a non-empty string", param="resource_type")
        if not isinstance(self.details, dict):
            raise ValidationError(message="Details must be a dictionary", param="details")
        if not isinstance(self.timestamp, datetime):
            raise ValidationError(message="Timestamp must be a datetime", param="timestamp")

    @classmethod
    def create(
        cls,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "AuditLog":
        """Create a new audit log entry."""
        now = datetime.utcnow()
        log_id = str(uuid.uuid4())

        return cls(
            id=log_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            timestamp=now,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

