"""Use case for retrieving system metrics."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from application.exceptions import ApplicationError, AuthorizationError, ValidationError
from application.ports import AuthorizationPort, MetricsRepositoryPort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseRequestDTO, BaseResponseDTO


@dataclass
class MetricDataPoint:
    """Data point for a metric."""

    timestamp: datetime
    value: float


@dataclass
class MetricSeries:
    """Time series data for a metric."""

    name: str
    data_points: List[MetricDataPoint]
    labels: Dict[str, str]


@dataclass
class SystemMetricsDTO:
    """DTO for system metrics information."""

    metrics: List[MetricSeries]
    start_time: datetime
    end_time: datetime
    aggregation_period: str  # e.g., "1m", "5m", "1h"


@dataclass
class GetSystemMetricsRequest(BaseRequestDTO):
    """Request for system metrics information."""

    user_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metrics: Optional[List[str]] = None
    aggregation_period: str = "5m"
    labels: Optional[Dict[str, str]] = None


@dataclass
class GetSystemMetricsResponse(BaseResponseDTO):
    """Response containing system metrics information."""

    metrics: Optional[SystemMetricsDTO] = None


class GetSystemMetricsUseCase(
    BaseUseCase[GetSystemMetricsRequest, GetSystemMetricsResponse]
):
    """Use case for retrieving system metrics information."""

    def __init__(
        self,
        metrics_repository: MetricsRepositoryPort,
        authorization_port: AuthorizationPort,
        tracer: TracingPort,
    ):
        super().__init__()
        self.metrics_repository = metrics_repository
        self.authorization_port = authorization_port
        self.tracer = tracer

    def _validate_request_internal(self, request: GetSystemMetricsRequest) -> None:
        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        # Set default time range if not provided
        if not request.end_time:
            request.end_time = datetime.utcnow()

        if not request.start_time:
            # Default to 24 hours before end time
            request.start_time = request.end_time - timedelta(hours=24)

        if request.start_time >= request.end_time:
            raise ValidationError(
                message="Start time must be before end time", field="start_time"
            )

        # Set default metrics if not provided
        if not request.metrics:
            request.metrics = [
                "system_cpu_usage",
                "system_memory_usage",
                "system_api_requests",
                "system_error_rate",
                "system_database_connections",
                "system_cache_hit_rate",
            ]

    async def _execute_internal(
        self, request: GetSystemMetricsRequest
    ) -> GetSystemMetricsResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="get_system_metrics",
            user_id=request.user_id,
        ):
            try:
                # Check authorization
                try:
                    self.authorization_port.check_permission(
                        user_id=request.user_id,
                        resource_type="system",
                        permission="view_metrics",
                    )
                except Exception as e:
                    raise AuthorizationError(
                        message="User does not have permission to view system metrics",
                        user_id=request.user_id,
                        resource_type="system",
                        permission="view_metrics",
                    ) from e

                # Fetch metrics data
                metric_series_list = []
                for metric_name in request.metrics:
                    try:
                        # Query metrics repository for each metric
                        data_points = self.metrics_repository.query_range(
                            metric=metric_name,
                            tenant_id="system",  # System metrics are global, not tenant-specific
                            start_time=request.start_time,
                            end_time=request.end_time,
                            labels=request.labels,
                        )

                        # Convert to MetricDataPoint objects
                        metric_data_points = [
                            MetricDataPoint(timestamp=ts, value=value)
                            for ts, value in data_points
                        ]

                        # Create MetricSeries object
                        labels = request.labels or {}
                        metric_series = MetricSeries(
                            name=metric_name,
                            data_points=metric_data_points,
                            labels=labels,
                        )

                        metric_series_list.append(metric_series)
                    except Exception as e:
                        self.tracer.record_metric(
                            name="system_metrics_query_errors",
                            value=1,
                            metric_name=metric_name,
                            error_type=type(e).__name__,
                        )
                        # Log error but continue with other metrics
                        continue

                # Create metrics DTO
                metrics_dto = SystemMetricsDTO(
                    metrics=metric_series_list,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    aggregation_period=request.aggregation_period,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_metrics_query",
                    value=1,
                    metric_count=len(metric_series_list),
                )

                return GetSystemMetricsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    metrics=metrics_dto,
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_metrics_query_errors",
                    value=1,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, AuthorizationError)):
                    return GetSystemMetricsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to get system metrics: {e}",
                    error_code="METRICS_QUERY_FAILED",
                ) from e
