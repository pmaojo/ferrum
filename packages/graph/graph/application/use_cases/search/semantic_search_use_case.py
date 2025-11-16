"""Semantic search use case for finding semantically similar content."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from prometheus_client import Counter, Histogram

from adapters.retrievers.hybrid_search_adapter import HybridSearchAdapter
from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, SemanticSearchPort
from application.ports.time import ClockPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    SearchResultDTO,
    SemanticSearchRequestDTO,
    SemanticSearchResponseDTO,
)

logger = logging.getLogger(__name__)

# Métricas Prometheus
SEMANTIC_SEARCH_REQUESTS = Counter(
    "semantic_search_requests_total",
    "Total semantic search requests",
    ["tenant_id", "status"],
)
SEMANTIC_SEARCH_LATENCY = Histogram(
    "semantic_search_latency_ms",
    "Semantic search latency in milliseconds",
    ["tenant_id"],
)


@dataclass(frozen=True)
class SemanticSearchConfig:
    """Configuration for semantic search use case."""

    max_limit: int = 1000
    default_limit: int = 20
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    valid_permissions: frozenset[str] = frozenset(["read"])


@dataclass(frozen=True)
class ProcessingTimer:
    """Timer utility for measuring processing time."""

    clock: ClockPort

    def start(self) -> float:
        """Start timing."""
        return self.clock.now()

    def elapsed_ms(self, start: float) -> float:
        """Calculate elapsed time in milliseconds."""
        return (self.clock.now() - start) * 1000


class SemanticSearchUseCase(
    BaseUseCase[SemanticSearchRequestDTO, SemanticSearchResponseDTO]
):
    """Use case for performing semantic search using embeddings."""

    def __init__(
        self,
        semantic_search_port: SemanticSearchPort,
        authorization_port: AuthorizationPort,
        clock_port: ClockPort,
        config: SemanticSearchConfig = SemanticSearchConfig(),
        hybrid_search_adapter: Optional[HybridSearchAdapter] = None,
    ):
        """Initialize the semantic search use case.

        Args:
            semantic_search_port: Port for semantic search operations
            authorization_port: Port for authorization checks
            clock_port: Port for time measurement
            config: Configuration for the use case
            hybrid_search_adapter: Optional hybrid search adapter for web results
        """
        super().__init__()
        self.search_port = semantic_search_port
        self.authz = authorization_port
        self.timer = ProcessingTimer(clock_port)
        self.config = config
        self.hybrid_search = hybrid_search_adapter

    async def _execute_internal(
        self, request: SemanticSearchRequestDTO
    ) -> SemanticSearchResponseDTO:
        """Execute semantic search operation.

        Args:
            request: Semantic search request

        Returns:
            Semantic search response with results

        Raises:
            AuthorizationError: When user lacks permission
            NotFoundError: When knowledge graph is not found
            ValidationError: When search parameters are invalid
        """
        request_id = str(uuid.uuid4())
        trace_prefix = f"[request_id={request_id}][tenant_id={request.tenant_id}]"
        logger.info(
            f"{trace_prefix} Starting semantic search for kg_id={request.kg_id}"
        )

        # Increment request counter
        SEMANTIC_SEARCH_REQUESTS.labels(
            tenant_id=request.tenant_id, status="started"
        ).inc()

        # Check authorization
        if not await self.authz.check_permission(
            request.user_id, request.kg_id, "read"
        ):
            logger.warning(
                f"{trace_prefix} Unauthorized access attempt by user {request.user_id}"
            )
            SEMANTIC_SEARCH_REQUESTS.labels(
                tenant_id=request.tenant_id, status="unauthorized"
            ).inc()
            raise AuthorizationError(
                message=f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="read",
            )

        # Start timing with Prometheus histogram
        with SEMANTIC_SEARCH_LATENCY.labels(tenant_id=request.tenant_id).time():
            start = self.timer.start()

            try:
                # Perform semantic search
                search_results = await self.search_port.search(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    query=request.query,
                    limit=request.limit,
                    threshold=request.threshold,
                    filter_by_node_types=request.filter_by_node_types,
                )

            except Exception as e:
                if (
                    "not found" in str(e).lower()
                    or "KnowledgeGraphNotFound" in type(e).__name__
                ):
                    logger.error(
                        f"{trace_prefix} Knowledge graph not found: {request.kg_id}"
                    )
                    SEMANTIC_SEARCH_REQUESTS.labels(
                        tenant_id=request.tenant_id, status="not_found"
                    ).inc()
                    raise NotFoundError(
                        message=f"Knowledge graph {request.kg_id} not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    ) from e
                logger.exception(f"{trace_prefix} Semantic search failed")
                SEMANTIC_SEARCH_REQUESTS.labels(
                    tenant_id=request.tenant_id, status="error"
                ).inc()
                raise ValidationError(f"Semantic search failed: {str(e)}") from e

            # Transform results to DTOs using list comprehension
            result_dtos = [
                SearchResultDTO(
                    node_id=result["node_id"],
                    node_type=result["node_type"],
                    label=result.get("label", ""),
                    properties=(
                        result.get("properties", {})
                        if request.include_properties
                        else {}
                    ),
                    score=result["score"],
                    snippet=result.get("snippet"),
                )
                for result in search_results
            ]

            # Add hybrid search results if adapter is available
            hybrid_results = None
            if self.hybrid_search:
                try:
                    # Convert knowledge graph results to format expected by hybrid adapter
                    kg_results = [
                        {
                            "title": result.label,
                            "content": result.snippet or "",
                            "url": f"/kg/{request.kg_id}/node/{result.node_id}",
                            "score": result.score,
                            "source": "knowledge_graph",
                        }
                        for result in result_dtos
                    ]

                    hybrid_results = await self.hybrid_search.hybrid_search(
                        query=request.query, kg_results=kg_results, web_limit=5
                    )
                except Exception as e:
                    logger.warning(f"{trace_prefix} Hybrid search failed: {e}")

            elapsed_ms = self.timer.elapsed_ms(start)
            logger.info(
                f"{trace_prefix} Semantic search completed in {elapsed_ms:.2f}ms, found {len(result_dtos)} results"
            )
            SEMANTIC_SEARCH_REQUESTS.labels(
                tenant_id=request.tenant_id, status="success"
            ).inc()

            response = SemanticSearchResponseDTO(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                query=request.query,
                results=result_dtos,
                total_results=len(result_dtos),
                processing_time_ms=elapsed_ms,
                search_timestamp=(
                    self.timer.clock.now_datetime()
                    if hasattr(self.timer.clock, "now_datetime")
                    else datetime.now()
                ),
            )

            # Add hybrid results as metadata
            if hybrid_results:
                response.metadata = {"hybrid_search": hybrid_results}

            return response

    def _validate_request_internal(self, request: SemanticSearchRequestDTO) -> None:
        """Validate semantic search request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: When request is invalid
        """
        if not request.kg_id:
            raise ValidationError("Knowledge graph ID is required")

        if not request.tenant_id:
            raise ValidationError("Tenant ID is required")

        if not request.user_id:
            raise ValidationError("User ID is required")

        if not request.query or not request.query.strip():
            raise ValidationError("Search query is required and cannot be empty")

        if request.limit <= 0:
            raise ValidationError("Limit must be greater than 0")

        if request.limit > self.config.max_limit:
            raise ValidationError(f"Limit cannot exceed {self.config.max_limit}")

        if not (
            self.config.min_threshold <= request.threshold <= self.config.max_threshold
        ):
            raise ValidationError(
                f"Threshold must be between {self.config.min_threshold} and {self.config.max_threshold}"
            )

        if request.filter_by_node_types is not None:
            if not isinstance(request.filter_by_node_types, list):
                raise ValidationError("filter_by_node_types must be a list")

            if not all(
                isinstance(node_type, str) for node_type in request.filter_by_node_types
            ):
                raise ValidationError("All node types in filter must be strings")
