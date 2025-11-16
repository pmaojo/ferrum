"""Supabase integration adapter for user management and subscriptions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from domain.exceptions import ApplicationError


@dataclass
class SupabaseConfig:
    """Supabase configuration."""

    url: str
    anon_key: str
    service_role_key: str
    project_ref: str


class SupabaseIntegrationAdapter:
    """Adapter for integrating with Supabase backend."""

    def __init__(self, config: SupabaseConfig):
        """Initialize Supabase adapter."""
        self.config = config
        self.headers = {
            "apikey": config.service_role_key,
            "Authorization": f"Bearer {config.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def create_user_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user profile in Supabase."""
        try:
            url = f"{self.config.url}/rest/v1/profiles"

            profile_data = {
                "id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "organization": user_data.get("organization"),
                "tier": user_data.get("tier", "free"),
                "created_at": datetime.now().isoformat(),
                "metadata": user_data.get("metadata", {}),
            }

            response = requests.post(url, headers=self.headers, json=profile_data)

            if response.status_code in [200, 201]:
                return response.json()[0] if response.json() else profile_data
            else:
                raise ApplicationError(
                    f"Failed to create user profile: {response.text}"
                )

        except Exception as e:
            raise ApplicationError(f"Supabase user creation failed: {str(e)}")

    def create_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create subscription in Supabase."""
        try:
            url = f"{self.config.url}/rest/v1/subscriptions"

            sub_data = {
                "user_id": subscription_data.get("user_id"),
                "tier": subscription_data.get("tier"),
                "status": subscription_data.get("status", "active"),
                "billing_cycle": subscription_data.get("billing_cycle", "monthly"),
                "price_usd": subscription_data.get("price_usd", 0.0),
                "stripe_subscription_id": subscription_data.get(
                    "stripe_subscription_id"
                ),
                "starts_at": subscription_data.get("starts_at"),
                "expires_at": subscription_data.get("expires_at"),
                "created_at": datetime.now().isoformat(),
            }

            response = requests.post(url, headers=self.headers, json=sub_data)

            if response.status_code in [200, 201]:
                return response.json()[0] if response.json() else sub_data
            else:
                raise ApplicationError(
                    f"Failed to create subscription: {response.text}"
                )

        except Exception as e:
            raise ApplicationError(f"Supabase subscription creation failed: {str(e)}")

    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user subscription from Supabase."""
        try:
            url = f"{self.config.url}/rest/v1/subscriptions"
            params = {"user_id": f"eq.{user_id}", "status": "eq.active", "select": "*"}

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                subscriptions = response.json()
                return subscriptions[0] if subscriptions else None
            else:
                return None

        except Exception as e:
            raise ApplicationError(f"Failed to get subscription: {str(e)}")

    def update_usage_metrics(self, user_id: str, metrics: Dict[str, Any]) -> bool:
        """Update usage metrics for user."""
        try:
            url = f"{self.config.url}/rest/v1/usage_metrics"

            usage_data = {
                "user_id": user_id,
                "month": datetime.now().strftime("%Y-%m"),
                "queries_count": metrics.get("queries_count", 0),
                "storage_gb": metrics.get("storage_gb", 0.0),
                "api_calls": metrics.get("api_calls", 0),
                "updated_at": datetime.now().isoformat(),
            }

            # Upsert operation
            response = requests.post(
                url,
                headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
                json=usage_data,
            )

            return response.status_code in [200, 201]

        except Exception as e:
            raise ApplicationError(f"Failed to update usage metrics: {str(e)}")

    def list_customers(self, page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """List customers with pagination."""
        try:
            url = f"{self.config.url}/rest/v1/profiles"
            params = {
                "select": "id,email,name,organization,tier,created_at",
                "order": "created_at.desc",
                "limit": limit,
                "offset": (page - 1) * limit,
            }

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                return []

        except Exception as e:
            raise ApplicationError(f"Failed to list customers: {str(e)}")

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with Supabase Auth."""
        try:
            url = f"{self.config.url}/auth/v1/token?grant_type=password"

            auth_data = {"email": email, "password": password}

            headers = {
                "apikey": self.config.anon_key,
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=auth_data)

            if response.status_code == 200:
                auth_result = response.json()
                return {
                    "access_token": auth_result.get("access_token"),
                    "refresh_token": auth_result.get("refresh_token"),
                    "user": auth_result.get("user"),
                    "expires_in": auth_result.get("expires_in"),
                }
            else:
                return None

        except Exception as e:
            raise ApplicationError(f"Authentication failed: {str(e)}")

    def sync_user_to_supabase(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync user data to Supabase and return profile info."""
        profile = self.create_user_profile(user_data)

        return {
            "supabase_profile_id": profile.get("id"),
            "synced_at": datetime.now().isoformat(),
        }
