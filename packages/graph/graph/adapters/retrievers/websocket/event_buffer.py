import time
from collections import deque
from typing import Dict, List

from domain.entities import GraphStreamEvent

from .exceptions import BufferOverflowError


class EventBuffer:
    """Buffer for batching graph stream events."""

    def __init__(
        self,
        max_size: int = 10000,
        flush_interval_ms: int = 100,
        max_batch_size: int = 1000,
    ):
        self.buffer: Dict[str, deque[GraphStreamEvent]] = {}
        self.max_size = max_size
        self.flush_interval_ms = flush_interval_ms
        self.max_batch_size = max_batch_size
        self.last_flush_time: Dict[str, float] = {}

    def add_event(self, event: GraphStreamEvent) -> bool:
        tenant_id = event.tenant_id
        if tenant_id not in self.buffer:
            self.buffer[tenant_id] = deque(maxlen=self.max_size)
            self.last_flush_time[tenant_id] = time.time()
        if len(self.buffer[tenant_id]) >= self.max_size:
            raise BufferOverflowError(
                buffer_size=len(self.buffer[tenant_id]),
                context={
                    "tenant_id": tenant_id,
                    "kg_id": event.kg_id,
                    "event_type": event.event_type.name,
                },
            )
        self.buffer[tenant_id].append(event)
        return True

    def add_event_front(self, event: GraphStreamEvent) -> bool:
        tenant_id = event.tenant_id
        if tenant_id not in self.buffer:
            self.buffer[tenant_id] = deque(maxlen=self.max_size)
            self.last_flush_time[tenant_id] = time.time()
        if len(self.buffer[tenant_id]) >= self.max_size:
            raise BufferOverflowError(
                buffer_size=len(self.buffer[tenant_id]),
                context={
                    "tenant_id": tenant_id,
                    "kg_id": event.kg_id,
                    "event_type": event.event_type.name,
                },
            )
        self.buffer[tenant_id].appendleft(event)
        return True

    def should_flush(self, tenant_id: str) -> bool:
        if tenant_id not in self.buffer:
            return False
        if not self.buffer[tenant_id]:
            return False
        current_time = time.time()
        time_since_last_flush = (current_time - self.last_flush_time[tenant_id]) * 1000
        return time_since_last_flush >= self.flush_interval_ms

    def get_batch(self, tenant_id: str) -> List[GraphStreamEvent]:
        if tenant_id not in self.buffer:
            return []
        batch = []
        while self.buffer[tenant_id] and len(batch) < self.max_batch_size:
            batch.append(self.buffer[tenant_id].popleft())
        self.last_flush_time[tenant_id] = time.time()
        return batch
