from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import (
    RepoFileModel,
    RepositoryIngestRequest,
    ValidationReportModel,
)

router = APIRouter()


@router.post("/api/v1/repositories/ingest", response_model=ValidationReportModel)
async def ingest_repository(
    request: RepositoryIngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> ValidationReportModel:
    if not hasattr(container, "code_ingestion_service"):
        raise HTTPException(status_code=503, detail="CodeIngestionService not configured")

    files: Dict[str, str] = {f.path: f.content for f in request.files}
    report = container.code_ingestion_service.ingest_repository(
        files=files,
        repo_id=request.repo_id,
        tenant_id=request.tenant_id,
        ontology_version_id=request.ontology_version_id,
    )

    if hasattr(container, "config_template_service"):
        yaml_text = container.config_template_service.generate_yaml(request.tenant_id)
        template_path = Path("marketplace/templates") / f"{request.tenant_id}.yaml"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(yaml_text)

    return ValidationReportModel(**report._asdict())
