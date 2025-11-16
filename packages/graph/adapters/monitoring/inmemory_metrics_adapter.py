"""In-memory implementation of MetricsPort for testing and development."""

from collections import defaultdict
from typing import Dict, Any, Optional, List

from application.ports.metrics_port import MetricsPort


class InMemoryMetricsAdapter(MetricsPort):
    """Simple in-memory metrics recorder."""

    def __init__(self) -> None:
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default",
    ) -> None:
        self._metrics[tenant_id].append(
            {"type": "counter", "name": name, "value": value, "labels": labels or {}}
        )

    def record_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default",
    ) -> None:
        self._metrics[tenant_id].append(
            {"type": "gauge", "name": name, "value": value, "labels": labels or {}}
        )

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default",
    ) -> None:
        self._metrics[tenant_id].append(
            {"type": "histogram", "name": name, "value": value, "labels": labels or {}}
        )

    def record_timing(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default",
    ) -> None:
        self._metrics[tenant_id].append(
            {
                "type": "timer",
                "name": name,
                "value": duration_ms,
                "labels": labels or {},
            }
        )

    def get_metrics(
        self, name_pattern: Optional[str] = None, tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        metrics = self._metrics.get(tenant_id, [])
        if name_pattern:
            return [m for m in metrics if name_pattern in m["name"]]
        return list(metrics)

    def get_health_metrics(self, tenant_id: str = "default") -> Dict[str, Any]:
        return {"total_metrics": len(self._metrics.get(tenant_id, []))}
