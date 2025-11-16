"""
Metrics Port for collecting and reporting system metrics.

This port defines the interface for collecting performance metrics,
health statistics, and other operational data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class MetricsPort(ABC):
    """Port for collecting and reporting metrics"""
    
    @abstractmethod
    def record_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default"
    ) -> None:
        """
        Record a counter metric
        
        Args:
            name: Metric name
            value: Counter value to add
            labels: Optional labels/tags
            tenant_id: Tenant identifier
        """
        ...
    
    @abstractmethod
    def record_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default"
    ) -> None:
        """
        Record a gauge metric
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels/tags
            tenant_id: Tenant identifier
        """
        ...
    
    @abstractmethod
    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default"
    ) -> None:
        """
        Record a histogram metric
        
        Args:
            name: Metric name
            value: Measured value
            labels: Optional labels/tags
            tenant_id: Tenant identifier
        """
        ...
    
    @abstractmethod
    def record_timing(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: str = "default"
    ) -> None:
        """
        Record a timing metric
        
        Args:
            name: Metric name
            duration_ms: Duration in milliseconds
            labels: Optional labels/tags
            tenant_id: Tenant identifier
        """
        ...
    
    @abstractmethod
    def get_metrics(
        self,
        name_pattern: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Get collected metrics
        
        Args:
            name_pattern: Optional pattern to filter metrics
            tenant_id: Tenant identifier
            
        Returns:
            List of metric data
        """
        ...
    
    @abstractmethod
    def get_health_metrics(
        self,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get system health metrics
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Health metrics data
        """
        ...
