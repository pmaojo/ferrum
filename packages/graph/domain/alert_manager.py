from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from application.ports import MessageBusPort, TracingPort
from domain.entities import ValidationReport

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage alerting logic with cooldown tracking."""

    def __init__(
        self,
        *,
        tracer: TracingPort,
        message_bus: Optional[MessageBusPort] = None,
        alert_thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        self.tracer = tracer
        self.message_bus = message_bus
        self.alert_thresholds = alert_thresholds or {
            "error_rate": 0.05,
            "latency_p95": 2000,
            "memory_usage": 0.85,
            "validation_failure_rate": 0.10,
        }
        self._cooldowns: Dict[str, datetime] = {}

    def check_performance_alerts(
        self,
        *,
        operation_name: str,
        duration_ms: float,
        success: bool,
        tenant_id: str,
    ) -> None:
        """Check metrics against thresholds and trigger alerts."""
        try:
            if duration_ms > self.alert_thresholds["latency_p95"]:
                self.trigger_alert(
                    alert_type="high_latency",
                    message=f"High latency for {operation_name}: {duration_ms}ms",
                    tenant_id=tenant_id,
                    severity="warning",
                    context={
                        "operation": operation_name,
                        "duration_ms": duration_ms,
                        "threshold": self.alert_thresholds["latency_p95"],
                    },
                )
            if not success:
                self.trigger_alert(
                    alert_type="operation_failure",
                    message=f"Operation failure: {operation_name}",
                    tenant_id=tenant_id,
                    severity="error",
                    context={"operation": operation_name, "duration_ms": duration_ms},
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to evaluate performance alerts: %s", exc, exc_info=True)

    def trigger_validation_failure_alert(
        self, *, validation_report: ValidationReport, tenant_id: str
    ) -> None:
        """Emit alert for validation failures."""
        try:
            self.trigger_alert(
                alert_type="validation_failure",
                message=(
                    f"Ontology validation failed with {len(validation_report.unsat_classes)} "
                    "unsatisfiable classes"
                ),
                tenant_id=tenant_id,
                severity="warning",
                context={
                    "ontology_version_id": validation_report.ontology_version_id,
                    "unsat_classes": validation_report.unsat_classes,
                    "repair_suggestions_count": len(validation_report.repair_suggestions),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to trigger validation alert: %s", exc, exc_info=True)

    def trigger_alert(
        self,
        *,
        alert_type: str,
        message: str,
        tenant_id: str,
        severity: str,
        context: Dict[str, Any],
    ) -> None:
        """Send alert if cooldown period has elapsed."""
        try:
            cooldown_key = f"{tenant_id}:{alert_type}"
            now = datetime.now()
            last_alert = self._cooldowns.get(cooldown_key)
            if last_alert and (now - last_alert).total_seconds() < 300:
                return

            self.tracer.record_metric(
                name=f"alerts.{alert_type}",
                value=1.0,
                tenant_id=tenant_id,
                severity=severity,
            )

            if self.message_bus:
                alert_message = {
                    "type": "alert",
                    "alert_type": alert_type,
                    "message": message,
                    "severity": severity,
                    "tenant_id": tenant_id,
                    "timestamp": now.isoformat(),
                    "context": context,
                }
                self.message_bus.publish(
                    topic="system.alerts", message=alert_message, tenant_id=tenant_id
                )

            self._cooldowns[cooldown_key] = now
            logger.warning(
                "Alert triggered: %s - %s (tenant: %s)", alert_type, message, tenant_id
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to trigger alert: %s", exc, exc_info=True)
