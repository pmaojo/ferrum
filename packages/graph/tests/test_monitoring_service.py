"""
Tests for the monitoring service.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from domain.services.monitoring_service import (
    MonitoringService,
    PerformanceMonitor,
    ComponentStatus,
    MetricType,
    Alert
)
from application.ports.alert_port import AlertPort
from application.ports.metrics_port import MetricsPort


class MockAlertPort(AlertPort):
    def __init__(self):
        self.sent_alerts = []
        self.resolved_alerts = []
    
    def send_alert(self, alert: Alert) -> None:
        self.sent_alerts.append(alert)
    
    def resolve_alert(self, alert_id: str) -> None:
        self.resolved_alerts.append(alert_id)
    
    def configure_alert_rules(self, rules):
        pass
    
    def get_alert_history(self, component=None, severity=None, limit=100):
        return []


class MockMetricsPort(MetricsPort):
    def __init__(self):
        self.recorded_metrics = []
    
    def record_metric(self, metric):
        self.recorded_metrics.append(metric)
    
    def get_metrics(self, name_pattern, start_time=None, end_time=None, labels=None):
        return []
    
    def create_dashboard(self, name, config):
        return f"dashboard_{name}"
    
    def get_dashboard_url(self, dashboard_id):
        return f"http://localhost:3000/d/{dashboard_id}"


@pytest.fixture
def mock_alert_port():
    return MockAlertPort()


@pytest.fixture
def mock_metrics_port():
    return MockMetricsPort()


@pytest.fixture
def monitoring_service(mock_alert_port, mock_metrics_port):
    return MonitoringService(mock_alert_port, mock_metrics_port)


class TestMonitoringService:
    
    def test_record_metric(self, monitoring_service, mock_metrics_port):
        """Test recording a metric."""
        monitoring_service.record_metric(
            "test_metric",
            42.0,
            MetricType.GAUGE,
            {"label1": "value1"}
        )
        
        assert len(mock_metrics_port.recorded_metrics) == 1
        metric = mock_metrics_port.recorded_metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.type == MetricType.GAUGE
        assert metric.labels == {"label1": "value1"}
    
    def test_record_reasoning_performance(self, monitoring_service, mock_metrics_port):
        """Test recording reasoning performance metrics."""
        monitoring_service.record_reasoning_performance(
            "ontology_validation",
            250.5,
            True,
            {"triples_count": 100}
        )
        
        # Should record duration and count metrics
        assert len(mock_metrics_port.recorded_metrics) == 2
        
        duration_metric = next(m for m in mock_metrics_port.recorded_metrics 
                              if "duration_ms" in m.name)
        assert duration_metric.value == 250.5
        assert duration_metric.labels["operation"] == "ontology_validation"
        assert duration_metric.labels["success"] == "True"
        
        count_metric = next(m for m in mock_metrics_port.recorded_metrics 
                           if "count" in m.name)
        assert count_metric.value == 1
    
    def test_record_reasoning_performance_slow_alert(self, monitoring_service, mock_alert_port):
        """Test that slow reasoning operations create alerts."""
        monitoring_service.record_reasoning_performance(
            "slow_operation",
            15000,  # 15 seconds - above threshold
            True
        )
        
        assert len(mock_alert_port.sent_alerts) == 1
        alert = mock_alert_port.sent_alerts[0]
        assert alert.id == "reasoning_performance"
        assert alert.severity == "warning"
        assert alert.component == "reasoning"
        assert "slow_operation took 15000ms" in alert.message
    
    def test_update_health_check(self, monitoring_service):
        """Test updating health check status."""
        monitoring_service.update_health_check(
            "test_component",
            ComponentStatus.HEALTHY,
            "All systems operational",
            25.5,
            {"test_detail": "passed"}
        )
        
        health_checks = monitoring_service.health_checks
        assert "test_component" in health_checks
        
        check = health_checks["test_component"]
        assert check.component == "test_component"
        assert check.status == ComponentStatus.HEALTHY
        assert check.message == "All systems operational"
        assert check.response_time_ms == 25.5
        assert check.details == {"test_detail": "passed"}
    
    def test_health_check_status_change_alert(self, monitoring_service, mock_alert_port):
        """Test that health status changes to unhealthy create alerts."""
        # First set healthy status
        monitoring_service.update_health_check(
            "test_component",
            ComponentStatus.HEALTHY,
            "Working fine"
        )
        
        # Then change to unhealthy
        monitoring_service.update_health_check(
            "test_component",
            ComponentStatus.UNHEALTHY,
            "Service down",
            0,
            {"error": "connection_refused"}
        )
        
        assert len(mock_alert_port.sent_alerts) == 1
        alert = mock_alert_port.sent_alerts[0]
        assert alert.id == "health_check_test_component"
        assert alert.severity == "critical"
        assert alert.component == "test_component"
        assert "test_component is unhealthy" in alert.message
    
    def test_get_system_health(self, monitoring_service):
        """Test getting overall system health."""
        # Add some health checks
        monitoring_service.update_health_check(
            "component1",
            ComponentStatus.HEALTHY,
            "OK"
        )
        monitoring_service.update_health_check(
            "component2",
            ComponentStatus.DEGRADED,
            "Slow response"
        )
        
        health = monitoring_service.get_system_health()
        
        assert health["overall_status"] == ComponentStatus.DEGRADED.value
        assert len(health["components"]) == 2
        assert health["unhealthy_components"] == []
        assert "timestamp" in health
    
    def test_get_system_health_with_unhealthy_component(self, monitoring_service):
        """Test system health with unhealthy components."""
        monitoring_service.update_health_check(
            "healthy_component",
            ComponentStatus.HEALTHY,
            "OK"
        )
        monitoring_service.update_health_check(
            "unhealthy_component",
            ComponentStatus.UNHEALTHY,
            "Failed"
        )
        
        health = monitoring_service.get_system_health()
        
        assert health["overall_status"] == ComponentStatus.UNHEALTHY.value
        assert health["unhealthy_components"] == ["unhealthy_component"]
    
    def test_get_performance_metrics(self, monitoring_service):
        """Test getting performance metrics summary."""
        # Add some performance data
        monitoring_service.reasoning_times.extend([100, 200, 300])
        monitoring_service.query_times.extend([50, 75, 100])
        monitoring_service.sync_times.extend([150, 200])
        
        metrics = monitoring_service.get_performance_metrics()
        
        assert metrics["reasoning"]["average_duration_ms"] == 200.0
        assert metrics["reasoning"]["recent_operations"] == 3
        assert metrics["reasoning"]["max_duration_ms"] == 300
        
        assert metrics["queries"]["average_duration_ms"] == 75.0
        assert metrics["queries"]["recent_queries"] == 3
        assert metrics["queries"]["max_duration_ms"] == 100
        
        assert metrics["synchronization"]["average_duration_ms"] == 175.0
        assert metrics["synchronization"]["recent_syncs"] == 2
        assert metrics["synchronization"]["max_duration_ms"] == 200
    
    def test_get_active_alerts(self, monitoring_service):
        """Test getting active alerts."""
        # Create some alerts
        monitoring_service._create_alert(
            "test_alert_1",
            "warning",
            "test_component",
            "Test alert 1",
            {"detail": "value1"}
        )
        monitoring_service._create_alert(
            "test_alert_2",
            "critical",
            "test_component",
            "Test alert 2",
            {"detail": "value2"}
        )
        
        alerts = monitoring_service.get_active_alerts()
        
        assert len(alerts) == 2
        assert alerts[0]["id"] == "test_alert_1"
        assert alerts[0]["severity"] == "warning"
        assert alerts[1]["id"] == "test_alert_2"
        assert alerts[1]["severity"] == "critical"
    
    def test_resolve_alert(self, monitoring_service, mock_alert_port):
        """Test resolving an alert."""
        # Create an alert
        monitoring_service._create_alert(
            "test_alert",
            "warning",
            "test_component",
            "Test alert",
            {}
        )
        
        assert len(monitoring_service.active_alerts) == 1
        
        # Resolve the alert
        success = monitoring_service.resolve_alert("test_alert")
        
        assert success is True
        assert len(monitoring_service.active_alerts) == 0
        assert len(monitoring_service.alert_history) == 1
        assert len(mock_alert_port.resolved_alerts) == 1
        assert mock_alert_port.resolved_alerts[0] == "test_alert"
    
    def test_resolve_nonexistent_alert(self, monitoring_service):
        """Test resolving a non-existent alert."""
        success = monitoring_service.resolve_alert("nonexistent_alert")
        assert success is False
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_collect_system_metrics(self, mock_net, mock_disk, mock_memory, mock_cpu, 
                                   monitoring_service, mock_metrics_port):
        """Test collecting system metrics."""
        # Mock system metrics
        mock_cpu.return_value = 75.5
        mock_memory.return_value = Mock(percent=60.2, available=8589934592)
        mock_disk.return_value = Mock(used=500000000000, total=1000000000000)
        mock_net.return_value = Mock(bytes_sent=1000000, bytes_recv=2000000)
        
        monitoring_service._collect_system_metrics()
        
        # Check that metrics were recorded
        metric_names = [m.name for m in mock_metrics_port.recorded_metrics]
        assert "system.cpu_percent" in metric_names
        assert "system.memory_percent" in metric_names
        assert "system.disk_percent" in metric_names
        assert "system.network_bytes_sent" in metric_names
        assert "system.network_bytes_recv" in metric_names


class TestPerformanceMonitor:
    
    def test_performance_monitor_context_manager(self, monitoring_service):
        """Test PerformanceMonitor as context manager."""
        with PerformanceMonitor(monitoring_service, "test_operation", "reasoning") as monitor:
            monitor.set_details(test_param="test_value")
            time.sleep(0.01)  # Small delay to measure
        
        # Check that reasoning performance was recorded
        assert len(monitoring_service.reasoning_times) == 1
        assert monitoring_service.reasoning_times[0] > 0
    
    def test_performance_monitor_with_exception(self, monitoring_service):
        """Test PerformanceMonitor handling exceptions."""
        try:
            with PerformanceMonitor(monitoring_service, "failing_operation", "reasoning"):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still record the performance (as failed)
        assert len(monitoring_service.reasoning_times) == 1
    
    def test_performance_monitor_query_type(self, monitoring_service):
        """Test PerformanceMonitor with query operation type."""
        with PerformanceMonitor(monitoring_service, "test_query", "query"):
            time.sleep(0.01)
        
        assert len(monitoring_service.query_times) == 1
        assert monitoring_service.query_times[0] > 0
    
    def test_performance_monitor_sync_type(self, monitoring_service):
        """Test PerformanceMonitor with sync operation type."""
        with PerformanceMonitor(monitoring_service, "test_sync", "sync"):
            time.sleep(0.01)
        
        assert len(monitoring_service.sync_times) == 1
        assert monitoring_service.sync_times[0] > 0


class TestMonitoringServiceIntegration:
    
    @patch('psutil.cpu_percent')
    def test_high_cpu_alert_creation(self, mock_cpu, monitoring_service, mock_alert_port):
        """Test that high CPU usage creates an alert."""
        mock_cpu.return_value = 95.0
        
        monitoring_service._check_system_health()
        
        assert len(mock_alert_port.sent_alerts) == 1
        alert = mock_alert_port.sent_alerts[0]
        assert alert.id == "high_cpu_usage"
        assert alert.severity == "warning"
        assert "High CPU usage: 95.0%" in alert.message
    
    @patch('psutil.virtual_memory')
    def test_high_memory_alert_creation(self, mock_memory, monitoring_service, mock_alert_port):
        """Test that high memory usage creates an alert."""
        mock_memory.return_value = Mock(percent=95.0)
        
        monitoring_service._check_system_health()
        
        assert len(mock_alert_port.sent_alerts) == 1
        alert = mock_alert_port.sent_alerts[0]
        assert alert.id == "high_memory_usage"
        assert alert.severity == "warning"
        assert "High memory usage: 95.0%" in alert.message
    
    @patch('psutil.disk_usage')
    def test_high_disk_alert_creation(self, mock_disk, monitoring_service, mock_alert_port):
        """Test that high disk usage creates a critical alert."""
        mock_disk.return_value = Mock(used=950000000000, total=1000000000000)
        
        monitoring_service._check_system_health()
        
        assert len(mock_alert_port.sent_alerts) == 1
        alert = mock_alert_port.sent_alerts[0]
        assert alert.id == "high_disk_usage"
        assert alert.severity == "critical"
        assert "High disk usage: 95.0%" in alert.message