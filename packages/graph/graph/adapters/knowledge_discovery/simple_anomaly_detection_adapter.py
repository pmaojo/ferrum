from typing import List

from application.ports.knowledge_discovery import AnomalyDetectionPort
from domain.entities import Triple
from domain.knowledge_discovery import Anomaly, AnomalyDetectionService


class SimpleAnomalyDetectionAdapter(AnomalyDetectionPort):
    """Adapter for anomaly detection using AnomalyDetectionService."""

    def __init__(self, service: AnomalyDetectionService) -> None:
        self._service = service

    def detect(
        self,
        *,
        triples: List[Triple],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[Anomaly]:
        return self._service.detect(
            triples=triples,
            ontology_version_id=ontology_version_id,
            tenant_id=tenant_id,
        )
