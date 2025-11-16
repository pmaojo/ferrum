from abc import abstractmethod
from typing import Any, Dict, Protocol


class GraphMetadataRepositoryPort(Protocol):
    """Port for storing and retrieving knowledge graph metadata."""

    @abstractmethod
    def save_description(self, kg_id: str, tenant_id: str, description: str) -> None:
        """Persist the description for a knowledge graph."""
        ...

    @abstractmethod
    def get_metadata(self, kg_id: str, tenant_id: str) -> Dict[str, Any]:
        """Retrieve metadata for a knowledge graph."""
        ...
