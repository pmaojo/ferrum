"""
Customer Data Platform (CDP) Integration
Supports RudderStack and Segment integration.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class CDPIntegration:
    """Integration with Customer Data Platforms."""

    def __init__(
        self, provider: str, api_key: str, data_plane_url: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.data_plane_url = data_plane_url

        if self.provider == "rudderstack":
            self.base_url = data_plane_url or "https://api.rudderlabs.com"
        elif self.provider == "segment":
            self.base_url = "https://api.segment.io"
        else:
            raise ValueError(f"Unsupported CDP provider: {provider}")

    async def track_event(
        self, user_id: str, event: str, properties: Dict[str, Any]
    ) -> bool:
        """Track an event in the CDP."""
        try:
            payload = {
                "userId": user_id,
                "event": event,
                "properties": properties,
                "timestamp": datetime.utcnow().isoformat(),
                "context": {
                    "library": {"name": "graphrag-ecommerce", "version": "1.0.0"}
                },
            }

            if self.provider == "rudderstack":
                url = f"{self.base_url}/v1/track"
                headers = {
                    "Authorization": f"Basic {self.api_key}",
                    "Content-Type": "application/json",
                }
            else:  # segment
                url = f"{self.base_url}/v1/track"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info(f"Event {event} tracked successfully for user {user_id}")
                return True
            else:
                logger.error(
                    f"Failed to track event: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error tracking event in CDP: {str(e)}")
            return False

    async def identify_user(self, user_id: str, traits: Dict[str, Any]) -> bool:
        """Identify a user in the CDP."""
        try:
            payload = {
                "userId": user_id,
                "traits": traits,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self.provider == "rudderstack":
                url = f"{self.base_url}/v1/identify"
                headers = {
                    "Authorization": f"Basic {self.api_key}",
                    "Content-Type": "application/json",
                }
            else:  # segment
                url = f"{self.base_url}/v1/identify"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

            response = requests.post(url, json=payload, headers=headers)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error identifying user in CDP: {str(e)}")
            return False
