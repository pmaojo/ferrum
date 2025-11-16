"""Token budget management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import SetBudgetRequest, TokenUsageRequest

router = APIRouter()


@router.post("/api/token-budget/track")
async def track_usage(
    request: TokenUsageRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "token_budget_service")
    return svc.track_usage(
        tenant_id=request.tenant_id,
        tokens=request.tokens,
        model=request.model,
        operation_type=request.operation_type,
        cost_usd=request.cost_usd,
        metadata=request.metadata,
    )


@router.get("/api/token-budget/{tenant_id}")
async def get_usage(
    tenant_id: str,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "token_budget_service")
    return svc.get_tenant_usage(tenant_id=tenant_id)


@router.get("/api/token-budget")
async def get_default_usage(
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Get token budget for default tenant."""
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "token_budget_service")
    return svc.get_tenant_usage(tenant_id="default")


@router.post("/api/token-budget/budget")
async def set_budget(
    request: SetBudgetRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "token_budget_service")
    return svc.set_tenant_budget(
        tenant_id=request.tenant_id,
        monthly_budget_usd=request.monthly_budget_usd,
        alert_threshold_percent=request.alert_threshold_percent,
        enable_degradation=request.enable_degradation,
    )
