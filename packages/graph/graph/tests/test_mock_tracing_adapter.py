import unittest

from ui_adapters.rest_api.server import MockTracingAdapter
from adapters.opentelemetry_tracing_adapter import NoOpSpan


class TestMockTracingAdapter(unittest.TestCase):
    def test_start_span_returns_noop_span(self):
        tracer = MockTracingAdapter()
        span = tracer.start_span(name="test", tenant_id="t1")
        self.assertIsInstance(span, NoOpSpan)
        ctx = span.get_span_context()
        self.assertTrue(hasattr(ctx, "trace_id"))
        self.assertTrue(hasattr(ctx, "span_id"))
        span.end()


if __name__ == "__main__":
    unittest.main()

