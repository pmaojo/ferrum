from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from application.ports import MetricsRepositoryPort

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Generate aggregated performance reports."""

    def __init__(self, *, metrics_repository: MetricsRepositoryPort) -> None:
        self.metrics_repository = metrics_repository

    def generate_report(self, *, tenant_id: str, time_range_hours: int = 24) -> Dict[str, Any]:
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            operations = ["graphrag_query", "ontology_validation", "graph_indexing"]
            op_reports: Dict[str, Dict[str, Any]] = {}
            total_ops = 0
            total_success = 0
            all_latencies: List[float] = []

            for op in operations:
                durations = self.metrics_repository.query_range(
                    metric=f"{op}.duration_ms",
                    tenant_id=tenant_id,
                    start_time=start_time,
                    end_time=end_time,
                )
                successes = self.metrics_repository.query_range(
                    metric=f"{op}.success",
                    tenant_id=tenant_id,
                    start_time=start_time,
                    end_time=end_time,
                )
                latency_values = [v for _, v in durations]
                count = len(successes)
                success_sum = sum(v for _, v in successes)
                total_ops += count
                total_success += success_sum
                all_latencies.extend(latency_values)

                op_report = {
                    "count": count,
                    "success_rate": success_sum / count if count else 0.0,
                    "avg_latency_ms": self._average(latency_values),
                    "p95_latency_ms": self._percentile(latency_values, 95),
                }
                if op == "ontology_validation":
                    failures = count - success_sum
                    op_report["validation_failure_rate"] = failures / count if count else 0.0
                op_reports[op] = op_report

            summary = {
                "total_operations": total_ops,
                "success_rate": total_success / total_ops if total_ops else 0.0,
                "avg_latency_ms": self._average(all_latencies),
                "p95_latency_ms": self._percentile(all_latencies, 95),
                "error_count": total_ops - total_success,
            }

            report = {
                "tenant_id": tenant_id,
                "time_range_hours": time_range_hours,
                "generated_at": datetime.now().isoformat(),
                "summary": summary,
                "operations": op_reports,
                "alerts": {"triggered_count": 0, "active_alerts": []},
            }
            report["recommendations"] = self._generate_recommendations(report)
            logger.info("Generated performance report for tenant %s", tenant_id)
            return report
        except Exception as exc:
            logger.error("Failed to generate performance report: %s", exc, exc_info=True)
            return {
                "error": f"Failed to generate report: {str(exc)}",
                "tenant_id": tenant_id,
                "generated_at": datetime.now().isoformat(),
            }

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        recommendations: List[str] = []
        try:
            if report["summary"]["success_rate"] < 0.95:
                recommendations.append(
                    "Success rate is below 95%. Consider reviewing error logs and implementing retry mechanisms."
                )
            if report["summary"]["p95_latency_ms"] > 2000:
                recommendations.append(
                    "P95 latency is above 2 seconds. Consider optimizing query performance or scaling resources."
                )
            validation_ops = report["operations"].get("ontology_validation", {})
            if validation_ops.get("validation_failure_rate", 0) > 0.1:
                recommendations.append(
                    "Validation failure rate is above 10%. Review ontology constraints and data quality."
                )
            recommendations.extend(
                [
                    "Monitor resource usage and scale horizontally if needed",
                    "Implement caching for frequently accessed knowledge graphs",
                    "Consider using incremental validation for large ontologies",
                ]
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to generate recommendations: %s", exc, exc_info=True)
            recommendations.append(
                "Unable to generate specific recommendations due to analysis error"
            )
        return recommendations

    @staticmethod
    def _average(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        values = sorted(values)
        k = (len(values) - 1) * (percentile / 100)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        if f == c:
            return values[f]
        d0 = values[f] * (c - k)
        d1 = values[c] * (k - f)
        return d0 + d1
