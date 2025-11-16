"""Graph visualization endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container

router = APIRouter()


@router.get("/api/visualization/overview/{kg_id}")
async def graph_overview(
    kg_id: str,
    tenant_id: str,
    algorithm: str = "louvain",
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Return graph overview data for a knowledge graph."""
    visualizer = container.graph_visualizer
    if visualizer is None:
        raise HTTPException(status_code=501, detail="Visualization service not configured")
    return visualizer.render_graph_overview(
        kg_id=kg_id, tenant_id=tenant_id, algorithm=algorithm
    )


@router.get("/api/visualization/community/{community_id}")
async def community_detail(
    community_id: str,
    tenant_id: str,
    include_neighbors: bool = False,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Return detailed community visualization data."""
    visualizer = container.graph_visualizer
    if visualizer is None:
        raise HTTPException(status_code=501, detail="Visualization service not configured")
    return visualizer.render_community_detail(
        community_id=community_id,
        tenant_id=tenant_id,
        include_neighbors=include_neighbors,
    )
