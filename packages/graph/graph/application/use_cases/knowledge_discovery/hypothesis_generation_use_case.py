"""Use case for hypothesis generation."""

from dataclasses import dataclass
from typing import List

from application.ports.knowledge_discovery import (
    HypothesisGenerationPort,
    PatternMiningPort,
    TripleProviderPort,
)
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Hypothesis


@dataclass
class HypothesisGenerationRequest:
    kg_id: str
    tenant_id: str
    min_support: int = 2


@dataclass
class HypothesisGenerationResponse:
    hypotheses: List[Hypothesis]


class HypothesisGenerationUseCase(
    BaseUseCase[HypothesisGenerationRequest, HypothesisGenerationResponse]
):
    """Generate hypotheses from patterns discovered in the graph."""

    def __init__(
        self,
        triple_provider: TripleProviderPort,
        miner: PatternMiningPort,
        generator: HypothesisGenerationPort,
    ) -> None:
        super().__init__()
        self._triple_provider = triple_provider
        self._miner = miner
        self._generator = generator

    async def _execute_internal(
        self, request: HypothesisGenerationRequest
    ) -> HypothesisGenerationResponse:
        triples = self._triple_provider.get_triples(
            kg_id=request.kg_id, tenant_id=request.tenant_id
        )
        patterns = self._miner.mine(triples=triples, min_support=request.min_support)
        hypotheses = self._generator.generate(patterns=patterns, triples=triples)
        return HypothesisGenerationResponse(hypotheses=hypotheses)
