"""Entity search use case for finding entities with property-based filtering."""

import logging
from dataclasses import dataclass
from datetime import datetime

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, ClockPort, EntitySearchPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    EntityDTO,
    EntitySearchRequestDTO,
    EntitySearchResponseDTO,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntitySearchConfig:
    """Configuration for entity search use case."""

    max_page_size: int = 1000
    default_page_size: int = 20
    valid_sort_fields: frozenset[str] = frozenset(
        ["id", "type", "label", "created_at", "updated_at", "relationship_count"]
    )
    valid_filter_operators: frozenset[str] = frozenset(
        ["eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "contains", "exists"]
    )


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


class EntitySearchUseCase(BaseUseCase[EntitySearchRequestDTO, EntitySearchResponseDTO]):
    """Use case for searching entities with property-based filtering."""

    def __init__(
        self,
        entity_search_port: EntitySearchPort,
        authorization_port: AuthorizationPort,
        clock_port: ClockPort,
        config: EntitySearchConfig = EntitySearchConfig(),
    ):
        """Initialize the entity search use case.

        Args:
            entity_search_port: Port for entity search operations
            authorization_port: Port for authorization checks
            clock_port: Port for time measurement
            config: Configuration for the use case
        """
        super().__init__()
        self.search_port = entity_search_port
        self.authz = authorization_port
        self.timer = ProcessingTimer(clock_port)
        self.config = config

    async def _execute_internal(
        self, request: EntitySearchRequestDTO
    ) -> EntitySearchResponseDTO:
        """Execute entity search operation.

        Args:
            request: Entity search request

        Returns:
            Entity search response with results

        Raises:
            AuthorizationError: When user lacks permission
            NotFoundError: When knowledge graph is not found
            ValidationError: When search parameters are invalid
        """
        logger.info(f"Starting entity search for kg_id={request.kg_id}")

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

        start = self.timer.start()

        try:
            # Set default pagination if not provided
            page = 1
            page_size = self.config.default_page_size
            if request.pagination:
                page = request.pagination.page
                page_size = request.pagination.page_size

            # Set default sorting if not provided
            sort_by = None
            sort_direction = "asc"
            if request.sort:
                sort_by = request.sort.sort_by
                sort_direction = request.sort.direction.value

            # Perform entity search
            entities_data, total_count = await self.search_port.search_entities(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                entity_types=request.entity_types,
                property_filters=request.property_filters,
                text_query=request.text_query,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )

        except Exception as e:
            if (
                "not found" in str(e).lower()
                or "KnowledgeGraphNotFound" in type(e).__name__
            ):
                raise NotFoundError(
                    message=f"Knowledge graph {request.kg_id} not found",
                    resource_type="knowledge_graph",
                    resource_id=request.kg_id,
                ) from e
            raise ValidationError(f"Entity search failed: {str(e)}") from e

        # Transform results to DTOs using list comprehension
        entity_dtos = [
            EntityDTO(
                id=entity_data["id"],
                type=entity_data["type"],
                label=entity_data.get("label", ""),
                properties=entity_data.get("properties", {}),
                relationship_count=entity_data.get("relationship_count", 0),
                created_at=entity_data.get("created_at"),
                updated_at=entity_data.get("updated_at"),
            )
            for entity_data in entities_data
        ]

        # Prepare filters applied summary
        filters_applied = {}
        if request.entity_types:
            filters_applied["entity_types"] = request.entity_types
        if request.property_filters:
            filters_applied["property_filters"] = request.property_filters
        if request.text_query:
            filters_applied["text_query"] = request.text_query

        return EntitySearchResponseDTO(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            entities=entity_dtos,
            total_entities=total_count,
            filters_applied=filters_applied,
            processing_time_ms=self.timer.elapsed_ms(start),
            search_timestamp=datetime.now(),
        )

    def _validate_request_internal(self, request: EntitySearchRequestDTO) -> None:
        """Validate entity search request.

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

        # Validate entity types if provided
        if request.entity_types is not None:
            if not isinstance(request.entity_types, list):
                raise ValidationError("entity_types must be a list")

            if not all(
                isinstance(entity_type, str) for entity_type in request.entity_types
            ):
                raise ValidationError("All entity types must be strings")

            if len(request.entity_types) == 0:
                raise ValidationError("entity_types cannot be empty if provided")

        # Validate property filters if provided
        if request.property_filters is not None:
            if not isinstance(request.property_filters, dict):
                raise ValidationError("property_filters must be a dictionary")

            # Check for valid filter operators
            valid_operators = [
                "eq",
                "ne",
                "gt",
                "gte",
                "lt",
                "lte",
                "in",
                "nin",
                "contains",
                "exists",
            ]
            for prop_name, filter_value in request.property_filters.items():
                if isinstance(filter_value, dict):
                    # Complex filter with operators
                    for operator in filter_value.keys():
                        if operator not in valid_operators:
                            raise ValidationError(
                                f"Invalid filter operator '{operator}' for property '{prop_name}'"
                            )

        # Validate text query if provided
        if request.text_query is not None:
            if not isinstance(request.text_query, str):
                raise ValidationError("text_query must be a string")

            if len(request.text_query.strip()) == 0:
                raise ValidationError("text_query cannot be empty if provided")

        # Validate pagination if provided
        if request.pagination is not None:
            if request.pagination.page < 1:
                raise ValidationError("Page must be greater than or equal to 1")

            if request.pagination.page_size < 1:
                raise ValidationError("Page size must be greater than or equal to 1")

            if request.pagination.page_size > 1000:
                raise ValidationError("Page size cannot exceed 1000")

        # Validate sort if provided
        if request.sort is not None:
            if not request.sort.sort_by:
                raise ValidationError("sort_by is required when sort is provided")

            valid_sort_fields = [
                "id",
                "type",
                "label",
                "created_at",
                "updated_at",
                "relationship_count",
            ]
            if request.sort.sort_by not in valid_sort_fields:
                raise ValidationError(
                    f"Invalid sort field '{request.sort.sort_by}'. Valid fields: {valid_sort_fields}"
                )

        # Ensure at least one search criterion is provided
        if (
            not request.entity_types
            and not request.property_filters
            and not request.text_query
        ):
            raise ValidationError(
                "At least one search criterion must be provided (entity_types, property_filters, or text_query)"
            )
