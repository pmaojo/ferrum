"""Use case for retrieving system health information."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationPort, TracingPort
from application.ports.health import HealthCheckPort, HealthStatus
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseRequestDTO, BaseResponseDTO


@dataclass
class ComponentHealthDTO:
    """DTO for component health information."""

    name: str
    status: str
    message: str
    details: dict


@dataclass
class SystemHealthDTO:
    """DTO for system health information."""

    overall_status: str
    components: List[ComponentHealthDTO]
    timestamp: datetime


@dataclass
class GetSystemHealthRequest(BaseRequestDTO):
    """Request for system health information."""

    user_id: str
    include_details: bool = False


@dataclass
class GetSystemHealthResponse(BaseResponseDTO):
    """Response containing system health information."""

    health: Optional[SystemHealthDTO] = None


class GetSystemHealthUseCase(
    BaseUseCase[GetSystemHealthRequest, GetSystemHealthResponse]
):
    """Use case for retrieving system health information."""

    def __init__(
        self,
        health_check_port: HealthCheckPort,
        authorization_port: AuthorizationPort,
        tracer: TracingPort,
    ):
        super().__init__()
        self.health_check_port = health_check_port
        self.authorization_port = authorization_port
        self.tracer = tracer

    def _validate_request_internal(self, request: GetSystemHealthRequest) -> None:
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

    async def _execute_internal(
        self, request: GetSystemHealthRequest
    ) -> GetSystemHealthResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="get_system_health",
            user_id=request.user_id,
        ):
            try:
                # Check authorization
                try:
                    self.authorization_port.check_permission(
                        user_id=request.user_id,
                        resource_type="system",
                        permission="view_health",
                    )
                except Exception as e:
                    raise AuthorizationError(
                        message="User does not have permission to view system health",
                        user_id=request.user_id,
                        resource_type="system",
                        permission="view_health",
                    ) from e

                # Get component health status
                database_health = self.health_check_port.check_database_health()
                cache_health = self.health_check_port.check_cache_health()
                graph_db_health = self.health_check_port.check_graph_db_health()
                llm_health = self.health_check_port.check_llm_health()

                # Calculate overall status
                components = [
                    database_health,
                    cache_health,
                    graph_db_health,
                    llm_health,
                ]

                if any(c.status == HealthStatus.CRITICAL for c in components):
                    overall_status = HealthStatus.CRITICAL
                elif any(c.status == HealthStatus.DEGRADED for c in components):
                    overall_status = HealthStatus.DEGRADED
                else:
                    overall_status = HealthStatus.HEALTHY

                # Create component DTOs
                component_dtos = []
                for component in components:
                    details = component.details if request.include_details else {}
                    component_dtos.append(
                        ComponentHealthDTO(
                            name=component.name,
                            status=component.status.value,
                            message=component.message,
                            details=details,
                        )
                    )

                # Create health DTO
                health_dto = SystemHealthDTO(
                    overall_status=overall_status.value,
                    components=component_dtos,
                    timestamp=datetime.utcnow(),
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_health_check", value=1, status=overall_status.value
                )

                return GetSystemHealthResponse(
                    success=True, processing_time_ms=processing_time, health=health_dto
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_health_check_errors",
                    value=1,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return GetSystemHealthResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to get system health: {e}",
                    error_code="HEALTH_CHECK_FAILED",
                ) from e
