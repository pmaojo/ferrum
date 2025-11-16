from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol

from application.exceptions import ApplicationError, ValidationError
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from domain.entities import KnowledgeGraph


@dataclass
class MergeKnowledgeGraphsRequest(TenantScopedRequestDTO):
    """Request to merge multiple knowledge graphs."""

    target_kg_id: str
    source_kg_ids: List[str]


@dataclass
class MergeKnowledgeGraphsResponse(BaseResponseDTO):
    """Response with merged graph info."""

    merged_graph: KnowledgeGraph | None = None


class GraphMergePort(Protocol):
    """Port defining graph merging operations."""

    def merge(
        self, *, target_kg_id: str, source_kg_ids: List[str], tenant_id: str
    ) -> KnowledgeGraph: ...


class MergeKnowledgeGraphsUseCase(
    BaseUseCase[MergeKnowledgeGraphsRequest, MergeKnowledgeGraphsResponse]
):
    """Use case for merging knowledge graphs."""

    def __init__(self, merger: GraphMergePort, tracer: TracingPort) -> None:
        super().__init__()
        self.merger = merger
        self.tracer = tracer

    def _validate_request_internal(self, request: MergeKnowledgeGraphsRequest) -> None:
        if not request.target_kg_id:
            raise ValidationError(
                message="target_kg_id is required", field="target_kg_id"
            )
        if not request.source_kg_ids:
            raise ValidationError(
                message="source_kg_ids is required", field="source_kg_ids"
            )

    async def _execute_internal(
        self, request: MergeKnowledgeGraphsRequest
    ) -> MergeKnowledgeGraphsResponse:
        with self.tracer.start_span(
            name="merge_knowledge_graphs",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.target_kg_id,
        ) as span:
            try:
                merged = self.merger.merge(
                    target_kg_id=request.target_kg_id,
                    source_kg_ids=request.source_kg_ids,
                    tenant_id=request.tenant_id,
                )
                return MergeKnowledgeGraphsResponse(
                    success=True,
                    processing_time_ms=span.duration_ms,
                    merged_graph=merged,
                )
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ApplicationError(
                    message=f"Graph merge failed: {e}",
                    error_code="GRAPH_MERGE_FAILED",
                )
