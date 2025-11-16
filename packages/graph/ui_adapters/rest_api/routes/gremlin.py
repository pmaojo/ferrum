"""Gremlin traversal endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from application.use_cases.execute_gremlin_query_use_case import (
    ExecuteGremlinQueryRequest,
    ExecuteGremlinQueryUseCase,
)
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container

router = APIRouter()


class GremlinQuery(BaseModel):
    query: str


@router.post("/api/gremlin")
def execute_gremlin_query(
    request: GremlinQuery,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    use_case = ExecuteGremlinQueryUseCase(container.graph_traversal)
    response = use_case.execute(ExecuteGremlinQueryRequest(query=request.query))
    return {"records": response.records}
