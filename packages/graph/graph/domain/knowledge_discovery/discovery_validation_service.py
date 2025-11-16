"""Service for validating generated hypotheses."""

from typing import List

from application.ports import OntologyValidatorPort
from domain.entities import Triple
from .entities import Hypothesis, ValidationResult


class DiscoveryValidationService:
    """Validate hypotheses using ontology constraints."""

    def __init__(self, validator: OntologyValidatorPort) -> None:
        self._validator = validator

    def validate(
        self,
        *,
        hypotheses: List[Hypothesis],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for hyp in hypotheses:
            triple = Triple("A", hyp.statement, "B", tenant_id)
            report = self._validator.validate(
                triples=[triple], ontology_version_id=ontology_version_id
            )
            confidence = 1.0 if report.is_consistent else 0.0
            results.append(ValidationResult(hypothesis=hyp, confidence=confidence))
        return results
