"""
Alert Port for sending alerts and notifications.

This port defines the interface for sending alerts about system health,
performance issues, and other important events.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertPort(ABC):
    """Port for sending alerts and notifications"""
    
    @abstractmethod
    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default"
    ) -> bool:
        """
        Send an alert notification
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            metadata: Additional metadata
            tenant_id: Tenant identifier
            
        Returns:
            True if alert was sent successfully
        """
        ...
    
    def send_health_alert(
        self,
        component: str,
        status: str,
        details: Dict[str, Any],
        tenant_id: str = "default"
    ) -> bool:
        """
        Send a health status alert
        
        Args:
            component: Component name
            status: Health status
            details: Health check details
            tenant_id: Tenant identifier
            
        Returns:
            True if alert was sent successfully
        """
        ...
    
    def send_performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        tenant_id: str = "default"
    ) -> bool:
        """
        Send a performance threshold alert
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            threshold: Threshold that was exceeded
            tenant_id: Tenant identifier
            
        Returns:
            True if alert was sent successfully
        """
        ...
