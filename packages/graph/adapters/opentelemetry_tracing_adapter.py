"""OpenTelemetry tracing adapter implementing TracingPort.

This adapter integrates OpenTelemetry for span creation and metric recording with tenant context,
structured logging with correlated traces, and performance metrics tracking with OTLP export
to Grafana dashboards.
"""

import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

# Import OpenTelemetry modules
try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.trace import Span, StatusCode

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    Span = Any  # Type alias for Span when OpenTelemetry is not available

# Import structured logging modules
try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

from application.ports import TracingPort


class OpenTelemetryTracingAdapter(TracingPort):
    """OpenTelemetry tracing adapter implementing TracingPort.

    This adapter provides distributed tracing and metrics collection with tenant context
    for comprehensive system observability. It integrates OpenTelemetry for span creation
    and metric recording, structured logging with correlated traces, and performance
    metrics tracking with OTLP export to Grafana dashboards.
    """

    def __init__(
        self,
        service_name: str = "graphrag-ontology-app",
        otlp_endpoint: Optional[str] = None,
        enable_console_export: bool = True,
        enable_structured_logging: bool = True,
        log_level: int = logging.INFO,
        environment: str = "development",
    ):
        """Initialize OpenTelemetry tracing adapter.

        Args:
            service_name: Name of the service for telemetry
            otlp_endpoint: Optional OTLP endpoint for telemetry export (e.g., "http://localhost:4317")
            enable_console_export: Whether to enable console export for development
            enable_structured_logging: Whether to enable structured logging integration
            log_level: Logging level (default: INFO)
            environment: Deployment environment (development, staging, production)

        Raises:
            ImportError: When required dependencies are not installed
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export
        self.enable_structured_logging = enable_structured_logging
        self.environment = environment

        # Initialize OpenTelemetry if available
        if HAS_OPENTELEMETRY:
            self._setup_opentelemetry()
        else:
            self.tracer = None
            self.meter = None
            logger = self._get_logger()
            logger.warning(
                "OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )

        # Initialize structured logging if available and enabled
        if enable_structured_logging and HAS_STRUCTLOG:
            self._setup_structured_logging(log_level)
        else:
            # Configure basic logging as fallback
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                stream=sys.stdout,
            )

            if enable_structured_logging and not HAS_STRUCTLOG:
                logger = self._get_logger()
                logger.warning(
                    "structlog not available. Install with: pip install structlog"
                )

    def start_span(self, *, name: str, tenant_id: str, **kwargs: Any) -> Span:
        """Start OpenTelemetry span with tenant context.

        Creates distributed tracing spans for operation tracking with
        tenant context for multi-tenant observability.

        Args:
            name: Span name for operation identification
            tenant_id: Tenant identifier for context isolation
            **kwargs: Additional span attributes and metadata

        Returns:
            OpenTelemetry Span object for context management

        Raises:
            TracingError: When span creation fails
        """
        if not HAS_OPENTELEMETRY or not self.tracer:
            # Return a no-op span if OpenTelemetry is not available
            return NoOpSpan(name=name, tenant_id=tenant_id, attributes=kwargs)

        try:
            # Add tenant_id to attributes
            attributes = dict(kwargs)
            attributes["tenant_id"] = tenant_id
            attributes["service.name"] = self.service_name

            # Start a new span
            span = self.tracer.start_span(name, attributes=attributes)

            # Log span creation with structured logging if available
            logger = self._get_logger()
            logger.info(
                "Started span",
                span_name=name,
                tenant_id=tenant_id,
                trace_id=self._get_hex_trace_id(span),
                span_id=self._get_hex_span_id(span),
            )

            return span

        except Exception as e:
            logger = self._get_logger()
            logger.error(
                "Failed to start span",
                span_name=name,
                tenant_id=tenant_id,
                error=str(e),
                exc_info=True,
            )
            # Return a no-op span as fallback
            return NoOpSpan(name=name, tenant_id=tenant_id, attributes=kwargs)

    def record_metric(
        self, *, name: str, value: float, tenant_id: str, **tags: Any
    ) -> None:
        """Record performance metrics with tenant isolation.

        Records system metrics (latency, throughput, error rates) with
        tenant context for comprehensive performance monitoring.

        Args:
            name: Metric name (e.g., 'graphrag_latency_ms')
            value: Metric value to record
            tenant_id: Tenant identifier for metric isolation
            **tags: Additional metric tags and dimensions

        Raises:
            MetricsError: When metric recording fails
        """
        if not HAS_OPENTELEMETRY or not self.meter:
            # Log metric to console if OpenTelemetry is not available
            logger = self._get_logger()
            if HAS_STRUCTLOG:
                logger.info(
                    "Metric recorded (no OpenTelemetry)",
                    metric_name=name,
                    metric_value=value,
                    tenant_id=tenant_id,
                    **tags,
                )
            else:
                # Use standard logging
                logger.info(
                    f"Metric recorded (no OpenTelemetry): {name}={value}, tenant_id={tenant_id}, tags={tags}"
                )
            return

        try:
            # Add tenant_id to attributes
            attributes = dict(tags)
            attributes["tenant_id"] = tenant_id
            attributes["service.name"] = self.service_name
            attributes["environment"] = self.environment

            # Get or create counter/gauge based on metric name pattern
            if name.endswith("_count") or name.endswith("_total"):
                # Use counter for count/total metrics
                counter = self.meter.create_counter(name)
                counter.add(value, attributes=attributes)
            elif name.endswith("_ratio") or name.endswith("_percentage"):
                # Use gauge for ratio/percentage metrics
                gauge = self.meter.create_gauge(name)
                gauge.set(value, attributes=attributes)
            else:
                # Use histogram for latency/duration metrics
                histogram = self.meter.create_histogram(name)
                histogram.record(value, attributes=attributes)

            # Log metric recording with structured logging
            logger = self._get_logger()
            logger.debug(
                "Recorded metric",
                metric_name=name,
                metric_value=value,
                tenant_id=tenant_id,
                **tags,
            )

        except Exception as e:
            logger = self._get_logger()
            logger.error(
                "Failed to record metric",
                metric_name=name,
                metric_value=value,
                tenant_id=tenant_id,
                error=str(e),
                exc_info=True,
            )

    @contextmanager
    def span_in_context(self, name: str, tenant_id: str, **kwargs: Any):
        """Context manager for span creation and automatic closing.

        Creates a span and ensures it's properly closed when the context exits.

        Args:
            name: Span name for operation identification
            tenant_id: Tenant identifier for context isolation
            **kwargs: Additional span attributes and metadata

        Yields:
            OpenTelemetry Span object for context management
        """
        span = self.start_span(name=name, tenant_id=tenant_id, **kwargs)
        try:
            yield span
        except Exception as e:
            if hasattr(span, "set_status") and callable(span.set_status):
                span.set_status(StatusCode.ERROR)
                span.record_exception(e)
            raise
        finally:
            if hasattr(span, "end") and callable(span.end):
                span.end()

    def _setup_opentelemetry(self) -> None:
        """Set up OpenTelemetry tracing and metrics.

        Configures TracerProvider, MeterProvider, and exporters for OpenTelemetry.
        """
        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.environment,
            }
        )

        # Set up trace provider
        trace_provider = TracerProvider(resource=resource)

        # Add exporters
        if self.otlp_endpoint:
            # Add OTLP exporter for production use
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        if self.enable_console_export:
            # Add console exporter for development
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Set global trace provider
        trace.set_tracer_provider(trace_provider)

        # Create tracer
        self.tracer = trace.get_tracer(self.service_name)

        # Set up metrics provider
        metric_readers = []

        if self.otlp_endpoint:
            # Add OTLP metric exporter
            otlp_metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
            metric_readers.append(PeriodicExportingMetricReader(otlp_metric_exporter))

        if self.enable_console_export:
            # Add console metric exporter for development
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

            metric_readers.append(
                PeriodicExportingMetricReader(ConsoleMetricExporter())
            )

        # Create meter provider with readers
        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)

        # Create meter
        self.meter = metrics.get_meter(self.service_name)

    def _setup_structured_logging(self, log_level: int) -> None:
        """Set up structured logging with OpenTelemetry correlation.

        Configures structlog with console and JSON processors, and adds
        OpenTelemetry trace correlation.

        Args:
            log_level: Logging level to configure
        """
        # Configure standard logging
        logging.basicConfig(level=log_level)

        # Configure structlog
        structlog.configure(
            processors=[
                # Add timestamps
                structlog.processors.TimeStamper(fmt="iso"),
                # Add log level
                structlog.processors.add_log_level,
                # Add trace context from OpenTelemetry
                self._add_trace_context,
                # Format for console output in development
                (
                    structlog.dev.ConsoleRenderer()
                    if self.environment == "development"
                    else structlog.processors.JSONRenderer()
                ),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _add_trace_context(self, logger, method_name, event_dict):
        """Add OpenTelemetry trace context to structured logs.

        Processor for structlog that adds trace_id and span_id from the current
        OpenTelemetry context to log events.

        Args:
            logger: Logger instance
            method_name: Logging method name
            event_dict: Log event dictionary

        Returns:
            Enhanced log event dictionary with trace context
        """
        if not HAS_OPENTELEMETRY:
            return event_dict

        try:
            # Get current span from context
            current_span = trace.get_current_span()
            if current_span:
                # Add trace_id and span_id to log event
                span_context = current_span.get_span_context()
                if span_context:
                    event_dict["trace_id"] = format(span_context.trace_id, "032x")
                    event_dict["span_id"] = format(span_context.span_id, "016x")
        except Exception:
            # Ignore errors in trace context extraction
            pass

        return event_dict

    def _get_logger(self) -> Any:
        """Get appropriate logger based on configuration.

        Returns:
            Logger instance (structlog or standard logging)
        """
        if self.enable_structured_logging and HAS_STRUCTLOG:
            return structlog.get_logger()
        else:
            return logging.getLogger("opentelemetry_tracing_adapter")

    def _get_hex_trace_id(self, span: Span) -> str:
        """Get hexadecimal trace ID from span.

        Args:
            span: OpenTelemetry span

        Returns:
            Hexadecimal trace ID or empty string if not available
        """
        try:
            if hasattr(span, "get_span_context"):
                span_context = span.get_span_context()
                if span_context and hasattr(span_context, "trace_id"):
                    return format(span_context.trace_id, "032x")
        except Exception:
            pass
        return ""

    def _get_hex_span_id(self, span: Span) -> str:
        """Get hexadecimal span ID from span.

        Args:
            span: OpenTelemetry span

        Returns:
            Hexadecimal span ID or empty string if not available
        """
        try:
            if hasattr(span, "get_span_context"):
                span_context = span.get_span_context()
                if span_context and hasattr(span_context, "span_id"):
                    return format(span_context.span_id, "016x")
        except Exception:
            pass
        return ""


class _SimpleSpanContext:
    """Lightweight span context used for no-op spans."""

    def __init__(self) -> None:
        self.trace_id = uuid.uuid4().int
        # Use lower 64 bits for span id to mimic OpenTelemetry behaviour
        self.span_id = uuid.uuid4().int & 0xFFFFFFFFFFFFFFFF


class NoOpSpan:
    """No-op implementation of Span for use when OpenTelemetry is not available."""

    def __init__(self, name: str, tenant_id: str, attributes: Dict[str, Any]):
        """Initialize no-op span.

        Args:
            name: Span name
            tenant_id: Tenant identifier
            attributes: Span attributes
        """
        self.name = name
        self.tenant_id = tenant_id
        self.attributes = attributes
        self.start_time = time.time()
        self.end_time = None
        self.status = "OK"
        self.events = []
        self._span_context = _SimpleSpanContext()

    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if self.end_time is None:
            # If span hasn't ended yet, calculate duration from start time
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and end the span."""
        self.end()
        return False

    def end(self) -> None:
        """End the span."""
        self.end_time = time.time()

    def set_status(self, status: Any, description: Optional[str] = None) -> None:
        """Set span status.

        Args:
            status: Status code
            description: Optional status description
        """
        # For NoOpSpan, we'll just check if the status is "ERROR" string
        # since we might not have access to StatusCode.ERROR enum
        self.status = "ERROR" if status == "ERROR" else "OK"
        if description:
            self.status_description = description

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        self.events.append(
            {"name": name, "timestamp": time.time(), "attributes": attributes or {}}
        )

    def record_exception(self, exception: Exception) -> None:
        """Record exception in span.

        Args:
            exception: Exception to record
        """
        self.add_event(
            name="exception",
            attributes={
                "exception.type": exception.__class__.__name__,
                "exception.message": str(exception),
            },
        )

    def get_span_context(self) -> Any:
        """Return lightweight span context."""
        return self._span_context
