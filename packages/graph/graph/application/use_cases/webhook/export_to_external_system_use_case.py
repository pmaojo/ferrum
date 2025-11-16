"""Export to external system use case implementation."""

import uuid
from datetime import datetime
from typing import Any, Dict

from application.ports.base import ExternalDataExportPort
from application.ports.security import AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    ExportToExternalSystemRequestDTO,
    ExternalDataExportResultDTO,
)
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)
from domain.exceptions import NotFoundError, ValidationError


class ExportToExternalSystemUseCase(
    BaseUseCase[ExportToExternalSystemRequestDTO, ExternalDataExportResultDTO]
):
    """Use case for exporting data to external systems."""

    # Valid target types
    VALID_TARGET_TYPES = ["api", "database", "file", "webhook"]

    # Valid export formats
    VALID_EXPORT_FORMATS = ["json", "rdf", "csv", "xml", "turtle", "n-triples"]

    def __init__(
        self,
        external_data_export_service: ExternalDataExportPort,
        kg_repository: KnowledgeGraphRepositoryPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            external_data_export_service: Service for external data export
            kg_repository: Repository for knowledge graph operations
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.external_data_export_service = external_data_export_service
        self.kg_repository = kg_repository
        self.authorization_service = authorization_service

    def execute(
        self, request: ExportToExternalSystemRequestDTO
    ) -> ExternalDataExportResultDTO:
        """Execute the export to external system use case.

        Args:
            request: Export to external system request DTO

        Returns:
            External data export result DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            NotFoundError: When source knowledge graph is not found
        """
        # Validate input
        self._validate_input(request)

        # Check authorization for knowledge graph access
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="knowledge_graph",
            action="read",
            resource_id=request.kg_id,
            tenant_id=request.tenant_id,
        )

        # Verify source knowledge graph exists
        kg = self.kg_repository.get_by_id(request.kg_id, request.tenant_id)
        if not kg:
            raise NotFoundError(f"Knowledge graph with ID {request.kg_id} not found")

        # Perform export
        try:
            export_result = self.external_data_export_service.export_to_target(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                target_type=request.target_type,
                target_config=request.target_config,
                export_format=request.export_format,
                export_filters=request.export_filters,
                transformation_rules=request.transformation_rules,
            )

            return ExternalDataExportResultDTO(
                export_id=export_result.get("export_id", str(uuid.uuid4())),
                kg_id=request.kg_id,
                target_type=request.target_type,
                export_format=request.export_format,
                status=export_result.get("status", "completed"),
                records_exported=export_result.get("records_exported", 0),
                records_failed=export_result.get("records_failed", 0),
                started_at=datetime.now(),
                completed_at=(
                    datetime.now()
                    if export_result.get("status") == "completed"
                    else None
                ),
                error_message=export_result.get("error_message"),
                export_location=export_result.get("export_location"),
                summary=export_result.get("summary", {}),
            )

        except Exception as e:
            # Return failed export result
            return ExternalDataExportResultDTO(
                export_id=str(uuid.uuid4()),
                kg_id=request.kg_id,
                target_type=request.target_type,
                export_format=request.export_format,
                status="failed",
                records_exported=0,
                records_failed=0,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error_message=str(e),
                export_location=None,
                summary={},
            )

    def _validate_input(self, request: ExportToExternalSystemRequestDTO) -> None:
        """Validate the export to external system request.

        Args:
            request: Export to external system request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate kg_id
        if not request.kg_id or not request.kg_id.strip():
            raise ValidationError("Knowledge graph ID is required", "kg_id")

        # Validate target_type
        if (
            not request.target_type
            or request.target_type not in self.VALID_TARGET_TYPES
        ):
            raise ValidationError(
                f"Invalid target type. Must be one of: {', '.join(self.VALID_TARGET_TYPES)}",
                "target_type",
            )

        # Validate target_config
        if not request.target_config or not isinstance(request.target_config, dict):
            raise ValidationError(
                "Target configuration is required and must be a dictionary",
                "target_config",
            )

        # Validate target_config based on target_type
        self._validate_target_config(request.target_type, request.target_config)

        # Validate export_format
        if request.export_format not in self.VALID_EXPORT_FORMATS:
            raise ValidationError(
                f"Invalid export format. Must be one of: {', '.join(self.VALID_EXPORT_FORMATS)}",
                "export_format",
            )

        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

        # Validate export_filters if provided
        if request.export_filters is not None and not isinstance(
            request.export_filters, dict
        ):
            raise ValidationError(
                "Export filters must be a dictionary", "export_filters"
            )

        # Validate transformation_rules if provided
        if request.transformation_rules is not None and not isinstance(
            request.transformation_rules, dict
        ):
            raise ValidationError(
                "Transformation rules must be a dictionary", "transformation_rules"
            )

    def _validate_target_config(
        self, target_type: str, target_config: Dict[str, Any]
    ) -> None:
        """Validate target configuration based on target type.

        Args:
            target_type: Type of external target
            target_config: Target configuration dictionary

        Raises:
            ValidationError: When target configuration is invalid
        """
        if target_type == "api":
            required_fields = ["url", "method"]
            for field in required_fields:
                if field not in target_config:
                    raise ValidationError(
                        f"API target config missing required field: {field}",
                        "target_config",
                    )

            # Validate HTTP method
            valid_methods = ["POST", "PUT", "PATCH"]
            if target_config["method"].upper() not in valid_methods:
                raise ValidationError(
                    f"Invalid HTTP method for export. Must be one of: {', '.join(valid_methods)}",
                    "target_config",
                )

        elif target_type == "database":
            required_fields = ["connection_string", "table_name"]
            for field in required_fields:
                if field not in target_config:
                    raise ValidationError(
                        f"Database target config missing required field: {field}",
                        "target_config",
                    )

        elif target_type == "file":
            required_fields = ["file_path"]
            for field in required_fields:
                if field not in target_config:
                    raise ValidationError(
                        f"File target config missing required field: {field}",
                        "target_config",
                    )

        elif target_type == "webhook":
            required_fields = ["webhook_url", "secret"]
            for field in required_fields:
                if field not in target_config:
                    raise ValidationError(
                        f"Webhook target config missing required field: {field}",
                        "target_config",
                    )
