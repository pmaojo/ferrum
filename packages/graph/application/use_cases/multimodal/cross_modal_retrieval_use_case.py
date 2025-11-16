"""Use case for cross-modal similarity retrieval."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from application.exceptions import AuthorizationError, ValidationError
from application.ports import (
    AuthorizationPort,
    CrossModalRetrievalPort,
    EmbeddingCachePort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO

logger = logging.getLogger(__name__)


@dataclass
class CrossModalRetrievalRequestDTO:
    """Request DTO for cross-modal retrieval."""

    tenant_id: str
    user_id: str
    kg_id: str
    text_query: Optional[str] = None
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    limit: int = 10
    threshold: float = 0.7


@dataclass
class CrossModalResultDTO:
    """DTO representing a retrieval result."""

    entity_id: str
    content_type: str
    content_path: str
    score: float
    metadata: Dict[str, Any] | None = None


@dataclass
class CrossModalRetrievalResponseDTO(BaseResponseDTO):
    """Response DTO for cross-modal retrieval."""

    results: List[CrossModalResultDTO] = field(default_factory=list)
    total_results: int = 0


class CrossModalRetrievalUseCase(
    BaseUseCase[CrossModalRetrievalRequestDTO, CrossModalRetrievalResponseDTO]
):
    """Use case for retrieving similar items across modalities."""

    def __init__(
        self,
        retrieval_port: CrossModalRetrievalPort,
        embedding_cache_port: EmbeddingCachePort,
        authorization_port: Optional[AuthorizationPort] = None,
    ) -> None:
        super().__init__()
        self.retrieval_port = retrieval_port
        self.cache_port = embedding_cache_port
        self.authz = authorization_port

    async def _execute_internal(
        self, request: CrossModalRetrievalRequestDTO
    ) -> CrossModalRetrievalResponseDTO:
        """Execute cross-modal retrieval."""

        if self.authz and not await self.authz.check_permission(
            request.user_id, request.kg_id, "read"
        ):
            raise AuthorizationError(
                message=(
                    f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}"
                ),
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="read",
            )

        start = time.time()
        results = await self.retrieval_port.retrieve_similar(
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            text_query=request.text_query,
            image_path=request.image_path,
            audio_path=request.audio_path,
            limit=request.limit,
            threshold=request.threshold,
        )

        result_dtos = [
            CrossModalResultDTO(
                entity_id=r["entity_id"],
                content_type=r.get("content_type", "unknown"),
                content_path=r.get("content_path", ""),
                score=r.get("score", 0.0),
                metadata=r.get("metadata"),
            )
            for r in results
        ]

        elapsed_ms = (time.time() - start) * 1000

        return CrossModalRetrievalResponseDTO(
            success=True,
            processing_time_ms=elapsed_ms,
            results=result_dtos,
            total_results=len(result_dtos),
        )

    def _validate_request_internal(
        self, request: CrossModalRetrievalRequestDTO
    ) -> None:
        """Validate request parameters."""

        if not request.kg_id:
            raise ValidationError("Knowledge graph ID is required", field="kg_id")

        if not request.tenant_id:
            raise ValidationError("Tenant ID is required", field="tenant_id")

        if not request.user_id:
            raise ValidationError("User ID is required", field="user_id")

        if not any([request.text_query, request.image_path, request.audio_path]):
            raise ValidationError(
                "At least one of text_query, image_path, or audio_path must be provided",
                field="inputs",
            )

        if request.limit <= 0:
            raise ValidationError("limit must be greater than 0", field="limit")

        if not 0.0 <= request.threshold <= 1.0:
            raise ValidationError(
                "threshold must be between 0.0 and 1.0", field="threshold"
            )
