"""
PagerDuty alerting adapter for PermaGraph monitoring.
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from application.ports.alert_port import AlertPort
from domain.services.monitoring_service import Alert


class PagerDutyAlertAdapter(AlertPort):
    """Adapter for PagerDuty alerting integration."""
    
    def __init__(self, integration_key: str, api_token: Optional[str] = None):
        self.integration_key = integration_key
        self.api_token = api_token
        self.events_url = "https://events.pagerduty.com/v2/enqueue"
        self.api_url = "https://api.pagerduty.com"
        self.logger = logging.getLogger(__name__)
        
        # Alert severity mapping
        self.severity_mapping = {
            "critical": "critical",
            "warning": "warning", 
            "info": "info"
        }
    
    def send_alert(self, alert: Alert) -> None:
        """Send alert to PagerDuty."""
        try:
            payload = {
                "routing_key": self.integration_key,
                "event_action": "trigger",
                "dedup_key": alert.id,
                "payload": {
                    "summary": alert.message,
                    "source": alert.component,
                    "severity": self.severity_mapping.get(alert.severity, "warning"),
                    "timestamp": alert.timestamp.isoformat(),
                    "component": alert.component,
                    "group": "permagraph",
                    "class": "system_alert",
                    "custom_details": alert.details
                }
            }
            
            response = requests.post(
                self.events_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "success":
                self.logger.info(f"Alert sent to PagerDuty: {alert.id}")
            else:
                self.logger.error(f"PagerDuty API error: {result}")
                
        except Exception as e:
            self.logger.error(f"Error sending alert to PagerDuty: {e}")
    
    def resolve_alert(self, alert_id: str) -> None:
        """Resolve alert in PagerDuty."""
        try:
            payload = {
                "routing_key": self.integration_key,
                "event_action": "resolve",
                "dedup_key": alert_id
            }
            
            response = requests.post(
                self.events_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "success":
                self.logger.info(f"Alert resolved in PagerDuty: {alert_id}")
            else:
                self.logger.error(f"PagerDuty resolve error: {result}")
                
        except Exception as e:
            self.logger.error(f"Error resolving alert in PagerDuty: {e}")
    
    def configure_alert_rules(self, rules: List[Dict[str, Any]]) -> None:
        """Configure alerting rules in PagerDuty."""
        if not self.api_token:
            self.logger.warning("API token required for configuring alert rules")
            return
        
        try:
            headers = {
                "Authorization": f"Token token={self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.pagerduty+json;version=2"
            }
            
            for rule in rules:
                # Create or update event rule
                rule_payload = {
                    "event_rule": {
                        "conditions": rule.get("conditions", []),
                        "actions": rule.get("actions", []),
                        "disabled": rule.get("disabled", False)
                    }
                }
                
                response = requests.post(
                    f"{self.api_url}/event_rules",
                    json=rule_payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 201:
                    self.logger.info(f"Alert rule created: {rule.get('name', 'unnamed')}")
                else:
                    self.logger.error(f"Error creating alert rule: {response.text}")
                    
        except Exception as e:
            self.logger.error(f"Error configuring alert rules: {e}")
    
    def get_alert_history(self, component: Optional[str] = None,
                         severity: Optional[str] = None,
                         limit: int = 100) -> List[Alert]:
        """Get alert history from PagerDuty."""
        if not self.api_token:
            self.logger.warning("API token required for getting alert history")
            return []
        
        try:
            headers = {
                "Authorization": f"Token token={self.api_token}",
                "Accept": "application/vnd.pagerduty+json;version=2"
            }
            
            params = {
                "limit": limit,
                "sort_by": "created_at:desc"
            }
            
            if component:
                params["service_ids[]"] = component
            
            response = requests.get(
                f"{self.api_url}/incidents",
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            alerts = []
            
            for incident in data.get("incidents", []):
                alert = Alert(
                    id=incident["id"],
                    severity=incident.get("urgency", "info"),
                    component=incident.get("service", {}).get("summary", "unknown"),
                    message=incident.get("title", ""),
                    timestamp=datetime.fromisoformat(
                        incident["created_at"].replace("Z", "+00:00")
                    ),
                    resolved=incident["status"] == "resolved",
                    details={
                        "status": incident["status"],
                        "incident_number": incident["incident_number"],
                        "html_url": incident["html_url"]
                    }
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting alert history: {e}")
            return []


class SlackAlertAdapter(AlertPort):
    """Simple Slack alerting adapter as alternative to PagerDuty."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)
        
        # Emoji mapping for severity levels
        self.severity_emojis = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
    
    def send_alert(self, alert: Alert) -> None:
        """Send alert to Slack."""
        try:
            emoji = self.severity_emojis.get(alert.severity, "📢")
            
            payload = {
                "text": f"{emoji} PermaGraph Alert",
                "attachments": [
                    {
                        "color": self._get_color(alert.severity),
                        "fields": [
                            {
                                "title": "Component",
                                "value": alert.component,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert.message,
                                "short": False
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True
                            }
                        ],
                        "footer": "PermaGraph Monitoring",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            self.logger.info(f"Alert sent to Slack: {alert.id}")
            
        except Exception as e:
            self.logger.error(f"Error sending alert to Slack: {e}")
    
    def resolve_alert(self, alert_id: str) -> None:
        """Send resolution notification to Slack."""
        try:
            payload = {
                "text": f"✅ Alert Resolved: {alert_id}",
                "attachments": [
                    {
                        "color": "good",
                        "text": f"Alert {alert_id} has been resolved.",
                        "footer": "PermaGraph Monitoring",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            self.logger.info(f"Resolution sent to Slack: {alert_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending resolution to Slack: {e}")
    
    def configure_alert_rules(self, rules: List[Dict[str, Any]]) -> None:
        """Slack doesn't support rule configuration."""
        self.logger.info("Alert rule configuration not supported for Slack adapter")
    
    def get_alert_history(self, component: Optional[str] = None,
                         severity: Optional[str] = None,
                         limit: int = 100) -> List[Alert]:
        """Slack doesn't provide alert history API."""
        self.logger.info("Alert history not available for Slack adapter")
        return []
    
    def _get_color(self, severity: str) -> str:
        """Get color for Slack attachment based on severity."""
        colors = {
            "critical": "danger",
            "warning": "warning",
            "info": "good"
        }
        return colors.get(severity, "good")