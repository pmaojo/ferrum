"""Prometheus metrics repository implementing MetricsRepositoryPort."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx

from application.ports import MetricsRepositoryPort

logger = logging.getLogger(__name__)


class PrometheusMetricsRepository(MetricsRepositoryPort):
    """Retrieve metrics from Prometheus using its HTTP API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=5)

    def query_range(
        self,
        *,
        metric: str,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Tuple[datetime, float]]:
        labels = labels or {}
        labels["tenant_id"] = tenant_id
        label_str = ",".join(f"{k}='{v}'" for k, v in labels.items())
        query = f"{metric}{{{label_str}}}"
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": "60",
        }
        try:
            response = self._client.get(
                f"{self.base_url}/api/v1/query_range", params=params
            )
            response.raise_for_status()
            data = response.json().get("data", {}).get("result", [])
            points: List[Tuple[datetime, float]] = []
            for series in data:
                for ts, value in series.get("values", []):
                    points.append((datetime.fromtimestamp(float(ts)), float(value)))
            return points
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Prometheus query failed: %s", exc)
            return []
