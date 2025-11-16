"""Search suggestions use case for query completion and auto-suggestions."""

import logging
import time
import uuid
from dataclasses import dataclass

from prometheus_client import CollectorRegistry, Counter, Histogram

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, SearchSuggestionsPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    SearchSuggestionsRequestDTO,
    SearchSuggestionsResponseDTO,
    SuggestionDTO,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchSuggestionsMetrics:
    """Prometheus metrics for the search suggestions use case."""

    requests_counter: Counter
    latency_histogram: Histogram

    @classmethod
    def create(
        cls,
        *,
        registry: CollectorRegistry | None = None,
    ) -> "SearchSuggestionsMetrics":
        """Create metrics with the given Prometheus registry."""
        reg = registry or CollectorRegistry()
        return cls(
            requests_counter=Counter(
                "search_suggestions_requests_total",
                "Total search suggestions requests",
                ["tenant_id", "status"],
                registry=reg,
            ),
            latency_histogram=Histogram(
                "search_suggestions_latency_ms",
                "Search suggestions latency in milliseconds",
                ["tenant_id"],
                registry=reg,
            ),
        )


@dataclass(frozen=True)
class SearchSuggestionsConfig:
    """Configuration for search suggestions use case."""

    max_limit: int = 50
    default_limit: int = 10
    min_partial_query_length: int = 1
    max_partial_query_length: int = 100
    valid_suggestion_types: frozenset[str] = frozenset(
        ["entities", "relationships", "properties"]
    )
    valid_permissions: frozenset[str] = frozenset(["read"])


class SearchSuggestionsUseCase(
    BaseUseCase[SearchSuggestionsRequestDTO, SearchSuggestionsResponseDTO]
):
    """Use case for providing search suggestions and query completion."""

    def __init__(
        self,
        search_suggestions_port: SearchSuggestionsPort,
        authorization_port: AuthorizationPort,
        config: SearchSuggestionsConfig = SearchSuggestionsConfig(),
        *,
        metrics: SearchSuggestionsMetrics | None = None,
        registry: CollectorRegistry | None = None,
    ) -> None:
        """Initialize the search suggestions use case.

        Args:
            search_suggestions_port: Port for search suggestions operations
            authorization_port: Port for authorization checks
            config: Configuration for the use case
            metrics: Optional Prometheus metrics instance
            registry: Optional Prometheus registry for metric creation
        """
        super().__init__()
        self.suggestions_port = search_suggestions_port
        self.authz = authorization_port
        self.config = config
        self.metrics = metrics or SearchSuggestionsMetrics.create(registry=registry)

    async def _execute_internal(
        self, request: SearchSuggestionsRequestDTO
    ) -> SearchSuggestionsResponseDTO:
        """Execute search suggestions operation.

        Args:
            request: Search suggestions request

        Returns:
            Search suggestions response with suggestions

        Raises:
            AuthorizationError: When user lacks permission
            NotFoundError: When knowledge graph is not found
            ValidationError: When suggestion parameters are invalid
        """
        request_id = str(uuid.uuid4())
        trace_prefix = f"[request_id={request_id}][tenant_id={request.tenant_id}]"
        logger.info(
            f"{trace_prefix} Starting search suggestions for kg_id={request.kg_id}"
        )

        # Increment request counter
        self.metrics.requests_counter.labels(
            tenant_id=request.tenant_id,
            status="started",
        ).inc()

        # Check authorization
        if not self.authz.check_permission(request.user_id, request.kg_id, "read"):
            logger.warning(
                f"{trace_prefix} Unauthorized access attempt by user {request.user_id}"
            )
            self.metrics.requests_counter.labels(
                tenant_id=request.tenant_id,
                status="unauthorized",
            ).inc()
            raise AuthorizationError(
                message=f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="read",
            )

        # Start timing with Prometheus histogram
        with self.metrics.latency_histogram.labels(tenant_id=request.tenant_id).time():
            start_time = time.time()

            try:
                # Get search suggestions
                suggestion_results = self.suggestions_port.get_suggestions(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    partial_query=request.partial_query,
                    suggestion_types=request.suggestion_types,
                    limit=request.limit,
                )

                # Optionally enhance with web-based suggestions
                # This would require integrating with hybrid search for suggestion enhancement

            except Exception as e:
                if (
                    "not found" in str(e).lower()
                    or "KnowledgeGraphNotFound" in type(e).__name__
                ):
                    logger.error(
                        f"{trace_prefix} Knowledge graph not found: {request.kg_id}"
                    )
                    self.metrics.requests_counter.labels(
                        tenant_id=request.tenant_id,
                        status="not_found",
                    ).inc()
                    raise NotFoundError(
                        message=f"Knowledge graph {request.kg_id} not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    ) from e
                logger.exception(f"{trace_prefix} Search suggestions failed")
                self.metrics.requests_counter.labels(
                    tenant_id=request.tenant_id,
                    status="error",
                ).inc()
                raise ValidationError(f"Search suggestions failed: {str(e)}") from e

            # Transform results to DTOs using list comprehension
            suggestion_dtos = [
                SuggestionDTO(
                    text=suggestion["text"],
                    type=suggestion["type"],
                    score=suggestion["score"],
                    metadata=suggestion.get("metadata", {}),
                )
                for suggestion in suggestion_results
            ]

            # Calculate processing time
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"{trace_prefix} Search suggestions completed in {elapsed_ms:.2f}ms, found {len(suggestion_dtos)} suggestions"
            )
            self.metrics.requests_counter.labels(
                tenant_id=request.tenant_id,
                status="success",
            ).inc()

            return SearchSuggestionsResponseDTO(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                partial_query=request.partial_query,
                suggestions=suggestion_dtos,
                total_suggestions=len(suggestion_dtos),
                processing_time_ms=elapsed_ms,
            )

    def _validate_request_internal(self, request: SearchSuggestionsRequestDTO) -> None:
        """Validate search suggestions request.

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

        if not request.partial_query or not request.partial_query.strip():
            raise ValidationError("Partial query is required and cannot be empty")

        if len(request.partial_query) < self.config.min_partial_query_length:
            raise ValidationError(
                f"Partial query must be at least {self.config.min_partial_query_length} character(s)"
            )

        if len(request.partial_query) > self.config.max_partial_query_length:
            raise ValidationError(
                f"Partial query cannot exceed {self.config.max_partial_query_length} characters"
            )

        if request.limit <= 0:
            raise ValidationError("Limit must be greater than 0")

        if request.limit > self.config.max_limit:
            raise ValidationError(f"Limit cannot exceed {self.config.max_limit}")

        if not isinstance(request.suggestion_types, list):
            raise ValidationError("suggestion_types must be a list")

        if not request.suggestion_types:
            raise ValidationError("At least one suggestion type must be specified")

        if not all(
            isinstance(suggestion_type, str)
            for suggestion_type in request.suggestion_types
        ):
            raise ValidationError("All suggestion types must be strings")

        invalid_types = (
            set(request.suggestion_types) - self.config.valid_suggestion_types
        )
        if invalid_types:
            raise ValidationError(
                f"Invalid suggestion types: {sorted(invalid_types)}. Valid types are: {sorted(self.config.valid_suggestion_types)}"
            )
