"""Use case for exporting knowledge graphs in different formats."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from application.ports import GraphExportPort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from domain.entities import KnowledgeGraph


class ExportFormat(str, Enum):
    """Supported export formats for knowledge graphs."""

    RDF_TURTLE = "rdf_turtle"
    RDF_XML = "rdf_xml"
    RDF_N_TRIPLES = "rdf_n_triples"
    RDF_JSON_LD = "rdf_json_ld"
    OWL_MANCHESTER = "owl_manchester"
    OWL_XML = "owl_xml"
    OWL_FUNCTIONAL = "owl_functional"
    JSON = "json"
    CYPHER = "cypher"


@dataclass
class ExportKnowledgeGraphRequest(TenantScopedRequestDTO):
    """Request to export a knowledge graph."""

    kg_id: str
    format: ExportFormat
    include_metadata: bool = True
    ontology_version_id: Optional[str] = None  # Required for OWL formats


@dataclass
class ExportKnowledgeGraphResponse(BaseResponseDTO):
    """Response from knowledge graph export."""

    exported_data: Optional[str] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None


# Repository port for knowledge graphs (reusing from create use case)
from abc import abstractmethod
from typing import Protocol


class KnowledgeGraphRepositoryPort(Protocol):
    """Port for knowledge graph repository operations."""

    @abstractmethod
    def get_by_id(self, kg_id: str, tenant_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph by ID and tenant.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier

        Returns:
            Knowledge graph entity if found, None otherwise
        """
        ...


# Authorization service port
class AuthorizationServicePort(Protocol):
    """Port for authorization service operations."""

    @abstractmethod
    def check_permission(self, user_id: str, resource_id: str, action: str) -> None:
        """Check if user has permission to perform action on resource.

        Args:
            user_id: User identifier
            resource_id: Resource identifier
            action: Action to check permission for

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        ...


class ExportKnowledgeGraphUseCase(
    BaseUseCase[ExportKnowledgeGraphRequest, ExportKnowledgeGraphResponse]
):
    """Use case for exporting knowledge graphs in different formats."""

    def __init__(
        self,
        kg_repository: KnowledgeGraphRepositoryPort,
        graph_export_adapter: GraphExportPort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            kg_repository: Repository for knowledge graph operations
            graph_export_adapter: Adapter for graph export operations
            authorization_service: Service for authorization checks
            tracer: Tracing service for observability
        """
        super().__init__()
        self.kg_repository = kg_repository
        self.graph_export_adapter = graph_export_adapter
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(self, request: ExportKnowledgeGraphRequest) -> None:
        """Validate the export knowledge graph request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError(
                message="Knowledge graph ID is required and cannot be empty",
                field="kg_id",
            )

        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not isinstance(request.format, ExportFormat):
            raise ValidationError(
                message="Export format must be a valid ExportFormat", field="format"
            )

        # Validate OWL format requirements
        if request.format in [
            ExportFormat.OWL_MANCHESTER,
            ExportFormat.OWL_XML,
            ExportFormat.OWL_FUNCTIONAL,
        ]:
            if (
                not request.ontology_version_id
                or not request.ontology_version_id.strip()
            ):
                raise ValidationError(
                    message="Ontology version ID is required for OWL export formats",
                    field="ontology_version_id",
                )

    async def _execute_internal(
        self, request: ExportKnowledgeGraphRequest
    ) -> ExportKnowledgeGraphResponse:
        """Execute the knowledge graph export.

        Args:
            request: The validated request

        Returns:
            Response containing the exported graph data

        Raises:
            NotFoundError: If knowledge graph doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="export_knowledge_graph",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
            format=request.format.value,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    user_id=request.user_id, resource_id=request.kg_id, action="read"
                )

                # Get knowledge graph
                kg = self.kg_repository.get_by_id(request.kg_id, request.tenant_id)
                if not kg:
                    raise NotFoundError(
                        message=f"Knowledge graph with ID '{request.kg_id}' not found",
                        resource_type="knowledge_graph",
                        resource_id=request.kg_id,
                    )

                # Export based on format
                exported_data = await self._export_graph(request, kg)

                # Calculate size
                size_bytes = len(exported_data.encode("utf-8"))

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="knowledge_graph_exported",
                    value=1,
                    tenant_id=request.tenant_id,
                    format=request.format.value,
                    size_bytes=size_bytes,
                )

                return ExportKnowledgeGraphResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    exported_data=exported_data,
                    format=request.format.value,
                    size_bytes=size_bytes,
                )

            except Exception as e:
                # Record error metrics
                original_error_type = type(e).__name__
                self.tracer.record_metric(
                    name="knowledge_graph_export_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=original_error_type,
                    format=request.format.value,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(e, (ValidationError, NotFoundError, AuthorizationError)):
                    return ExportKnowledgeGraphResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to export knowledge graph: {str(e)}",
                    error_code="KNOWLEDGE_GRAPH_EXPORT_FAILED",
                ) from e

    async def _export_graph(
        self, request: ExportKnowledgeGraphRequest, kg: KnowledgeGraph
    ) -> str:
        """Export the knowledge graph in the requested format.

        Args:
            request: The export request
            kg: The knowledge graph entity

        Returns:
            Exported graph data as string

        Raises:
            ApplicationError: If export fails
        """
        try:
            # RDF formats
            if request.format == ExportFormat.RDF_TURTLE:
                return self.graph_export_adapter.export_to_rdf(
                    kg_id=request.kg_id, tenant_id=request.tenant_id, format="turtle"
                )
            elif request.format == ExportFormat.RDF_XML:
                return self.graph_export_adapter.export_to_rdf(
                    kg_id=request.kg_id, tenant_id=request.tenant_id, format="xml"
                )
            elif request.format == ExportFormat.RDF_N_TRIPLES:
                return self.graph_export_adapter.export_to_rdf(
                    kg_id=request.kg_id, tenant_id=request.tenant_id, format="n-triples"
                )
            elif request.format == ExportFormat.RDF_JSON_LD:
                return self.graph_export_adapter.export_to_rdf(
                    kg_id=request.kg_id, tenant_id=request.tenant_id, format="json-ld"
                )

            # OWL formats
            elif request.format == ExportFormat.OWL_MANCHESTER:
                return self.graph_export_adapter.export_to_owl(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    ontology_version_id=request.ontology_version_id,
                    format="manchester",
                )
            elif request.format == ExportFormat.OWL_XML:
                return self.graph_export_adapter.export_to_owl(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    ontology_version_id=request.ontology_version_id,
                    format="xml",
                )
            elif request.format == ExportFormat.OWL_FUNCTIONAL:
                return self.graph_export_adapter.export_to_owl(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    ontology_version_id=request.ontology_version_id,
                    format="functional",
                )

            # JSON format
            elif request.format == ExportFormat.JSON:
                return self.graph_export_adapter.export_to_json(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    include_metadata=request.include_metadata,
                )

            elif request.format == ExportFormat.CYPHER:
                return self.graph_export_adapter.export_to_cypher(
                    kg_id=request.kg_id, tenant_id=request.tenant_id
                )

            else:
                raise ApplicationError(
                    message=f"Unsupported export format: {request.format}",
                    error_code="UNSUPPORTED_EXPORT_FORMAT",
                )

        except Exception as e:
            if isinstance(e, ApplicationError):
                raise

            raise ApplicationError(
                message=f"Export failed for format {request.format.value}: {str(e)}",
                error_code="EXPORT_OPERATION_FAILED",
            ) from e
