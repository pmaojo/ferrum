"""Use case for exporting graph visualizations to various formats."""

import base64
import time
from datetime import datetime
from typing import Any, Dict

from application.exceptions import NotFoundError, ValidationError
from application.ports import (
    AuthorizationServicePort,
    GraphVisualizationPort,
    TracingPort,
    VisualizationLayoutRepositoryPort,
)
from application.use_cases.dto import (
    ExportVisualizationRequestDTO,
    VisualizationExportDTO,
)
from domain.exceptions import VisualizationError


class ExportVisualizationUseCase:
    """Use case for exporting graph visualizations to various formats."""

    def __init__(
        self,
        graph_visualization_port: GraphVisualizationPort,
        layout_repository: VisualizationLayoutRepositoryPort,
        authorization_service: AuthorizationServicePort,
        tracing_port: TracingPort,
    ):
        """Initialize the use case with required ports.

        Args:
            graph_visualization_port: Port for graph visualization operations
            authorization_service: Port for authorization checks
            tracing_port: Port for observability tracing
        """
        self.graph_visualization_port = graph_visualization_port
        self.layout_repository = layout_repository
        self.authorization_service = authorization_service
        self.tracing_port = tracing_port

    def execute(self, request: ExportVisualizationRequestDTO) -> VisualizationExportDTO:
        """Execute visualization export.

        Args:
            request: Request containing export parameters

        Returns:
            Visualization export results

        Raises:
            ValidationError: When request parameters are invalid
            NotFoundError: When knowledge graph or visualization is not found
            VisualizationError: When export fails
        """
        start_time = time.time()

        with self.tracing_port.start_span(
            name="export_visualization",
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            export_format=request.export_format,
        ):
            # Validate input
            self._validate_request(request)

            # Check authorization
            self.authorization_service.check_permission(
                user_id=request.user_id, resource_id=request.kg_id, action="read"
            )

            try:
                # First, generate the visualization layout if needed
                layout_data = self._get_or_generate_layout_data(request)

                # Export visualization
                export_data = self.graph_visualization_port.export_visualization(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    layout_data=layout_data,
                    export_format=request.export_format,
                    width=request.width,
                    height=request.height,
                    include_metadata=request.include_metadata,
                )

                # Convert to DTO
                export_dto = self._convert_export_to_dto(
                    export_data=export_data, request=request
                )

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000
                export_dto.processing_time_ms = processing_time_ms

                # Record metrics
                self.tracing_port.record_metric(
                    name="visualization_export_duration_ms",
                    value=processing_time_ms,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                    export_format=request.export_format,
                )

                self.tracing_port.record_metric(
                    name="visualization_export_size_bytes",
                    value=export_dto.file_size_bytes,
                    tenant_id=request.tenant_id,
                    kg_id=request.kg_id,
                    export_format=request.export_format,
                )

                return export_dto

            except Exception as e:
                if isinstance(e, (ValidationError, NotFoundError)):
                    raise
                raise VisualizationError(f"Visualization export failed: {str(e)}")

    def _validate_request(self, request: ExportVisualizationRequestDTO) -> None:
        """Validate the export request.

        Args:
            request: Request to validate

        Raises:
            ValidationError: When validation fails
        """
        if not request.kg_id:
            raise ValidationError(
                message="Knowledge graph ID is required", field="kg_id"
            )

        if not request.tenant_id:
            raise ValidationError(message="Tenant ID is required", field="tenant_id")

        if not request.user_id:
            raise ValidationError(message="User ID is required", field="user_id")

        if not request.visualization_id:
            raise ValidationError(
                message="Visualization ID is required", field="visualization_id"
            )

        # Validate export format
        supported_formats = [
            "svg",
            "png",
            "pdf",
            "json",
            "graphml",
            "gexf",
            "dot",
            "cypher",
        ]

        if request.export_format not in supported_formats:
            raise ValidationError(
                message=(
                    f"Unsupported export format: {request.export_format}. "
                    f"Supported formats: {', '.join(supported_formats)}"
                ),
                field="export_format",
            )

        # Validate dimensions for image formats
        image_formats = ["svg", "png", "pdf"]
        if request.export_format in image_formats:
            if request.width < 100 or request.width > 10000:
                raise ValidationError(
                    message="Width must be between 100 and 10000 pixels", field="width"
                )

            if request.height < 100 or request.height > 10000:
                raise ValidationError(
                    message="Height must be between 100 and 10000 pixels",
                    field="height",
                )

    def _get_or_generate_layout_data(
        self, request: ExportVisualizationRequestDTO
    ) -> Dict[str, Any]:
        """Get existing layout data or generate new layout for export.

        Args:
            request: Export request

        Returns:
            Layout data dictionary

        Note:
            This method first attempts to retrieve cached layout data
            using the provided visualization identifier. A new layout is
            generated only when no cached data exists.
        """
        existing_layout = self.layout_repository.get_layout(
            visualization_id=request.visualization_id,
            tenant_id=request.tenant_id,
        )
        if existing_layout:
            return existing_layout

        return self.graph_visualization_port.generate_layout(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            algorithm="force_directed",  # Default algorithm
            node_limit=1000,
            include_communities=False,
            filters={},
        )

    def _convert_export_to_dto(
        self, export_data: Dict[str, Any], request: ExportVisualizationRequestDTO
    ) -> VisualizationExportDTO:
        """Convert export data to DTO.

        Args:
            export_data: Raw export data from visualization port
            request: Original request

        Returns:
            VisualizationExportDTO object
        """
        # Extract file content and metadata
        file_content = export_data.get("content", "")
        file_size_bytes = export_data.get("size_bytes", len(file_content))
        metadata = export_data.get("metadata", {})

        # Encode binary content as base64 for binary formats
        binary_formats = ["png", "pdf"]
        if request.export_format in binary_formats:
            if isinstance(file_content, bytes):
                file_content = base64.b64encode(file_content).decode("utf-8")
            elif isinstance(file_content, str):
                # Assume it's already base64 encoded
                pass

        # Add export-specific metadata
        export_metadata = {
            **metadata,
            "export_format": request.export_format,
            "dimensions": (
                {"width": request.width, "height": request.height}
                if request.export_format in ["svg", "png", "pdf"]
                else None
            ),
            "include_metadata": request.include_metadata,
            "visualization_id": request.visualization_id,
        }

        return VisualizationExportDTO(
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            export_format=request.export_format,
            file_content=file_content,
            file_size_bytes=file_size_bytes,
            metadata=export_metadata,
            export_timestamp=datetime.utcnow(),
            processing_time_ms=0.0,  # Will be set by caller
        )
