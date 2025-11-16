"""Synchronization routes for initializing and syncing triples."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import SyncInitRequest, SyncRequest

router = APIRouter()


@router.post("/api/v1/init")
async def init_sync(
    request: SyncInitRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Persist the initial project snapshot."""
    from application.services import synchronization_bridge

    return synchronization_bridge.persist_initial_snapshot(request.project_path)


@router.post("/api/v1/sync")
async def sync(
    request: SyncRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Synchronize triples according to mode."""
    from application.services import synchronization_bridge

    triples = [t.model_dump() for t in request.triples]
    return synchronization_bridge.synchronize(request.mode, triples)
