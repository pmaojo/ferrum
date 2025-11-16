import logging
import pytest
from unittest.mock import AsyncMock, Mock

from application.ports.erp import ERPPort

from adapters.auth.user_registration_service import (
    RegistrationRequest,
    UserRegistrationService,
)


@pytest.mark.asyncio
async def test_register_user_logs_warning_on_odoo_failure(caplog):
    create_user_use_case = Mock()
    create_user_use_case.execute = AsyncMock(return_value=Mock(success=True, user="user"))

    erp_adapter = Mock(spec=ERPPort)
    erp_adapter.create_customer = AsyncMock(side_effect=Exception("erp error"))

    service = UserRegistrationService(create_user_use_case, erp_adapter)
    service._create_organization = AsyncMock(return_value="org-123")

    request = RegistrationRequest(
        email="test@example.com",
        name="Test User",
        password="pass1234",
        organization_name="Test Org",
    )

    caplog.set_level(logging.WARNING, logger="adapters.auth.user_registration_service")

    response = await service.register_user(request)

    assert response["success"] is True
    assert any(
        "Failed to sync to ERP" in record.getMessage() for record in caplog.records
    )
