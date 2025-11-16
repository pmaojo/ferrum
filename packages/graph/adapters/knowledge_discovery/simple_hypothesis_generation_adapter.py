from typing import List

from application.ports.knowledge_discovery import HypothesisGenerationPort
from domain.entities import Triple
from domain.knowledge_discovery import Hypothesis, HypothesisGenerationService, Pattern


class SimpleHypothesisGenerationAdapter(HypothesisGenerationPort):
    """Adapter delegating to HypothesisGenerationService."""

    def __init__(self, service: HypothesisGenerationService) -> None:
        self._service = service

    def generate(
        self,
        *,
        patterns: List[Pattern],
        triples: List[Triple],
    ) -> List[Hypothesis]:
        return self._service.generate(patterns=patterns, triples=triples)
