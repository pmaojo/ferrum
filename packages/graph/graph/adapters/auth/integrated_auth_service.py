"""Integrated authentication service combining Odoo ERP and Supabase backend.

The service coordinates user registration and authentication across Supabase,
Stripe and Odoo.  It now relies on explicit configuration objects, making it
easier to inject settings from the outside and to test in isolation."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from adapters.auth.stripe_billing_adapter import StripeBillingAdapter
from adapters.auth.supabase_auth_adapter import SupabaseAuthAdapter
from adapters.external.odoo_integration_adapter import (
    OdooConfig,
    OdooIntegrationAdapter,
)
from adapters.external.supabase_integration_adapter import (
    SupabaseConfig,
    SupabaseIntegrationAdapter,
)
from application.exceptions import ApplicationError
from application.ports.erp import ERPPort
from application.use_cases.create_user_use_case import CreateUserUseCase
from application.use_cases.dto import CreateUserRequestDTO

ERROR_CREATE_USER_FAILED = "INTEGRATED_AUTH_CREATE_USER_FAILED"
ERROR_COMPLETE_REGISTRATION_FAILED = "INTEGRATED_AUTH_REGISTRATION_ERROR"
ERROR_GET_PROFILE_FAILED = "INTEGRATED_AUTH_GET_PROFILE_FAILED"
ERROR_SYNC_USAGE_FAILED = "INTEGRATED_AUTH_SYNC_USAGE_FAILED"


class IntegratedAuthService:
    """Integrated authentication service with full ERP and backend integration."""

    def __init__(
        self,
        create_user_use_case: CreateUserUseCase,
        supabase_config: SupabaseConfig,
        odoo_config: OdooConfig,
        erp_adapter: Optional[ERPPort] = None,
    ) -> None:
        """Initialize the service with required configuration.

        Parameters
        ----------
        create_user_use_case:
            Use case responsible for creating domain users.
        supabase_config:
            Connection details for the Supabase backend.
        odoo_config:
            Connection details for the Odoo ERP.
        erp_adapter:
            Optional custom ERP adapter, mainly used for testing.
        """
        self.create_user_use_case = create_user_use_case

        # Initialize Supabase
        self.supabase_auth = SupabaseAuthAdapter()
        self.supabase_adapter = SupabaseIntegrationAdapter(supabase_config)

        # Initialize ERP adapter
        if erp_adapter is not None:
            self.erp_adapter = erp_adapter
        else:
            self.erp_adapter = OdooIntegrationAdapter(odoo_config)

        # Initialize Stripe
        self.stripe_billing = StripeBillingAdapter()

    async def register_user_complete(
        self, registration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete user registration across all systems."""
        try:
            # 1. Create organization in our system
            org_id = await self._create_organization(
                registration_data.get("organization_name")
            )

            # 2. Create user in our domain
            user_request = CreateUserRequestDTO(
                email=registration_data.get("email"),
                name=registration_data.get("name"),
                password=registration_data.get("password"),
                organization_id=org_id,
                role="admin",
                created_by_user_id="system",
            )

            user_response = await self.create_user_use_case.execute(
                request=user_request
            )

            if not user_response.success:
                raise ApplicationError(
                    f"Failed to create user: {user_response.error_message}",
                    error_code=ERROR_CREATE_USER_FAILED,
                )

            user_id = user_response.user.id

            # 3. Create customer in Odoo ERP
            odoo_customer_id = await self.erp_adapter.create_customer(
                {
                    "name": registration_data.get("name"),
                    "email": registration_data.get("email"),
                    "organization": registration_data.get("organization_name"),
                    "user_id": user_id,
                }
            )

            # 4. Create Stripe customer for billing
            stripe_customer_id = self.stripe_billing.create_customer(
                {
                    "email": registration_data.get("email"),
                    "name": registration_data.get("name"),
                    "user_id": user_id,
                    "organization": registration_data.get("organization_name"),
                }
            )

            # 5. Sync user profile to Supabase
            supabase_profile = self.supabase_adapter.sync_user_to_supabase(
                {
                    "user_id": user_id,
                    "email": registration_data.get("email"),
                    "name": registration_data.get("name"),
                    "organization": registration_data.get("organization_name"),
                    "tier": registration_data.get("subscription_tier", "free"),
                    "metadata": {
                        "odoo_customer_id": odoo_customer_id,
                        "stripe_customer_id": stripe_customer_id,
                        "registration_source": "webapp",
                        "created_at": datetime.now().isoformat(),
                    },
                }
            )

            # 6. Handle subscription if not free tier
            subscription_data = None
            tier = registration_data.get("subscription_tier", "free")

            if tier != "free":
                # Create subscription product in Odoo
                product_id = await self.erp_adapter.create_subscription_product(
                    {
                        "name": f"GraphRAG SaaS - {tier.title()} Plan",
                        "tier": tier,
                        "price": self._get_tier_price(tier),
                        "billing_cycle": registration_data.get(
                            "billing_cycle", "monthly"
                        ),
                    }
                )

                # Create subscription order in Odoo
                odoo_order_id = await self.erp_adapter.create_subscription_order(
                    customer_id=odoo_customer_id,
                    product_id=product_id,
                    billing_cycle=registration_data.get("billing_cycle", "monthly"),
                )

                # Create Stripe subscription
                stripe_subscription = self.stripe_billing.create_subscription(
                    customer_id=stripe_customer_id,
                    tier=tier,
                    billing_cycle=registration_data.get("billing_cycle", "monthly"),
                )

                # Save subscription in Supabase
                subscription_data = self.supabase_adapter.create_subscription(
                    {
                        "user_id": user_id,
                        "tier": tier,
                        "status": "pending",
                        "billing_cycle": registration_data.get(
                            "billing_cycle", "monthly"
                        ),
                        "stripe_subscription_id": stripe_subscription.get(
                            "subscription_id"
                        ),
                        "odoo_order_id": odoo_order_id,
                        "starts_at": datetime.now().isoformat(),
                        "expires_at": self._calculate_expiry_date(
                            registration_data.get("billing_cycle", "monthly")
                        ).isoformat(),
                    }
                )

            return {
                "success": True,
                "user": user_response.user,
                "integrations": {
                    "odoo": {
                        "customer_id": odoo_customer_id,
                        "order_id": odoo_order_id if tier != "free" else None,
                    },
                    "stripe": {
                        "customer_id": stripe_customer_id,
                        "subscription_id": (
                            stripe_subscription.get("subscription_id")
                            if tier != "free"
                            else None
                        ),
                        "client_secret": (
                            stripe_subscription.get("client_secret")
                            if tier != "free"
                            else None
                        ),
                    },
                    "supabase": {
                        "profile_id": supabase_profile.get("supabase_profile_id"),
                        "subscription": subscription_data,
                    },
                },
                "next_steps": {
                    "payment_required": tier != "free",
                    "setup_client_secret": (
                        stripe_subscription.get("client_secret")
                        if tier != "free"
                        else None
                    ),
                },
            }

        except Exception as e:
            # Rollback logic could be implemented here
            raise ApplicationError(
                f"Complete registration failed: {str(e)}",
                error_code=ERROR_COMPLETE_REGISTRATION_FAILED,
            )

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user and return complete profile."""
        auth_result = self.supabase_auth.authenticate_user(email, password)

        if auth_result:
            user_id = auth_result.get("user", {}).get("id")

            # Get subscription info from Supabase
            subscription = self.supabase_adapter.get_user_subscription(user_id)

            # Get customer info from Odoo
            odoo_subscriptions = await self.erp_adapter.get_customer_subscriptions(
                email
            )

            return {
                "access_token": auth_result.get("access_token"),
                "user": auth_result.get("user"),
                "subscription": subscription,
                "odoo_orders": odoo_subscriptions,
                "expires_in": auth_result.get("expires_in"),
            }

        return None

    async def get_complete_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile from all systems."""
        try:
            # Get from Supabase
            supabase_profile = self.supabase_adapter.list_customers(page=1, limit=1)

            if supabase_profile:
                profile = supabase_profile[0]
                email = profile.get("email")

                # Get Odoo data
                odoo_subscriptions = await self.erp_adapter.get_customer_subscriptions(
                    email
                )

                # Get subscription
                subscription = self.supabase_adapter.get_user_subscription(user_id)

                return {
                    "profile": profile,
                    "subscription": subscription,
                    "erp_orders": odoo_subscriptions,
                    "integrations_status": {
                        "supabase": "connected",
                        "odoo": "connected",
                        "stripe": "connected" if subscription else "not_connected",
                    },
                }

            return {}

        except Exception as e:
            raise ApplicationError(
                f"Failed to get complete profile: {str(e)}",
                error_code=ERROR_GET_PROFILE_FAILED,
            )

    def sync_usage_across_systems(
        self, user_id: str, usage_data: Dict[str, Any]
    ) -> bool:
        """Sync usage metrics across all systems."""
        supabase_updated = False
        erp_updated = False
        supabase_error: Optional[Exception] = None
        erp_error: Optional[Exception] = None

        try:
            supabase_updated = self.supabase_adapter.update_usage_metrics(
                user_id, usage_data
            )
        except Exception as e:  # pragma: no cover - error aggregation handled below
            supabase_error = e

        try:
            erp_updated = self.erp_adapter.update_usage_metrics(user_id, usage_data)
        except Exception as e:  # pragma: no cover - error aggregation handled below
            erp_error = e

        if supabase_error or erp_error:
            errors = []
            if supabase_error:
                errors.append(f"Supabase update failed: {supabase_error}")
            if erp_error:
                errors.append(f"ERP update failed: {erp_error}")
            raise ApplicationError(
                "; ".join(errors),
                error_code=ERROR_SYNC_USAGE_FAILED,
            )

        return supabase_updated and erp_updated

    def _get_tier_price(self, tier: str) -> float:
        """Get price for subscription tier."""
        prices = {"starter": 29.0, "professional": 99.0, "enterprise": 299.0}
        return prices.get(tier, 0.0)

    def _calculate_expiry_date(self, billing_cycle: str) -> datetime:
        """Calculate subscription expiry date."""
        now = datetime.now()
        if billing_cycle == "monthly":
            return now + timedelta(days=30)
        elif billing_cycle == "yearly":
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=30)

    async def _create_organization(self, name: str) -> str:
        """Create organization."""
        return str(uuid.uuid4())
