"""Stripe billing adapter for subscription management."""

import os
from datetime import datetime
from typing import Any, Dict, List

import stripe

from domain.exceptions import ApplicationError


class StripeBillingAdapter:
    """Stripe billing adapter for subscription management."""

    def __init__(self):
        """Initialize Stripe adapter."""
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        # Subscription tier price mapping
        self.tier_prices = {
            "starter": os.getenv("STRIPE_STARTER_PRICE_ID"),
            "professional": os.getenv("STRIPE_PROFESSIONAL_PRICE_ID"),
            "enterprise": os.getenv("STRIPE_ENTERPRISE_PRICE_ID"),
        }

    def create_customer(self, user_data: Dict[str, Any]) -> str:
        """Create Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=user_data.get("email"),
                name=user_data.get("name"),
                metadata={
                    "user_id": user_data.get("user_id"),
                    "organization": user_data.get("organization", ""),
                },
            )
            return customer.id
        except Exception as e:
            raise ApplicationError(f"Failed to create Stripe customer: {str(e)}")

    def create_subscription(
        self,
        customer_id: str,
        tier: str,
        billing_cycle: str = "monthly",
    ) -> Dict[str, Any]:
        """Create Stripe subscription."""
        try:
            price_id = self.tier_prices.get(tier)
            if not price_id:
                raise ApplicationError(f"Invalid tier: {tier}")

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"],
            )

            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "status": subscription.status,
            }
        except Exception as e:
            raise ApplicationError(f"Failed to create subscription: {str(e)}")

    def get_customer_subscriptions(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get customer subscriptions."""
        try:
            subscriptions = stripe.Subscription.list(customer=customer_id)
            return [
                {
                    "id": sub.id,
                    "status": sub.status,
                    "current_period_start": datetime.fromtimestamp(
                        sub.current_period_start
                    ),
                    "current_period_end": datetime.fromtimestamp(
                        sub.current_period_end
                    ),
                    "tier": self._get_tier_from_price_id(sub.items.data[0].price.id),
                }
                for sub in subscriptions.data
            ]
        except Exception as e:
            raise ApplicationError(f"Failed to get subscriptions: {str(e)}")

    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> bool:
        """Cancel Stripe subscription."""
        try:
            if cancel_at_period_end:
                stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            else:
                stripe.Subscription.cancel(subscription_id)
            return True
        except Exception as e:
            raise ApplicationError(f"Failed to cancel subscription: {str(e)}")

    def _get_tier_from_price_id(self, price_id: str) -> str:
        """Get tier name from Stripe price ID."""
        for tier, pid in self.tier_prices.items():
            if pid == price_id:
                return tier
        return "unknown"

    def handle_webhook(self, payload: str, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )

            if event["type"] == "customer.subscription.updated":
                subscription = event["data"]["object"]
                return {
                    "event_type": "subscription_updated",
                    "subscription_id": subscription["id"],
                    "customer_id": subscription["customer"],
                    "status": subscription["status"],
                }
            elif event["type"] == "customer.subscription.deleted":
                subscription = event["data"]["object"]
                return {
                    "event_type": "subscription_cancelled",
                    "subscription_id": subscription["id"],
                    "customer_id": subscription["customer"],
                }

            return {"event_type": "unknown"}

        except Exception as e:
            raise ApplicationError(f"Webhook handling failed: {str(e)}")
