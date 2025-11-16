from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, List

from adapters.opentelemetry_tracing_adapter import NoOpSpan
from application.ports import TracingPort


class InMemoryTracingAdapter(TracingPort):
    """Simple tracing adapter storing spans and metrics in memory."""

    def __init__(self) -> None:
        self.spans: List[NoOpSpan] = []
        self.metrics: List[Dict[str, Any]] = []

    def start_span(self, *, name: str, tenant_id: str, **kwargs: Any) -> NoOpSpan:
        span = NoOpSpan(name=name, tenant_id=tenant_id, attributes=kwargs)
        self.spans.append(span)
        return span

    @contextmanager
    def span_in_context(
        self, name: str, tenant_id: str, **kwargs: Any
    ) -> Generator[NoOpSpan, None, None]:
        span = self.start_span(name=name, tenant_id=tenant_id, **kwargs)
        try:
            yield span
        finally:
            span.end()

    def record_metric(
        self, *, name: str, value: float, tenant_id: str, **tags: Any
    ) -> None:
        self.metrics.append(
            {
                "name": name,
                "value": value,
                "tenant_id": tenant_id,
                "tags": dict(tags),
            }
        )
