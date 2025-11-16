"""Port for hybrid search operations combining knowledge graph and web search."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol


class HybridSearchPort(Protocol):
    """Port for hybrid search operations."""

    @abstractmethod
    async def search_hybrid(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        query: str,
        kg_limit: int = 10,
        web_limit: int = 5,
        web_categories: Optional[List[str]] = None,
        threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Perform hybrid search combining knowledge graph and web results.

        Args:
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            query: Search query text
            kg_limit: Maximum knowledge graph results
            web_limit: Maximum web search results
            web_categories: Optional web search categories
            threshold: Minimum similarity threshold for KG results

        Returns:
            Dictionary with combined search results

        Raises:
            SearchError: When hybrid search operation fails
        """
        ...

    @abstractmethod
    async def enrich_entities(
        self,
        *,
        entities: List[Dict[str, Any]],
        query: str,
        web_limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Enrich entity results with web search context.

        Args:
            entities: List of entity dictionaries
            query: Original search query
            web_limit: Maximum web results per entity

        Returns:
            List of enriched entity dictionaries

        Raises:
            SearchError: When enrichment fails
        """
        ...
