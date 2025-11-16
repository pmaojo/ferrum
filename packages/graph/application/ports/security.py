"""Port interfaces for security and audit functionality."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from domain.entities import APIKey, APIKeyStatus, AuditLog


class APIKeyManagementPort(ABC):
    """Port for API key management."""

    @abstractmethod
    async def create_api_key(
        self,
        api_key: APIKey,
    ) -> APIKey:
        """Create a new API key."""

    @abstractmethod
    async def get_api_key_by_hash(
        self,
        key_hash: str,
        tenant_id: str,
    ) -> Optional[APIKey]:
        """Get API key by hash."""

    @abstractmethod
    async def list_api_keys(
        self,
        tenant_id: str,
        status: Optional[APIKeyStatus] = None,
    ) -> List[APIKey]:
        """List API keys for a tenant."""

    @abstractmethod
    async def revoke_api_key(
        self,
        key_id: str,
        tenant_id: str,
    ) -> None:
        """Revoke an API key."""

    @abstractmethod
    async def record_api_key_usage(
        self,
        key_hash: str,
        tenant_id: str,
    ) -> None:
        """Record usage of an API key."""

    @abstractmethod
    async def check_rate_limit(
        self,
        key_hash: str,
        tenant_id: str,
    ) -> bool:
        """Check if API key has exceeded rate limit."""


class AuditLoggingPort(ABC):
    """Port for audit logging."""

    @abstractmethod
    async def log_action(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """Log an action to the audit trail."""

    @abstractmethod
    async def get_audit_logs(
        self,
        tenant_id: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs with filtering."""

    @abstractmethod
    async def get_audit_summary(
        self,
        tenant_id: str,
        time_period_days: int = 30,
    ) -> Dict[str, Any]:
        """Get audit summary for a time period."""

    @abstractmethod
    async def export_audit_logs(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json",
    ) -> str:
        """Export audit logs for compliance."""


class AuthenticationPort(ABC):
    """Port for authentication operations."""

    @abstractmethod
    async def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user."""

    @abstractmethod
    async def generate_session_token(
        self,
        user_id: str,
        tenant_id: str,
    ) -> str:
        """Generate a session token."""

    @abstractmethod
    async def validate_session_token(
        self,
        token: str,
    ) -> Optional[Dict[str, Any]]:
        """Validate a session token."""

    @abstractmethod
    async def revoke_session_token(
        self,
        token: str,
    ) -> None:
        """Revoke a session token."""

    @abstractmethod
    async def refresh_session_token(
        self,
        token: str,
    ) -> str:
        """Refresh a session token."""


class AuthorizationPort(ABC):
    """Port for authorization operations."""

    @abstractmethod
    async def check_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        resource_type: str = "knowledge_graph",
    ) -> bool:
        """Check if user has permission for a resource."""

    @abstractmethod
    async def get_user_permissions(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str = "knowledge_graph",
    ) -> List[str]:
        """Get all permissions for a user on a resource."""

    @abstractmethod
    async def grant_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        granted_by: Optional[str] = None,
        resource_type: str = "knowledge_graph",
    ) -> None:
        """Grant a permission to a user."""

    @abstractmethod
    async def revoke_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
        revoked_by: Optional[str] = None,
        resource_type: str = "knowledge_graph",
    ) -> None:
        """Revoke a permission from a user."""

    @abstractmethod
    async def check_resource_access(
        self,
        user_id: str,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """Check if user has access to a resource within tenant."""
