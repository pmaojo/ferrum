"""Faceted search use case for navigating knowledge graphs with faceted filters."""

import time
from datetime import datetime
from typing import Dict, List

from application.exceptions import AuthorizationError, NotFoundError, ValidationError
from application.ports import AuthorizationPort, FacetedSearchPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    FacetDTO,
    FacetedSearchRequestDTO,
    FacetedSearchResponseDTO,
    FacetValueDTO,
    SearchResultDTO,
)


class FacetedSearchUseCase(
    BaseUseCase[FacetedSearchRequestDTO, FacetedSearchResponseDTO]
):
    """Use case for performing faceted search with navigation filters."""

    def __init__(
        self,
        faceted_search_port: FacetedSearchPort,
        authorization_port: AuthorizationPort,
    ):
        """Initialize the faceted search use case.

        Args:
            faceted_search_port: Port for faceted search operations
            authorization_port: Port for authorization checks
        """
        super().__init__()
        self.faceted_search_port = faceted_search_port
        self.authorization_port = authorization_port

    async def _execute_internal(
        self, request: FacetedSearchRequestDTO
    ) -> FacetedSearchResponseDTO:
        """Execute faceted search operation.

        Args:
            request: Faceted search request

        Returns:
            Faceted search response with results and facets

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
                message=f"User {request.user_id} lacks read permission for knowledge graph {request.kg_id}",
                user_id=request.user_id,
                resource_type="knowledge_graph",
                resource_id=request.kg_id,
                required_permission="read",
            )

        try:
            # Set default pagination if not provided
            pagination = (
                request.pagination
                or type("obj", (object,), {"page": 1, "page_size": 20})()
            )

            # Perform faceted search
            search_result = self.faceted_search_port.search_with_facets(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                query=request.query,
                selected_facets=request.selected_facets or {},
                facet_fields=request.facet_fields,
                page=pagination.page,
                page_size=pagination.page_size,
            )

            # Transform search results to DTOs
            result_dtos = []
            for result in search_result.get("results", []):
                result_dto = SearchResultDTO(
                    node_id=result["node_id"],
                    node_type=result["node_type"],
                    label=result.get("label", ""),
                    properties=result.get("properties", {}),
                    score=result.get("score", 1.0),
                    snippet=result.get("snippet"),
                )
                result_dtos.append(result_dto)

            # Transform facets to DTOs
            facet_dtos = []
            for facet_data in search_result.get("facets", []):
                facet_values = []
                for value_data in facet_data.get("values", []):
                    facet_value = FacetValueDTO(
                        value=value_data["value"],
                        count=value_data["count"],
                        selected=self._is_facet_value_selected(
                            facet_data["field"],
                            value_data["value"],
                            request.selected_facets or {},
                        ),
                    )
                    facet_values.append(facet_value)

                facet_dto = FacetDTO(
                    field=facet_data["field"],
                    label=facet_data.get("label", facet_data["field"]),
                    values=facet_values,
                    total_values=len(facet_values),
                )
                facet_dtos.append(facet_dto)

            processing_time_ms = (time.time() - start_time) * 1000

            return FacetedSearchResponseDTO(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                query=request.query,
                results=result_dtos,
                facets=facet_dtos,
                total_results=search_result.get("total_results", len(result_dtos)),
                applied_filters=request.selected_facets or {},
                processing_time_ms=processing_time_ms,
                search_timestamp=datetime.now(),
            )

        except Exception as e:
            if "not found" in str(e).lower():
                raise NotFoundError(
                    message=f"Knowledge graph {request.kg_id} not found",
                    resource_type="knowledge_graph",
                    resource_id=request.kg_id,
                )
            raise ValidationError(f"Faceted search failed: {str(e)}")

    def _validate_request_internal(self, request: FacetedSearchRequestDTO) -> None:
        """Validate faceted search request.

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

        # Validate pagination if provided
        if request.pagination:
            if request.pagination.page <= 0:
                raise ValidationError("Page must be greater than 0")

            if request.pagination.page_size <= 0:
                raise ValidationError("Page size must be greater than 0")

            if request.pagination.page_size > 1000:
                raise ValidationError("Page size cannot exceed 1000")

        # Validate selected facets if provided
        if request.selected_facets:
            if not isinstance(request.selected_facets, dict):
                raise ValidationError("Selected facets must be a dictionary")

            for field, values in request.selected_facets.items():
                if not isinstance(field, str):
                    raise ValidationError("Facet field names must be strings")

                if not isinstance(values, list):
                    raise ValidationError(
                        f"Facet values for field '{field}' must be a list"
                    )

                if not all(isinstance(value, str) for value in values):
                    raise ValidationError(
                        f"All facet values for field '{field}' must be strings"
                    )

        # Validate facet fields if provided
        if request.facet_fields:
            if not isinstance(request.facet_fields, list):
                raise ValidationError("Facet fields must be a list")

            if not all(isinstance(field, str) for field in request.facet_fields):
                raise ValidationError("All facet fields must be strings")

            if len(request.facet_fields) > 50:
                raise ValidationError("Cannot request more than 50 facet fields")

    def _is_facet_value_selected(
        self, field: str, value: str, selected_facets: Dict[str, List[str]]
    ) -> bool:
        """Check if a facet value is currently selected.

        Args:
            field: Facet field name
            value: Facet value to check
            selected_facets: Currently selected facets

        Returns:
            True if the facet value is selected, False otherwise
        """
        return field in selected_facets and value in selected_facets[field]
