from typing import List

from application.ports.knowledge_discovery import PatternMiningPort
from domain.entities import Triple
from domain.knowledge_discovery import Pattern, PatternMiningService


class SimplePatternMiningAdapter(PatternMiningPort):
    """Adapter using PatternMiningService."""

    def __init__(self, service: PatternMiningService) -> None:
        self._service = service

    def mine(self, *, triples: List[Triple], min_support: int = 2) -> List[Pattern]:
        return self._service.mine(triples=triples, min_support=min_support)
