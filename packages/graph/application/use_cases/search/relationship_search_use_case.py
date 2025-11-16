"""Relationship search use case for finding relationship patterns."""

import time
from datetime import datetime

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, RelationshipSearchPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    RelationshipDTO,
    RelationshipSearchRequestDTO,
    RelationshipSearchResponseDTO,
)


class RelationshipSearchUseCase(
    BaseUseCase[RelationshipSearchRequestDTO, RelationshipSearchResponseDTO]
):
    """Use case for searching relationships with pattern matching."""

    def __init__(
        self,
        relationship_search_port: RelationshipSearchPort,
        authorization_port: AuthorizationPort,
    ):
        """Initialize the relationship search use case.

        Args:
            relationship_search_port: Port for relationship search operations
            authorization_port: Port for authorization checks
        """
        super().__init__()
        self.relationship_search_port = relationship_search_port
        self.authorization_port = authorization_port

    async def _execute_internal(
        self, request: RelationshipSearchRequestDTO
    ) -> RelationshipSearchResponseDTO:
        """Execute relationship search operation.

        Args:
            request: Relationship search request

        Returns:
            Relationship search response with results

        Raises:
            AuthorizationError: When user lacks permission
            NotFoundError: When knowledge graph is not found
            ValidationError: When search parameters are invalid
        """
        start_time = time.time()

        # Check authorization
        if not self.authorization_port.check_permission(
            request.user_id, request.kg_id, "read"
        ):
            raise AuthorizationError(
                f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}"
            )

        try:
            # Set default pagination if not provided
            page = 1
            page_size = 20
            if request.pagination:
                page = request.pagination.page
                page_size = request.pagination.page_size

            # Perform relationship search
            relationships_data, total_count = (
                self.relationship_search_port.search_relationships(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    source_node_id=request.source_node_id,
                    target_node_id=request.target_node_id,
                    relationship_types=request.relationship_types,
                    pattern=request.pattern,
                    property_filters=request.property_filters,
                    page=page,
                    page_size=page_size,
                )
            )

            # Transform results to DTOs
            relationship_dtos = []
            for rel_data in relationships_data:
                relationship_dto = RelationshipDTO(
                    id=rel_data["id"],
                    source_node_id=rel_data["source_node_id"],
                    target_node_id=rel_data["target_node_id"],
                    relationship_type=rel_data["relationship_type"],
                    properties=rel_data.get("properties", {}),
                    source_node_label=rel_data.get("source_node_label", ""),
                    target_node_label=rel_data.get("target_node_label", ""),
                    weight=rel_data.get("weight"),
                )
                relationship_dtos.append(relationship_dto)

            processing_time_ms = (time.time() - start_time) * 1000

            return RelationshipSearchResponseDTO(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                relationships=relationship_dtos,
                total_relationships=total_count,
                pattern_matched=request.pattern,
                processing_time_ms=processing_time_ms,
                search_timestamp=datetime.now(),
            )

        except Exception as e:
            if "not found" in str(e).lower():
                raise NotFoundError(f"Knowledge graph {request.kg_id} not found")
            raise ValidationError(f"Relationship search failed: {str(e)}")

    def _validate_request_internal(self, request: RelationshipSearchRequestDTO) -> None:
        """Validate relationship search request.

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

        # Validate source node ID if provided
        if request.source_node_id is not None:
            if (
                not isinstance(request.source_node_id, str)
                or not request.source_node_id.strip()
            ):
                raise ValidationError(
                    "source_node_id must be a non-empty string if provided"
                )

        # Validate target node ID if provided
        if request.target_node_id is not None:
            if (
                not isinstance(request.target_node_id, str)
                or not request.target_node_id.strip()
            ):
                raise ValidationError(
                    "target_node_id must be a non-empty string if provided"
                )

        # Validate relationship types if provided
        if request.relationship_types is not None:
            if not isinstance(request.relationship_types, list):
                raise ValidationError("relationship_types must be a list")

            if not all(
                isinstance(rel_type, str) for rel_type in request.relationship_types
            ):
                raise ValidationError("All relationship types must be strings")

            if len(request.relationship_types) == 0:
                raise ValidationError("relationship_types cannot be empty if provided")

        # Validate pattern if provided
        if request.pattern is not None:
            if not isinstance(request.pattern, str) or not request.pattern.strip():
                raise ValidationError("pattern must be a non-empty string if provided")

            # Basic pattern validation - check for common Cypher-like patterns
            pattern = request.pattern.strip()
            if not (pattern.startswith("(") or pattern.startswith("MATCH")):
                raise ValidationError(
                    "pattern should be a valid Cypher-like pattern starting with '(' or 'MATCH'"
                )

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

        # Validate pagination if provided
        if request.pagination is not None:
            if request.pagination.page < 1:
                raise ValidationError("Page must be greater than or equal to 1")

            if request.pagination.page_size < 1:
                raise ValidationError("Page size must be greater than or equal to 1")

            if request.pagination.page_size > 1000:
                raise ValidationError("Page size cannot exceed 1000")

        # Ensure at least one search criterion is provided
        if (
            not request.source_node_id
            and not request.target_node_id
            and not request.relationship_types
            and not request.pattern
            and not request.property_filters
        ):
            raise ValidationError("At least one search criterion must be provided")

        # Validate that pattern is not used with conflicting parameters
        if request.pattern and (
            request.source_node_id
            or request.target_node_id
            or request.relationship_types
        ):
            raise ValidationError(
                "pattern cannot be used together with source_node_id, target_node_id, or relationship_types"
            )

    def _validate_cypher_pattern(self, pattern: str) -> bool:
        """Validate basic Cypher pattern syntax.

        Args:
            pattern: Cypher pattern to validate

        Returns:
            True if pattern appears valid, False otherwise
        """
        # Basic validation for common Cypher patterns
        pattern = pattern.strip()

        # Check for balanced parentheses and brackets
        paren_count = pattern.count("(") - pattern.count(")")
        bracket_count = pattern.count("[") - pattern.count("]")

        if paren_count != 0 or bracket_count != 0:
            return False

        # Check for basic pattern structure
        if pattern.startswith("MATCH"):
            return True

        if pattern.startswith("(") and pattern.endswith(")"):
            return True

        # Check for relationship patterns like (a)-[r]->(b)
        if "(" in pattern and ")" in pattern and ("-" in pattern or "--" in pattern):
            return True

        return False
