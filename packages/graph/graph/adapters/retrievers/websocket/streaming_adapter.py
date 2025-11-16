import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from adapters.strategies.event_handling import (
    CommunityUpdateEmitter,
    DefaultStrategy,
    EdgeAddedStrategy,
    EventHandlingContext,
    EventHandlingStrategy,
    NodeAddedStrategy,
    PathHighlightedStrategy,
)
from application.ports import ClusteringPort, GraphStreamPort, TracingPort
from domain.entities import GraphStreamEvent, GraphStreamEventType

from .client import WebSocketClient
from .client_manager import ClientManager
from .event_buffer import EventBuffer
from .exceptions import BufferOverflowError, StreamingException

logger = logging.getLogger(__name__)


class WebSocketGraphStreamAdapter(GraphStreamPort):
    """WebSocket-based graph stream adapter with buffering."""

    def __init__(
        self,
        tracing_adapter: Optional[TracingPort] = None,
        clustering_adapter: Optional[ClusteringPort] = None,
        buffer_size: int = 10000,
        flush_interval_ms: int = 100,
        max_batch_size: int = 1000,
        client_timeout_seconds: int = 300,
        enable_progressive_rendering: bool = True,
        community_threshold: int = 50000,
    ) -> None:
        self.tracing_adapter = tracing_adapter
        self.clustering_adapter = clustering_adapter
        self.buffer = EventBuffer(
            max_size=buffer_size,
            flush_interval_ms=flush_interval_ms,
            max_batch_size=max_batch_size,
        )
        self.client_timeout_seconds = client_timeout_seconds
        self.enable_progressive_rendering = enable_progressive_rendering
        self.community_threshold = community_threshold

        self._community_counters: Dict[str, Dict[str, Dict[str, int]]] = {}
        self._community_emitter = CommunityUpdateEmitter(self._community_counters)

        self._strategies: Dict[GraphStreamEventType, EventHandlingStrategy] = {
            GraphStreamEventType.NODE_ADDED: NodeAddedStrategy(),
            GraphStreamEventType.EDGE_ADDED: EdgeAddedStrategy(),
            GraphStreamEventType.PATH_HIGHLIGHTED: PathHighlightedStrategy(),
            GraphStreamEventType.COMMUNITY_UPDATED: DefaultStrategy(),
        }

        self.client_manager = ClientManager(tracer=tracing_adapter)
        self.graph_metadata: Dict[str, Dict[str, Any]] = {}

        self._start_background_tasks()

    # ---------------------------------------------------------------
    @property
    def clients(self) -> Dict[str, WebSocketClient]:
        return self.client_manager.clients

    @property
    def clients_by_tenant(self) -> Dict[str, Set[str]]:
        return self.client_manager.clients_by_tenant

    # Public API
    # ---------------------------------------------------------------
    def send_event(self, *, event: GraphStreamEvent) -> None:
        try:
            if self.tracing_adapter:
                self.tracing_adapter.record_metric(
                    name="graph_stream_events",
                    value=1.0,
                    tenant_id=event.tenant_id,
                    event_type=event.event_type.name,
                    kg_id=event.kg_id,
                )

            ctx = EventHandlingContext(
                buffer=self.buffer,
                flush=self._flush_buffer,
                clustering=self.clustering_adapter,
                community_counters=self._community_counters,
            )

            strategy = self._strategies.get(event.event_type, DefaultStrategy())
            if event.event_type == GraphStreamEventType.PATH_HIGHLIGHTED:
                strategy.handle(event, ctx)
            elif (
                self.enable_progressive_rendering
                and self._should_use_progressive_rendering(event)
            ):
                strategy.handle(event, ctx)
            else:
                DefaultStrategy().handle(event, ctx)

            if self.buffer.should_flush(event.tenant_id):
                self._flush_buffer(event.tenant_id)

        except BufferOverflowError as exc:
            logger.warning("Buffer overflow detected: %s", exc)
            self._flush_buffer(event.tenant_id)
            self.buffer.add_event(event)
            if self.tracing_adapter:
                self.tracing_adapter.record_metric(
                    name="buffer_overflow_count",
                    value=1.0,
                    tenant_id=event.tenant_id,
                    kg_id=event.kg_id,
                )
        except Exception as exc:
            logger.error("Failed to send event: %s", exc, exc_info=True)
            raise StreamingException(
                message=f"Failed to send event: {exc}",
                error_code="EVENT_SEND_ERROR",
                context={
                    "tenant_id": event.tenant_id,
                    "kg_id": event.kg_id,
                    "event_type": event.event_type.name,
                },
            ) from exc

    def send_batch(
        self, *, events: List[GraphStreamEvent], buffer_size: int = 1000
    ) -> None:
        if buffer_size <= 0:
            raise ValueError("buffer_size must be positive")
        try:
            events_by_tenant: Dict[str, List[GraphStreamEvent]] = {}
            for event in events:
                events_by_tenant.setdefault(event.tenant_id, []).append(event)
            for tenant_id, tenant_events in events_by_tenant.items():
                for i in range(0, len(tenant_events), buffer_size):
                    batch = tenant_events[i : i + buffer_size]
                    if self.tracing_adapter:
                        self.tracing_adapter.record_metric(
                            name="graph_stream_batch_size",
                            value=len(batch),
                            tenant_id=tenant_id,
                        )
                    self._send_batch_to_clients(tenant_id, batch)
        except Exception as exc:
            logger.error("Failed to send batch: %s", exc, exc_info=True)
            raise StreamingException(
                message=f"Failed to send batch: {exc}",
                error_code="BATCH_SEND_ERROR",
                context={"batch_size": len(events)},
            ) from exc

    def register_client(
        self,
        client_id: str,
        tenant_id: str,
        send_callback: Callable[[str], None],
        subscribed_kg_ids: Optional[Set[str]] = None,
    ) -> None:
        self.client_manager.register(
            client_id=client_id,
            tenant_id=tenant_id,
            send_callback=send_callback,
            subscribed_kg_ids=subscribed_kg_ids,
        )

    def unregister_client(self, client_id: str) -> None:
        self.client_manager.unregister(client_id)

    def update_client_subscriptions(
        self, client_id: str, subscribed_kg_ids: Set[str]
    ) -> None:
        self.client_manager.update_subscriptions(client_id, subscribed_kg_ids)

    def set_graph_metadata(
        self,
        kg_id: str,
        tenant_id: str,
        node_count: int,
        edge_count: int,
        has_communities: bool = False,
    ) -> None:
        self.graph_metadata[f"{tenant_id}:{kg_id}"] = {
            "node_count": node_count,
            "edge_count": edge_count,
            "has_communities": has_communities,
            "updated_at": datetime.now().isoformat(),
        }

    # ---------------------------------------------------------------
    # Background tasks
    # ---------------------------------------------------------------
    def _start_background_tasks(self) -> None:
        threading.Thread(target=self._buffer_flush_loop, daemon=True).start()
        threading.Thread(target=self._client_cleanup_loop, daemon=True).start()

    def _buffer_flush_loop(self) -> None:
        while True:
            try:
                for tenant_id in list(self.buffer.buffer.keys()):
                    if self.buffer.should_flush(tenant_id):
                        self._flush_buffer(tenant_id)
                time.sleep(self.buffer.flush_interval_ms / 1000)
            except Exception as exc:  # pragma: no cover - log and continue
                logger.error("Error in buffer flush loop: %s", exc, exc_info=True)
                time.sleep(1)

    def _client_cleanup_loop(self) -> None:
        while True:
            try:
                self.client_manager.remove_inactive(self.client_timeout_seconds)
                time.sleep(60)
            except Exception as exc:  # pragma: no cover - log and continue
                logger.error("Error in client cleanup loop: %s", exc, exc_info=True)
                time.sleep(60)

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------
    def _flush_buffer(self, tenant_id: str) -> None:
        self._community_emitter.enqueue_updates(tenant_id, self.buffer)
        batch = self.buffer.get_batch(tenant_id)
        if not batch:
            return
        self._send_batch_to_clients(tenant_id, batch)

    def _send_batch_to_clients(
        self, tenant_id: str, events: List[GraphStreamEvent]
    ) -> None:
        if not events:
            return
        events_by_kg: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            kg_id = event.kg_id
            events_by_kg.setdefault(kg_id, []).append(
                {
                    "event_type": event.event_type.name,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                    "kg_id": event.kg_id,
                }
            )
        for client in self.client_manager.clients_for_tenant(tenant_id):
            if not client.is_active:
                continue
            client_events: List[Dict[str, Any]] = []
            for kg_id, kg_events in events_by_kg.items():
                if client.is_subscribed_to(kg_id):
                    client_events.extend(kg_events)
            if client_events:
                message = {"type": "graph_events", "events": client_events}
                client.send(message)

    def _should_use_progressive_rendering(self, event: GraphStreamEvent) -> bool:
        if not self.enable_progressive_rendering:
            return False
        graph_key = f"{event.tenant_id}:{event.kg_id}"
        if graph_key not in self.graph_metadata:
            return False
        metadata = self.graph_metadata[graph_key]
        return metadata["node_count"] > self.community_threshold
