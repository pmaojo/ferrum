import time
from typing import Callable, Dict, List, Optional, Set

from application.ports import TracingPort

from .client import WebSocketClient


class ClientManager:
    """Manage connected WebSocket clients."""

    def __init__(self, tracer: Optional[TracingPort] = None):
        self._tracer = tracer
        self._clients: Dict[str, WebSocketClient] = {}
        self._clients_by_tenant: Dict[str, Set[str]] = {}

    @property
    def clients(self) -> Dict[str, WebSocketClient]:
        return self._clients

    @property
    def clients_by_tenant(self) -> Dict[str, Set[str]]:
        return self._clients_by_tenant

    def register(
        self,
        client_id: str,
        tenant_id: str,
        send_callback: Callable[[str], None],
        subscribed_kg_ids: Optional[Set[str]] = None,
    ) -> None:
        if client_id in self._clients:
            raise ValueError(f"Client {client_id} already registered")
        client = WebSocketClient(client_id, tenant_id, send_callback, subscribed_kg_ids)
        self._clients[client_id] = client
        self._clients_by_tenant.setdefault(tenant_id, set()).add(client_id)
        if self._tracer:
            self._tracer.record_metric(
                name="websocket_clients_total",
                value=len(self._clients),
                tenant_id=tenant_id,
            )

    def unregister(self, client_id: str) -> None:
        if client_id not in self._clients:
            raise ValueError(f"Client {client_id} not registered")
        tenant_id = self._clients[client_id].tenant_id
        del self._clients[client_id]
        if tenant_id in self._clients_by_tenant:
            self._clients_by_tenant[tenant_id].discard(client_id)
            if not self._clients_by_tenant[tenant_id]:
                del self._clients_by_tenant[tenant_id]

    def update_subscriptions(self, client_id: str, subscribed_kg_ids: Set[str]) -> None:
        if client_id not in self._clients:
            raise ValueError(f"Client {client_id} not registered")
        self._clients[client_id].subscribed_kg_ids = subscribed_kg_ids

    def clients_for_tenant(self, tenant_id: str) -> List[WebSocketClient]:
        ids = self._clients_by_tenant.get(tenant_id, set())
        return [self._clients[cid] for cid in ids if cid in self._clients]

    def remove_inactive(self, timeout_seconds: int) -> None:
        current = time.time()
        for client_id in list(self._clients.keys()):
            client = self._clients.get(client_id)
            if client and (current - client.last_activity) > timeout_seconds:
                try:
                    self.unregister(client_id)
                except ValueError:
                    pass
