"""Use case for suggesting ontology enrichment."""

from dataclasses import dataclass
from typing import List

from application.ports.knowledge_discovery import (
    OntologyEnrichmentPort,
    TripleProviderPort,
)
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Hypothesis


@dataclass
class OntologyEnrichmentRequest:
    kg_id: str
    tenant_id: str
    ontology_version_id: str


@dataclass
class OntologyEnrichmentResponse:
    suggestions: List[Hypothesis]


class OntologyEnrichmentUseCase(
    BaseUseCase[OntologyEnrichmentRequest, OntologyEnrichmentResponse]
):
    """Suggest ontology enrichment based on graph patterns."""

    def __init__(
        self,
        triple_provider: TripleProviderPort,
        enrichment: OntologyEnrichmentPort,
    ) -> None:
        super().__init__()
        self._triple_provider = triple_provider
        self._enrichment = enrichment

    async def _execute_internal(
        self, request: OntologyEnrichmentRequest
    ) -> OntologyEnrichmentResponse:
        triples = self._triple_provider.get_triples(
            kg_id=request.kg_id, tenant_id=request.tenant_id
        )
        suggestions = self._enrichment.suggest(
            triples=triples,
            ontology_version_id=request.ontology_version_id,
            tenant_id=request.tenant_id,
        )
        return OntologyEnrichmentResponse(suggestions=suggestions)
