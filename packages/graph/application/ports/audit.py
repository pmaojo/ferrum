"""Audit logging ports for system audit operations."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple


class AuditLogSeverity(str, Enum):
    """Severity levels for audit logs."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogCategory(str, Enum):
    """Categories for audit logs."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIGURATION = "system_configuration"
    USER_MANAGEMENT = "user_management"
    RESOURCE_MANAGEMENT = "resource_management"
    API_ACCESS = "api_access"


@dataclass
class AuditLogFilter:
    """Filter criteria for audit logs."""

    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    severity: Optional[AuditLogSeverity] = None
    category: Optional[AuditLogCategory] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    resource_id: Optional[str] = None


class AuditRepositoryPort(Protocol):
    """Port for audit log repository operations."""

    def create_log(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        severity: AuditLogSeverity,
        category: AuditLogCategory,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Create a new audit log entry.

        Args:
            tenant_id: Tenant identifier
            user_id: User who performed the action
            action: Action performed (e.g., "create", "update", "delete")
            resource_type: Type of resource affected (e.g., "user", "knowledge_graph")
            resource_id: Identifier of the affected resource
            severity: Severity level of the action
            category: Category of the action
            details: Additional details about the action
            ip_address: IP address of the user
            user_agent: User agent string
            session_id: Session identifier

        Returns:
            Identifier of the created audit log
        """
        ...

    def get_logs(
        self,
        filter_criteria: AuditLogFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get audit logs matching filter criteria.

        Args:
            filter_criteria: Filter criteria for logs
            page: Page number (1-based)
            page_size: Number of logs per page

        Returns:
            Tuple of (list of audit logs, total count)
        """
        ...

    def get_log_by_id(
        self,
        log_id: str,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get audit log by ID.

        Args:
            log_id: Audit log identifier
            tenant_id: Tenant identifier

        Returns:
            Audit log or None if not found
        """
        ...

    def get_summary(
        self,
        filter_criteria: AuditLogFilter,
    ) -> Dict[str, int]:
        """Get summary statistics for audit logs.

        Args:
            filter_criteria: Filter criteria for logs

        Returns:
            Dictionary with summary statistics
        """
        ...
