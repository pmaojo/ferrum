from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, Optional

from application.ports import ClusteringPort
from domain.entities import GraphStreamEvent, GraphStreamEventType

if TYPE_CHECKING:  # pragma: no cover
    from adapters.retrievers.websocket_graph_stream_adapter import (
        BufferOverflowError,
        EventBuffer,
    )


@dataclass
class EventHandlingContext:
    """Context object passed to event handling strategies."""

    buffer: "EventBuffer"
    flush: Callable[[str], None]
    clustering: Optional[ClusteringPort]
    community_counters: Dict[str, Dict[str, Dict[str, int]]]


class EventHandlingStrategy(ABC):
    """Strategy interface for handling graph stream events."""

    @abstractmethod
    def handle(self, event: GraphStreamEvent, ctx: EventHandlingContext) -> None:
        """Process the provided event using the given context."""
        ...


class DefaultStrategy(EventHandlingStrategy):
    """Default strategy that simply buffers events."""

    def handle(self, event: GraphStreamEvent, ctx: EventHandlingContext) -> None:
        ctx.buffer.add_event(event)


class NodeAddedStrategy(EventHandlingStrategy):
    """Strategy for NODE_ADDED events with community awareness."""

    def handle(self, event: GraphStreamEvent, ctx: EventHandlingContext) -> None:
        community_id = event.data.get("community_id")
        if community_id:
            counters = ctx.community_counters.setdefault(
                event.tenant_id, {}
            ).setdefault(
                community_id, {"node_count": 0, "edge_count": 0, "kg_id": event.kg_id}
            )
            counters["node_count"] += 1
        ctx.buffer.add_event(event)


class EdgeAddedStrategy(EventHandlingStrategy):
    """Strategy for EDGE_ADDED events with community awareness."""

    def handle(self, event: GraphStreamEvent, ctx: EventHandlingContext) -> None:
        community_id = event.data.get("community_id")
        if community_id:
            counters = ctx.community_counters.setdefault(
                event.tenant_id, {}
            ).setdefault(
                community_id, {"node_count": 0, "edge_count": 0, "kg_id": event.kg_id}
            )
            counters["edge_count"] += 1
        ctx.buffer.add_event(event)


class PathHighlightedStrategy(EventHandlingStrategy):
    """Strategy for PATH_HIGHLIGHTED events."""

    def handle(self, event: GraphStreamEvent, ctx: EventHandlingContext) -> None:
        ctx.buffer.add_event_front(event)
        ctx.flush(event.tenant_id)


class CommunityUpdateEmitter:
    """Utility to emit community update events on buffer flush."""

    def __init__(self, counters: Dict[str, Dict[str, Dict[str, int]]]):
        self._counters = counters

    def enqueue_updates(self, tenant_id: str, buffer: "EventBuffer") -> None:
        if tenant_id not in self._counters:
            return
        updates = self._counters[tenant_id]
        for community_id, data in updates.items():
            if data["node_count"] == 0 and data["edge_count"] == 0:
                continue
            event = GraphStreamEvent(
                event_type=GraphStreamEventType.COMMUNITY_UPDATED,
                data={
                    "community_id": community_id,
                    "node_count": data["node_count"],
                    "edge_count": data["edge_count"],
                },
                timestamp=datetime.now(),
                kg_id=data.get("kg_id", community_id.split(":")[0]),
                tenant_id=tenant_id,
            )
            try:
                buffer.add_event_front(event)
            except BufferOverflowError:
                # Drop update if buffer is full to avoid blocking flush
                pass
            data["node_count"] = 0
            data["edge_count"] = 0
