"""Windmill MCP message bus adapter using Server-Sent Events."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

import httpx

from application.ports import TracingPort
from application.ports.messaging import MessageBusPort
from domain.exceptions import PublishError, SubscriptionError

logger = logging.getLogger(__name__)


class WindmillMCPAdapter(MessageBusPort):
    """Message bus adapter that communicates with Windmill MCP using SSE."""

    def __init__(
        self,
        *,
        base_url: str,
        token: Optional[str] = None,
        tracer: Optional[TracingPort] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.tracer = tracer
        self._client = http_client or httpx.Client(timeout=None)
        self._threads: Dict[tuple[str, str], threading.Thread] = {}

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def publish(
        self,
        *,
        topic: str,
        message: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        tenant_id: str,
    ) -> None:
        url = f"{self.base_url}/publish"
        payload = {"topic": topic, "message": message, "tenant_id": tenant_id}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        span = None
        if self.tracer:
            span = self.tracer.start_span(
                name="windmill.publish", tenant_id=tenant_id, topic=topic
            )
        try:
            response = self._client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to publish to %s: %s", topic, exc, exc_info=True)
            raise PublishError("Failed to publish message", topic=topic) from exc
        finally:
            if span and hasattr(span, "end"):
                span.end()

    def _listen(
        self,
        *,
        topic: str,
        tenant_id: str,
        handler: Callable[[Dict[str, Any]], None],
    ) -> None:
        url = f"{self.base_url}/subscribe"
        params = {"topic": topic, "tenant_id": tenant_id}
        try:
            with self._client.stream(
                "GET", url, params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode())
                        handler(data)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.error(
                            "Handler error for topic %s: %s", topic, exc, exc_info=True
                        )
        except Exception as exc:
            logger.error("Subscription failed for %s: %s", topic, exc, exc_info=True)
            raise SubscriptionError("Failed to subscribe", topic=topic) from exc

    def subscribe(
        self,
        *,
        topic: str,
        handler: Callable[[Dict[str, Any]], None],
        tenant_id: str,
    ) -> None:
        if not callable(handler):
            raise ValueError("handler must be callable")
        key = (topic, tenant_id)
        if key in self._threads:
            return
        thread = threading.Thread(
            target=self._listen,
            kwargs={"topic": topic, "tenant_id": tenant_id, "handler": handler},
            daemon=True,
        )
        self._threads[key] = thread
        thread.start()
