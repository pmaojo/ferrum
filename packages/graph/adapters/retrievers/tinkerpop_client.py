from __future__ import annotations

from typing import Iterable, Protocol

from gremlin_python.driver.client import Client
from gremlin_python.driver.serializer import GraphSONSerializersV3d0


class GraphDBClient(Protocol):
    """Protocol for Gremlin-compatible clients."""

    def query(self, gremlin: str) -> Iterable:
        """Execute a traversal and return the raw result set."""
        ...

    def close(self) -> None:
        """Close the underlying client connection."""
        ...


class TinkerPopClient(GraphDBClient):
    """Concrete Gremlin client using ``gremlinpython``."""

    def __init__(self, url: str) -> None:
        self._client = Client(url, "g", message_serializer=GraphSONSerializersV3d0())

    def query(self, gremlin: str) -> Iterable:
        return self._client.submit(gremlin).all().result()

    def close(self) -> None:
        self._client.close()
