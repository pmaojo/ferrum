"""Cache management utilities and endpoints."""
from __future__ import annotations

import time
from typing import Dict

from fastapi import APIRouter, Depends
try:
    import cachetools
except Exception:  # pragma: no cover - fallback stub
    from infrastructure.stubs import cachetools

from ui_adapters.rest_api.dependencies import get_container

router = APIRouter()

# Cache for frequently accessed data
cache = cachetools.TTLCache(maxsize=1000, ttl=300)


@router.post("/api/v1/cache/clear")
async def clear_cache() -> Dict[str, float]:
    cache.clear()
    return {"timestamp": time.time()}


@router.get("/api/v1/cache/stats")
async def cache_stats() -> Dict[str, int]:
    return {
        "size": len(cache),
        "max_size": cache.maxsize,
        "ttl": cache.ttl,
        "hits": getattr(cache, "hits", 0),
        "misses": getattr(cache, "misses", 0),
    }
