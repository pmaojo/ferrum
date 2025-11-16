"""LLM related endpoints including context compression."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container

router = APIRouter()


@router.post("/api/v1/context/compress")
async def compress_context(
    request: Dict[str, Any],
    container: ServiceContainer = Depends(get_container),
) -> Dict[str, Any]:
    from domain.entities import Triple

    triples_data = request.get("triples", [])
    query = request.get("query", "")
    tenant_id = request.get("tenant_id", "default")
    compression_ratio = request.get("compression_ratio")
    opts = request.get("opts", {})

    triples = [
        Triple(
            subject=t["subject"],
            predicate=t["predicate"],
            object=t["object"],
            tenant_id=tenant_id,
        )
        for t in triples_data
    ]

    compressed = container.context_compression_service.compress_context(
        triples=triples,
        query=query,
        tenant_id=tenant_id,
        compression_ratio=compression_ratio,
        opts=opts,
    )

    result = [
        {
            "subject": t.subject,
            "predicate": t.predicate,
            "object": t.object,
            "tenant_id": t.tenant_id,
        }
        for t in compressed
    ]
    return {
        "original_count": len(triples),
        "compressed_count": len(compressed),
        "compression_ratio": 1.0 - (len(compressed) / len(triples)) if triples else 0.0,
        "compressed_triples": result,
    }


@router.get("/api/v1/llm/circuit-status")
async def get_circuit_status(
    container: ServiceContainer = Depends(get_container),
) -> Any:
    return container.llm_fallback_policy.get_circuit_status()


@router.post("/api/v1/llm/generate")
async def llm_generate(
    request: Dict[str, Any],
    container: ServiceContainer = Depends(get_container),
) -> Dict[str, Any]:
    prompt = request.get("prompt", "")
    tenant_id = request.get("tenant_id", "default")
    stream = request.get("stream", False)
    tools = request.get("tools")
    opts = request.get("opts")

    result = container.llm_fallback_policy.generate(
        prompt=prompt,
        tenant_id=tenant_id,
        stream=stream,
        tools=tools,
        opts=opts,
    )
    return {"result": result}
