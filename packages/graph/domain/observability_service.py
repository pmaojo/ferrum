from __future__ import annotations

import logging
from typing import Any, Optional

from application.ports import MessageBusPort, MetricsRepositoryPort, TracingPort
from domain.entities import ValidationReport

from .alert_manager import AlertManager
from .metrics_recorder import MetricsRecorder
from .performance_reporter import PerformanceReporter

logger = logging.getLogger(__name__)


class ObservabilityService:
    """Facade coordinating observability helpers."""

    def __init__(
        self,
        *,
        tracer: TracingPort,
        metrics_repository: MetricsRepositoryPort,
        message_bus: Optional[MessageBusPort] = None,
        alert_manager: Optional[AlertManager] = None,
        metrics_recorder: Optional[MetricsRecorder] = None,
        performance_reporter: Optional[PerformanceReporter] = None,
    ) -> None:
        alert_manager = alert_manager or AlertManager(
            tracer=tracer, message_bus=message_bus
        )
        self.metrics_recorder = metrics_recorder or MetricsRecorder(
            tracer=tracer, alert_manager=alert_manager
        )
        self.performance_reporter = performance_reporter or PerformanceReporter(
            metrics_repository=metrics_repository
        )
        self.tracer = tracer

    def record_operation_metrics(
        self,
        *,
        operation_name: str,
        duration_ms: float,
        success: bool,
        tenant_id: str,
        **additional_tags: Any,
    ) -> None:
        self.metrics_recorder.record_operation_metrics(
            operation_name=operation_name,
            duration_ms=duration_ms,
            success=success,
            tenant_id=tenant_id,
            **additional_tags,
        )

    def record_validation_metrics(
        self,
        *,
        validation_report: ValidationReport,
        triple_count: int,
        duration_ms: float,
        tenant_id: str,
    ) -> None:
        self.metrics_recorder.record_validation_metrics(
            validation_report=validation_report,
            triple_count=triple_count,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
        )

    def record_graph_metrics(
        self,
        *,
        kg_id: str,
        node_count: int,
        edge_count: int,
        tenant_id: str,
        operation: str = "update",
    ) -> None:
        self.metrics_recorder.record_graph_metrics(
            kg_id=kg_id,
            node_count=node_count,
            edge_count=edge_count,
            tenant_id=tenant_id,
            operation=operation,
        )

    def start_operation_trace(self, *, operation_name: str, tenant_id: str, **context: Any) -> Any:
        try:
            span = self.tracer.start_span(
                name=operation_name, tenant_id=tenant_id, **context
            )
            logger.debug("Started trace for %s, tenant=%s", operation_name, tenant_id)
            return span
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to start operation trace: %s", exc, exc_info=True)
            return None

    def generate_performance_report(self, *, tenant_id: str, time_range_hours: int = 24) -> dict:
        return self.performance_reporter.generate_report(
            tenant_id=tenant_id, time_range_hours=time_range_hours
        )
