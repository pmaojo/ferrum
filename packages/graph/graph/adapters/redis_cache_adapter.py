"""Redis-backed implementation of the CachePort protocol."""
from __future__ import annotations

import json
from typing import Any, Optional

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None  # type: ignore

from application.ports.base import CachePort


class RedisCacheAdapter(CachePort):
    """Simple cache adapter storing values in Redis.

    The adapter namespaces all keys by tenant to provide multi-tenant isolation.
    Values are JSON-serialised before storage to support complex Python types.
    """

    def __init__(self, *, url: str) -> None:
        if redis is None:
            raise ImportError("redis library is required for RedisCacheAdapter")
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def _format_key(self, tenant_id: str, key: str) -> str:
        return f"{tenant_id}:{key}"

    def get(self, *, key: str, tenant_id: str) -> Optional[Any]:
        data = self._client.get(self._format_key(tenant_id, key))
        if data is None:
            return None
        try:
            return json.loads(data)
        except Exception:
            return data

    def set(
        self,
        *,
        key: str,
        value: Any,
        tenant_id: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        data = json.dumps(value)
        if ttl_seconds is not None:
            self._client.setex(self._format_key(tenant_id, key), ttl_seconds, data)
        else:
            self._client.set(self._format_key(tenant_id, key), data)

    def delete(self, *, key: str, tenant_id: str) -> bool:
        return self._client.delete(self._format_key(tenant_id, key)) > 0

    def exists(self, *, key: str, tenant_id: str) -> bool:
        return self._client.exists(self._format_key(tenant_id, key)) == 1

    def clear(self, *, tenant_id: str) -> int:
        pattern = f"{tenant_id}:*"
        keys = list(self._client.scan_iter(match=pattern))
        if keys:
            self._client.delete(*keys)
        return len(keys)
