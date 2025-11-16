"""Repository ingestion endpoints."""
from __future__ import annotations

import io
import json
import functools
import tarfile
import tempfile
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import sqlalchemy as sa
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from adapters.repositories.database_config import DatabaseConfig, create_db_manager
from domain.entities import ValidationReport
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import AsyncJobResponse, RepoIngestRequest, ValidationReportModel


router = APIRouter()


class RepositoryIngestionDB:
    """Simple helper for persisting ingestion job metadata."""

    def __init__(self) -> None:
        cfg = DatabaseConfig.from_env()
        self.manager = create_db_manager(cfg)
        self.manager.initialize()
        metadata = sa.MetaData()
        self.table = sa.Table(
            "repository_ingestions",
            metadata,
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("repo_id", sa.String(length=255), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("result", sa.Text(), nullable=True),
            sa.Column("result_path", sa.String(length=255), nullable=True),
        )
        metadata.create_all(self.manager.engine)

    def add_job(self, *, job_id: str, repo_id: str, tenant_id: str) -> None:
        with self.manager.get_session() as session:
            stmt = sa.insert(self.table).values(
                id=job_id,
                repo_id=repo_id,
                tenant_id=tenant_id,
                status="queued",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                result_path=None,
                result=None,
            )
            session.execute(stmt)
            session.commit()

    def update_job(
        self,
        *,
        job_id: str,
        status: str,
        result: Optional[dict] = None,
        result_path: Optional[str] = None,
    ) -> None:
        with self.manager.get_session() as session:
            stmt = (
                sa.update(self.table)
                .where(self.table.c.id == job_id)
                .values(
                    status=status,
                    updated_at=datetime.utcnow(),
                    result=json.dumps(result) if result else None,
                    result_path=result_path,
                )
            )
            session.execute(stmt)
            session.commit()



@functools.lru_cache()
def get_db() -> RepositoryIngestionDB:
    return RepositoryIngestionDB()


def _extract_files(data: bytes) -> Dict[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return {
                name: zf.read(name).decode("utf-8", "ignore")
                for name in zf.namelist()
                if name.endswith(".py")
            }
    except zipfile.BadZipFile:
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            files = {}
            for member in tf.getmembers():
                if member.isfile() and member.name.endswith(".py"):
                    files[member.name] = tf.extractfile(member).read().decode(
                        "utf-8", "ignore"
                    )
            return files
    except tarfile.TarError:
        raise HTTPException(status_code=400, detail="Invalid archive format")


async def _process_repo_ingestion(
    *,
    job_id: str,
    repo_id: str,
    files: Dict[str, str],
    tenant_id: str,
    ontology_version_id: str,
    container: ServiceContainer,
) -> None:
    try:
        job_repo = container.job_repository()
        job = job_repo.get(job_id)
        if job:
            job["status"] = "processing"
            job_repo.update(job)
        get_db().update_job(job_id=job_id, status="processing")

        if not hasattr(container, "code_ingestion_service"):
            raise RuntimeError("code_ingestion_service not configured")
        report: ValidationReport = container.code_ingestion_service.ingest_repository(
            files=files,
            repo_id=repo_id,
            tenant_id=tenant_id,
            ontology_version_id=ontology_version_id,
        )
        result = {
            "is_consistent": report.is_consistent,
            "unsat_classes": report.unsat_classes,
            "repair_suggestions": report.repair_suggestions,
            "tenant_id": report.tenant_id,
            "ontology_version_id": report.ontology_version_id,
        }
        if job:
            job["status"] = "completed"
            job["progress"] = 1.0
            job["result"] = result
            job["result_path"] = None
            job_repo.update(job)
        path = Path(tempfile.gettempdir()) / f"{job_id}.json"
        with path.open("w") as fh:
            json.dump(result, fh)
        get_db().update_job(
            job_id=job_id,
            status="completed",
            result=result,
            result_path=str(path),
        )
    except Exception as exc:  # pragma: no cover - safety net
        if job := job_repo.get(job_id):
            job["status"] = "failed"
            job["error"] = str(exc)
            job_repo.update(job)
        get_db().update_job(
            job_id=job_id,
            status="failed",
            result={"error": str(exc)},
        )


@router.post("/api/v1/repo-ingest", response_model=AsyncJobResponse)
async def repo_ingest_v1(
    background_tasks: BackgroundTasks,
    repo_url: str | None = Form(None),
    file: UploadFile | None = File(None),
    tenant_id: str = Form("default"),
    ontology_version_id: str = Form("default"),
    container: ServiceContainer = Depends(get_container),
) -> AsyncJobResponse:
    if not repo_url and file is None:
        raise HTTPException(status_code=400, detail="repo_url or file required")

    job_id = str(uuid.uuid4())
    created_at = time.time()
    job_repo = container.job_repository()
    job_repo.add(
        {
            "job_id": job_id,
            "status": "queued",
            "progress": 0.0,
            "created_at": created_at,
            "updated_at": created_at,
            "result": None,
            "error": None,
        }
    )

    repo_id = repo_url or (file.filename if file else job_id)
    get_db().add_job(job_id=job_id, repo_id=repo_id, tenant_id=tenant_id)

    files: Dict[str, str] = {}
    if file is not None:
        data = await file.read()
        files = _extract_files(data)

    background_tasks.add_task(
        _process_repo_ingestion,
        job_id=job_id,
        repo_id=repo_id,
        files=files,
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id,
        container=container,
    )

    return AsyncJobResponse(
        job_id=job_id,
        status="queued",
        created_at=str(created_at),
        estimated_completion=str(created_at + 300),
    )
