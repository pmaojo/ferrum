from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.exceptions import ApplicationError, ValidationError
from application.ports import BackupRepositoryPort, BackupStoragePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO
from domain.entities import GraphBackup


@dataclass
class BackupSystemDataRequest(TenantScopedRequestDTO):
    """Request to create a system data backup."""

    kg_id: str


@dataclass
class BackupSystemDataResponse(BaseResponseDTO):
    """Response returned after creating a backup."""

    backup: Optional[GraphBackup] = None


class BackupSystemDataUseCase(
    BaseUseCase[BackupSystemDataRequest, BackupSystemDataResponse]
):
    """Use case for backing up system data."""

    def __init__(
        self,
        backup_repository: BackupRepositoryPort,
        storage: BackupStoragePort,
        tracer: TracingPort,
    ):
        super().__init__()
        self.backup_repository = backup_repository
        self.storage = storage
        self.tracer = tracer

    def _validate_request_internal(self, request: BackupSystemDataRequest) -> None:
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

    async def _execute_internal(
        self, request: BackupSystemDataRequest
    ) -> BackupSystemDataResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="backup_system_data",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
        ):
            try:
                # Create the backup using the storage port
                backup_location = self.storage.create_backup(
                    kg_id=request.kg_id, tenant_id=request.tenant_id
                )

                # Create a backup entity to track the backup metadata
                backup = GraphBackup.create(
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                    location=backup_location,
                )

                # Store the backup metadata in the repository
                saved_backup = self.backup_repository.create(backup)

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_backup_created",
                    value=1,
                    tenant_id=request.tenant_id,
                )

                return BackupSystemDataResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    backup=saved_backup,
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_backup_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, ValidationError):
                    return BackupSystemDataResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to backup system data: {e}",
                    error_code="BACKUP_FAILED",
                ) from e
