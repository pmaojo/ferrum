from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import requests

from application.ports import TracingPort
from application.ports.messaging import MessageBusPort
from domain.exceptions import SubscriptionError

logger = logging.getLogger(__name__)


class WindmillMessageBusAdapter(MessageBusPort):
    """Message bus adapter for publishing events to a Windmill deployment.

    The HTTP API offered by Windmill only exposes a ``/publish`` endpoint and
    lacks a server-side subscription mechanism. If subscription capabilities are
    required, use :class:`~adapters.windmill_mcp_adapter.WindmillMCPAdapter`,
    which communicates with Windmill's MCP using Server-Sent Events (SSE).
    """

    def __init__(
        self, base_url: str, api_key: str, tracer: Optional[TracingPort] = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._tracer = tracer

    def publish(
        self,
        *,
        topic: str,
        message: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        tenant_id: str,
    ) -> None:
        span = None
        if self._tracer:
            span = self._tracer.start_span(
                name="windmill.publish", tenant_id=tenant_id, topic=topic
            )
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            payload = {
                "topic": topic,
                "message": message,
                "idempotency_key": idempotency_key,
                "tenant_id": tenant_id,
            }
            requests.post(
                f"{self._base_url}/publish", json=payload, headers=headers, timeout=5
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.error("Failed to publish message to Windmill: %s", exc)
        finally:
            if span and hasattr(span, "end"):
                span.end()

    def subscribe(
        self, *, topic: str, handler: Callable[[Dict[str, Any]], None], tenant_id: str
    ) -> None:
        """Windmill's HTTP message bus cannot deliver subscriptions.

        Args:
            topic: Topic name that would be subscribed to.
            handler: Callable that would process incoming messages.
            tenant_id: Tenant associated with the subscription.

        Raises:
            SubscriptionError: Always raised to inform users that the Windmill
                message bus lacks subscription support. Use
                :class:`~adapters.windmill_mcp_adapter.WindmillMCPAdapter` for
                subscription capabilities.
        """

        raise SubscriptionError(
            "Windmill message bus does not support subscriptions; "
            "use WindmillMCPAdapter for SSE subscriptions.",
            topic=topic,
        )
