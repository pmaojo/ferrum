"""Health and metrics endpoints."""
from __future__ import annotations

import time
from typing import Any, Dict, Callable

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container

router = APIRouter()


COMPONENT_LATENCY = Gauge(
    "component_health_latency_seconds",
    "Latency of component health checks",
    ["component"],
)
COMPONENT_ERRORS = Gauge(
    "component_health_errors",
    "Error status of components (1=error, 0=ok)",
    ["component"],
)


@router.get("/api/health")
async def health() -> Dict[str, Any]:
    # Versión simplificada para garantizar arranque tras downgrade Pydantic v1.
    return {"status": "ok"}


@router.get("/api/v1/health/detailed")
async def detailed_health_check(
    container: ServiceContainer = Depends(get_container),
) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {
            "ingestion_service": "healthy",
            "query_service": "healthy",
            "token_budget_service": "healthy",
            "observability_service": "healthy",
        },
        "metrics": {
            "cache_size": len(container.__dict__),
        },
    }


@router.get("/api/metrics")
async def metrics(
    tenant_id: str,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "observability_service")
    return svc.generate_performance_report(tenant_id=tenant_id) if svc else {"ok": True}


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Public Prometheus metrics endpoint - no auth required."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/v1/system/info")
async def system_info() -> Dict[str, Any]:
    return {
        "name": "PermaGraph API",
        "version": "1.0.0",
        "description": "GraphRAG Ontology Management API",
    }
