"""Tests for ObservabilityService performance report generation."""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from unittest.mock import Mock

import pytest

from domain.observability_service import ObservabilityService
from application.ports import MetricsRepositoryPort, TracingPort


class InMemoryMetricsRepository(MetricsRepositoryPort):
    def __init__(self, records: List[Dict[str, any]]) -> None:
        self.records = records

    def query_range(
        self,
        *,
        metric: str,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Tuple[datetime, float]]:
        return [
            (r["timestamp"], r["value"])
            for r in self.records
            if r["metric"] == metric
            and r["tenant_id"] == tenant_id
            and start_time <= r["timestamp"] <= end_time
        ]


def test_generate_performance_report_basic():
    now = datetime.utcnow()
    repo = InMemoryMetricsRepository(
        [
            {
                "metric": "graphrag_query.duration_ms",
                "tenant_id": "t",
                "timestamp": now,
                "value": 100,
            },
            {
                "metric": "graphrag_query.success",
                "tenant_id": "t",
                "timestamp": now,
                "value": 1,
            },
            {
                "metric": "ontology_validation.duration_ms",
                "tenant_id": "t",
                "timestamp": now,
                "value": 200,
            },
            {
                "metric": "ontology_validation.success",
                "tenant_id": "t",
                "timestamp": now,
                "value": 0,
            },
        ]
    )

    tracer = Mock(spec=TracingPort)

    service = ObservabilityService(tracer=tracer, metrics_repository=repo)

    report = service.generate_performance_report(tenant_id="t", time_range_hours=1)

    assert report["summary"]["total_operations"] == 2
    assert report["operations"]["graphrag_query"]["count"] == 1
    assert report["operations"]["graphrag_query"]["success_rate"] == 1.0
    assert report["operations"]["ontology_validation"]["success_rate"] == 0.0
    assert report["operations"]["ontology_validation"]["validation_failure_rate"] == 1.0
