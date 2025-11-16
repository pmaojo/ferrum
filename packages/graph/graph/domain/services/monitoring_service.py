"""
Monitoring service for PermaGraph system observability.
Provides metrics collection, health checks, and alerting capabilities.
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import psutil
import threading
from collections import defaultdict, deque

from ..entities.validation_report import ValidationReport
from application.ports.alert_port import AlertPort
from application.ports.metrics_port import MetricsPort


class ComponentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class HealthCheck:
    component: str
    status: ComponentStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    id: str
    severity: str  # critical, warning, info
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class MonitoringService:
    """Central monitoring service for system observability."""
    
    def __init__(self, alert_port: AlertPort, metrics_port: MetricsPort):
        self.alert_port = alert_port
        self.metrics_port = metrics_port
        self.logger = logging.getLogger(__name__)
        
        # Health check registry
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_check_lock = threading.Lock()
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.metrics_lock = threading.Lock()
        
        # Performance tracking
        self.reasoning_times: deque = deque(maxlen=100)
        self.query_times: deque = deque(maxlen=100)
        self.sync_times: deque = deque(maxlen=100)
        
        # Alert tracking
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        # System resource monitoring
        self.start_monitoring_thread()
    
    def start_monitoring_thread(self):
        """Start background thread for system monitoring."""
        def monitor_loop():
            while True:
                try:
                    self._collect_system_metrics()
                    self._check_system_health()
                    time.sleep(30)  # Collect metrics every 30 seconds
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(60)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def record_metric(self, name: str, value: float, metric_type: MetricType, 
                     labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        with self.metrics_lock:
            self.metrics[name].append(metric)
        
        # Send to external metrics system
        self.metrics_port.record_metric(metric)
    
    def record_reasoning_performance(self, operation: str, duration_ms: float, 
                                   success: bool, details: Optional[Dict] = None):
        """Record reasoning operation performance."""
        self.reasoning_times.append(duration_ms)
        
        # Record metrics
        self.record_metric(
            f"reasoning.{operation}.duration_ms",
            duration_ms,
            MetricType.HISTOGRAM,
            {"operation": operation, "success": str(success)}
        )
        
        self.record_metric(
            f"reasoning.{operation}.count",
            1,
            MetricType.COUNTER,
            {"operation": operation, "success": str(success)}
        )
        
        # Check for performance degradation
        if duration_ms > 10000:  # 10 seconds threshold
            self._create_alert(
                "reasoning_performance",
                "warning",
                "reasoning",
                f"Slow reasoning operation: {operation} took {duration_ms}ms",
                details or {}
            )
    
    def record_query_performance(self, query_type: str, duration_ms: float, 
                               result_count: int, success: bool):
        """Record SPARQL query performance."""
        self.query_times.append(duration_ms)
        
        self.record_metric(
            f"query.{query_type}.duration_ms",
            duration_ms,
            MetricType.HISTOGRAM,
            {"query_type": query_type, "success": str(success)}
        )
        
        self.record_metric(
            f"query.{query_type}.result_count",
            result_count,
            MetricType.GAUGE,
            {"query_type": query_type}
        )
    
    def record_sync_performance(self, sync_type: str, duration_ms: float, 
                              changes_count: int, success: bool):
        """Record synchronization performance."""
        self.sync_times.append(duration_ms)
        
        self.record_metric(
            f"sync.{sync_type}.duration_ms",
            duration_ms,
            MetricType.HISTOGRAM,
            {"sync_type": sync_type, "success": str(success)}
        )
        
        self.record_metric(
            f"sync.{sync_type}.changes_count",
            changes_count,
            MetricType.GAUGE,
            {"sync_type": sync_type}
        )
    
    def update_health_check(self, component: str, status: ComponentStatus, 
                          message: str, response_time_ms: float = 0,
                          details: Optional[Dict] = None):
        """Update health check status for a component."""
        health_check = HealthCheck(
            component=component,
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            response_time_ms=response_time_ms,
            details=details or {}
        )
        
        with self.health_check_lock:
            previous_status = self.health_checks.get(component)
            self.health_checks[component] = health_check
        
        # Create alert if status changed to unhealthy
        if (previous_status and 
            previous_status.status != ComponentStatus.UNHEALTHY and 
            status == ComponentStatus.UNHEALTHY):
            self._create_alert(
                f"health_check_{component}",
                "critical",
                component,
                f"Component {component} is unhealthy: {message}",
                details or {}
            )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        with self.health_check_lock:
            health_checks = dict(self.health_checks)
        
        overall_status = ComponentStatus.HEALTHY
        unhealthy_components = []
        
        for component, check in health_checks.items():
            if check.status == ComponentStatus.UNHEALTHY:
                overall_status = ComponentStatus.UNHEALTHY
                unhealthy_components.append(component)
            elif check.status == ComponentStatus.DEGRADED and overall_status == ComponentStatus.HEALTHY:
                overall_status = ComponentStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "components": {k: {
                "status": v.status.value,
                "message": v.message,
                "timestamp": v.timestamp.isoformat(),
                "response_time_ms": v.response_time_ms,
                "details": v.details
            } for k, v in health_checks.items()},
            "unhealthy_components": unhealthy_components,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        reasoning_avg = sum(self.reasoning_times) / len(self.reasoning_times) if self.reasoning_times else 0
        query_avg = sum(self.query_times) / len(self.query_times) if self.query_times else 0
        sync_avg = sum(self.sync_times) / len(self.sync_times) if self.sync_times else 0
        
        return {
            "reasoning": {
                "average_duration_ms": reasoning_avg,
                "recent_operations": len(self.reasoning_times),
                "max_duration_ms": max(self.reasoning_times) if self.reasoning_times else 0
            },
            "queries": {
                "average_duration_ms": query_avg,
                "recent_queries": len(self.query_times),
                "max_duration_ms": max(self.query_times) if self.query_times else 0
            },
            "synchronization": {
                "average_duration_ms": sync_avg,
                "recent_syncs": len(self.sync_times),
                "max_duration_ms": max(self.sync_times) if self.sync_times else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        return [
            {
                "id": alert.id,
                "severity": alert.severity,
                "component": alert.component,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "details": alert.details
            }
            for alert in self.active_alerts.values()
        ]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            self.alert_port.resolve_alert(alert_id)
            return True
        return False
    
    def _collect_system_metrics(self):
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system.cpu_percent", cpu_percent, MetricType.GAUGE)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric("system.memory_percent", memory.percent, MetricType.GAUGE)
            self.record_metric("system.memory_available_mb", memory.available / 1024 / 1024, MetricType.GAUGE)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric("system.disk_percent", disk_percent, MetricType.GAUGE)
            
            # Network I/O
            network = psutil.net_io_counters()
            self.record_metric("system.network_bytes_sent", network.bytes_sent, MetricType.COUNTER)
            self.record_metric("system.network_bytes_recv", network.bytes_recv, MetricType.COUNTER)
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _check_system_health(self):
        """Check system health and create alerts if needed."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 90:
                self._create_alert(
                    "high_cpu_usage",
                    "warning",
                    "system",
                    f"High CPU usage: {cpu_percent}%",
                    {"cpu_percent": cpu_percent}
                )
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self._create_alert(
                    "high_memory_usage",
                    "warning",
                    "system",
                    f"High memory usage: {memory.percent}%",
                    {"memory_percent": memory.percent}
                )
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                self._create_alert(
                    "high_disk_usage",
                    "critical",
                    "system",
                    f"High disk usage: {disk_percent}%",
                    {"disk_percent": disk_percent}
                )
                
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
    
    def _create_alert(self, alert_id: str, severity: str, component: str, 
                     message: str, details: Dict[str, Any]):
        """Create a new alert."""
        # Don't create duplicate alerts
        if alert_id in self.active_alerts:
            return
        
        alert = Alert(
            id=alert_id,
            severity=severity,
            component=component,
            message=message,
            timestamp=datetime.utcnow(),
            details=details
        )
        
        self.active_alerts[alert_id] = alert
        
        # Send to external alerting system
        self.alert_port.send_alert(alert)
        
        self.logger.warning(f"Alert created: {alert_id} - {message}")


class PerformanceMonitor:
    """Context manager for monitoring operation performance."""
    
    def __init__(self, monitoring_service: MonitoringService, operation: str, 
                 operation_type: str = "general"):
        self.monitoring_service = monitoring_service
        self.operation = operation
        self.operation_type = operation_type
        self.start_time = None
        self.success = True
        self.details = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.success = exc_type is None
        
        if self.operation_type == "reasoning":
            self.monitoring_service.record_reasoning_performance(
                self.operation, duration_ms, self.success, self.details
            )
        elif self.operation_type == "query":
            self.monitoring_service.record_query_performance(
                self.operation, duration_ms, 0, self.success
            )
        elif self.operation_type == "sync":
            self.monitoring_service.record_sync_performance(
                self.operation, duration_ms, 0, self.success
            )
    
    def set_details(self, **kwargs):
        """Set additional details for the operation."""
        self.details.update(kwargs)