"""Production authentication service combining Supabase + Stripe."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from adapters.auth.stripe_billing_adapter import StripeBillingAdapter
from adapters.auth.supabase_auth_adapter import SupabaseAuthAdapter
from adapters.external.supabase_integration_adapter import (
    SupabaseConfig,
    SupabaseIntegrationAdapter,
)
from application.use_cases.create_user_use_case import CreateUserUseCase
from application.use_cases.dto import CreateUserRequestDTO
from domain.exceptions import ApplicationError


class ProductionAuthService:
    """Production-ready authentication service."""

    def __init__(self, create_user_use_case: CreateUserUseCase):
        """Initialize production auth service."""
        self.create_user_use_case = create_user_use_case
        self.supabase_auth = SupabaseAuthAdapter()
        self.stripe_billing = StripeBillingAdapter()

        # Initialize Supabase integration
        config = SupabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            project_ref=os.getenv("SUPABASE_PROJECT_REF", ""),
        )
        self.supabase_adapter = SupabaseIntegrationAdapter(config)

    async def register_user(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new user with Supabase + Stripe integration."""
        try:
            # Create organization first
            org_id = await self._create_organization(
                registration_data.get("organization_name")
            )

            # Create user in our system
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
                    f"Failed to create user: {user_response.error_message}"
                )

            user_id = user_response.user.id

            # Create Stripe customer
            stripe_customer_id = self.stripe_billing.create_customer(
                {
                    "email": registration_data.get("email"),
                    "name": registration_data.get("name"),
                    "user_id": user_id,
                    "organization": registration_data.get("organization_name"),
                }
            )

            # Sync to Supabase
            supabase_data = self.supabase_adapter.sync_user_to_supabase(
                {
                    "user_id": user_id,
                    "email": registration_data.get("email"),
                    "name": registration_data.get("name"),
                    "organization": registration_data.get("organization_name"),
                    "tier": registration_data.get("subscription_tier", "free"),
                    "metadata": {
                        "stripe_customer_id": stripe_customer_id,
                        "registration_source": "webapp",
                    },
                }
            )

            # Create subscription if not free tier
            subscription_data = None
            tier = registration_data.get("subscription_tier", "free")
            if tier != "free":
                subscription_result = self.stripe_billing.create_subscription(
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
                        "stripe_subscription_id": subscription_result.get(
                            "subscription_id"
                        ),
                        "starts_at": datetime.now().isoformat(),
                        "expires_at": (
                            datetime.now().replace(day=1) + timedelta(days=32)
                        )
                        .replace(day=1)
                        .isoformat(),
                    }
                )

            return {
                "success": True,
                "user": user_response.user,
                "stripe_customer_id": stripe_customer_id,
                "supabase_profile": supabase_data,
                "subscription": subscription_data,
                "setup_intent_client_secret": (
                    subscription_result.get("client_secret")
                    if subscription_data
                    else None
                ),
            }

        except Exception as e:
            raise ApplicationError(f"Registration failed: {str(e)}")

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return session info."""
        auth_result = self.supabase_auth.authenticate_user(email, password)

        if auth_result:
            # Get subscription info
            user_id = auth_result.get("user", {}).get("id")
            subscription = self.supabase_adapter.get_user_subscription(user_id)

            return {
                "access_token": auth_result.get("access_token"),
                "user": auth_result.get("user"),
                "subscription": subscription,
                "expires_in": auth_result.get("expires_in"),
            }

        return None

    def get_user_context(
        self, request_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get user context from request."""
        return self.supabase_auth.get_current_user(request_context)

    async def _create_organization(self, name: str) -> str:
        """Create organization (placeholder)."""
        import uuid

        return str(uuid.uuid4())
