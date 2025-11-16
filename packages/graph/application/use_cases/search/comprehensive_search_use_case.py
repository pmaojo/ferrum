"""Comprehensive search use case combining multiple search strategies."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List

from adapters.retrievers.hybrid_search_adapter import HybridSearchAdapter
from application.exceptions import AuthorizationError, ValidationError
from application.ports import (
    AuthorizationPort,
    ClockPort,
    EntitySearchPort,
    SemanticSearchPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    ComprehensiveSearchRequestDTO,
    ComprehensiveSearchResponseDTO,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComprehensiveSearchConfig:
    """Configuration for comprehensive search use case."""

    max_kg_results: int = 20
    max_web_results: int = 10
    enable_entity_search: bool = True
    enable_semantic_search: bool = True
    enable_web_search: bool = True
    web_search_categories: List[str] = None


class ComprehensiveSearchUseCase(
    BaseUseCase[ComprehensiveSearchRequestDTO, ComprehensiveSearchResponseDTO]
):
    """Use case for comprehensive search across knowledge graph and web."""

    def __init__(
        self,
        semantic_search_port: SemanticSearchPort,
        entity_search_port: EntitySearchPort,
        authorization_port: AuthorizationPort,
        clock_port: ClockPort,
        hybrid_search_adapter: HybridSearchAdapter,
        config: ComprehensiveSearchConfig = ComprehensiveSearchConfig(),
    ):
        """Initialize the comprehensive search use case."""
        super().__init__()
        self.semantic_search_port = semantic_search_port
        self.entity_search_port = entity_search_port
        self.authz = authorization_port
        self.clock_port = clock_port
        self.hybrid_search = hybrid_search_adapter
        self.config = config

    async def _execute_internal(
        self, request: ComprehensiveSearchRequestDTO
    ) -> ComprehensiveSearchResponseDTO:
        """Execute comprehensive search operation."""
        request_id = str(uuid.uuid4())
        trace_prefix = f"[request_id={request_id}][tenant_id={request.tenant_id}]"
        logger.info(
            f"{trace_prefix} Starting comprehensive search for kg_id={request.kg_id}"
        )

        # Check authorization
        if not await self.authz.check_permission(
            request.user_id, request.kg_id, "read"
        ):
            raise AuthorizationError(
                message=f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="read",
            )

        start_time = self.clock_port.now()
        results = {}

        # Perform semantic search if enabled
        if self.config.enable_semantic_search:
            try:
                semantic_results = await self.semantic_search_port.search(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    query=request.query,
                    limit=self.config.max_kg_results // 2,
                    threshold=request.threshold or 0.7,
                    filter_by_node_types=request.filter_by_node_types,
                )
                results["semantic"] = semantic_results
            except Exception as e:
                logger.warning(f"{trace_prefix} Semantic search failed: {e}")
                results["semantic"] = []

        # Perform entity search if enabled
        if self.config.enable_entity_search:
            try:
                entity_results, _ = await self.entity_search_port.search_entities(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    text_query=request.query,
                    page=1,
                    page_size=self.config.max_kg_results // 2,
                )
                results["entities"] = entity_results
            except Exception as e:
                logger.warning(f"{trace_prefix} Entity search failed: {e}")
                results["entities"] = []

        # Combine KG results for hybrid search
        combined_kg_results = []
        for semantic_result in results.get("semantic", []):
            combined_kg_results.append(
                {
                    "title": semantic_result.get("label", ""),
                    "content": semantic_result.get("snippet", ""),
                    "url": f'/kg/{request.kg_id}/node/{semantic_result["node_id"]}',
                    "score": semantic_result["score"],
                    "source": "knowledge_graph_semantic",
                }
            )

        for entity_result in results.get("entities", []):
            combined_kg_results.append(
                {
                    "title": entity_result.get("label", entity_result["id"]),
                    "content": str(entity_result.get("properties", {})),
                    "url": f'/kg/{request.kg_id}/entity/{entity_result["id"]}',
                    "score": 0.8,  # Default score for entities
                    "source": "knowledge_graph_entity",
                }
            )

        # Perform hybrid search with web results
        hybrid_results = None
        if self.config.enable_web_search:
            try:
                hybrid_results = await self.hybrid_search.hybrid_search(
                    query=request.query,
                    kg_results=combined_kg_results,
                    web_limit=self.config.max_web_results,
                )
            except Exception as e:
                logger.warning(f"{trace_prefix} Web search failed: {e}")

        elapsed_ms = (self.clock_port.now() - start_time) * 1000

        return ComprehensiveSearchResponseDTO(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            query=request.query,
            semantic_results=results.get("semantic", []),
            entity_results=results.get("entities", []),
            hybrid_results=hybrid_results,
            total_kg_results=len(combined_kg_results),
            total_web_results=(
                len(hybrid_results.get("web_results", [])) if hybrid_results else 0
            ),
            processing_time_ms=elapsed_ms,
            search_timestamp=datetime.now(),
        )

    def _validate_request_internal(
        self, request: ComprehensiveSearchRequestDTO
    ) -> None:
        """Validate comprehensive search request."""
        if not request.kg_id:
            raise ValidationError("Knowledge graph ID is required")

        if not request.tenant_id:
            raise ValidationError("Tenant ID is required")

        if not request.user_id:
            raise ValidationError("User ID is required")

        if not request.query or not request.query.strip():
            raise ValidationError("Search query is required and cannot be empty")
