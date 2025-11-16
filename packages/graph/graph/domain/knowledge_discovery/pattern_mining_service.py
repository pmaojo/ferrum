"""Service for discovering frequent patterns in knowledge graph triples."""

from collections import Counter
from typing import List

from domain.entities import Triple
from .entities import Pattern


class PatternMiningService:
    """Simple frequency-based pattern mining service."""

    def mine(self, *, triples: List[Triple], min_support: int = 2) -> List[Pattern]:
        """Find frequent predicates appearing at least ``min_support`` times."""
        counts = Counter(t.predicate for t in triples)
        return [
            Pattern(predicate=p, support=c)
            for p, c in counts.items()
            if c >= min_support
        ]
