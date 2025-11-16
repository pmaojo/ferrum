from typing import List

from application.ports.knowledge_discovery import OntologyEnrichmentPort
from domain.entities import Triple
from domain.knowledge_discovery import Hypothesis, OntologyEnrichmentService


class SimpleOntologyEnrichmentAdapter(OntologyEnrichmentPort):
    """Adapter delegating to OntologyEnrichmentService."""

    def __init__(self, service: OntologyEnrichmentService) -> None:
        self._service = service

    def suggest(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[Hypothesis]:
        return self._service.suggest(
            triples=triples,
            ontology_version_id=ontology_version_id,
            tenant_id=tenant_id,
        )
