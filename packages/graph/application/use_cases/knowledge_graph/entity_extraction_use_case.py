from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""

    entity_types: List[str]
    relationship_patterns: List[str]


@dataclass
class EntityExtractionRequest(TenantScopedRequestDTO):
    """Request for customizable entity extraction."""

    documents: List[str]
    config: ExtractionConfig
    kg_id: str


@dataclass
class EntityExtractionResponse(BaseResponseDTO):
    """Extraction results."""

    entities: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None


class EntityExtractionPort(Protocol):
    """Port for performing entity extraction."""

    async def extract(
        self,
        *,
        documents: List[str],
        config: ExtractionConfig,
        kg_id: str,
        tenant_id: str,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: ...


class EntityExtractionUseCase(
    BaseUseCase[EntityExtractionRequest, EntityExtractionResponse]
):
    """Use case for configurable entity extraction."""

    def __init__(self, extractor: EntityExtractionPort, tracer: TracingPort) -> None:
        super().__init__()
        self.extractor = extractor
        self.tracer = tracer

    def _validate_request_internal(self, request: EntityExtractionRequest) -> None:
        if not request.documents:
            raise ValidationError(message="No documents provided", field="documents")
        if not request.kg_id:
            raise ValidationError(message="kg_id is required", field="kg_id")

    async def _execute_internal(
        self, request: EntityExtractionRequest
    ) -> EntityExtractionResponse:
        with self.tracer.start_span(
            name="extract_entities",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                entities, relationships = await self.extractor.extract(
                    documents=request.documents,
                    config=request.config,
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                )
                return EntityExtractionResponse(
                    success=True,
                    processing_time_ms=span.duration_ms,
                    entities=entities,
                    relationships=relationships,
                )
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ApplicationError(
                    message=f"Entity extraction failed: {e}",
                    error_code="ENTITY_EXTRACTION_FAILED",
                )
