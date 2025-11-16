"""Tests for EnforceDataRetentionUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from domain.entities import DataRetentionPolicy, DataRetentionTarget
from domain.exceptions import ValidationError
from application.use_cases.data_retention.enforce_data_retention_use_case import (
    EnforceDataRetentionUseCase,
    EnforceDataRetentionRequest,
)


class TestEnforceDataRetentionUseCase:
    """Unit tests for enforcing data retention policies."""

    def setup_method(self) -> None:
        self.service = Mock()
        self.use_case = EnforceDataRetentionUseCase(service=self.service)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_policy_enforced_successfully(self):
        """Expired data is deleted according to policy."""
        policy = DataRetentionPolicy(
            tenant_id="tenant1",
            retention_days=30,
            applies_to=DataRetentionTarget.LOGS,
        )
        request = EnforceDataRetentionRequest(policy=policy)
        self.service.delete_expired_data.return_value = 5

        response = await self.use_case.execute(request)

        assert response.success is True
        assert response.deleted_count == 5
        args, kwargs = self.service.delete_expired_data.call_args
        assert kwargs["tenant_id"] == "tenant1"
        assert kwargs["applies_to"] == DataRetentionTarget.LOGS
        assert isinstance(kwargs["older_than"], datetime)
        assert kwargs["older_than"] <= datetime.utcnow() - timedelta(days=29)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_invalid_request_policy_type(self):
        """Request with invalid policy type raises ValidationError."""
        request = EnforceDataRetentionRequest(policy="not_a_policy")

        with pytest.raises(ValidationError):
            await self.use_case.execute(request)

    def test_policy_validation_error(self):
        """DataRetentionPolicy validates its fields."""
        with pytest.raises(ValidationError):
            DataRetentionPolicy(
                tenant_id="",
                retention_days=0,
                applies_to=DataRetentionTarget.BACKUPS,
            )
