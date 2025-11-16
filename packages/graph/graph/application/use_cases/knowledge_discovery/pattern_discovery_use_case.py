"""Use case for discovering frequent patterns."""

from dataclasses import dataclass
from typing import List

from application.ports.knowledge_discovery import PatternMiningPort, TripleProviderPort
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Pattern


@dataclass
class PatternDiscoveryRequest:
    kg_id: str
    tenant_id: str
    min_support: int = 2


@dataclass
class PatternDiscoveryResponse:
    patterns: List[Pattern]


class PatternDiscoveryUseCase(
    BaseUseCase[PatternDiscoveryRequest, PatternDiscoveryResponse]
):
    """Discover frequent patterns in a knowledge graph."""

    def __init__(
        self,
        triple_provider: TripleProviderPort,
        miner: PatternMiningPort,
    ) -> None:
        super().__init__()
        self._triple_provider = triple_provider
        self._miner = miner

    async def _execute_internal(
        self, request: PatternDiscoveryRequest
    ) -> PatternDiscoveryResponse:
        triples = self._triple_provider.get_triples(
            kg_id=request.kg_id, tenant_id=request.tenant_id
        )
        patterns = self._miner.mine(triples=triples, min_support=request.min_support)
        return PatternDiscoveryResponse(patterns=patterns)
