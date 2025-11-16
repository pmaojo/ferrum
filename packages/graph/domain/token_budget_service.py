"""Token budget service for managing LLM token usage and costs.

This service tracks token usage and costs across tenants, providing
budget management, alerts, and automatic degradation strategies when
budgets are exceeded.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
import json
import os
from pathlib import Path
import threading

from application.ports import TracingPort, LLMPort, AlertingPort

logger = logging.getLogger(__name__)


class TokenBudgetService:
    """Service for tracking and managing LLM token usage and costs.

    Provides budget management, alerts, and automatic degradation strategies
    when token budgets are exceeded. Supports multi-tenant isolation with
    per-tenant budget limits.
    """

    def __init__(
        self,
        tracer: Optional[TracingPort] = None,
        storage_path: Optional[str] = None,
        alerting_service: Optional[AlertingPort] = None,
        default_monthly_budget_usd: float = 100.0,  # Default $100 monthly budget
        alert_threshold_percent: float = 80.0,  # Alert at 80% of budget
        enable_degradation: bool = True,  # Enable automatic degradation
        tenant_budget_limits: Optional[Dict[str, float]] = None,
    ):
        """Initialize TokenBudgetService.

        Args:
            tracer: Optional tracing port for observability
            storage_path: Path to store token usage data (defaults to ~/.graphrag/token_usage)
            alerting_service: Optional alerting port for external notifications
            default_monthly_budget_usd: Default monthly budget in USD
            alert_threshold_percent: Percentage of budget at which to trigger alerts
            enable_degradation: Whether to enable automatic degradation strategies
            tenant_budget_limits: Optional mapping of tenant IDs to budget limits
        """
        self.tracer = tracer
        self.alerting_service = alerting_service
        self.default_monthly_budget_usd = default_monthly_budget_usd
        self.alert_threshold_percent = alert_threshold_percent
        self.enable_degradation = enable_degradation
        self.tenant_budget_limits = tenant_budget_limits or {}

        # Set up storage path
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / ".graphrag" / "token_usage"

        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)

        # Load tenant budgets and usage
        self.tenant_budgets = self._load_tenant_budgets()
        # Apply configured tenant budget limits
        for tid, limit in self.tenant_budget_limits.items():
            self.tenant_budgets.setdefault(tid, {})
            self.tenant_budgets[tid]["monthly_budget_usd"] = limit
        self.usage_data = self._load_usage_data()

        # Thread lock for concurrent updates
        self.lock = threading.RLock()

        logger.info(
            f"Initialized TokenBudgetService with "
            f"default_monthly_budget_usd={default_monthly_budget_usd}, "
            f"alert_threshold_percent={alert_threshold_percent}, "
            f"enable_degradation={enable_degradation}, "
            f"storage_path={self.storage_path}"
        )

    def track_usage(
        self,
        *,
        tenant_id: str,
        tokens: int,
        model: str,
        operation_type: str,  # "generate", "embed", "moderate"
        cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track token usage for a tenant.

        Args:
            tenant_id: Tenant identifier
            tokens: Number of tokens used
            model: LLM model identifier (e.g., "gemini-1.5-flash", "gpt-4o")
            operation_type: Type of operation ("generate", "embed", "moderate")
            cost_usd: Optional cost in USD (calculated from model if not provided)
            metadata: Optional additional metadata about the operation

        Returns:
            Dictionary with usage information and budget status

        Raises:
            ValueError: When parameters are invalid
        """
        if tokens < 0:
            raise ValueError("Token count must be non-negative")

        if not tenant_id:
            raise ValueError("Tenant ID is required")

        # Calculate cost if not provided
        if cost_usd is None:
            cost_usd = self._calculate_cost(tokens, model, operation_type)

        # Get current date for tracking
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"

        # Thread-safe update of usage data
        with self.lock:
            # Initialize tenant data if not exists
            if tenant_id not in self.usage_data:
                self.usage_data[tenant_id] = {}

            # Initialize month data if not exists
            if current_month not in self.usage_data[tenant_id]:
                self.usage_data[tenant_id][current_month] = {
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "operations": {
                        "generate": {"tokens": 0, "cost_usd": 0.0},
                        "embed": {"tokens": 0, "cost_usd": 0.0},
                        "moderate": {"tokens": 0, "cost_usd": 0.0}
                    },
                    "models": {}
                }

            # Update total usage
            self.usage_data[tenant_id][current_month]["total_tokens"] += tokens
            self.usage_data[tenant_id][current_month]["total_cost_usd"] += cost_usd

            # Update operation-specific usage
            if operation_type in self.usage_data[tenant_id][current_month]["operations"]:
                self.usage_data[tenant_id][current_month]["operations"][operation_type]["tokens"] += tokens
                self.usage_data[tenant_id][current_month]["operations"][operation_type]["cost_usd"] += cost_usd

            # Update model-specific usage
            if model not in self.usage_data[tenant_id][current_month]["models"]:
                self.usage_data[tenant_id][current_month]["models"][model] = {
                    "tokens": 0,
                    "cost_usd": 0.0
                }

            self.usage_data[tenant_id][current_month]["models"][model]["tokens"] += tokens
            self.usage_data[tenant_id][current_month]["models"][model]["cost_usd"] += cost_usd

            # Save updated usage data
            self._save_usage_data()

            # Get budget information
            budget = self._get_tenant_budget(tenant_id)
            monthly_budget_usd = budget.get("monthly_budget_usd", self.default_monthly_budget_usd)

            # Calculate budget status
            monthly_cost = self.usage_data[tenant_id][current_month]["total_cost_usd"]
            budget_percent = (monthly_cost / monthly_budget_usd) * 100 if monthly_budget_usd > 0 else 0

            # Check if we need to alert
            alert_triggered = budget_percent >= self.alert_threshold_percent
            budget_exceeded = budget_percent >= 100.0

            # Record metrics if tracer available
            if self.tracer:
                self.tracer.record_metric(
                    name="token_budget.tokens_used",
                    value=tokens,
                    tenant_id=tenant_id,
                    model=model,
                    operation_type=operation_type
                )

                self.tracer.record_metric(
                    name="token_budget.cost_usd",
                    value=cost_usd,
                    tenant_id=tenant_id,
                    model=model,
                    operation_type=operation_type
                )

                self.tracer.record_metric(
                    name="token_budget.monthly_percent",
                    value=budget_percent,
                    tenant_id=tenant_id
                )

            # Handle alerts and degradation
            degradation_applied = False
            degradation_actions = []

            if alert_triggered:
                self._trigger_alert(
                    tenant_id=tenant_id,
                    budget_percent=budget_percent,
                    monthly_cost=monthly_cost,
                    monthly_budget_usd=monthly_budget_usd
                )
                self._emit_alerts(
                    tenant_id=tenant_id,
                    budget_percent=budget_percent,
                    monthly_cost=monthly_cost,
                    monthly_budget_usd=monthly_budget_usd,
                )

            if budget_exceeded and self.enable_degradation:
                degradation_actions = self._apply_degradation_strategy(
                    tenant_id=tenant_id,
                    budget_percent=budget_percent
                )
                degradation_applied = len(degradation_actions) > 0

            # Return usage information
            return {
                "tenant_id": tenant_id,
                "tokens": tokens,
                "cost_usd": cost_usd,
                "model": model,
                "operation_type": operation_type,
                "timestamp": datetime.now().isoformat(),
                "budget_status": {
                    "monthly_cost_usd": monthly_cost,
                    "monthly_budget_usd": monthly_budget_usd,
                    "budget_percent": budget_percent,
                    "alert_triggered": alert_triggered,
                    "budget_exceeded": budget_exceeded,
                    "degradation_applied": degradation_applied,
                    "degradation_actions": degradation_actions
                }
            }

    def get_tenant_usage(
        self,
        *,
        tenant_id: str,
        month: Optional[str] = None  # Format: "YYYY-MM"
    ) -> Dict[str, Any]:
        """Get token usage for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            month: Optional month in "YYYY-MM" format (defaults to current month)

        Returns:
            Dictionary with usage information

        Raises:
            ValueError: When tenant not found or month format is invalid
        """
        if not tenant_id:
            raise ValueError("Tenant ID is required")

        # Default to current month if not specified
        if month is None:
            today = date.today()
            month = f"{today.year}-{today.month:02d}"

        # Validate month format
        try:
            year, month_num = month.split("-")
            if not (len(year) == 4 and len(month_num) == 2):
                raise ValueError()
            int(year)
            int(month_num)
        except (ValueError, IndexError):
            raise ValueError("Month must be in format 'YYYY-MM'")

        # Get usage data for tenant and month
        with self.lock:
            if tenant_id not in self.usage_data:
                return {
                    "tenant_id": tenant_id,
                    "month": month,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "operations": {},
                    "models": {}
                }

            if month not in self.usage_data[tenant_id]:
                return {
                    "tenant_id": tenant_id,
                    "month": month,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "operations": {},
                    "models": {}
                }

            # Get budget information
            budget = self._get_tenant_budget(tenant_id)
            monthly_budget_usd = budget.get("monthly_budget_usd", self.default_monthly_budget_usd)

            # Calculate budget status
            monthly_cost = self.usage_data[tenant_id][month]["total_cost_usd"]
            budget_percent = (monthly_cost / monthly_budget_usd) * 100 if monthly_budget_usd > 0 else 0

            # Return usage with budget information
            return {
                "tenant_id": tenant_id,
                "month": month,
                "total_tokens": self.usage_data[tenant_id][month]["total_tokens"],
                "total_cost_usd": monthly_cost,
                "operations": self.usage_data[tenant_id][month]["operations"],
                "models": self.usage_data[tenant_id][month]["models"],
                "budget_status": {
                    "monthly_budget_usd": monthly_budget_usd,
                    "budget_percent": budget_percent,
                    "alert_threshold_percent": self.alert_threshold_percent,
                    "alert_triggered": budget_percent >= self.alert_threshold_percent,
                    "budget_exceeded": budget_percent >= 100.0
                }
            }

    def set_tenant_budget(
        self,
        *,
        tenant_id: str,
        monthly_budget_usd: float,
        alert_threshold_percent: Optional[float] = None,
        enable_degradation: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Set budget parameters for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            monthly_budget_usd: Monthly budget in USD
            alert_threshold_percent: Optional percentage of budget at which to trigger alerts
            enable_degradation: Optional flag to enable/disable automatic degradation

        Returns:
            Dictionary with updated budget information

        Raises:
            ValueError: When parameters are invalid
        """
        if not tenant_id:
            raise ValueError("Tenant ID is required")

        if monthly_budget_usd < 0:
            raise ValueError("Monthly budget must be non-negative")

        if alert_threshold_percent is not None and (alert_threshold_percent < 0 or alert_threshold_percent > 100):
            raise ValueError("Alert threshold must be between 0 and 100")

        # Thread-safe update of tenant budgets
        with self.lock:
            # Initialize tenant budget if not exists
            if tenant_id not in self.tenant_budgets:
                self.tenant_budgets[tenant_id] = {}

            # Update budget parameters
            self.tenant_budgets[tenant_id]["monthly_budget_usd"] = monthly_budget_usd

            if alert_threshold_percent is not None:
                self.tenant_budgets[tenant_id]["alert_threshold_percent"] = alert_threshold_percent

            if enable_degradation is not None:
                self.tenant_budgets[tenant_id]["enable_degradation"] = enable_degradation

            # Save updated budgets
            self._save_tenant_budgets()

            # Return updated budget information
            return {
                "tenant_id": tenant_id,
                "monthly_budget_usd": monthly_budget_usd,
                "alert_threshold_percent": self.tenant_budgets[tenant_id].get(
                    "alert_threshold_percent", self.alert_threshold_percent
                ),
                "enable_degradation": self.tenant_budgets[tenant_id].get(
                    "enable_degradation", self.enable_degradation
                )
            }

    def get_degradation_options(
        self,
        *,
        tenant_id: str,
        model: str,
        operation_type: str
    ) -> Dict[str, Any]:
        """Get degradation options for a specific tenant and model.

        This method provides recommended parameter adjustments based on
        the tenant's budget status to reduce token usage and costs.

        Args:
            tenant_id: Tenant identifier
            model: LLM model identifier
            operation_type: Type of operation ("generate", "embed", "moderate")

        Returns:
            Dictionary with degradation options
        """
        # Get current budget status
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"

        with self.lock:
            # Get budget information
            budget = self._get_tenant_budget(tenant_id)
            monthly_budget_usd = budget.get("monthly_budget_usd", self.default_monthly_budget_usd)

            # Calculate budget status
            monthly_cost = 0.0
            if tenant_id in self.usage_data and current_month in self.usage_data[tenant_id]:
                monthly_cost = self.usage_data[tenant_id][current_month]["total_cost_usd"]

            budget_percent = (monthly_cost / monthly_budget_usd) * 100 if monthly_budget_usd > 0 else 0

        # Determine degradation level based on budget percent
        degradation_level = 0  # No degradation

        if budget_percent >= 100:
            degradation_level = 3  # Severe degradation
        elif budget_percent >= 90:
            degradation_level = 2  # Moderate degradation
        elif budget_percent >= 80:
            degradation_level = 1  # Mild degradation

        # Define degradation options based on operation type and level
        options = {
            "degradation_level": degradation_level,
            "budget_percent": budget_percent
        }

        if operation_type == "generate":
            options.update({
                "temperature": max(0.1, 0.7 - (degradation_level * 0.2)),  # Reduce temperature
                "max_tokens": max(50, 1000 - (degradation_level * 300)),  # Reduce max tokens
                "context_tokens": max(1000, 4000 - (degradation_level * 1000)),  # Reduce context
                "top_p": max(0.5, 0.95 - (degradation_level * 0.15))  # Reduce top_p
            })
        elif operation_type == "embed":
            options.update({
                "batch_size": max(5, 20 - (degradation_level * 5)),  # Reduce batch size
                "dimensions": [768, 384, 128][min(degradation_level, 2)]  # Reduce dimensions
            })
        elif operation_type == "moderate":
            options.update({
                "threshold": min(0.9, 0.7 + (degradation_level * 0.1))  # Increase threshold
            })

        return options

    def _get_tenant_budget(self, tenant_id: str) -> Dict[str, Any]:
        """Get budget configuration for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with budget configuration
        """
        if tenant_id not in self.tenant_budgets:
            return {
                "monthly_budget_usd": self.default_monthly_budget_usd,
                "alert_threshold_percent": self.alert_threshold_percent,
                "enable_degradation": self.enable_degradation
            }

        return self.tenant_budgets[tenant_id]

    def _calculate_cost(self, tokens: int, model: str, operation_type: str) -> float:
        """Calculate cost in USD based on token count and model.

        Args:
            tokens: Number of tokens
            model: LLM model identifier
            operation_type: Type of operation

        Returns:
            Cost in USD
        """
        # Define cost per 1000 tokens for common models
        # Based on public pricing as of July 2023
        cost_per_1k = {
            # OpenAI models
            "gpt-4o": 5.0 if operation_type == "generate" else 1.0,
            "gpt-4-turbo": 10.0 if operation_type == "generate" else 3.0,
            "gpt-3.5-turbo": 0.5 if operation_type == "generate" else 0.1,

            # Google models
            "gemini-1.5-flash": 0.35 if operation_type == "generate" else 0.1,
            "gemini-1.5-pro": 3.5 if operation_type == "generate" else 0.5,
            "gemini-1.0-pro": 1.0 if operation_type == "generate" else 0.25,

            # Embedding models
            "text-embedding-ada-002": 0.1,
            "text-embedding-3-small": 0.02,
            "text-embedding-3-large": 0.13,
            "text-embedding-4": 0.1,

            # Default fallback
            "default": 1.0 if operation_type == "generate" else 0.2
        }

        # Get cost per 1K tokens for the model, or use default
        cost_per_1k_tokens = cost_per_1k.get(model, cost_per_1k["default"])

        # Calculate and return cost
        return (tokens / 1000) * cost_per_1k_tokens

    def _trigger_alert(
        self,
        *,
        tenant_id: str,
        budget_percent: float,
        monthly_cost: float,
        monthly_budget_usd: float
    ) -> None:
        """Trigger budget alert for a tenant.

        Args:
            tenant_id: Tenant identifier
            budget_percent: Percentage of budget used
            monthly_cost: Current monthly cost in USD
            monthly_budget_usd: Monthly budget in USD
        """
        alert_message = (
            f"Token budget alert for tenant {tenant_id}: "
            f"{budget_percent:.1f}% of monthly budget used "
            f"(${monthly_cost:.2f} of ${monthly_budget_usd:.2f})"
        )

        logger.warning(alert_message)

        # Record alert metric if tracer available
        if self.tracer:
            self.tracer.record_metric(
                name="token_budget.alert",
                value=1.0,
                tenant_id=tenant_id,
                budget_percent=budget_percent,
                monthly_cost=monthly_cost,
                monthly_budget_usd=monthly_budget_usd
            )

    def _emit_alerts(
        self,
        *,
        tenant_id: str,
        budget_percent: float,
        monthly_cost: float,
        monthly_budget_usd: float,
    ) -> None:
        """Emit alert via configured alerting service."""
        if not self.alerting_service:
            return
        message = (
            f"Token budget alert for tenant {tenant_id}: "
            f"{budget_percent:.1f}% used"
        )
        context = {
            "tenant_id": tenant_id,
            "budget_percent": budget_percent,
            "monthly_cost": monthly_cost,
            "monthly_budget_usd": monthly_budget_usd,
        }
        try:
            self.alerting_service.send_alert(message=message, context=context)
        except Exception as e:  # pragma: no cover - alerting failures should not crash
            logger.error(f"Failed to send alert: {str(e)}")


    def _apply_degradation_strategy(
        self,
        *,
        tenant_id: str,
        budget_percent: float
    ) -> List[str]:
        """Apply automatic degradation strategy when budget is exceeded.

        Args:
            tenant_id: Tenant identifier
            budget_percent: Percentage of budget used

        Returns:
            List of applied degradation actions
        """
        actions = []

        # Define degradation levels based on budget percent
        if budget_percent >= 120:
            # Severe degradation
            actions.append("reduced_context_tokens_severe")
            actions.append("reduced_temperature_severe")
            actions.append("reduced_max_tokens_severe")

            logger.warning(
                f"Applying severe degradation for tenant {tenant_id} "
                f"({budget_percent:.1f}% of budget used)"
            )

        elif budget_percent >= 110:
            # Moderate degradation
            actions.append("reduced_context_tokens_moderate")
            actions.append("reduced_temperature_moderate")

            logger.warning(
                f"Applying moderate degradation for tenant {tenant_id} "
                f"({budget_percent:.1f}% of budget used)"
            )

        elif budget_percent >= 100:
            # Mild degradation
            actions.append("reduced_context_tokens_mild")

            logger.warning(
                f"Applying mild degradation for tenant {tenant_id} "
                f"({budget_percent:.1f}% of budget used)"
            )

        # Record degradation metric if tracer available
        if self.tracer and actions:
            self.tracer.record_metric(
                name="token_budget.degradation",
                value=1.0,
                tenant_id=tenant_id,
                budget_percent=budget_percent,
                actions=",".join(actions)
            )

        return actions

    def _load_tenant_budgets(self) -> Dict[str, Dict[str, Any]]:
        """Load tenant budgets from storage.

        Returns:
            Dictionary mapping tenant IDs to budget configurations
        """
        budget_file = self.storage_path / "tenant_budgets.json"

        if not budget_file.exists():
            return {}

        try:
            with open(budget_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load tenant budgets: {str(e)}")
            return {}

    def _save_tenant_budgets(self) -> None:
        """Save tenant budgets to storage."""
        budget_file = self.storage_path / "tenant_budgets.json"

        try:
            with open(budget_file, "w") as f:
                json.dump(self.tenant_budgets, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save tenant budgets: {str(e)}")

    def _load_usage_data(self) -> Dict[str, Dict[str, Any]]:
        """Load token usage data from storage.

        Returns:
            Dictionary mapping tenant IDs to usage data
        """
        usage_file = self.storage_path / "token_usage.json"

        if not usage_file.exists():
            return {}

        try:
            with open(usage_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load token usage data: {str(e)}")
            return {}

    def _save_usage_data(self) -> None:
        """Save token usage data to storage."""
        usage_file = self.storage_path / "token_usage.json"

        try:
            with open(usage_file, "w") as f:
                json.dump(self.usage_data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save token usage data: {str(e)}")
