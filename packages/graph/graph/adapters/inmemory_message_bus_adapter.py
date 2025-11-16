from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional

from application.ports import TracingPort
from application.ports.messaging import MessageBusPort

logger = logging.getLogger(__name__)


class InMemoryMessageBusAdapter(MessageBusPort):
    """Simple in-memory implementation of :class:`MessageBusPort`."""

    def __init__(
        self,
        tracer: Optional[TracingPort] = None,
        *,
        ttl_seconds: Optional[float] = None,
        max_entries: Optional[int] = None,
    ) -> None:
        self._tracer = tracer
        self._subscribers: Dict[
            str, Dict[str, List[Callable[[Dict[str, Any]], None]]]
        ] = {}
        self._idempotency: Dict[str, OrderedDict[str, float]] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries

    def _evict(self, processed: "OrderedDict[str, float]", now: float) -> None:
        if self._ttl_seconds is not None:
            ttl = self._ttl_seconds
            expired = []
            for key, ts in processed.items():
                if now - ts >= ttl:
                    expired.append(key)
                else:
                    break
            for key in expired:
                processed.pop(key, None)

        if self._max_entries is not None:
            while len(processed) > self._max_entries:
                processed.popitem(last=False)

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
                name="message_bus.publish", tenant_id=tenant_id, topic=topic
            )
        try:
            handlers: List[Callable[[Dict[str, Any]], None]] = []
            with self._lock:
                processed = self._idempotency.setdefault(tenant_id, OrderedDict())
                now = time.monotonic()
                self._evict(processed, now)
                if idempotency_key:
                    unique_key = f"{topic}:{idempotency_key}"
                    if unique_key in processed:
                        logger.debug(
                            "Duplicate message skipped for topic %s",
                            topic,
                        )
                        return
                    processed[unique_key] = now
                    self._evict(processed, now)
                handlers = list(
                    self._subscribers.get(tenant_id, {}).get(
                        topic,
                        [],
                    )
                )
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:  # pragma: no cover - defensive
                    logger.error(
                        "Subscriber error on topic %s: %s",
                        topic,
                        str(e),
                        exc_info=True,
                    )
        finally:
            if span and hasattr(span, "end"):
                span.end()

    def subscribe(
        self,
        *,
        topic: str,
        handler: Callable[[Dict[str, Any]], None],
        tenant_id: str,
    ) -> None:
        if not callable(handler):
            raise ValueError("handler must be callable")
        with self._lock:
            tenant_topics = self._subscribers.setdefault(tenant_id, {})
            handlers = tenant_topics.setdefault(topic, [])
            handlers.append(handler)

    async def publish_async(
        self,
        *,
        topic: str,
        message: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        tenant_id: str,
    ) -> None:
        """Asynchronously publish a message using a thread executor."""

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.publish(
                topic=topic,
                message=message,
                idempotency_key=idempotency_key,
                tenant_id=tenant_id,
            ),
        )

    async def subscribe_async(
        self,
        *,
        topic: str,
        handler: Callable[[Dict[str, Any]], None],
        tenant_id: str,
    ) -> None:
        """Asynchronously register a subscriber in a thread executor."""

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.subscribe(topic=topic, handler=handler, tenant_id=tenant_id),
        )
