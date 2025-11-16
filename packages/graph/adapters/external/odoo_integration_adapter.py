"""Odoo integration adapter for user and product management."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from application.exceptions import ApplicationError
from application.ports.erp import ERPPort

ERROR_ODOO_AUTH_FAILED = "ODOO_AUTH_FAILED"
ERROR_ODOO_CREATE_CUSTOMER_FAILED = "ODOO_CREATE_CUSTOMER_FAILED"
ERROR_ODOO_CREATE_PRODUCT_FAILED = "ODOO_CREATE_PRODUCT_FAILED"
ERROR_ODOO_CREATE_ORDER_FAILED = "ODOO_CREATE_ORDER_FAILED"
ERROR_ODOO_FIND_CUSTOMER_FAILED = "ODOO_FIND_CUSTOMER_FAILED"
ERROR_ODOO_GET_SUBSCRIPTIONS_FAILED = "ODOO_GET_SUBSCRIPTIONS_FAILED"


@dataclass
class OdooConfig:
    """Odoo configuration."""

    url: str
    database: str
    username: str
    password: str
    api_key: Optional[str] = None


class OdooIntegrationAdapter(ERPPort):
    """Adapter for integrating with Odoo ERP system."""

    def __init__(
        self,
        config: OdooConfig,
        client: Optional[httpx.AsyncClient] = None,
        auto_authenticate: bool = True,
    ) -> None:
        """Initialize Odoo adapter with provided HTTP client."""
        self.config = config
        self.client = client or httpx.AsyncClient()
        self.user_id: Optional[int] = None

        if auto_authenticate:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._authenticate())
            else:
                loop.run_until_complete(self._authenticate())

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

    async def _authenticate(self) -> None:
        """Authenticate with Odoo."""
        try:
            auth_url = f"{self.config.url}/xmlrpc/2/common"

            response = await self.client.post(
                auth_url,
                json={
                    "service": "common",
                    "method": "authenticate",
                    "args": [
                        self.config.database,
                        self.config.username,
                        self.config.password,
                        {},
                    ],
                },
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("result"):
                    self.user_id = result["result"]
                else:
                    raise ApplicationError(
                        "Odoo authentication failed",
                        error_code=ERROR_ODOO_AUTH_FAILED,
                    )
            else:
                raise ApplicationError(
                    f"Odoo authentication error: {response.status_code}",
                    error_code=ERROR_ODOO_AUTH_FAILED,
                )

        except Exception as e:
            raise ApplicationError(
                f"Failed to authenticate with Odoo: {str(e)}",
                error_code=ERROR_ODOO_AUTH_FAILED,
            )

    @classmethod
    async def create(
        cls, config: OdooConfig, client: Optional[httpx.AsyncClient] = None
    ) -> "OdooIntegrationAdapter":
        """Instantiate adapter and authenticate."""
        adapter = cls(config=config, client=client)
        await adapter._authenticate()
        return adapter

    async def create_customer(self, user_data: Dict[str, Any]) -> int:
        """Create a customer in Odoo."""
        try:
            url = f"{self.config.url}/xmlrpc/2/object"

            customer_data = {
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "is_company": False,
                "customer_rank": 1,
                "supplier_rank": 0,
                "category_id": [(4, 1)],  # Customer category
            }

            response = await self.client.post(
                url,
                json={
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        self.config.database,
                        self.user_id,
                        self.config.password,
                        "res.partner",
                        "create",
                        [customer_data],
                    ],
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result["result"]
            else:
                raise ApplicationError(
                    f"Failed to create customer: {response.status_code}",
                    error_code=ERROR_ODOO_CREATE_CUSTOMER_FAILED,
                )

        except Exception as e:
            raise ApplicationError(
                f"Failed to create customer in Odoo: {str(e)}",
                error_code=ERROR_ODOO_CREATE_CUSTOMER_FAILED,
            )

    async def create_subscription_product(
        self, subscription_data: Dict[str, Any]
    ) -> int:
        """Create a subscription product in Odoo."""
        try:
            url = f"{self.config.url}/xmlrpc/2/object"

            product_data = {
                "name": subscription_data.get("name"),
                "list_price": subscription_data.get("price", 0.0),
                "type": "service",
                "categ_id": 1,  # Service category
                "sale_ok": True,
                "purchase_ok": False,
                "recurring_invoice": True,
                "invoice_policy": "order",
                "default_code": subscription_data.get("tier", "").upper(),
            }

            response = await self.client.post(
                url,
                json={
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        self.config.database,
                        self.user_id,
                        self.config.password,
                        "product.template",
                        "create",
                        [product_data],
                    ],
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result["result"]
            else:
                raise ApplicationError(
                    f"Failed to create product: {response.status_code}",
                    error_code=ERROR_ODOO_CREATE_PRODUCT_FAILED,
                )

        except Exception as e:
            raise ApplicationError(
                f"Failed to create product in Odoo: {str(e)}",
                error_code=ERROR_ODOO_CREATE_PRODUCT_FAILED,
            )

    async def create_subscription_order(
        self,
        customer_id: int,
        product_id: int,
        billing_cycle: str = "monthly",
    ) -> int:
        """Create a subscription order in Odoo."""
        try:
            url = f"{self.config.url}/xmlrpc/2/object"

            # Create sale order
            order_data = {
                "partner_id": customer_id,
                "state": "draft",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_id,
                            "product_uom_qty": 1,
                            "name": f"GraphRAG SaaS - {billing_cycle.title()} Subscription",
                        },
                    )
                ],
            }

            response = await self.client.post(
                url,
                json={
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        self.config.database,
                        self.user_id,
                        self.config.password,
                        "sale.order",
                        "create",
                        [order_data],
                    ],
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result["result"]
            else:
                raise ApplicationError(
                    f"Failed to create order: {response.status_code}",
                    error_code=ERROR_ODOO_CREATE_ORDER_FAILED,
                )

        except Exception as e:
            raise ApplicationError(
                f"Failed to create order in Odoo: {str(e)}",
                error_code=ERROR_ODOO_CREATE_ORDER_FAILED,
            )

    async def get_customer_subscriptions(
        self, customer_email: str
    ) -> List[Dict[str, Any]]:
        """Get customer subscriptions from Odoo."""
        try:
            url = f"{self.config.url}/xmlrpc/2/object"

            # First, find the customer
            customer_response = await self.client.post(
                url,
                json={
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        self.config.database,
                        self.user_id,
                        self.config.password,
                        "res.partner",
                        "search_read",
                        [[["email", "=", customer_email]]],
                        {"fields": ["id", "name", "email"]},
                    ],
                },
            )

            if customer_response.status_code != 200:
                raise ApplicationError(
                    "Failed to find customer",
                    error_code=ERROR_ODOO_FIND_CUSTOMER_FAILED,
                )

            customers = customer_response.json()["result"]
            if not customers:
                return []

            customer_id = customers[0]["id"]

            # Get customer orders
            orders_response = await self.client.post(
                url,
                json={
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        self.config.database,
                        self.user_id,
                        self.config.password,
                        "sale.order",
                        "search_read",
                        [[["partner_id", "=", customer_id]]],
                        {
                            "fields": [
                                "id",
                                "name",
                                "state",
                                "amount_total",
                                "date_order",
                            ]
                        },
                    ],
                },
            )

            if orders_response.status_code == 200:
                return orders_response.json()["result"]
            else:
                return []

        except Exception as e:
            raise ApplicationError(
                f"Failed to get customer subscriptions: {str(e)}",
                error_code=ERROR_ODOO_GET_SUBSCRIPTIONS_FAILED,
            )

    async def sync_user_to_odoo(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync user data to Odoo and return Odoo customer info."""
        customer_id = await self.create_customer(user_data)

        return {"odoo_customer_id": customer_id, "synced_at": "2024-01-15T10:00:00Z"}
