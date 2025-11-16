"""Service for suggesting ontology enrichment from triples."""

from typing import Any, List

from domain.entities import Triple
from .entities import Hypothesis


class OntologyEnrichmentService:
    """Suggest new concepts or relationships for an ontology."""

    def __init__(self, ontology_repo: Any) -> None:
        self._ontology_repo = ontology_repo

    def suggest(
        self, *, triples: List[Triple], ontology_version_id: str, tenant_id: str
    ) -> List[Hypothesis]:
        ontology = self._ontology_repo.get_version(ontology_version_id, tenant_id)
        existing = set(getattr(ontology, "predicates", []))
        suggestions = {
            t.predicate for t in triples if t.predicate not in existing
        }
        return [Hypothesis(statement=p) for p in suggestions]
