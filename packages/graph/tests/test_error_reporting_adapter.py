"""Unit tests for ErrorReportingAdapter."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
import json
import time
from typing import Dict, Any, List

from application.ports import TracingPort

from adapters.error_reporting_adapter import (
    ErrorReportingAdapter, AlertThreshold, MetricDataPoint
)


class TestErrorReportingAdapter(unittest.TestCase):
    """Test cases for ErrorReportingAdapter."""

    def setUp(self):
        """Set up test environment."""
        # Create mock tracing adapter conforming to TracingPort
        self.mock_tracing = Mock(spec=TracingPort)
        self.mock_tracing.record_metric = Mock()

        # Create test alert thresholds
        self.test_thresholds = [
            AlertThreshold(
                metric_name="test_latency",
                warning_threshold=100.0,
                critical_threshold=200.0,
                lookback_period_seconds=60,
                min_data_points=2,
                cooldown_seconds=10
            )
        ]

        # Create test alert handler
        self.alert_handler_calls = []
        def test_alert_handler(alert_id, context):
            self.alert_handler_calls.append((alert_id, context))

        # Create adapter with test configuration
        self.adapter = ErrorReportingAdapter(
            tracing_adapter=self.mock_tracing,
            alert_thresholds=self.test_thresholds,
            enable_alerts=True,
            alert_handlers={"warning": test_alert_handler, "critical": test_alert_handler},
            metric_history_size=100,
            baseline_period_seconds=60
        )

        # Disable background alert monitoring for tests
        self.adapter._start_alert_monitoring = Mock()

    def test_report_error(self):
        """Test error reporting with context."""
        # Create test error
        test_error = ValueError("Test error")

        # Report error
        error_id = self.adapter.report_error(
            error=test_error,
            error_code="TEST_ERROR",
            context={"test_key": "test_value"},
            tenant_id="test_tenant",
            doc_id="test_doc",
            agent_id="test_agent",
            question_id="test_question",
            severity="error"
        )

        # Verify error_id format
        self.assertTrue(error_id.startswith("err_"))

        # Verify metric was recorded
        self.mock_tracing.record_metric.assert_called_once()
        args, kwargs = self.mock_tracing.record_metric.call_args
        self.assertEqual(kwargs["name"], "error_count")
        self.assertEqual(kwargs["value"], 1.0)
        self.assertEqual(kwargs["tenant_id"], "test_tenant")
        self.assertEqual(kwargs["error_code"], "TEST_ERROR")
        self.assertEqual(kwargs["error_type"], "ValueError")

    def test_track_metric(self):
        """Test metric tracking."""
        # Track metric
        self.adapter.track_metric(
            name="test_latency",
            value=50.0,
            tenant_id="test_tenant",
            custom_tag="custom_value"
        )

        # Verify metric was recorded via tracing adapter
        self.mock_tracing.record_metric.assert_called_once()
        args, kwargs = self.mock_tracing.record_metric.call_args
        self.assertEqual(kwargs["name"], "test_latency")
        self.assertEqual(kwargs["value"], 50.0)
        self.assertEqual(kwargs["tenant_id"], "test_tenant")
        self.assertEqual(kwargs["custom_tag"], "custom_value")

        # Verify metric was added to history
        self.assertIn("test_latency", self.adapter.metric_history)
        self.assertEqual(len(self.adapter.metric_history["test_latency"]), 1)
        data_point = self.adapter.metric_history["test_latency"][0]
        self.assertEqual(data_point.value, 50.0)
        self.assertEqual(data_point.tenant_id, "test_tenant")
        self.assertEqual(data_point.tags["custom_tag"], "custom_value")

    def test_get_metric_baseline(self):
        """Test metric baseline calculation."""
        # Add test data points
        self.adapter.metric_history["test_metric"] = [
            MetricDataPoint(value=10.0, timestamp=time.time(), tenant_id="test_tenant", tags={}),
            MetricDataPoint(value=20.0, timestamp=time.time(), tenant_id="test_tenant", tags={}),
            MetricDataPoint(value=30.0, timestamp=time.time(), tenant_id="test_tenant", tags={}),
            MetricDataPoint(value=40.0, timestamp=time.time(), tenant_id="test_tenant", tags={}),
            MetricDataPoint(value=50.0, timestamp=time.time(), tenant_id="test_tenant", tags={})
        ]

        # Get baseline
        baseline = self.adapter.get_metric_baseline(name="test_metric")

        # Verify baseline statistics
        self.assertEqual(baseline["p50"], 30.0)  # Median of [10, 20, 30, 40, 50]
        self.assertEqual(baseline["p95"], 50.0)  # 95th percentile
        self.assertEqual(baseline["mean"], 30.0)  # Mean
        self.assertEqual(baseline["count"], 5)    # Count

        # Test with tenant filtering
        baseline_tenant = self.adapter.get_metric_baseline(
            name="test_metric",
            tenant_id="test_tenant"
        )
        self.assertEqual(baseline_tenant["count"], 5)

        baseline_other = self.adapter.get_metric_baseline(
            name="test_metric",
            tenant_id="other_tenant"
        )
        self.assertEqual(baseline_other["count"], 0)

    def test_alert_triggering(self):
        """Test alert triggering based on thresholds."""
        # Add baseline data points
        current_time = time.time()
        for i in range(10):
            self.adapter.metric_history.setdefault("test_latency", []).append(
                MetricDataPoint(
                    value=50.0,  # Below threshold
                    timestamp=current_time - 30,  # 30 seconds ago
                    tenant_id="test_tenant",
                    tags={}
                )
            )

        # Verify no alerts initially
        self.assertEqual(len(self.alert_handler_calls), 0)

        # Mock the _trigger_alert method to track calls without side effects
        original_trigger_alert = self.adapter._trigger_alert
        trigger_alert_calls = []

        def mock_trigger_alert(*args, **kwargs):
            # Store the original kwargs before modifying
            original_kwargs = kwargs.copy()
            trigger_alert_calls.append((args, original_kwargs))
            # Don't call handlers in test to avoid side effects
            kwargs["alert_type"] = "test_" + kwargs["alert_type"]
            return original_trigger_alert(*args, **kwargs)

        self.adapter._trigger_alert = mock_trigger_alert

        # Add data point above warning threshold
        self.adapter._check_alert_thresholds(
            metric_name="test_latency",
            value=150.0,  # Above warning (100) but below critical (200)
            tenant_id="test_tenant",
            tags={}
        )

        # Verify warning alert was triggered
        self.assertEqual(len(trigger_alert_calls), 1)
        args, kwargs = trigger_alert_calls[0]
        self.assertEqual(kwargs["alert_type"], "warning_spike")
        self.assertEqual(kwargs["metric_name"], "test_latency")

        # Reset trigger calls
        trigger_alert_calls = []

        # Add data point above critical threshold
        self.adapter._check_alert_thresholds(
            metric_name="test_latency",
            value=250.0,  # Above critical (200)
            tenant_id="test_tenant",
            tags={}
        )

        # Verify no alert due to cooldown
        self.assertEqual(len(trigger_alert_calls), 0)

        # Reset cooldown
        self.test_thresholds[0].last_alert_time = 0

        # Try again
        self.adapter._check_alert_thresholds(
            metric_name="test_latency",
            value=250.0,  # Above critical (200)
            tenant_id="test_tenant",
            tags={}
        )

        # Verify critical alert was triggered
        self.assertEqual(len(trigger_alert_calls), 1)
        args, kwargs = trigger_alert_calls[0]
        self.assertEqual(kwargs["alert_type"], "critical_spike")
        self.assertEqual(kwargs["metric_name"], "test_latency")

        # Restore original method
        self.adapter._trigger_alert = original_trigger_alert

    def test_evaluate_metric_alerts(self):
        """Test metric alert evaluation."""
        # Add test data points
        current_time = time.time()
        for i in range(10):
            self.adapter.metric_history.setdefault("test_latency", []).append(
                MetricDataPoint(
                    value=50.0,  # Baseline
                    timestamp=current_time - 120,  # 2 minutes ago
                    tenant_id="test_tenant",
                    tags={}
                )
            )

        # Add recent data points above threshold
        for i in range(5):
            self.adapter.metric_history["test_latency"].append(
                MetricDataPoint(
                    value=150.0,  # Above warning threshold
                    timestamp=current_time - 30,  # 30 seconds ago
                    tenant_id="test_tenant",
                    tags={}
                )
            )

        # Reset alert calls
        self.alert_handler_calls = []

        # Evaluate alerts
        self.adapter._evaluate_metric_alerts("test_latency")

        # Verify alert was triggered
        self.assertEqual(len(self.alert_handler_calls), 1)
        alert_id, context = self.alert_handler_calls[0]
        self.assertEqual(context["alert_type"], "warning")
        self.assertEqual(context["metric_name"], "test_latency")
        self.assertEqual(context["current_value"], 150.0)

    def test_set_alert_handler(self):
        """Test setting custom alert handler."""
        # Create test handler
        custom_handler_calls = []
        def custom_handler(alert_id, context):
            custom_handler_calls.append((alert_id, context))

        # Set custom handler
        self.adapter.set_alert_handler("custom_alert", custom_handler)

        # Trigger custom alert
        self.adapter._trigger_alert(
            alert_type="custom_alert",
            metric_name="test_metric",
            current_value=100.0,
            threshold=50.0,
            baseline=25.0,
            data_points=5
        )

        # Verify custom handler was called
        self.assertEqual(len(custom_handler_calls), 1)
        alert_id, context = custom_handler_calls[0]
        self.assertEqual(context["alert_type"], "custom_alert")
        self.assertEqual(context["metric_name"], "test_metric")


class TestAlertThreshold(unittest.TestCase):
    """Test cases for AlertThreshold."""

    def test_alert_threshold_initialization(self):
        """Test AlertThreshold initialization."""
        threshold = AlertThreshold(
            metric_name="test_metric",
            warning_threshold=100.0,
            critical_threshold=200.0,
            lookback_period_seconds=300,
            min_data_points=5,
            cooldown_seconds=60
        )

        self.assertEqual(threshold.metric_name, "test_metric")
        self.assertEqual(threshold.warning_threshold, 100.0)
        self.assertEqual(threshold.critical_threshold, 200.0)
        self.assertEqual(threshold.lookback_period_seconds, 300)
        self.assertEqual(threshold.min_data_points, 5)
        self.assertEqual(threshold.cooldown_seconds, 60)
        self.assertEqual(threshold.last_alert_time, 0)


class TestMetricDataPoint(unittest.TestCase):
    """Test cases for MetricDataPoint."""

    def test_metric_data_point_initialization(self):
        """Test MetricDataPoint initialization."""
        timestamp = time.time()
        data_point = MetricDataPoint(
            value=42.0,
            timestamp=timestamp,
            tenant_id="test_tenant",
            tags={"tag1": "value1", "tag2": "value2"}
        )

        self.assertEqual(data_point.value, 42.0)
        self.assertEqual(data_point.timestamp, timestamp)
        self.assertEqual(data_point.tenant_id, "test_tenant")
        self.assertEqual(data_point.tags["tag1"], "value1")
        self.assertEqual(data_point.tags["tag2"], "value2")


if __name__ == '__main__':
    unittest.main()