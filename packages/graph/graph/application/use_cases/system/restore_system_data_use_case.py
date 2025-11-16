from dataclasses import dataclass
from datetime import datetime

from application.exceptions import ApplicationError, NotFoundError, ValidationError
from application.ports import BackupRepositoryPort, BackupStoragePort, TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO, TenantScopedRequestDTO


@dataclass
class RestoreSystemDataRequest(TenantScopedRequestDTO):
    """Request to restore system data from a backup."""

    backup_id: str
    kg_id: str


@dataclass
class RestoreSystemDataResponse(BaseResponseDTO):
    """Response returned after restoring a backup."""

    restored: bool = False


class RestoreSystemDataUseCase(
    BaseUseCase[RestoreSystemDataRequest, RestoreSystemDataResponse]
):
    """Use case for restoring system data from a backup."""

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

    def _validate_request_internal(self, request: RestoreSystemDataRequest) -> None:
        if not request.backup_id or not request.backup_id.strip():
            raise ValidationError(
                message="Backup ID is required and cannot be empty", field="backup_id"
            )
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
        self, request: RestoreSystemDataRequest
    ) -> RestoreSystemDataResponse:
        start_time = datetime.utcnow()
        with self.tracer.start_span(
            name="restore_system_data",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            kg_id=request.kg_id,
            backup_id=request.backup_id,
        ):
            try:
                backup = self.backup_repository.get_by_id(request.backup_id)
                if (
                    not backup
                    or backup.kg_id != request.kg_id
                    or backup.tenant_id != request.tenant_id
                ):
                    raise NotFoundError(
                        message=f"Backup '{request.backup_id}' not found",
                        resource_type="graph_backup",
                        resource_id=request.backup_id,
                    )

                self.storage.restore_backup(
                    location=backup.location,
                    kg_id=request.kg_id,
                    tenant_id=request.tenant_id,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="system_backup_restored",
                    value=1,
                    tenant_id=request.tenant_id,
                )

                return RestoreSystemDataResponse(
                    success=True, processing_time_ms=processing_time, restored=True
                )
            except Exception as e:
                self.tracer.record_metric(
                    name="system_restore_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                if isinstance(e, (ValidationError, NotFoundError)):
                    return RestoreSystemDataResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )
                raise ApplicationError(
                    message=f"Failed to restore system data: {e}",
                    error_code="RESTORE_FAILED",
                ) from e
