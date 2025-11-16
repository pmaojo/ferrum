"""URL ingestion endpoints.

Permite descargar contenido de URLs públicas (texto/HTML) y pasarlo al
servicio de ingestión como documentos. Uso rápido:

POST /api/v1/url-ingest  {
  "urls": ["https://example.com"],
  "kg_id": "default",
  "tenant_id": "default",
  "ontology_version_id": "default"
}

Respuesta: ValidationReportModel (igual que otras rutas de ingestión).
"""
from __future__ import annotations

import uuid
import re
from typing import List

import requests
from bs4 import BeautifulSoup  # opcional si está instalado; si no, fallback simple
from fastapi import APIRouter, Depends, HTTPException

from domain.entities import Document, ValidationReport
from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import ValidationReportModel
from pydantic import BaseModel, AnyHttpUrl

router = APIRouter()

MAX_CONTENT_LEN = 200_000  # caracteres
TIMEOUT = 15  # segundos
TEXT_MIME_RE = re.compile(r"text/(html|plain|markdown).*", re.IGNORECASE)


class UrlIngestRequest(BaseModel):
    urls: List[AnyHttpUrl]
    kg_id: str = "default"
    tenant_id: str = "default"
    ontology_version_id: str = "default"


def _fetch(url: str) -> str:
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "PermaGraphBot/1.0"})
    except requests.RequestException as e:  # pragma: no cover - red externa
        raise HTTPException(status_code=502, detail=f"Error al descargar {url}: {e}")
    ctype = resp.headers.get("content-type", "")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=f"Respuesta {resp.status_code} en {url}")
    if not TEXT_MIME_RE.match(ctype):
        raise HTTPException(status_code=400, detail=f"Tipo de contenido no soportado ({ctype}) en {url}")
    text = resp.text or ""
    if "BeautifulSoup" in globals():
        try:  # Limpieza HTML básica
            soup = BeautifulSoup(text, "html.parser")
            # Eliminar scripts y estilos
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            cleaned = soup.get_text(" ")
            text = cleaned
        except Exception:  # pragma: no cover
            pass
    if len(text) > MAX_CONTENT_LEN:
        text = text[:MAX_CONTENT_LEN]
    return text.strip()


@router.post("/api/v1/url-ingest", response_model=ValidationReportModel)
async def url_ingest(
    request: UrlIngestRequest,
    container: ServiceContainer = Depends(get_container),
) -> ValidationReportModel:
    if not request.urls:
        raise HTTPException(status_code=400, detail="Lista de URLs vacía")

    contents = []
    for u in request.urls:
        contents.append((u, _fetch(str(u))))

    docs = [
        Document(
            id=str(uuid.uuid4()),
            content=content,
            metadata={"url": url},
            processed_at=None,
            extraction_status="pending",
            tenant_id=request.tenant_id,
        )
        for url, content in contents
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
    data = report.__dict__
    return ValidationReportModel(**data)
