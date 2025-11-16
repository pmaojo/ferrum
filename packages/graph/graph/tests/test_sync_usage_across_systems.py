"""Tests for usage synchronization across systems."""

import sys

import pytest
from unittest.mock import MagicMock, Mock, patch

sys.modules.setdefault("numpy", MagicMock())
sys.modules.setdefault("stripe", MagicMock())
sys.modules.setdefault("requests", MagicMock())
sys.modules.setdefault("httpx", MagicMock())

import domain.exceptions as domain_exceptions
from application.exceptions import ApplicationError

setattr(domain_exceptions, "ApplicationError", ApplicationError)
from adapters.auth.integrated_auth_service import (
    IntegratedAuthService,
    ERROR_SYNC_USAGE_FAILED,
)
from adapters.external.supabase_integration_adapter import SupabaseConfig
from adapters.external.odoo_integration_adapter import OdooConfig


class StubAdapter:
    """Simple adapter stub for usage metrics updates."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.called = False

    def update_usage_metrics(self, user_id: str, usage_data):
        self.called = True
        if self.should_fail:
            raise Exception("update failed")
        return True


def _make_service(supabase_adapter: StubAdapter, erp_adapter: StubAdapter):
    """Create service instance with stubbed dependencies."""

    with patch("adapters.auth.integrated_auth_service.SupabaseAuthAdapter"), \
        patch("adapters.auth.integrated_auth_service.StripeBillingAdapter"), \
        patch("adapters.auth.integrated_auth_service.SupabaseIntegrationAdapter"):
        service = IntegratedAuthService(
            create_user_use_case=Mock(),
            supabase_config=SupabaseConfig(
                url="http://supabase",
                anon_key="anon",
                service_role_key="service",
                project_ref="proj",
            ),
            odoo_config=OdooConfig(
                url="http://odoo",
                database="db",
                username="user",
                password="pass",
            ),
            erp_adapter=erp_adapter,
        )
        service.supabase_adapter = supabase_adapter
        return service


def test_sync_usage_success():
    """Usage metrics sync succeeds when all systems update."""
    supabase = StubAdapter()
    erp = StubAdapter()
    service = _make_service(supabase, erp)

    result = service.sync_usage_across_systems("user-1", {"api_calls": 1})

    assert result is True
    assert supabase.called and erp.called


def test_sync_usage_supabase_failure():
    """Failure in Supabase update raises ApplicationError."""
    supabase = StubAdapter(should_fail=True)
    erp = StubAdapter()
    service = _make_service(supabase, erp)

    with pytest.raises(ApplicationError) as exc_info:
        service.sync_usage_across_systems("user-1", {"api_calls": 1})

    assert exc_info.value.error_code == ERROR_SYNC_USAGE_FAILED
    assert supabase.called and erp.called


def test_sync_usage_erp_failure():
    """Failure in ERP update raises ApplicationError."""
    supabase = StubAdapter()
    erp = StubAdapter(should_fail=True)
    service = _make_service(supabase, erp)

    with pytest.raises(ApplicationError) as exc_info:
        service.sync_usage_across_systems("user-1", {"api_calls": 1})

    assert exc_info.value.error_code == ERROR_SYNC_USAGE_FAILED
    assert supabase.called and erp.called

