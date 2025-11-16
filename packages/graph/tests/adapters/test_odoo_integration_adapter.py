from unittest.mock import AsyncMock, MagicMock
import sys
import httpx
import pytest

sys.modules.setdefault("numpy", MagicMock())
from adapters.external.odoo_integration_adapter import OdooIntegrationAdapter, OdooConfig


@pytest.mark.asyncio
async def test_session_post_invoked_during_operations():
    config = OdooConfig(url="http://odoo.test", database="db", username="user", password="pass")
    session = MagicMock(spec=httpx.AsyncClient)

    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.json.return_value = {"result": 1}

    create_response = MagicMock()
    create_response.status_code = 200
    create_response.json.return_value = {"result": 99}

    session.post = AsyncMock(side_effect=[auth_response, create_response])

    adapter = await OdooIntegrationAdapter.create(config, client=session)
    customer_id = await adapter.create_customer({"name": "Test", "email": "a@b.com"})

    assert customer_id == 99
    assert session.post.call_count == 2
