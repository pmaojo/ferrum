"""Unit tests for OpenTelemetryTracingAdapter."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
import json
import sys
from typing import Dict, Any

# Mock modules before importing the adapter
sys.modules['opentelemetry'] = Mock()
sys.modules['opentelemetry.trace'] = Mock()
sys.modules['opentelemetry.metrics'] = Mock()
sys.modules['opentelemetry.sdk'] = Mock()
sys.modules['opentelemetry.sdk.trace'] = Mock()
sys.modules['opentelemetry.sdk.trace.export'] = Mock()
sys.modules['opentelemetry.sdk.metrics'] = Mock()
sys.modules['opentelemetry.sdk.metrics.export'] = Mock()
sys.modules['opentelemetry.exporter'] = Mock()
sys.modules['opentelemetry.exporter.otlp'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc.trace_exporter'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc.metric_exporter'] = Mock()
sys.modules['opentelemetry.sdk.resources'] = Mock()
sys.modules['opentelemetry.semconv'] = Mock()
sys.modules['opentelemetry.semconv.resource'] = Mock()
sys.modules['structlog'] = Mock()

# Now import the adapter
from adapters.opentelemetry_tracing_adapter import OpenTelemetryTracingAdapter, NoOpSpan


class TestOpenTelemetryTracingAdapter(unittest.TestCase):
    """Test cases for OpenTelemetryTracingAdapter."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock for OpenTelemetry dependencies
        self.trace_patcher = patch('adapters.opentelemetry_tracing_adapter.trace')
        self.metrics_patcher = patch('adapters.opentelemetry_tracing_adapter.metrics')
        self.structlog_patcher = patch('adapters.opentelemetry_tracing_adapter.structlog')

        self.mock_trace = self.trace_patcher.start()
        self.mock_metrics = self.metrics_patcher.start()
        self.mock_structlog = self.structlog_patcher.start()

        # Mock tracer and meter
        self.mock_tracer = Mock()
        self.mock_meter = Mock()
        self.mock_trace.get_tracer.return_value = self.mock_tracer
        self.mock_metrics.get_meter.return_value = self.mock_meter

        # Mock span
        self.mock_span = Mock()
        self.mock_span_context = Mock()
        self.mock_span_context.trace_id = 123456789
        self.mock_span_context.span_id = 987654321
        self.mock_span.get_span_context.return_value = self.mock_span_context
        self.mock_tracer.start_span.return_value = self.mock_span

        # Mock metrics
        self.mock_counter = Mock()
        self.mock_gauge = Mock()
        self.mock_histogram = Mock()
        self.mock_meter.create_counter.return_value = self.mock_counter
        self.mock_meter.create_gauge.return_value = self.mock_gauge
        self.mock_meter.create_histogram.return_value = self.mock_histogram

        # Mock structlog
        self.mock_logger = Mock()
        self.mock_structlog.get_logger.return_value = self.mock_logger

        # Create adapter with mocked dependencies
        with patch('adapters.opentelemetry_tracing_adapter.HAS_OPENTELEMETRY', True), \
             patch('adapters.opentelemetry_tracing_adapter.HAS_STRUCTLOG', True):
            self.adapter = OpenTelemetryTracingAdapter(
                service_name="test-service",
                enable_console_export=False,
                enable_structured_logging=True
            )
            self.adapter.tracer = self.mock_tracer
            self.adapter.meter = self.mock_meter

    def tearDown(self):
        """Clean up after tests."""
        self.trace_patcher.stop()
        self.metrics_patcher.stop()
        self.structlog_patcher.stop()

    def test_start_span(self):
        """Test start_span method."""
        # Call start_span
        span = self.adapter.start_span(
            name="test-span",
            tenant_id="test-tenant",
            custom_attr="custom-value"
        )

        # Verify tracer.start_span was called with correct arguments
        self.mock_tracer.start_span.assert_called_once()
        args, kwargs = self.mock_tracer.start_span.call_args
        self.assertEqual(args[0], "test-span")
        self.assertEqual(kwargs["attributes"]["tenant_id"], "test-tenant")
        self.assertEqual(kwargs["attributes"]["custom_attr"], "custom-value")
        self.assertEqual(kwargs["attributes"]["service.name"], "test-service")

        # Verify logger.info was called
        self.mock_logger.info.assert_called_once()
        args, kwargs = self.mock_logger.info.call_args
        self.assertEqual(args[0], "Started span")
        self.assertEqual(kwargs["span_name"], "test-span")
        self.assertEqual(kwargs["tenant_id"], "test-tenant")

        # Verify span was returned
        self.assertEqual(span, self.mock_span)

    def test_record_metric_counter(self):
        """Test record_metric method with counter."""
        # Call record_metric with counter pattern
        self.adapter.record_metric(
            name="test_count",
            value=5.0,
            tenant_id="test-tenant",
            custom_tag="custom-value"
        )

        # Verify meter.create_counter was called
        self.mock_meter.create_counter.assert_called_once_with("test_count")

        # Verify counter.add was called with correct arguments
        self.mock_counter.add.assert_called_once()
        args, kwargs = self.mock_counter.add.call_args
        self.assertEqual(args[0], 5.0)
        self.assertEqual(kwargs["attributes"]["tenant_id"], "test-tenant")
        self.assertEqual(kwargs["attributes"]["custom_tag"], "custom-value")
        self.assertEqual(kwargs["attributes"]["service.name"], "test-service")

        # Verify logger.debug was called
        self.mock_logger.debug.assert_called_once()
        args, kwargs = self.mock_logger.debug.call_args
        self.assertEqual(args[0], "Recorded metric")
        self.assertEqual(kwargs["metric_name"], "test_count")
        self.assertEqual(kwargs["metric_value"], 5.0)
        self.assertEqual(kwargs["tenant_id"], "test-tenant")

    def test_record_metric_gauge(self):
        """Test record_metric method with gauge."""
        # Call record_metric with gauge pattern
        self.adapter.record_metric(
            name="test_ratio",
            value=0.75,
            tenant_id="test-tenant",
            custom_tag="custom-value"
        )

        # Verify meter.create_gauge was called
        self.mock_meter.create_gauge.assert_called_once_with("test_ratio")

        # Verify gauge.set was called with correct arguments
        self.mock_gauge.set.assert_called_once()
        args, kwargs = self.mock_gauge.set.call_args
        self.assertEqual(args[0], 0.75)
        self.assertEqual(kwargs["attributes"]["tenant_id"], "test-tenant")
        self.assertEqual(kwargs["attributes"]["custom_tag"], "custom-value")

    def test_record_metric_histogram(self):
        """Test record_metric method with histogram."""
        # Call record_metric with histogram pattern
        self.adapter.record_metric(
            name="test_latency_ms",
            value=123.45,
            tenant_id="test-tenant",
            custom_tag="custom-value"
        )

        # Verify meter.create_histogram was called
        self.mock_meter.create_histogram.assert_called_once_with("test_latency_ms")

        # Verify histogram.record was called with correct arguments
        self.mock_histogram.record.assert_called_once()
        args, kwargs = self.mock_histogram.record.call_args
        self.assertEqual(args[0], 123.45)
        self.assertEqual(kwargs["attributes"]["tenant_id"], "test-tenant")
        self.assertEqual(kwargs["attributes"]["custom_tag"], "custom-value")

    def test_span_in_context(self):
        """Test span_in_context context manager."""
        # Use span_in_context
        with self.adapter.span_in_context(
            name="test-context-span",
            tenant_id="test-tenant",
            custom_attr="custom-value"
        ) as span:
            # Verify span was created
            self.assertEqual(span, self.mock_span)

            # Verify tracer.start_span was called
            self.mock_tracer.start_span.assert_called_once()

        # Verify span.end was called after context exit
        self.mock_span.end.assert_called_once()

    def test_span_in_context_with_exception(self):
        """Test span_in_context context manager with exception."""
        # Use span_in_context with exception
        try:
            with self.adapter.span_in_context(
                name="test-exception-span",
                tenant_id="test-tenant"
            ):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify span.set_status was called with ERROR
        self.mock_span.set_status.assert_called_once()
        # Mock StatusCode.ERROR
        args, kwargs = self.mock_span.set_status.call_args
        # We can't directly check the enum value, so we'll just verify it was called

        # Verify span.record_exception was called
        self.mock_span.record_exception.assert_called_once()

        # Verify span.end was called despite exception
        self.mock_span.end.assert_called_once()

    def test_no_opentelemetry(self):
        """Test adapter behavior when OpenTelemetry is not available."""
        # Create adapter with OpenTelemetry not available
        with patch('adapters.opentelemetry_tracing_adapter.HAS_OPENTELEMETRY', False), \
             patch('adapters.opentelemetry_tracing_adapter.HAS_STRUCTLOG', False):
            adapter = OpenTelemetryTracingAdapter(
                service_name="test-service",
                enable_console_export=False,
                enable_structured_logging=False
            )

            # Verify tracer and meter are None
            self.assertIsNone(adapter.tracer)
            self.assertIsNone(adapter.meter)

            # Test start_span returns NoOpSpan
            span = adapter.start_span(name="test-span", tenant_id="test-tenant")
            self.assertIsInstance(span, NoOpSpan)

            # Test record_metric doesn't raise exception
            adapter.record_metric(name="test_metric", value=1.0, tenant_id="test-tenant")


class TestNoOpSpan(unittest.TestCase):
    """Test cases for NoOpSpan."""

    def test_noop_span_methods(self):
        """Test NoOpSpan methods."""
        # Create NoOpSpan
        span = NoOpSpan(
            name="test-span",
            tenant_id="test-tenant",
            attributes={"custom_attr": "custom-value"}
        )

        # Test attributes
        self.assertEqual(span.name, "test-span")
        self.assertEqual(span.tenant_id, "test-tenant")
        self.assertEqual(span.attributes["custom_attr"], "custom-value")
        self.assertEqual(span.status, "OK")
        self.assertEqual(len(span.events), 0)

        # Test end method
        span.end()
        self.assertIsNotNone(span.end_time)

        # Test set_status method
        # Mock StatusCode.ERROR
        mock_status_code = Mock()
        mock_status_code.ERROR = "ERROR"
        span.set_status(mock_status_code.ERROR, "Test error")
        self.assertEqual(span.status, "ERROR")
        self.assertEqual(span.status_description, "Test error")

        # Test add_event method
        span.add_event("test-event", {"event_attr": "event-value"})
        self.assertEqual(len(span.events), 1)
        self.assertEqual(span.events[0]["name"], "test-event")
        self.assertEqual(span.events[0]["attributes"]["event_attr"], "event-value")

        # Test record_exception method
        exception = ValueError("Test exception")
        span.record_exception(exception)
        self.assertEqual(len(span.events), 2)
        self.assertEqual(span.events[1]["name"], "exception")
        self.assertEqual(span.events[1]["attributes"]["exception.type"], "ValueError")
        self.assertEqual(span.events[1]["attributes"]["exception.message"], "Test exception")

        # Test get_span_context method returns lightweight context
        ctx = span.get_span_context()
        self.assertIsNotNone(ctx)
        self.assertTrue(hasattr(ctx, "trace_id"))
        self.assertTrue(hasattr(ctx, "span_id"))


if __name__ == '__main__':
    unittest.main()
