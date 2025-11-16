"""In-memory implementation of WebhookRepositoryPort."""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from application.ports import WebhookRepositoryPort
from domain.entities import Webhook


class InMemoryWebhookRepository(WebhookRepositoryPort):
    """Thread-safe in-memory repository for webhooks."""

    def __init__(self) -> None:
        self._webhooks: Dict[str, Webhook] = {}
        self._lock = threading.Lock()

    def create(self, webhook: Webhook) -> Webhook:
        with self._lock:
            self._webhooks[webhook.id] = webhook
        return webhook

    def update(self, webhook: Webhook) -> Webhook:
        with self._lock:
            if webhook.id not in self._webhooks:
                raise ValueError(f"Webhook {webhook.id} not found")
            self._webhooks[webhook.id] = webhook
        return webhook

    def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        with self._lock:
            return self._webhooks.get(webhook_id)

    def list_by_tenant(
        self, tenant_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Webhook], int]:
        with self._lock:
            items = [w for w in self._webhooks.values() if w.tenant_id == tenant_id]
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def delete_by_id(self, webhook_id: str) -> bool:
        with self._lock:
            return self._webhooks.pop(webhook_id, None) is not None
