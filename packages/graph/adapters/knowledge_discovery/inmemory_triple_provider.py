from typing import List

from application.ports.knowledge_discovery import TripleProviderPort
from domain.entities import Triple


class InMemoryTripleProvider(TripleProviderPort):
    """Simple in-memory triple store."""

    def __init__(self, triples: List[Triple]):
        self._triples = triples

    def get_triples(self, *, kg_id: str, tenant_id: str) -> List[Triple]:
        return [t for t in self._triples if t.tenant_id == tenant_id]
