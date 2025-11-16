"""In-memory implementation of AlertPort for testing and development."""

from collections import defaultdict
from typing import Dict, Any, Optional

from application.ports.alert_port import AlertPort, AlertSeverity


class InMemoryAlertAdapter(AlertPort):
    """Store alerts in memory instead of sending them to external systems."""

    def __init__(self) -> None:
        self.alerts: Dict[str, list] = defaultdict(list)

    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
    ) -> bool:
        self.alerts[tenant_id].append(
            {
                "type": "general",
                "title": title,
                "message": message,
                "severity": severity.value,
                "metadata": metadata or {},
            }
        )
        return True

    def send_health_alert(
        self,
        component: str,
        status: str,
        details: Dict[str, Any],
        tenant_id: str = "default",
    ) -> bool:
        self.alerts[tenant_id].append(
            {
                "type": "health",
                "component": component,
                "status": status,
                "details": details,
            }
        )
        return True

    def send_performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        tenant_id: str = "default",
    ) -> bool:
        self.alerts[tenant_id].append(
            {
                "type": "performance",
                "metric": metric_name,
                "current_value": current_value,
                "threshold": threshold,
            }
        )
        return True
