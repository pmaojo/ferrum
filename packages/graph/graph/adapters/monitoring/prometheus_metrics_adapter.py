"""
Prometheus metrics adapter for PermaGraph monitoring.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, push_to_gateway

from application.ports.metrics_port import MetricsPort
from domain.services.monitoring_service import Metric, MetricType


class PrometheusMetricsAdapter(MetricsPort):
    """Adapter for Prometheus metrics collection."""
    
    def __init__(self, pushgateway_url: str = "http://localhost:9091",
                 prometheus_url: str = "http://localhost:9090",
                 job_name: str = "permagraph"):
        self.pushgateway_url = pushgateway_url
        self.prometheus_url = prometheus_url
        self.job_name = job_name
        self.logger = logging.getLogger(__name__)
        
        # Create registry for metrics
        self.registry = CollectorRegistry()
        
        # Initialize metric collectors
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
    
    def record_metric(self, metric: Metric) -> None:
        """Record a metric to Prometheus."""
        try:
            metric_name = self._sanitize_metric_name(metric.name)
            
            if metric.type == MetricType.COUNTER:
                counter = self._get_or_create_counter(metric_name, metric.labels)
                counter.inc(metric.value)
            
            elif metric.type == MetricType.GAUGE:
                gauge = self._get_or_create_gauge(metric_name, metric.labels)
                gauge.set(metric.value)
            
            elif metric.type == MetricType.HISTOGRAM:
                histogram = self._get_or_create_histogram(metric_name, metric.labels)
                histogram.observe(metric.value)
            
            elif metric.type == MetricType.TIMER:
                # Treat timers as histograms
                histogram = self._get_or_create_histogram(metric_name, metric.labels)
                histogram.observe(metric.value / 1000.0)  # Convert ms to seconds
            
            # Push metrics to gateway
            self._push_metrics()
            
        except Exception as e:
            self.logger.error(f"Error recording metric {metric.name}: {e}")
    
    def get_metrics(self, name_pattern: str, 
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   labels: Optional[Dict[str, str]] = None) -> List[Metric]:
        """Retrieve metrics from Prometheus."""
        try:
            # Build Prometheus query
            query = f'{name_pattern}'
            if labels:
                label_filters = [f'{k}="{v}"' for k, v in labels.items()]
                query = f'{name_pattern}{{{",".join(label_filters)}}}'
            
            # Add time range if specified
            params = {'query': query}
            if start_time and end_time:
                params['start'] = start_time.timestamp()
                params['end'] = end_time.timestamp()
                params['step'] = '30s'
                endpoint = 'query_range'
            else:
                endpoint = 'query'
            
            response = requests.get(
                f"{self.prometheus_url}/api/v1/{endpoint}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            metrics = []
            
            if data['status'] == 'success':
                for result in data['data']['result']:
                    metric_labels = result.get('metric', {})
                    
                    if endpoint == 'query_range':
                        for timestamp, value in result['values']:
                            metrics.append(Metric(
                                name=result['metric'].get('__name__', name_pattern),
                                type=MetricType.GAUGE,  # Default type
                                value=float(value),
                                timestamp=datetime.fromtimestamp(timestamp),
                                labels=metric_labels
                            ))
                    else:
                        timestamp, value = result['value']
                        metrics.append(Metric(
                            name=result['metric'].get('__name__', name_pattern),
                            type=MetricType.GAUGE,
                            value=float(value),
                            timestamp=datetime.fromtimestamp(timestamp),
                            labels=metric_labels
                        ))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error retrieving metrics: {e}")
            return []
    
    def create_dashboard(self, name: str, config: Dict[str, Any]) -> str:
        """Create a Grafana dashboard (if Grafana is configured)."""
        # This would integrate with Grafana API
        # For now, return a placeholder dashboard ID
        dashboard_id = f"permagraph-{name.lower().replace(' ', '-')}"
        self.logger.info(f"Dashboard created: {dashboard_id}")
        return dashboard_id
    
    def get_dashboard_url(self, dashboard_id: str) -> str:
        """Get URL for accessing dashboard."""
        # Assuming Grafana is running on port 3000
        return f"http://localhost:3000/d/{dashboard_id}"
    
    def _sanitize_metric_name(self, name: str) -> str:
        """Sanitize metric name for Prometheus."""
        # Replace invalid characters with underscores
        sanitized = name.replace('.', '_').replace('-', '_')
        # Ensure it starts with a letter or underscore
        if not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"permagraph_{sanitized}"
        return sanitized
    
    def _get_or_create_counter(self, name: str, labels: Dict[str, str]) -> Counter:
        """Get or create a Prometheus counter."""
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.counters:
            self.counters[key] = Counter(
                name, 
                f"PermaGraph counter metric: {name}",
                labelnames=list(labels.keys()),
                registry=self.registry
            )
        return self.counters[key].labels(**labels)
    
    def _get_or_create_gauge(self, name: str, labels: Dict[str, str]) -> Gauge:
        """Get or create a Prometheus gauge."""
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.gauges:
            self.gauges[key] = Gauge(
                name,
                f"PermaGraph gauge metric: {name}",
                labelnames=list(labels.keys()),
                registry=self.registry
            )
        return self.gauges[key].labels(**labels)
    
    def _get_or_create_histogram(self, name: str, labels: Dict[str, str]) -> Histogram:
        """Get or create a Prometheus histogram."""
        key = f"{name}_{hash(frozenset(labels.items()))}"
        if key not in self.histograms:
            self.histograms[key] = Histogram(
                name,
                f"PermaGraph histogram metric: {name}",
                labelnames=list(labels.keys()),
                registry=self.registry,
                buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
            )
        return self.histograms[key].labels(**labels)
    
    def _push_metrics(self):
        """Push metrics to Prometheus pushgateway."""
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=self.job_name,
                registry=self.registry
            )
        except Exception as e:
            self.logger.error(f"Error pushing metrics to gateway: {e}")