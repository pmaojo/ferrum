"""Similar entities use case for finding entities with similar properties."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from prometheus_client import Counter, Histogram

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, SimilaritySearchPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    EntityDTO,
    SimilarEntitiesRequestDTO,
    SimilarEntitiesResponseDTO,
    SimilarEntityDTO,
    SimilarityExplanationDTO,
)

logger = logging.getLogger(__name__)

# Prometheus metrics
SIMILAR_ENTITIES_REQUESTS = Counter(
    "similar_entities_requests_total",
    "Total similar entities requests",
    ["tenant_id", "status"],
)
SIMILAR_ENTITIES_LATENCY = Histogram(
    "similar_entities_latency_ms",
    "Similar entities search latency in milliseconds",
    ["tenant_id"],
)


@dataclass(frozen=True)
class SimilarEntitiesConfig:
    """Configuration for similar entities use case."""

    max_limit: int = 100
    default_limit: int = 10
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    valid_algorithms: frozenset[str] = frozenset(
        ["embedding", "structural", "property"]
    )
    valid_permissions: frozenset[str] = frozenset(["read"])


class SimilarEntitiesUseCase(
    BaseUseCase[SimilarEntitiesRequestDTO, SimilarEntitiesResponseDTO]
):
    """Use case for finding entities similar to a given entity."""

    def __init__(
        self,
        similarity_search_port: SimilaritySearchPort,
        authorization_port: AuthorizationPort,
        config: SimilarEntitiesConfig = SimilarEntitiesConfig(),
    ):
        """Initialize the similar entities use case.

        Args:
            similarity_search_port: Port for similarity search operations
            authorization_port: Port for authorization checks
            config: Configuration for the use case
        """
        super().__init__()
        self.similarity_port = similarity_search_port
        self.authz = authorization_port
        self.config = config

    async def _execute_internal(
        self, request: SimilarEntitiesRequestDTO
    ) -> SimilarEntitiesResponseDTO:
        """Execute similar entities search operation.

        Args:
            request: Similar entities search request

        Returns:
            Similar entities response with results

        Raises:
            AuthorizationError: When user lacks permission
            NotFoundError: When knowledge graph or entity is not found
            ValidationError: When search parameters are invalid
        """
        request_id = str(uuid.uuid4())
        trace_prefix = f"[request_id={request_id}][tenant_id={request.tenant_id}]"
        logger.info(
            f"{trace_prefix} Starting similar entities search for entity_id={request.entity_id}"
        )

        # Increment request counter
        SIMILAR_ENTITIES_REQUESTS.labels(
            tenant_id=request.tenant_id, status="started"
        ).inc()

        # Check authorization
        if not self.authz.check_permission(request.user_id, request.kg_id, "read"):
            logger.warning(
                f"{trace_prefix} Unauthorized access attempt by user {request.user_id}"
            )
            SIMILAR_ENTITIES_REQUESTS.labels(
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
        with SIMILAR_ENTITIES_LATENCY.labels(tenant_id=request.tenant_id).time():
            start_time = time.time()

            try:
                # Perform similarity search
                search_results = self.similarity_port.find_similar_entities(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    entity_id=request.entity_id,
                    similarity_algorithm=request.similarity_algorithm,
                    limit=request.limit,
                    threshold=request.threshold,
                    include_explanation=request.include_explanation,
                )

            except Exception as e:
                if (
                    "not found" in str(e).lower()
                    or "EntityNotFound" in type(e).__name__
                ):
                    logger.error(
                        f"{trace_prefix} Entity not found: {request.entity_id}"
                    )
                    SIMILAR_ENTITIES_REQUESTS.labels(
                        tenant_id=request.tenant_id, status="not_found"
                    ).inc()
                    raise NotFoundError(
                        message=f"Entity {request.entity_id} not found in knowledge graph {request.kg_id}",
                        resource_type="entity",
                        resource_id=request.entity_id,
                    ) from e
                logger.exception(f"{trace_prefix} Similar entities search failed")
                SIMILAR_ENTITIES_REQUESTS.labels(
                    tenant_id=request.tenant_id, status="error"
                ).inc()
                raise ValidationError(
                    f"Similar entities search failed: {str(e)}"
                ) from e

            # Transform results to DTOs
            similar_entity_dtos = []
            for result in search_results:
                # Create entity DTO
                entity_dto = EntityDTO(
                    id=result["entity"]["id"],
                    type=result["entity"]["type"],
                    label=result["entity"].get("label", ""),
                    properties=result["entity"].get("properties", {}),
                    relationship_count=result["entity"].get("relationship_count", 0),
                    created_at=result["entity"].get("created_at"),
                    updated_at=result["entity"].get("updated_at"),
                )

                # Create explanation DTO if included
                explanation_dto = None
                if request.include_explanation and "explanation" in result:
                    explanation_dto = SimilarityExplanationDTO(
                        algorithm=result["explanation"]["algorithm"],
                        factors=result["explanation"].get("factors", {}),
                        description=result["explanation"].get("description", ""),
                    )

                # Create similar entity DTO
                similar_entity_dto = SimilarEntityDTO(
                    entity=entity_dto,
                    similarity_score=result["similarity_score"],
                    explanation=explanation_dto,
                )

                similar_entity_dtos.append(similar_entity_dto)

            processing_time_ms = (time.time() - start_time) * 1000
            logger.info(
                f"{trace_prefix} Similar entities search completed in {processing_time_ms:.2f}ms, found {len(similar_entity_dtos)} results"
            )
            SIMILAR_ENTITIES_REQUESTS.labels(
                tenant_id=request.tenant_id, status="success"
            ).inc()

            return SimilarEntitiesResponseDTO(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                source_entity_id=request.entity_id,
                similar_entities=similar_entity_dtos,
                algorithm_used=request.similarity_algorithm,
                processing_time_ms=processing_time_ms,
                search_timestamp=datetime.now(),
            )

    def _validate_request_internal(self, request: SimilarEntitiesRequestDTO) -> None:
        """Validate similar entities search request.

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

        if not request.entity_id:
            raise ValidationError("Entity ID is required")

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

        if request.similarity_algorithm not in self.config.valid_algorithms:
            raise ValidationError(
                f"Invalid similarity algorithm: {request.similarity_algorithm}. Valid algorithms: {list(self.config.valid_algorithms)}"
            )
