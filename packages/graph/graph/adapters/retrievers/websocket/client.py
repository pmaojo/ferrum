import json
import logging
import time
from typing import Any, Callable, Optional, Set

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Represents a connected WebSocket client with tenant isolation."""

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        send_callback: Callable[[str], None],
        subscribed_kg_ids: Optional[Set[str]] = None,
    ):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.send_callback = send_callback
        self.subscribed_kg_ids = subscribed_kg_ids or set()
        self.last_activity = time.time()
        self.is_active = True

    def send(self, data: dict[str, Any]) -> bool:
        if not self.is_active:
            return False
        try:
            json_data = json.dumps(data)
            self.send_callback(json_data)
            self.last_activity = time.time()
            return True
        except Exception as exc:  # pragma: no cover - logging only
            logger.error("Failed to send data to client %s: %s", self.client_id, exc)
            self.is_active = False
            return False

    def is_subscribed_to(self, kg_id: str) -> bool:
        if not self.subscribed_kg_ids:
            return True
        return kg_id in self.subscribed_kg_ids
