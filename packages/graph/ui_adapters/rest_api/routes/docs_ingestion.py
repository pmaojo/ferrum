"""Direct document ingestion endpoints."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from domain.entities import Document, ValidationReport
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import DocsIngestRequest, ValidationReportModel

MAX_FILE_SIZE = 1_000_000  # 1MB
ALLOWED_EXTENSIONS = {".txt", ".md"}

router = APIRouter()


def _validate_file(*, path: str, content: str) -> None:
    if Path(path).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {path}")
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large: {path}")


@router.post("/api/v1/docs-ingest", response_model=ValidationReportModel)
async def docs_ingest(
    request: DocsIngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> ValidationReportModel:
    for f in request.files:
        _validate_file(path=f.path, content=f.content)

    docs = [
        Document(
            id=str(uuid.uuid4()),
            content=f.content,
            metadata={"path": f.path},
            processed_at=None,
            extraction_status="pending",
            tenant_id=request.tenant_id,
        )
        for f in request.files
    ]
    ingestion_service = container.ingestion_service
    if not hasattr(ingestion_service, "process_documents"):
        ingestion_service = ingestion_service()
    report: ValidationReport = ingestion_service.process_documents(
        documents=docs,
        kg_id=request.kg_id,
        tenant_id=request.tenant_id,
        ontology_version_id=request.ontology_version_id,
    )
    data = report._asdict() if hasattr(report, "_asdict") else report.__dict__
    return ValidationReportModel(**data)
