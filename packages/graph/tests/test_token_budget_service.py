"""Tests for TokenBudgetService."""

import unittest
from unittest.mock import Mock, patch
import pytest
import tempfile
import os
import json
from pathlib import Path
from datetime import date

from domain.token_budget_service import TokenBudgetService


class TestTokenBudgetService:
    """Test suite for TokenBudgetService."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for test storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = self.temp_dir.name

        # Create mock tracer
        self.tracer_mock = Mock()
        self.alerting_mock = Mock()

        # Initialize service with test configuration
        self.service = TokenBudgetService(
            tracer=self.tracer_mock,
            alerting_service=self.alerting_mock,
            storage_path=self.storage_path,
            default_monthly_budget_usd=100.0,
            alert_threshold_percent=80.0,
            enable_degradation=True
        )

    def teardown_method(self):
        """Tear down test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def test_track_usage_basic(self):
        """Test basic token usage tracking."""
        # Arrange
        tenant_id = "test-tenant"
        tokens = 1000
        model = "gemini-1.5-flash"
        operation_type = "generate"

        # Act
        result = self.service.track_usage(
            tenant_id=tenant_id,
            tokens=tokens,
            model=model,
            operation_type=operation_type
        )

        # Assert
        assert result["tenant_id"] == tenant_id
        assert result["tokens"] == tokens
        assert result["model"] == model
        assert result["operation_type"] == operation_type
        assert result["cost_usd"] > 0
        assert "budget_status" in result
        assert result["budget_status"]["monthly_cost_usd"] > 0
        assert result["budget_status"]["monthly_budget_usd"] == 100.0
        assert result["budget_status"]["budget_percent"] > 0

        # Check that metrics were recorded
        self.tracer_mock.record_metric.assert_called()
        self.alerting_mock.send_alert.assert_not_called()

    def test_track_usage_with_explicit_cost(self):
        """Test token usage tracking with explicit cost."""
        # Arrange
        tenant_id = "test-tenant"
        tokens = 1000
        model = "gemini-1.5-flash"
        operation_type = "generate"
        cost_usd = 0.5

        # Act
        result = self.service.track_usage(
            tenant_id=tenant_id,
            tokens=tokens,
            model=model,
            operation_type=operation_type,
            cost_usd=cost_usd
        )

        # Assert
        assert result["cost_usd"] == cost_usd
        assert result["budget_status"]["monthly_cost_usd"] == cost_usd

    def test_track_usage_multiple_operations(self):
        """Test tracking multiple operations for the same tenant."""
        # Arrange
        tenant_id = "test-tenant"

        # Act - Track multiple operations
        self.service.track_usage(
            tenant_id=tenant_id,
            tokens=1000,
            model="gemini-1.5-flash",
            operation_type="generate"
        )

        self.service.track_usage(
            tenant_id=tenant_id,
            tokens=500,
            model="text-embedding-4",
            operation_type="embed"
        )

        # Get usage data
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"
        usage = self.service.get_tenant_usage(tenant_id=tenant_id, month=current_month)

        # Assert
        assert usage["total_tokens"] == 1500  # 1000 + 500
        assert usage["operations"]["generate"]["tokens"] == 1000
        assert usage["operations"]["embed"]["tokens"] == 500
        assert "gemini-1.5-flash" in usage["models"]
        assert "text-embedding-4" in usage["models"]

    def test_track_usage_multiple_tenants(self):
        """Test tracking usage for multiple tenants."""
        # Arrange
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Act - Track usage for different tenants
        self.service.track_usage(
            tenant_id=tenant1,
            tokens=1000,
            model="gemini-1.5-flash",
            operation_type="generate"
        )

        self.service.track_usage(
            tenant_id=tenant2,
            tokens=2000,
            model="gemini-1.5-flash",
            operation_type="generate"
        )

        # Get usage data
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"
        usage1 = self.service.get_tenant_usage(tenant_id=tenant1, month=current_month)
        usage2 = self.service.get_tenant_usage(tenant_id=tenant2, month=current_month)

        # Assert
        assert usage1["total_tokens"] == 1000
        assert usage2["total_tokens"] == 2000
        assert usage1["tenant_id"] == tenant1
        assert usage2["tenant_id"] == tenant2

    def test_tenant_specific_budget_limits(self):
        """Tenants can have distinct budget limits from configuration."""
        service = TokenBudgetService(
            tracer=self.tracer_mock,
            alerting_service=self.alerting_mock,
            storage_path=self.storage_path,
            default_monthly_budget_usd=100.0,
            tenant_budget_limits={"t1": 50.0, "t2": 200.0},
        )

        res1 = service.track_usage(
            tenant_id="t1",
            tokens=1000,
            model="gemini-1.5-flash",
            operation_type="generate",
        )
        res2 = service.track_usage(
            tenant_id="t2",
            tokens=1000,
            model="gemini-1.5-flash",
            operation_type="generate",
        )

        assert res1["budget_status"]["monthly_budget_usd"] == 50.0
        assert res2["budget_status"]["monthly_budget_usd"] == 200.0

    def test_track_usage_alert_triggered(self):
        """Test alert triggering when threshold is reached."""
        # Arrange
        tenant_id = "test-tenant"
        tokens = 1000000  # Large number to exceed budget
        model = "gpt-4o"  # Expensive model
        operation_type = "generate"

        # Act
        result = self.service.track_usage(
            tenant_id=tenant_id,
            tokens=tokens,
            model=model,
            operation_type=operation_type
        )

        # Assert
        assert result["budget_status"]["alert_triggered"] is True
        assert result["budget_status"]["budget_percent"] >= 80.0

        # Check that alert metric was recorded
        self.tracer_mock.record_metric.assert_any_call(
            name="token_budget.alert",
            value=1.0,
            tenant_id=tenant_id,
            budget_percent=result["budget_status"]["budget_percent"],
            monthly_cost=result["budget_status"]["monthly_cost_usd"],
            monthly_budget_usd=result["budget_status"]["monthly_budget_usd"]
        )
        self.alerting_mock.send_alert.assert_called_once()

    def test_track_usage_budget_exceeded(self):
        """Test degradation when budget is exceeded."""
        # Arrange
        tenant_id = "test-tenant"
        tokens = 2000000  # Very large number to exceed budget
        model = "gpt-4-turbo"  # Very expensive model
        operation_type = "generate"

        # Act
        result = self.service.track_usage(
            tenant_id=tenant_id,
            tokens=tokens,
            model=model,
            operation_type=operation_type
        )

        # Assert
        assert result["budget_status"]["budget_exceeded"] is True
        assert result["budget_status"]["degradation_applied"] is True
        assert len(result["budget_status"]["degradation_actions"]) > 0

        # Check that degradation metric was recorded
        self.tracer_mock.record_metric.assert_any_call(
            name="token_budget.degradation",
            value=1.0,
            tenant_id=tenant_id,
            budget_percent=result["budget_status"]["budget_percent"],
            actions=",".join(result["budget_status"]["degradation_actions"])
        )
        self.alerting_mock.send_alert.assert_called_once()

    def test_get_tenant_usage_nonexistent(self):
        """Test getting usage for nonexistent tenant."""
        # Arrange
        tenant_id = "nonexistent-tenant"
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"

        # Act
        usage = self.service.get_tenant_usage(tenant_id=tenant_id, month=current_month)

        # Assert
        assert usage["tenant_id"] == tenant_id
        assert usage["month"] == current_month
        assert usage["total_tokens"] == 0
        assert usage["total_cost_usd"] == 0.0
        assert usage["operations"] == {}
        assert usage["models"] == {}

    def test_get_tenant_usage_invalid_month(self):
        """Test getting usage with invalid month format."""
        # Arrange
        tenant_id = "test-tenant"
        invalid_month = "2023/05"  # Wrong format

        # Act/Assert
        with pytest.raises(ValueError):
            self.service.get_tenant_usage(tenant_id=tenant_id, month=invalid_month)

    def test_set_tenant_budget(self):
        """Test setting custom budget for a tenant."""
        # Arrange
        tenant_id = "test-tenant"
        monthly_budget_usd = 200.0
        alert_threshold_percent = 70.0

        # Act
        result = self.service.set_tenant_budget(
            tenant_id=tenant_id,
            monthly_budget_usd=monthly_budget_usd,
            alert_threshold_percent=alert_threshold_percent
        )

        # Assert
        assert result["tenant_id"] == tenant_id
        assert result["monthly_budget_usd"] == monthly_budget_usd
        assert result["alert_threshold_percent"] == alert_threshold_percent

        # Verify budget was saved
        budget_file = Path(self.storage_path) / "tenant_budgets.json"
        with open(budget_file, "r") as f:
            budgets = json.load(f)

        assert tenant_id in budgets
        assert budgets[tenant_id]["monthly_budget_usd"] == monthly_budget_usd
        assert budgets[tenant_id]["alert_threshold_percent"] == alert_threshold_percent

    def test_set_tenant_budget_invalid_values(self):
        """Test setting invalid budget values."""
        # Arrange
        tenant_id = "test-tenant"

        # Act/Assert - Negative budget
        with pytest.raises(ValueError):
            self.service.set_tenant_budget(
                tenant_id=tenant_id,
                monthly_budget_usd=-100.0
            )

        # Act/Assert - Invalid threshold
        with pytest.raises(ValueError):
            self.service.set_tenant_budget(
                tenant_id=tenant_id,
                monthly_budget_usd=100.0,
                alert_threshold_percent=110.0
            )

    def test_get_degradation_options(self):
        """Test getting degradation options based on budget status."""
        # Arrange
        tenant_id = "test-tenant"
        model = "gemini-1.5-flash"

        # Set up usage to exceed budget
        self.service.track_usage(
            tenant_id=tenant_id,
            tokens=2000000,  # Very large number to exceed budget
            model="gpt-4-turbo",  # Very expensive model
            operation_type="generate"
        )

        # Act - Get options for different operation types
        generate_options = self.service.get_degradation_options(
            tenant_id=tenant_id,
            model=model,
            operation_type="generate"
        )

        embed_options = self.service.get_degradation_options(
            tenant_id=tenant_id,
            model=model,
            operation_type="embed"
        )

        moderate_options = self.service.get_degradation_options(
            tenant_id=tenant_id,
            model=model,
            operation_type="moderate"
        )

        # Assert
        assert generate_options["degradation_level"] > 0
        assert "temperature" in generate_options
        assert "max_tokens" in generate_options
        assert "context_tokens" in generate_options

        assert embed_options["degradation_level"] > 0
        assert "batch_size" in embed_options
        assert "dimensions" in embed_options

        assert moderate_options["degradation_level"] > 0
        assert "threshold" in moderate_options

    def test_calculate_cost(self):
        """Test cost calculation for different models."""
        # Test OpenAI models
        assert self.service._calculate_cost(1000, "gpt-4o", "generate") == 5.0
        assert self.service._calculate_cost(1000, "gpt-4o", "embed") == 1.0
        assert self.service._calculate_cost(1000, "gpt-3.5-turbo", "generate") == 0.5

        # Test Google models
        assert self.service._calculate_cost(1000, "gemini-1.5-flash", "generate") == 0.35
        assert self.service._calculate_cost(1000, "gemini-1.5-pro", "generate") == 3.5

        # Test embedding models
        assert self.service._calculate_cost(1000, "text-embedding-4", "embed") == 0.1
        assert self.service._calculate_cost(1000, "text-embedding-3-small", "embed") == 0.02

        # Test unknown model (should use default)
        assert self.service._calculate_cost(1000, "unknown-model", "generate") == 1.0

    def test_persistence(self):
        """Test that usage data persists between service instances."""
        # Arrange
        tenant_id = "test-tenant"
        tokens = 1000
        model = "gemini-1.5-flash"
        operation_type = "generate"

        # Act - Track usage with first service instance
        self.service.track_usage(
            tenant_id=tenant_id,
            tokens=tokens,
            model=model,
            operation_type=operation_type
        )

        # Create new service instance with same storage path
        new_service = TokenBudgetService(
            tracer=self.tracer_mock,
            storage_path=self.storage_path
        )

        # Get usage data from new instance
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"
        usage = new_service.get_tenant_usage(tenant_id=tenant_id, month=current_month)

        # Assert
        assert usage["total_tokens"] == tokens
        assert usage["models"][model]["tokens"] == tokens