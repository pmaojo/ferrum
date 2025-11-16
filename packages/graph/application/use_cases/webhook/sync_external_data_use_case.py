"""Sync external data use case implementation."""

import uuid
from datetime import datetime
from typing import Any, Dict

from application.ports.base import ExternalDataSyncPort
from application.ports.security import AuthorizationPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    ExternalDataSyncResultDTO,
    SyncExternalDataRequestDTO,
)
from application.use_cases.knowledge_graph.create_knowledge_graph_use_case import (
    KnowledgeGraphRepositoryPort,
)
from domain.exceptions import NotFoundError, ValidationError


class SyncExternalDataUseCase(
    BaseUseCase[SyncExternalDataRequestDTO, ExternalDataSyncResultDTO]
):
    """Use case for synchronizing data from external systems."""

    # Valid source types
    VALID_SOURCE_TYPES = ["api", "database", "file", "webhook"]

    # Valid sync modes
    VALID_SYNC_MODES = ["full", "incremental", "delta"]

    def __init__(
        self,
        external_data_sync_service: ExternalDataSyncPort,
        kg_repository: KnowledgeGraphRepositoryPort,
        authorization_service: AuthorizationPort,
    ):
        """Initialize the use case.

        Args:
            external_data_sync_service: Service for external data synchronization
            kg_repository: Repository for knowledge graph operations
            authorization_service: Service for authorization checks
        """
        super().__init__()
        self.external_data_sync_service = external_data_sync_service
        self.kg_repository = kg_repository
        self.authorization_service = authorization_service

    def execute(self, request: SyncExternalDataRequestDTO) -> ExternalDataSyncResultDTO:
        """Execute the sync external data use case.

        Args:
            request: Sync external data request DTO

        Returns:
            External data sync result DTO

        Raises:
            ValidationError: When input validation fails
            AuthorizationError: When user lacks permission
            NotFoundError: When target knowledge graph is not found
        """
        # Validate input
        self._validate_input(request)

        # Check authorization for knowledge graph access
        self.authorization_service.check_permission(
            user_id=request.user_id,
            resource_type="knowledge_graph",
            action="update",
            resource_id=request.target_kg_id,
            tenant_id=request.tenant_id,
        )

        # Verify target knowledge graph exists
        kg = self.kg_repository.get_by_id(request.target_kg_id, request.tenant_id)
        if not kg:
            raise NotFoundError(
                f"Knowledge graph with ID {request.target_kg_id} not found"
            )

        # Perform synchronization
        try:
            sync_result = self.external_data_sync_service.sync_from_source(
                source_type=request.source_type,
                source_config=request.source_config,
                target_kg_id=request.target_kg_id,
                tenant_id=request.tenant_id,
                sync_mode=request.sync_mode,
                transformation_rules=request.transformation_rules,
            )

            return ExternalDataSyncResultDTO(
                sync_id=sync_result.get("sync_id", str(uuid.uuid4())),
                source_type=request.source_type,
                target_kg_id=request.target_kg_id,
                sync_mode=request.sync_mode,
                status=sync_result.get("status", "completed"),
                records_processed=sync_result.get("records_processed", 0),
                records_imported=sync_result.get("records_imported", 0),
                records_failed=sync_result.get("records_failed", 0),
                started_at=datetime.now(),
                completed_at=(
                    datetime.now() if sync_result.get("status") == "completed" else None
                ),
                error_message=sync_result.get("error_message"),
                summary=sync_result.get("summary", {}),
            )

        except Exception as e:
            # Return failed sync result
            return ExternalDataSyncResultDTO(
                sync_id=str(uuid.uuid4()),
                source_type=request.source_type,
                target_kg_id=request.target_kg_id,
                sync_mode=request.sync_mode,
                status="failed",
                records_processed=0,
                records_imported=0,
                records_failed=0,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error_message=str(e),
                summary={},
            )

    def _validate_input(self, request: SyncExternalDataRequestDTO) -> None:
        """Validate the sync external data request.

        Args:
            request: Sync external data request DTO

        Raises:
            ValidationError: When validation fails
        """
        # Validate source_type
        if (
            not request.source_type
            or request.source_type not in self.VALID_SOURCE_TYPES
        ):
            raise ValidationError(
                f"Invalid source type. Must be one of: {', '.join(self.VALID_SOURCE_TYPES)}",
                "source_type",
            )

        # Validate source_config
        if not request.source_config or not isinstance(request.source_config, dict):
            raise ValidationError(
                "Source configuration is required and must be a dictionary",
                "source_config",
            )

        # Validate source_config based on source_type
        self._validate_source_config(request.source_type, request.source_config)

        # Validate target_kg_id
        if not request.target_kg_id or not request.target_kg_id.strip():
            raise ValidationError(
                "Target knowledge graph ID is required", "target_kg_id"
            )

        # Validate sync_mode
        if request.sync_mode not in self.VALID_SYNC_MODES:
            raise ValidationError(
                f"Invalid sync mode. Must be one of: {', '.join(self.VALID_SYNC_MODES)}",
                "sync_mode",
            )

        # Validate tenant_id
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError("Tenant ID is required", "tenant_id")

        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            raise ValidationError("User ID is required", "user_id")

        # Validate transformation_rules if provided
        if request.transformation_rules is not None and not isinstance(
            request.transformation_rules, dict
        ):
            raise ValidationError(
                "Transformation rules must be a dictionary", "transformation_rules"
            )

    def _validate_source_config(
        self, source_type: str, source_config: Dict[str, Any]
    ) -> None:
        """Validate source configuration based on source type.

        Args:
            source_type: Type of external source
            source_config: Source configuration dictionary

        Raises:
            ValidationError: When source configuration is invalid
        """
        if source_type == "api":
            required_fields = ["url", "method"]
            for field in required_fields:
                if field not in source_config:
                    raise ValidationError(
                        f"API source config missing required field: {field}",
                        "source_config",
                    )

            # Validate HTTP method
            valid_methods = ["GET", "POST", "PUT", "PATCH"]
            if source_config["method"].upper() not in valid_methods:
                raise ValidationError(
                    f"Invalid HTTP method. Must be one of: {', '.join(valid_methods)}",
                    "source_config",
                )

        elif source_type == "database":
            required_fields = ["connection_string", "query"]
            for field in required_fields:
                if field not in source_config:
                    raise ValidationError(
                        f"Database source config missing required field: {field}",
                        "source_config",
                    )

        elif source_type == "file":
            required_fields = ["file_path", "format"]
            for field in required_fields:
                if field not in source_config:
                    raise ValidationError(
                        f"File source config missing required field: {field}",
                        "source_config",
                    )

            # Validate file format
            valid_formats = ["json", "csv", "xml", "rdf", "ttl"]
            if source_config["format"] not in valid_formats:
                raise ValidationError(
                    f"Invalid file format. Must be one of: {', '.join(valid_formats)}",
                    "source_config",
                )

        elif source_type == "webhook":
            required_fields = ["webhook_id"]
            for field in required_fields:
                if field not in source_config:
                    raise ValidationError(
                        f"Webhook source config missing required field: {field}",
                        "source_config",
                    )
