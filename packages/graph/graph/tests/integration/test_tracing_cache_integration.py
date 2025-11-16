import pytest

pytest.importorskip("redis")
pytest.importorskip("opentelemetry")
pytest.importorskip("fakeredis")

import fakeredis

from adapters.opentelemetry_tracing_adapter import NoOpSpan, OpenTelemetryTracingAdapter
from adapters.redis_cache_adapter import RedisCacheAdapter
from ui_adapters.rest_api.dependencies import get_context_manager


def test_tracing_span_and_cache_hit(monkeypatch):
    """Ensure tracing uses OpenTelemetry and cache hits Redis."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.Redis.from_url", lambda url, decode_responses=True: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")

    class DummyGraphAdapter:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "ui_adapters.rest_api.dependencies.FalkorGraphAdapter", DummyGraphAdapter
    )
    get_context_manager.cache_clear()

    cm = get_context_manager()
    assert isinstance(cm.tracer, OpenTelemetryTracingAdapter)
    assert isinstance(cm.cache_port, RedisCacheAdapter)

    span = cm.tracer.start_span(name="test-span", tenant_id="t1")
    try:
        assert not isinstance(span, NoOpSpan)
    finally:
        span.end()

    cm.cache_port.set(key="foo", value="bar", tenant_id="t1")
    assert cm.cache_port.exists(key="foo", tenant_id="t1")
    assert cm.cache_port.get(key="foo", tenant_id="t1") == "bar"
