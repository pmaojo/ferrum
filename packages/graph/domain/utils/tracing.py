from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional

from application.ports import TracingPort


@contextmanager
def tracing_span(
    tracer: Optional[TracingPort],
    *,
    name: str,
    tenant_id: str,
    **attributes: Any,
) -> Generator[Any, None, None]:
    """Yield a tracing span and ensure it closes correctly."""
    if tracer is None:
        yield None
        return

    span_in_context = getattr(tracer, "span_in_context", None)
    if callable(span_in_context):
        try:
            with span_in_context(name=name, tenant_id=tenant_id, **attributes) as span:
                yield span
            return
        except TypeError:
            # If the provided attribute isn't a valid context manager fall back
            # to manual span management.
            pass

    span = tracer.start_span(name=name, tenant_id=tenant_id, **attributes)
    try:
        yield span
    finally:
        if hasattr(span, "end") and callable(span.end):
            span.end()

