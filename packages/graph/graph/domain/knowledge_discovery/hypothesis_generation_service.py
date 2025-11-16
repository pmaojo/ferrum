"""Service for generating hypotheses from discovered patterns."""

from typing import List

from domain.entities import Triple
from .entities import Pattern, Hypothesis


class HypothesisGenerationService:
    """Generate simple hypotheses based on frequent patterns."""

    def generate(self, *, patterns: List[Pattern], triples: List[Triple]) -> List[Hypothesis]:
        hypotheses = []
        for pattern in patterns:
            hypotheses.append(
                Hypothesis(statement=f"Relationship {pattern.predicate} is meaningful")
            )
        return hypotheses
