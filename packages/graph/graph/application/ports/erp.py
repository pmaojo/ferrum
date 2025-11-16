from abc import abstractmethod
from typing import Any, Dict, List, Protocol


class ERPPort(Protocol):
    """Port for ERP integrations such as customer and subscription management."""

    @abstractmethod
    async def create_customer(self, user_data: Dict[str, Any]) -> int:
        """Create a customer and return its identifier."""
        ...

    @abstractmethod
    async def create_subscription_product(
        self, subscription_data: Dict[str, Any]
    ) -> int:
        """Create a subscription product and return its identifier."""
        ...

    @abstractmethod
    async def create_subscription_order(
        self,
        customer_id: int,
        product_id: int,
        billing_cycle: str = "monthly",
    ) -> int:
        """Create a subscription order for a customer."""
        ...

    @abstractmethod
    async def get_customer_subscriptions(
        self, customer_email: str
    ) -> List[Dict[str, Any]]:
        """Retrieve subscriptions for a customer."""
        ...


__all__ = ["ERPPort"]
