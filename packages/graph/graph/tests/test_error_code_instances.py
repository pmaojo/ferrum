from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

import sys
import domain.exceptions as domain_exceptions
from application.exceptions import ApplicationError

sys.modules.setdefault("stripe", MagicMock())  # noqa: E402
setattr(domain_exceptions, "ApplicationError", ApplicationError)  # noqa: E402

from adapters.external.odoo_integration_adapter import (  # noqa: E402
    OdooConfig,
    OdooIntegrationAdapter,
    ERROR_ODOO_AUTH_FAILED,
)
from adapters.external.supabase_integration_adapter import SupabaseConfig  # noqa: E402
from adapters.auth.user_registration_service import (  # noqa: E402
    UserRegistrationService,
    RegistrationRequest,
    ERROR_REGISTRATION_FAILED,
)
from adapters.auth.integrated_auth_service import (  # noqa: E402
    IntegratedAuthService,
    ERROR_COMPLETE_REGISTRATION_FAILED,
)


@pytest.mark.asyncio
async def test_user_registration_service_error_code():
    create_user_use_case = Mock()
    create_user_use_case.execute = AsyncMock(return_value=Mock(success=False, error_message="boom"))
    service = UserRegistrationService(create_user_use_case)
    service._create_organization = AsyncMock(return_value="org-1")

    request = RegistrationRequest(
        email="a@test.com",
        name="Test",
        password="secret",
        organization_name="Org",
    )

    with pytest.raises(ApplicationError) as exc_info:
        await service.register_user(request)

    assert exc_info.value.error_code == ERROR_REGISTRATION_FAILED


@pytest.mark.asyncio
async def test_integrated_auth_service_error_code():
    create_user_use_case = Mock()
    create_user_use_case.execute = AsyncMock(return_value=Mock(success=False, error_message="fail"))

    with patch("adapters.auth.integrated_auth_service.OdooIntegrationAdapter"), \
         patch("adapters.auth.integrated_auth_service.SupabaseIntegrationAdapter"), \
         patch("adapters.auth.integrated_auth_service.SupabaseAuthAdapter"), \
         patch("adapters.auth.integrated_auth_service.StripeBillingAdapter"):
        service = IntegratedAuthService(
            create_user_use_case,
            SupabaseConfig(
                url="http://supabase",
                anon_key="anon",
                service_role_key="service",
                project_ref="proj",
            ),
            OdooConfig(
                url="http://odoo",
                database="db",
                username="u",
                password="p",
            ),
        )
        service._create_organization = AsyncMock(return_value="org-1")

        with pytest.raises(ApplicationError) as exc_info:
            await service.register_user_complete({
                "email": "user@test.com",
                "name": "User",
                "password": "pass"
            })

    assert exc_info.value.error_code == ERROR_COMPLETE_REGISTRATION_FAILED


@pytest.mark.asyncio
async def test_odoo_integration_adapter_error_code():
    config = OdooConfig(url="http://odoo.local", database="db", username="u", password="p")
    mock_response = MagicMock(status_code=401)
    mock_response.json.return_value = {}

    with patch(
        "adapters.external.odoo_integration_adapter.httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        with pytest.raises(ApplicationError) as exc_info:
            await OdooIntegrationAdapter.create(config)

    assert exc_info.value.error_code == ERROR_ODOO_AUTH_FAILED
