"""Ingestion related API endpoints."""
from __future__ import annotations

import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from domain.auth import Role
from ui_adapters.rest_api.server import require_role

from domain.entities import Document, ValidationReport, Triple
from infrastructure.ferrus_doc_parser import FerrusDocParser
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import (
    AsyncJobResponse,
    IngestRequest,
    JobStatusResponse,
    ValidationReportModel,
)

from application.tasks.ingestion import ingest_documents_task

router = APIRouter(dependencies=[Depends(require_role(Role.INGEST))])


async def _handle_ingestion(
    ingest_request: IngestRequest,
    container: ServiceContainer,
) -> ValidationReportModel:
    """Common logic for synchronous ingestion."""
    docs = [
        Document(
            id=doc.id or str(uuid.uuid4()),
            content=doc.content,
            metadata=doc.metadata,
            processed_at=None,
            extraction_status="pending",
            tenant_id=ingest_request.tenant_id,
        )
        for doc in ingest_request.documents
    ]

    # Attempt to parse as Ferrus requirement documents first
    parser = FerrusDocParser()
    ferrus_triples: List[Triple] = []
    for d in docs:
        triples = parser.parse_content(d.content, source_file=d.metadata.get("path", ""))
        if not triples:
            ferrus_triples = []
            break
        ferrus_triples.extend(triples)

    if ferrus_triples:
        from ui_adapters.rest_api.dependencies import resolve
        ingestion = resolve(container, "ingestion_service")
        report: ValidationReport = ingestion.validate_triples(
            triples=ferrus_triples,
            tenant_id=ingest_request.tenant_id,
            ontology_version_id=ingest_request.ontology_version_id,
        )
    else:
        from ui_adapters.rest_api.dependencies import resolve
        ingestion = resolve(container, "ingestion_service")
        report = ingestion.process_documents(
            documents=docs,
            kg_id=ingest_request.kg_id,
            tenant_id=ingest_request.tenant_id,
            ontology_version_id=ingest_request.ontology_version_id,
        )

    return ValidationReportModel(
        is_consistent=report.is_consistent,
        unsat_classes=report.unsat_classes,
        repair_suggestions=report.repair_suggestions,
        tenant_id=report.tenant_id,
        ontology_version_id=report.ontology_version_id or ingest_request.ontology_version_id,
    )


@router.post(
    "/api/ingest",
    response_model=ValidationReportModel,
    deprecated=True,
)
async def ingest(
    request: IngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> ValidationReportModel:
    return await _handle_ingestion(request, container)


@router.post("/api/v1/ingest", response_model=ValidationReportModel)
async def ingest_v1(
    request: Request,
    ingest_request: IngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> ValidationReportModel:
    return await _handle_ingestion(ingest_request, container)


@router.post("/api/v1/ingest/async", response_model=AsyncJobResponse)
async def ingest_async(
    request: Request,
    ingest_request: IngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> AsyncJobResponse:
    job_id = str(uuid.uuid4())
    created_at = time.time()

    from ui_adapters.rest_api.dependencies import resolve
    jobs = resolve(container, "job_repository")
    jobs.add(
        {
            "job_id": job_id,
            "repo_id": ingest_request.kg_id,
            "tenant_id": ingest_request.tenant_id,
            "status": "queued",
            "progress": 0.0,
            "created_at": created_at,
            "updated_at": created_at,
            "result_path": None,
            "result": None,
            "error": None,
            "task_id": None,
        }
    )

    docs = [
        Document(
            id=doc.id or str(uuid.uuid4()),
            content=doc.content,
            metadata=doc.metadata,
            processed_at=None,
            extraction_status="pending",
            tenant_id=ingest_request.tenant_id,
        )
        for doc in ingest_request.documents
    ]

    task = ingest_documents_task.delay(
        job_id,
        [d.__dict__ for d in docs],
        ingest_request.kg_id,
        ingest_request.tenant_id,
        ingest_request.ontology_version_id,
    )
    job = jobs.get(job_id)
    if job is not None:
        job["task_id"] = task.id
        jobs.update(job)

    return AsyncJobResponse(
        job_id=job_id,
        status="queued",
        created_at=str(created_at),
        estimated_completion=str(created_at + 300),
    )


@router.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def job_status(
    job_id: str, container: ServiceContainer = Depends(get_container)
) -> JobStatusResponse:
    from ui_adapters.rest_api.dependencies import resolve
    jobs = resolve(container, "job_repository")
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job["updated_at"] = time.time()
    jobs.update(job)
    return JobStatusResponse(**job)
