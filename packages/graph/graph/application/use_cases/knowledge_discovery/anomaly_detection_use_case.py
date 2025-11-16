"""Use case for detecting ontology anomalies."""

from dataclasses import dataclass
from typing import List

from application.ports.knowledge_discovery import (
    AnomalyDetectionPort,
    TripleProviderPort,
)
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Anomaly


@dataclass
class AnomalyDetectionRequest:
    kg_id: str
    tenant_id: str
    ontology_version_id: str


@dataclass
class AnomalyDetectionResponse:
    anomalies: List[Anomaly]


class AnomalyDetectionUseCase(
    BaseUseCase[AnomalyDetectionRequest, AnomalyDetectionResponse]
):
    """Identify anomalies in the knowledge graph."""

    def __init__(
        self,
        triple_provider: TripleProviderPort,
        detector: AnomalyDetectionPort,
    ) -> None:
        super().__init__()
        self._triple_provider = triple_provider
        self._detector = detector

    async def _execute_internal(
        self, request: AnomalyDetectionRequest
    ) -> AnomalyDetectionResponse:
        triples = self._triple_provider.get_triples(
            kg_id=request.kg_id, tenant_id=request.tenant_id
        )
        anomalies = self._detector.detect(
            triples=triples,
            ontology_version_id=request.ontology_version_id,
            tenant_id=request.tenant_id,
        )
        return AnomalyDetectionResponse(anomalies=anomalies)
