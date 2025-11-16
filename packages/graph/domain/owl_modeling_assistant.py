from __future__ import annotations

from typing import List, Optional

from application.ports import OwlAxiomGeneratorPort, OntologyValidatorPort
from domain.entities import Triple, ValidationReport


class OwlModelingAssistant:
    """Service coordinating text parsing, axiom generation and validation."""

    def __init__(
        self,
        generator: OwlAxiomGeneratorPort,
        validator: OntologyValidatorPort,
    ) -> None:
        self._generator = generator
        self._validator = validator

    def generate_model(
        self,
        *,
        text: str,
        ontology_version_id: str,
        tenant_id: str,
    ) -> ValidationReport:
        axioms = self._generator.generate_axioms(
            text=text, tenant_id=tenant_id
        )
        triples = [
            t for ax in axioms if (t := self._axiom_to_triple(ax, tenant_id))
        ]
        return self._validator.validate(
            triples=triples, ontology_version_id=ontology_version_id
        )

    def _axiom_to_triple(self, axiom: str, tenant_id: str) -> Optional[Triple]:
        parts = axiom.strip().split()
        if not parts:
            return None
        head = parts[0]
        if head == "Class:" and len(parts) == 2:
            return Triple(parts[1], "rdf:type", "Class", tenant_id)
        if head == "ObjectProperty:" and len(parts) == 2:
            return Triple(parts[1], "rdf:type", "ObjectProperty", tenant_id)
        if head == "DataProperty:" and len(parts) == 2:
            return Triple(parts[1], "rdf:type", "DataProperty", tenant_id)
        if head == "Individual:" and len(parts) == 2:
            return Triple(parts[1], "rdf:type", "Individual", tenant_id)
        if head == "ClassAssertion:" and len(parts) == 3:
            return Triple(parts[2], "type", parts[1], tenant_id)
        if head == "ObjectPropertyAssertion:" and len(parts) == 4:
            return Triple(parts[2], parts[1], parts[3], tenant_id)
        if head == "DataPropertyAssertion:" and len(parts) >= 4:
            return Triple(parts[2], parts[1], " ".join(parts[3:]), tenant_id)
        return None

