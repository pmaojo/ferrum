"""Authentication service for the SaaS marketplace."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class SubscriptionTier(Enum):
    """Subscription tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class UserSubscription:
    """User subscription information."""
    tier: SubscriptionTier
    max_deployments: int
    max_queries_per_month: int
    custom_ontologies: bool
    priority_support: bool
    api_access: bool

class MarketplaceAuthService:
    """Authentication and authorization service for marketplace."""

    def __init__(self):
        """Initialize the service."""
        self.subscription_limits = {
            SubscriptionTier.FREE: UserSubscription(
                tier=SubscriptionTier.FREE,
                max_deployments=1,
                max_queries_per_month=1000,
                custom_ontologies=False,
                priority_support=False,
                api_access=False
            ),
            SubscriptionTier.STARTER: UserSubscription(
                tier=SubscriptionTier.STARTER,
                max_deployments=3,
                max_queries_per_month=10000,
                custom_ontologies=True,
                priority_support=False,
                api_access=True
            ),
            SubscriptionTier.PROFESSIONAL: UserSubscription(
                tier=SubscriptionTier.PROFESSIONAL,
                max_deployments=10,
                max_queries_per_month=100000,
                custom_ontologies=True,
                priority_support=True,
                api_access=True
            ),
            SubscriptionTier.ENTERPRISE: UserSubscription(
                tier=SubscriptionTier.ENTERPRISE,
                max_deployments=-1,  # Unlimited
                max_queries_per_month=-1,  # Unlimited
                custom_ontologies=True,
                priority_support=True,
                api_access=True
            )
        }

    def get_user_subscription(self, user_id: str) -> UserSubscription:
        """Get user subscription information."""
        # For demo purposes, return FREE tier
        # In production, query from your subscription service
        return self.subscription_limits[SubscriptionTier.FREE]

    def can_create_deployment(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create a new deployment."""
        subscription = self.get_user_subscription(user_id)

        if subscription.max_deployments == -1:
            return True, "Unlimited deployments"

        # Check current deployment count (mock)
        current_deployments = 0  # Query from deployment service

        if current_deployments >= subscription.max_deployments:
            return False, f"Deployment limit reached ({subscription.max_deployments})"

        return True, "Deployment allowed"

    def can_use_template(self, user_id: str, template_name: str) -> tuple[bool, str]:
        """Check if user can use a specific template."""
        subscription = self.get_user_subscription(user_id)

        # Enterprise templates require professional or enterprise tier
        if template_name == "enterprise_intelligence":
            if subscription.tier not in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]:
                return False, "Enterprise template requires Professional or Enterprise subscription"

        return True, "Template access granted"

    def get_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Get user usage limits."""
        subscription = self.get_user_subscription(user_id)

        return {
            "subscription_tier": subscription.tier.value,
            "max_deployments": subscription.max_deployments,
            "max_queries_per_month": subscription.max_queries_per_month,
            "features": {
                "custom_ontologies": subscription.custom_ontologies,
                "priority_support": subscription.priority_support,
                "api_access": subscription.api_access
            }
        }
