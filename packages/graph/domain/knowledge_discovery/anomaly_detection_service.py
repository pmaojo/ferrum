"""Service for detecting anomalies in triples using ontology validation."""

from typing import List

from application.ports import OntologyValidatorPort
from domain.entities import Triple
from .entities import Anomaly


class AnomalyDetectionService:
    """Detect ontology inconsistencies as anomalies."""

    def __init__(self, validator: OntologyValidatorPort) -> None:
        self._validator = validator

    def detect(
        self, *, triples: List[Triple], ontology_version_id: str, tenant_id: str
    ) -> List[Anomaly]:
        report = self._validator.validate(
            triples=triples, ontology_version_id=ontology_version_id
        )
        if report.is_consistent:
            return []
        return [Anomaly(description=cls) for cls in report.unsat_classes]
