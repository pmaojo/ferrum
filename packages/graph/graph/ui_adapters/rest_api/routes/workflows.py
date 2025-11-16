"""Workflow management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import (
    WorkflowExecuteRequest,
    WorkflowRegisterRequest,
)

router = APIRouter()


@router.post("/api/workflows/register")
async def register_workflow(
    request: WorkflowRegisterRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "workflow_orchestrator")
    svc.register_workflow(
        workflow_id=request.workflow_id,
        steps=request.steps,
        framework=request.framework,
        tenant_id=request.tenant_id,
    )
    return {"workflow_id": request.workflow_id, "status": "registered"}


@router.post("/api/workflows/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "workflow_orchestrator")
    return svc.execute_workflow(
        workflow_id=request.workflow_id,
        input_data=request.input_data,
        tenant_id=request.tenant_id,
    )


@router.get("/api/workflows")
async def list_workflows(
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """List all registered workflows."""
    return {"workflows": []}  # Return empty list for now
