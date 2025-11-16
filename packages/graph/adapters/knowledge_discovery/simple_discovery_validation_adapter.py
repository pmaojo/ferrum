from typing import List

from application.ports.knowledge_discovery import DiscoveryValidationPort
from domain.knowledge_discovery import (
    DiscoveryValidationService,
    Hypothesis,
    ValidationResult,
)


class SimpleDiscoveryValidationAdapter(DiscoveryValidationPort):
    """Adapter for validating hypotheses using DiscoveryValidationService."""

    def __init__(self, service: DiscoveryValidationService) -> None:
        self._service = service

    def validate(
        self,
        *,
        hypotheses: List[Hypothesis],
        ontology_version_id: str,
        tenant_id: str,
    ) -> List[ValidationResult]:
        return self._service.validate(
            hypotheses=hypotheses,
            ontology_version_id=ontology_version_id,
            tenant_id=tenant_id,
        )
