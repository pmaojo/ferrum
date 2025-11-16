import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import logging
from celery import Celery
import yaml

from domain.entities import Document
from kernel.container import create_container
from ui_adapters.rest_api.settings import RestApiSettings
from ui_adapters.rest_api.dependencies import resolve

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "ingestion",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)


logger = logging.getLogger(__name__)


@celery_app.task(name="ingestion.process_documents")
def ingest_documents_task(
    job_id: str,
    docs_data: List[Dict[str, Any]],
    kg_id: str,
    tenant_id: str,
    ontology_version_id: str,
) -> None:
    """Process an ingestion job and persist status to the job repository."""

    logger.info(
        "Starting ingestion task",
        extra={
            "job_id": job_id,
            "kg_id": kg_id,
            "tenant_id": tenant_id,
            "ontology_version_id": ontology_version_id,
        },
    )

    with create_container(RestApiSettings()) as container:
        jobs = resolve(container, "job_repository")
        job = jobs.get(job_id)
        if job:
            job.update(
                {"status": "processing", "progress": 0.1, "updated_at": time.time()}
            )
            jobs.update(job)

        documents = [Document(**d) for d in docs_data]

        try:
            ingestion = resolve(container, "ingestion_service")
            report = ingestion.process_documents(
                documents=documents,
                kg_id=kg_id,
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id,
            )
            if job:
                result = {
                    "is_consistent": report.is_consistent,
                    "unsat_classes": report.unsat_classes,
                    "repair_suggestions": report.repair_suggestions,
                    "tenant_id": report.tenant_id,
                    "ontology_version_id": report.ontology_version_id,
                }
                path = Path(tempfile.gettempdir()) / f"{job_id}.yaml"
                with path.open("w") as fh:
                    yaml.safe_dump(result, fh)
                job.update(
                    {
                        "status": "completed",
                        "progress": 1.0,
                        "result": result,
                        "result_path": str(path),
                        "updated_at": time.time(),
                    }
                )
                jobs.update(job)
            logger.info("Ingestion task completed", extra={"job_id": job_id})
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Ingestion task failed", extra={"job_id": job_id})
            if job:
                job.update(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "updated_at": time.time(),
                    }
                )
                jobs.update(job)
            raise
