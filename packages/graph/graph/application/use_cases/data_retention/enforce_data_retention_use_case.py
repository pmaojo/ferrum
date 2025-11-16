from dataclasses import dataclass
from datetime import datetime, timedelta

from application.ports import DataRetentionServicePort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import BaseResponseDTO
from domain.entities import DataRetentionPolicy
from domain.exceptions import ValidationError


@dataclass
class EnforceDataRetentionRequest:
    """Request object for enforcing a data retention policy."""

    policy: DataRetentionPolicy


@dataclass
class EnforceDataRetentionResponse(BaseResponseDTO):
    """Response returned after enforcing the policy."""

    deleted_count: int = 0


class EnforceDataRetentionUseCase(
    BaseUseCase[EnforceDataRetentionRequest, EnforceDataRetentionResponse]
):
    """Use case to enforce data retention policies."""

    def __init__(self, service: DataRetentionServicePort) -> None:
        super().__init__()
        self.service = service

    def _validate_request_internal(self, request: EnforceDataRetentionRequest) -> None:
        if not isinstance(request.policy, DataRetentionPolicy):
            raise ValidationError(
                message="Invalid policy type",
                field="policy",
            )

    async def _execute_internal(
        self, request: EnforceDataRetentionRequest
    ) -> EnforceDataRetentionResponse:
        start = datetime.utcnow()
        cutoff = start - timedelta(days=request.policy.retention_days)
        deleted = self.service.delete_expired_data(
            tenant_id=request.policy.tenant_id,
            applies_to=request.policy.applies_to,
            older_than=cutoff,
        )
        elapsed_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return EnforceDataRetentionResponse(
            success=True,
            processing_time_ms=elapsed_ms,
            deleted_count=deleted,
        )
