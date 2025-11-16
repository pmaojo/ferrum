"""Error reporting and alerting adapter with correlation.

This adapter provides comprehensive error reporting with contextual information,
performance degradation alerts, and structured log correlation with OpenTelemetry
trace IDs for effective troubleshooting and monitoring.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from application.ports import TracingPort

# Configure logging
logger = logging.getLogger(__name__)


class AlertThreshold:
    """Alert threshold configuration for performance metrics."""

    def __init__(
        self,
        metric_name: str,
        warning_threshold: float,
        critical_threshold: float,
        lookback_period_seconds: int = 300,
        min_data_points: int = 5,
        cooldown_seconds: int = 60,
    ):
        """Initialize alert threshold configuration.

        Args:
            metric_name: Name of the metric to monitor
            warning_threshold: Warning threshold value
            critical_threshold: Critical threshold value
            lookback_period_seconds: Period to consider for threshold evaluation
            min_data_points: Minimum data points required for evaluation
            cooldown_seconds: Cooldown period between alerts
        """
        self.metric_name = metric_name
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.lookback_period_seconds = lookback_period_seconds
        self.min_data_points = min_data_points
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time = 0


class MetricDataPoint:
    """Data point for metric time series."""

    def __init__(
        self, value: float, timestamp: float, tenant_id: str, tags: Dict[str, Any]
    ):
        """Initialize metric data point.

        Args:
            value: Metric value
            timestamp: Unix timestamp
            tenant_id: Tenant identifier
            tags: Additional metric tags
        """
        self.value = value
        self.timestamp = timestamp
        self.tenant_id = tenant_id
        self.tags = tags


class ErrorReportingAdapter:
    """Error reporting and alerting adapter with correlation.

    This adapter provides comprehensive error reporting with contextual information,
    performance degradation alerts, and structured log correlation with OpenTelemetry
    trace IDs for effective troubleshooting and monitoring.
    """

    def __init__(
        self,
        tracing_adapter: TracingPort,
        alert_thresholds: Optional[List[AlertThreshold]] = None,
        enable_alerts: bool = True,
        alert_handlers: Optional[
            Dict[str, Callable[[str, Dict[str, Any]], None]]
        ] = None,
        metric_history_size: int = 1000,
        baseline_period_seconds: int = 3600,
    ):
        """Initialize error reporting adapter.

        Args:
            tracing_adapter: TracingPort implementation for tracing and metrics
            alert_thresholds: Optional list of alert thresholds
            enable_alerts: Whether to enable alerting
            alert_handlers: Optional dictionary of alert handlers
            metric_history_size: Maximum size of metric history
            baseline_period_seconds: Period for baseline calculation
        """
        self.tracing_adapter = tracing_adapter
        self.alert_thresholds = alert_thresholds or self._default_alert_thresholds()
        self.enable_alerts = enable_alerts
        self.alert_handlers = alert_handlers or {}
        self.metric_history_size = metric_history_size
        self.baseline_period_seconds = baseline_period_seconds

        # Initialize metric history
        self.metric_history: Dict[str, deque[MetricDataPoint]] = {}

        # Initialize baseline values
        self.metric_baselines: Dict[str, Dict[str, float]] = {}

        # Initialize alert state
        self.active_alerts: Dict[str, Dict[str, Any]] = {}

        # Start background alert monitoring if enabled
        if enable_alerts:
            self._start_alert_monitoring()

    def report_error(
        self,
        *,
        error: Exception,
        error_code: str,
        context: Dict[str, Any],
        tenant_id: str,
        doc_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        question_id: Optional[str] = None,
        severity: str = "error",
    ) -> str:
        """Report error with comprehensive context.

        Args:
            error: Exception object
            error_code: Error code for categorization
            context: Error context dictionary
            tenant_id: Tenant identifier
            doc_id: Optional document identifier
            agent_id: Optional agent identifier
            question_id: Optional question identifier
            severity: Error severity (debug, info, warning, error, critical)

        Returns:
            Error report ID for correlation
        """
        # Generate error report ID
        error_id = f"err_{int(time.time())}_{hash(str(error)) % 10000:04d}"

        # Enhance context with additional identifiers
        enhanced_context = dict(context)
        enhanced_context["tenant_id"] = tenant_id
        enhanced_context["error_code"] = error_code
        enhanced_context["error_type"] = error.__class__.__name__
        enhanced_context["error_id"] = error_id

        if doc_id:
            enhanced_context["doc_id"] = doc_id
        if agent_id:
            enhanced_context["agent_id"] = agent_id
        if question_id:
            enhanced_context["question_id"] = question_id

        # Get current trace context if available
        if hasattr(self.tracing_adapter, "_add_trace_context"):
            trace_context = {}
            self.tracing_adapter._add_trace_context(None, None, trace_context)
            if "trace_id" in trace_context:
                enhanced_context["trace_id"] = trace_context["trace_id"]
            if "span_id" in trace_context:
                enhanced_context["span_id"] = trace_context["span_id"]

        # Log error with enhanced context
        log_method = getattr(logger, severity, logger.error)
        log_method(
            f"[{error_code}] {str(error)}", extra={"error_context": enhanced_context}
        )

        # Record error metric
        self.tracing_adapter.record_metric(
            name="error_count",
            value=1.0,
            tenant_id=tenant_id,
            error_code=error_code,
            error_type=error.__class__.__name__,
            severity=severity,
        )

        return error_id

    def track_metric(
        self, *, name: str, value: float, tenant_id: str, **tags: Any
    ) -> None:
        """Track metric with history for alerting.

        Args:
            name: Metric name
            value: Metric value
            tenant_id: Tenant identifier
            **tags: Additional metric tags
        """
        # Record metric using tracing adapter
        self.tracing_adapter.record_metric(
            name=name, value=value, tenant_id=tenant_id, **tags
        )

        # Store metric in history for alerting
        if self.enable_alerts:
            # Initialize history for this metric if not exists
            if name not in self.metric_history:
                self.metric_history[name] = deque(maxlen=self.metric_history_size)

            # Add data point to history
            self.metric_history[name].append(
                MetricDataPoint(
                    value=value, timestamp=time.time(), tenant_id=tenant_id, tags=tags
                )
            )

            # Check for alerts
            self._check_alert_thresholds(name, value, tenant_id, tags)

    def get_metric_baseline(
        self, *, name: str, tenant_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Get baseline statistics for a metric.

        Args:
            name: Metric name
            tenant_id: Optional tenant identifier for filtering

        Returns:
            Dictionary with baseline statistics (p50, p95, mean, etc.)
        """
        if name not in self.metric_history:
            return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "count": 0}

        # Filter data points by tenant_id if specified
        data_points = list(self.metric_history[name])
        if tenant_id:
            data_points = [dp for dp in data_points if dp.tenant_id == tenant_id]

        # Filter by timestamp for baseline period
        current_time = time.time()
        baseline_start = current_time - self.baseline_period_seconds
        data_points = [dp for dp in data_points if dp.timestamp >= baseline_start]

        if not data_points:
            return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "count": 0}

        # Calculate statistics
        values = [dp.value for dp in data_points]
        values.sort()

        return {
            "p50": values[len(values) // 2],
            "p95": values[int(len(values) * 0.95)],
            "mean": sum(values) / len(values),
            "count": len(values),
        }

    def set_alert_handler(
        self, alert_type: str, handler: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Set handler for specific alert type.

        Args:
            alert_type: Alert type identifier
            handler: Alert handler function
        """
        self.alert_handlers[alert_type] = handler

    def _default_alert_thresholds(self) -> List[AlertThreshold]:
        """Create default alert thresholds.

        Returns:
            List of default AlertThreshold objects
        """
        return [
            # Latency thresholds
            AlertThreshold(
                metric_name="graphrag_latency_ms",
                warning_threshold=300.0,  # 300ms
                critical_threshold=500.0,  # 500ms
                lookback_period_seconds=300,  # 5 minutes
                min_data_points=5,
            ),
            # Validation failure ratio thresholds
            AlertThreshold(
                metric_name="validation_fail_ratio",
                warning_threshold=0.05,  # 5%
                critical_threshold=0.10,  # 10%
                lookback_period_seconds=600,  # 10 minutes
                min_data_points=10,
            ),
            # Agent turns thresholds (high values indicate potential issues)
            AlertThreshold(
                metric_name="agent_turns",
                warning_threshold=10.0,
                critical_threshold=15.0,
                lookback_period_seconds=600,  # 10 minutes
                min_data_points=5,
            ),
        ]

    def _start_alert_monitoring(self) -> None:
        """Start background thread for alert monitoring."""
        alert_thread = threading.Thread(target=self._alert_monitoring_loop, daemon=True)
        alert_thread.start()

    def _alert_monitoring_loop(self) -> None:
        """Background loop for alert monitoring."""
        while True:
            try:
                # Check all metrics for alerts
                for name in list(self.metric_history.keys()):
                    self._evaluate_metric_alerts(name)

                # Sleep for a short period
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {str(e)}", exc_info=True)
                time.sleep(30)  # Longer sleep on error

    def _evaluate_metric_alerts(self, metric_name: str) -> None:
        """Evaluate alerts for a specific metric.

        Args:
            metric_name: Metric name to evaluate
        """
        # Find thresholds for this metric
        thresholds = [t for t in self.alert_thresholds if t.metric_name == metric_name]
        if not thresholds:
            return

        # Get baseline for comparison
        baseline = self.get_metric_baseline(name=metric_name)

        # Skip if not enough data
        if baseline["count"] < thresholds[0].min_data_points:
            return

        # Get recent data for evaluation
        current_time = time.time()
        lookback_start = current_time - thresholds[0].lookback_period_seconds
        recent_data = [
            dp
            for dp in self.metric_history[metric_name]
            if dp.timestamp >= lookback_start
        ]

        # Skip if not enough recent data
        if len(recent_data) < thresholds[0].min_data_points:
            return

        # Calculate current statistics
        recent_values = [dp.value for dp in recent_data]
        recent_mean = sum(recent_values) / len(recent_values)

        # Check against thresholds
        for threshold in thresholds:
            # Skip if in cooldown period
            if (current_time - threshold.last_alert_time) < threshold.cooldown_seconds:
                continue

            # Check for critical threshold
            if recent_mean >= threshold.critical_threshold:
                self._trigger_alert(
                    alert_type="critical",
                    metric_name=metric_name,
                    current_value=recent_mean,
                    threshold=threshold.critical_threshold,
                    baseline=baseline["mean"],
                    data_points=len(recent_data),
                )
                threshold.last_alert_time = current_time
            # Check for warning threshold
            elif recent_mean >= threshold.warning_threshold:
                self._trigger_alert(
                    alert_type="warning",
                    metric_name=metric_name,
                    current_value=recent_mean,
                    threshold=threshold.warning_threshold,
                    baseline=baseline["mean"],
                    data_points=len(recent_data),
                )
                threshold.last_alert_time = current_time

    def _check_alert_thresholds(
        self, metric_name: str, value: float, tenant_id: str, tags: Dict[str, Any]
    ) -> None:
        """Check individual metric value against thresholds.

        Args:
            metric_name: Metric name
            value: Metric value
            tenant_id: Tenant identifier
            tags: Additional metric tags
        """
        # Find thresholds for this metric
        thresholds = [t for t in self.alert_thresholds if t.metric_name == metric_name]
        if not thresholds:
            return

        # Get baseline for comparison
        baseline = self.get_metric_baseline(name=metric_name, tenant_id=tenant_id)

        # Skip if not enough data for baseline
        if baseline["count"] < 10:
            return

        current_time = time.time()

        # Check for sudden spikes (individual value much higher than p95)
        for threshold in thresholds:
            # Skip if in cooldown period
            if (current_time - threshold.last_alert_time) < threshold.cooldown_seconds:
                continue

            # Check for critical spike (value > 2x p95)
            if value > (baseline["p95"] * 2) and value > threshold.critical_threshold:
                self._trigger_alert(
                    alert_type="critical_spike",
                    metric_name=metric_name,
                    current_value=value,
                    threshold=baseline["p95"] * 2,
                    baseline=baseline["p95"],
                    data_points=1,
                    tenant_id=tenant_id,
                    tags=tags,
                )
                threshold.last_alert_time = current_time
            # Check for warning spike (value > 1.5x p95)
            elif (
                value > (baseline["p95"] * 1.5) and value > threshold.warning_threshold
            ):
                self._trigger_alert(
                    alert_type="warning_spike",
                    metric_name=metric_name,
                    current_value=value,
                    threshold=baseline["p95"] * 1.5,
                    baseline=baseline["p95"],
                    data_points=1,
                    tenant_id=tenant_id,
                    tags=tags,
                )
                threshold.last_alert_time = current_time

    def _trigger_alert(
        self,
        *,
        alert_type: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        baseline: float,
        data_points: int,
        tenant_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Trigger alert based on threshold violation.

        Args:
            alert_type: Alert type (warning, critical, etc.)
            metric_name: Metric name
            current_value: Current metric value
            threshold: Threshold that was violated
            baseline: Baseline value for comparison
            data_points: Number of data points considered
            tenant_id: Optional tenant identifier
            tags: Optional additional tags
        """
        # Create alert context
        alert_id = f"alert_{int(time.time())}_{metric_name}_{alert_type}"
        alert_context = {
            "alert_id": alert_id,
            "alert_type": alert_type,
            "metric_name": metric_name,
            "current_value": current_value,
            "threshold": threshold,
            "baseline": baseline,
            "data_points": data_points,
            "percentage_increase": (
                ((current_value - baseline) / baseline) * 100 if baseline > 0 else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }

        if tenant_id:
            alert_context["tenant_id"] = tenant_id

        if tags:
            alert_context["tags"] = tags

        # Log alert
        logger.warning(
            f"Performance alert: {alert_type} for {metric_name} - "
            f"value: {current_value:.2f}, threshold: {threshold:.2f}, "
            f"baseline: {baseline:.2f}, increase: {alert_context['percentage_increase']:.1f}%",
            extra={"alert_context": alert_context},
        )

        # Record alert metric
        self.tracing_adapter.record_metric(
            name="alert_count",
            value=1.0,
            tenant_id=tenant_id or "unknown",
            alert_type=alert_type,
            metric_name=metric_name,
        )

        # Call alert handler if available
        if alert_type in self.alert_handlers:
            try:
                self.alert_handlers[alert_type](alert_id, alert_context)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}", exc_info=True)

        # Store active alert
        self.active_alerts[alert_id] = alert_context
