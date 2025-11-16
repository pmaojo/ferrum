from __future__ import annotations

import logging
from typing import Any

from application.ports import TracingPort
from domain.entities import ValidationReport

from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


class MetricsRecorder:
    """Record domain metrics and delegate alert checks."""

    def __init__(self, *, tracer: TracingPort, alert_manager: AlertManager) -> None:
        self.tracer = tracer
        self.alert_manager = alert_manager

    def record_operation_metrics(
        self,
        *,
        operation_name: str,
        duration_ms: float,
        success: bool,
        tenant_id: str,
        **additional_tags: Any,
    ) -> None:
        try:
            self.tracer.record_metric(
                name=f"{operation_name}.duration_ms",
                value=duration_ms,
                tenant_id=tenant_id,
                **additional_tags,
            )
            self.tracer.record_metric(
                name=f"{operation_name}.success",
                value=1.0 if success else 0.0,
                tenant_id=tenant_id,
                **additional_tags,
            )
            self.alert_manager.check_performance_alerts(
                operation_name=operation_name,
                duration_ms=duration_ms,
                success=success,
                tenant_id=tenant_id,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to record operation metrics: %s", exc, exc_info=True)

    def record_validation_metrics(
        self,
        *,
        validation_report: ValidationReport,
        triple_count: int,
        duration_ms: float,
        tenant_id: str,
    ) -> None:
        try:
            self.tracer.record_metric(
                name="validation.success",
                value=1.0 if validation_report.is_consistent else 0.0,
                tenant_id=tenant_id,
                ontology_version=validation_report.ontology_version_id,
            )
            self.tracer.record_metric(
                name="validation.duration_ms",
                value=duration_ms,
                tenant_id=tenant_id,
                triple_count=triple_count,
            )
            self.tracer.record_metric(
                name="validation.unsat_classes_count",
                value=len(validation_report.unsat_classes),
                tenant_id=tenant_id,
            )
            self.tracer.record_metric(
                name="validation.repair_suggestions_count",
                value=len(validation_report.repair_suggestions),
                tenant_id=tenant_id,
            )
            if not validation_report.is_consistent:
                self.alert_manager.trigger_validation_failure_alert(
                    validation_report=validation_report, tenant_id=tenant_id
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to record validation metrics: %s", exc, exc_info=True)

    def record_graph_metrics(
        self,
        *,
        kg_id: str,
        node_count: int,
        edge_count: int,
        tenant_id: str,
        operation: str = "update",
    ) -> None:
        try:
            self.tracer.record_metric(
                name="graph.node_count",
                value=node_count,
                tenant_id=tenant_id,
                kg_id=kg_id,
                operation=operation,
            )
            self.tracer.record_metric(
                name="graph.edge_count",
                value=edge_count,
                tenant_id=tenant_id,
                kg_id=kg_id,
                operation=operation,
            )
            if node_count > 1:
                max_edges = node_count * (node_count - 1) / 2
                density = edge_count / max_edges if max_edges > 0 else 0
                self.tracer.record_metric(
                    name="graph.density",
                    value=density,
                    tenant_id=tenant_id,
                    kg_id=kg_id,
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to record graph metrics: %s", exc, exc_info=True)
