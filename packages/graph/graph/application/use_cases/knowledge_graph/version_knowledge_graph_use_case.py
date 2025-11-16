from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO


@dataclass
class VersionKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to create a version of a knowledge graph."""

    kg_id: str
    parent_version_id: Optional[str] = None


@dataclass
class KnowledgeGraphVersionDTO:
    version_id: str
    kg_id: str
    parent_version_id: Optional[str]
    created_at: str


@dataclass
class VersionKnowledgeGraphResponse(BaseResponseDTO):
    """Response containing version info."""

    version: Optional[KnowledgeGraphVersionDTO] = None


class KnowledgeGraphVersioningPort(Protocol):
    """Port for knowledge graph version management."""

    def create_version(
        self, *, kg_id: str, tenant_id: str, parent_version_id: Optional[str]
    ) -> KnowledgeGraphVersionDTO: ...

    def list_versions(
        self, *, kg_id: str, tenant_id: str
    ) -> List[KnowledgeGraphVersionDTO]: ...


class VersionKnowledgeGraphUseCase(
    BaseUseCase[VersionKnowledgeGraphRequest, VersionKnowledgeGraphResponse]
):
    """Use case for knowledge graph versioning."""

    def __init__(
        self, repository: KnowledgeGraphVersioningPort, tracer: TracingPort
    ) -> None:
        super().__init__()
        self.repository = repository
        self.tracer = tracer

    def _validate_request_internal(self, request: VersionKnowledgeGraphRequest) -> None:
        if not request.kg_id:
            raise ValidationError(message="kg_id is required", field="kg_id")

    async def _execute_internal(
        self, request: VersionKnowledgeGraphRequest
    ) -> VersionKnowledgeGraphResponse:
        with self.tracer.start_span(
            name="version_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ) as span:
            try:
                version = self.repository.create_version(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    parent_version_id=request.parent_version_id,
                )
                return VersionKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=span.duration_ms,
                    version=version,
                )
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ApplicationError(
                    message=f"Versioning failed: {e}",
                    error_code="GRAPH_VERSIONING_FAILED",
                )
