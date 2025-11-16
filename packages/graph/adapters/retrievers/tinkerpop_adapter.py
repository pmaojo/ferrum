from __future__ import annotations

from typing import Any, Callable, Dict, List

from application.ports import GraphTraversalPort

from .tinkerpop_client import GraphDBClient, TinkerPopClient


class TinkerPopAdapter(GraphTraversalPort):
    """Adapter that delegates traversal execution to a Gremlin client."""

    def __init__(
        self,
        endpoint: str,
        *,
        client_factory: Callable[[str], GraphDBClient] = TinkerPopClient,
    ) -> None:
        self._client = client_factory(endpoint)

    def execute_traversal(self, traversal_query: str) -> List[Dict[str, Any]]:
        result = self._client.query(traversal_query)
        return list(result)

    def close(self) -> None:
        self._client.close()
