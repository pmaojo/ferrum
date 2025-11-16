"""Query related API endpoints."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from domain.auth import Role
from ui_adapters.rest_api.server import require_role

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.routes.cache import cache
from ui_adapters.rest_api.models import QueryRequest, SparqlExecuteRequest

router = APIRouter(dependencies=[Depends(require_role(Role.QUERY))])

QUERIES_DIR = Path(__file__).resolve().parents[3] / "application" / "queries"


async def _execute_query(
    query_request: QueryRequest,
    container: ServiceContainer,
    *,
    use_cache: bool = False,
) -> Any:
    """Common logic for natural language queries."""
    cache_key = None
    if use_cache:
        cache_key = hashlib.sha256(
            f"{query_request.question}:{query_request.kg_id}:{query_request.tenant_id}".encode()
        ).hexdigest()
        if cache_key in cache:
            return cache[cache_key]

    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "query_service")
    result = svc.execute_natural_language_query(
        question=query_request.question,
        kg_id=query_request.kg_id,
        tenant_id=query_request.tenant_id,
        user_id=query_request.user_id,
        include_explanation=query_request.include_explanation,
        include_subgraph=query_request.include_subgraph,
        max_results=query_request.max_results,
        query_opts=query_request.query_opts,
    )

    if use_cache and not result.get("metadata", {}).get("error", False):
        cache[cache_key] = result

    return result


@router.post("/api/query", deprecated=True)
async def query(
    request: QueryRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    return await _execute_query(request, container)


@router.post("/api/v1/query")
async def query_v1(
    request: Request,
    query_request: QueryRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    return await _execute_query(query_request, container, use_cache=True)


@router.get("/api/v1/queries")
async def list_queries() -> Any:
    """Return available SPARQL preset queries.

    Each preset is loaded from the ``application/queries`` directory and
    returned with its identifier and raw SPARQL text.
    """
    presets: list[dict[str, str]] = []
    if QUERIES_DIR.exists():
        for path in QUERIES_DIR.glob("*.rq"):
            presets.append({"id": path.stem, "sparql": path.read_text()})
    return {"queries": presets}


@router.post("/api/v1/queries/{query_id}/execute")
async def execute_query_preset(
    query_id: str,
    request: SparqlExecuteRequest,
    container: ServiceContainer = Depends(get_container),
) -> Any:
    """Execute a SPARQL preset and return its results."""
    file_path = QUERIES_DIR / f"{query_id}.rq"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Query not found")

    sparql = file_path.read_text()
    from ui_adapters.rest_api.dependencies import resolve
    svc = resolve(container, "query_service")
    result = svc.execute_sparql(
        tenant_id=request.tenant_id, query=sparql
    )

    # Ensure a consistent response structure
    if isinstance(result, dict):
        rows = result.get("rows", [])
        graph = result.get("graph", [])
    else:
        rows = result
        graph = []

    return {"rows": rows, "graph": graph}
