from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from domain.entities import Triple
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import (
    OntologyVersionCreateRequest,
    OntologyVersionResponse,
    TripleModel,
)

router = APIRouter()


@router.post("/api/ontology/versions", response_model=OntologyVersionResponse)
async def store_version(
    request: OntologyVersionCreateRequest,
    container: ServiceContainer = Depends(get_container),
) -> OntologyVersionResponse:
    triples = [
        Triple(
            subject=t.subject,
            predicate=t.predicate,
            object=t.object,
            tenant_id=request.tenant_id,
        )
        for t in request.triples
    ]
    version = container.ontology_version_service.store_version(
        triples=triples,
        parent_version_id=request.parent_version_id,
        tenant_id=request.tenant_id,
    )
    return OntologyVersionResponse(**asdict(version))


@router.get(
    "/api/ontology/versions/{version_id}", response_model=OntologyVersionResponse
)
async def get_version(
    version_id: str,
    tenant_id: str,
    container: ServiceContainer = Depends(get_container),
) -> OntologyVersionResponse:
    version = container.ontology_version_service.get_version(
        version_id=version_id, tenant_id=tenant_id
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return OntologyVersionResponse(**asdict(version))


@router.get("/api/ontology/versions", response_model=List[OntologyVersionResponse])
async def list_versions(
    tenant_id: str,
    limit: int = 10,
    container: ServiceContainer = Depends(get_container),
) -> List[OntologyVersionResponse]:
    history = container.ontology_version_service.get_version_history(
        tenant_id=tenant_id, limit=limit
    )
    return [OntologyVersionResponse(**asdict(v)) for v in history]


@router.delete("/api/ontology/versions/{version_id}")
async def delete_version(
    version_id: str,
    tenant_id: str,
    container: ServiceContainer = Depends(get_container),
) -> dict:
    success = container.ontology_version_service.delete_version(
        version_id=version_id, tenant_id=tenant_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"status": "deleted"}
