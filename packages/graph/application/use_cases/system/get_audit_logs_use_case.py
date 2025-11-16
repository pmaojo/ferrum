"""Use case for retrieving system audit logs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationPort, TracingPort
from application.ports.audit import (
    AuditLogCategory,
    AuditLogFilter,
    AuditLogSeverity,
    AuditRepositoryPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseRequestDTO, BaseResponseDTO, PaginationParams


@dataclass
class AuditLogDTO:
    """DTO for audit log entry."""

    id: str
    tenant_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    severity: str
    category: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    timestamp: datetime


@dataclass
class GetAuditLogsRequest(BaseRequestDTO):
    """Request for retrieving audit logs."""

    user_id: str
    tenant_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    resource_id: Optional[str] = None
    actor_id: Optional[str] = None  # Filter by user who performed the action
    include_summary: bool = False
    pagination: Optional[PaginationParams] = None


@dataclass
class GetAuditLogsResponse(BaseResponseDTO):
    """Response containing audit logs."""

    logs: List[AuditLogDTO] = field(default_factory=list)
    total_count: int = 0
    summary: Optional[Dict[str, int]] = None


class GetAuditLogsUseCase(BaseUseCase[GetAuditLogsRequest, GetAuditLogsResponse]):
    """Use case for retrieving system audit logs."""

    def __init__(
        self,
        audit_repository: AuditRepositoryPort,
        authorization_port: AuthorizationPort,
        tracer: TracingPort,
    ):
        super().__init__()
        self.audit_repository = audit_repository
        self.authorization_port = authorization_port
        self.tracer = tracer

    def _validate_request_internal(self, request: GetAuditLogsRequest) -> None:
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        # Validate severity if provided
        if request.severity:
            try:
                AuditLogSeverity(request.severity)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid severity: {request.severity}. Must be one of: {', '.join([s.value for s in AuditLogSeverity])}",
                    field="severity",
                )

        # Validate category if provided
        if request.category:
            try:
                AuditLogCategory(request.category)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid category: {request.category}. Must be one of: {', '.join([c.value for c in AuditLogCategory])}",
                    field="category",
                )

        # Validate time range if both are provided
        if (
            request.start_time
            and request.end_time
            and request.start_time > request.end_time
        ):
            raise ValidationError(
                message="Start time must be before end time", field="start_time"
            )

        # Set default pagination if not provided
        if not request.pagination:
            request.pagination = PaginationParams(page=1, page_size=20)

    async def _execute_internal(
        self, request: GetAuditLogsRequest
    ) -> GetAuditLogsResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="get_audit_logs",
            user_id=request.user_id,
            tenant_id=request.tenant_id,
        ):
            try:
                # Check authorization
                try:
                    self.authorization_port.check_permission(
                        user_id=request.user_id,
                        resource_type="audit_logs",
                        permission="view_audit_logs",
                    )
                except Exception as e:
                    raise AuthorizationError(
                        message="User does not have permission to view audit logs",
                        user_id=request.user_id,
                        resource_type="audit_logs",
                        permission="view_audit_logs",
                    ) from e

                # Create filter criteria
                filter_criteria = AuditLogFilter(
                    tenant_id=request.tenant_id,
                    user_id=request.actor_id,  # Filter by actor (user who performed the action)
                    resource_type=request.resource_type,
                    action=request.action,
                    severity=(
                        AuditLogSeverity(request.severity) if request.severity else None
                    ),
                    category=(
                        AuditLogCategory(request.category) if request.category else None
                    ),
                    start_time=request.start_time,
                    end_time=request.end_time,
                    resource_id=request.resource_id,
                )

                # Get logs with pagination
                logs, total_count = self.audit_repository.get_logs(
                    filter_criteria=filter_criteria,
                    page=request.pagination.page,
                    page_size=request.pagination.page_size,
                )

                # Convert to DTOs
                log_dtos = [
                    AuditLogDTO(
                        id=log["id"],
                        tenant_id=log["tenant_id"],
                        user_id=log["user_id"],
                        action=log["action"],
                        resource_type=log["resource_type"],
                        resource_id=log.get("resource_id"),
                        severity=log["severity"],
                        category=log["category"],
                        details=log["details"],
                        ip_address=log.get("ip_address"),
                        user_agent=log.get("user_agent"),
                        session_id=log.get("session_id"),
                        timestamp=log["timestamp"],
                    )
                    for log in logs
                ]

                # Get summary if requested
                summary = None
                if request.include_summary:
                    summary = self.audit_repository.get_summary(filter_criteria)

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="audit_logs_query",
                    value=1,
                    log_count=len(log_dtos),
                    total_count=total_count,
                )

                return GetAuditLogsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    logs=log_dtos,
                    total_count=total_count,
                    summary=summary,
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="audit_logs_query_errors",
                    value=1,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return GetAuditLogsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to get audit logs: {e}",
                    error_code="AUDIT_LOGS_QUERY_FAILED",
                ) from e
