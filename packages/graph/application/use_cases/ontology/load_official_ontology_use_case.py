from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from adapters.ontology.owl_ontology_loader import OwlOntologyLoader
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import TenantScopedRequestDTO
from domain.entities import OntologyVersion, ScientificDomain, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class LoadOfficialOntologyRequestDTO(TenantScopedRequestDTO):
    """Request to load an official ontology."""

    ontology_name: str
    merge_with_custom_rules: bool = True
    custom_compatibility_rules: Optional[Dict[str, Any]] = None
    force_refresh: bool = False


@dataclass
class LoadOfficialOntologyResponseDTO:
    """Response from loading official ontology."""

    ontology_version_id: str
    axiom_count: int
    official_axioms: int
    custom_rules_added: int
    validation_result: ValidationReport
    available_relationships: List[str]
    processing_time_ms: float


class LoadOfficialOntologyUseCase(
    BaseUseCase[LoadOfficialOntologyRequestDTO, LoadOfficialOntologyResponseDTO]
):
    """Load official OWL ontologies and integrate with custom compatibility logic."""

    def __init__(
        self,
        owl_loader: OwlOntologyLoader,
        ontology_repository,  # Your ontology repository
        ontology_validator,  # Your validator
        tracer,
    ):
        super().__init__(tracer)
        self.owl_loader = owl_loader
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator

    def execute(
        self, request: LoadOfficialOntologyRequestDTO
    ) -> LoadOfficialOntologyResponseDTO:
        """Execute the use case."""
        from datetime import datetime

        start_time = datetime.utcnow()

        logger.info(f"Loading official ontology: {request.ontology_name}")

        # Load the official ontology
        official_ontology = self.owl_loader.load_official_ontology(
            ontology_name=request.ontology_name,
            tenant_id=request.tenant_id,
            force_refresh=request.force_refresh,
        )

        axioms = official_ontology.axioms.copy()
        official_count = len(axioms)

        # Add custom compatibility rules if requested
        custom_rules_count = 0
        if request.merge_with_custom_rules:
            compatibility_rules = (
                request.custom_compatibility_rules
                or self._get_default_permaculture_rules()
            )
            custom_axioms = self._generate_compatibility_axioms(compatibility_rules)
            axioms.extend(custom_axioms)
            custom_rules_count = len(custom_axioms)

        # Create enhanced ontology version
        enhanced_ontology = OntologyVersion.create(
            tenant_id=request.tenant_id,
            domain=ScientificDomain.AGRICULTURE,
            axioms=axioms,
            metadata={
                "base_ontology": request.ontology_name,
                "official_axioms": official_count,
                "custom_rules": custom_rules_count,
                "enhanced": True,
            },
        )

        # Save to repository
        saved_version = self.ontology_repository.save(enhanced_ontology)

        # Validate the combined ontology
        validation_result = self.ontology_validator.validate(
            triples=[], ontology_version_id=saved_version.id  # Ontology-only validation
        )

        # Extract available relationships
        relationships = self._extract_relationships(axioms)

        # Record metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.tracer.record_metric(
            name="official_ontology_loaded",
            value=1,
            tenant_id=request.tenant_id,
            ontology_name=request.ontology_name,
            axiom_count=len(axioms),
        )

        return LoadOfficialOntologyResponseDTO(
            ontology_version_id=saved_version.id,
            axiom_count=len(axioms),
            official_axioms=official_count,
            custom_rules_added=custom_rules_count,
            validation_result=validation_result,
            available_relationships=relationships,
            processing_time_ms=processing_time,
        )

    def _get_default_permaculture_rules(self) -> Dict[str, Any]:
        """Get default permaculture compatibility rules."""
        return {
            "nitrogen_cycle": {
                "fixers": ["Legume", "Clover", "Bean", "Pea", "Alfalfa", "Vetch"],
                "consumers": ["Tomato", "Corn", "Brassica", "Lettuce", "Spinach"],
                "compatibility": "high",
            },
            "allelopathy": {
                "walnut_inhibitors": ["Walnut", "Black_Walnut"],
                "sensitive_plants": ["Tomato", "Apple", "Pine"],
                "compatibility": "incompatible",
            },
            "pest_management": {
                "pest_repellers": ["Marigold", "Basil", "Mint", "Rosemary"],
                "protected_plants": ["Tomato", "Pepper", "Cabbage"],
                "compatibility": "beneficial",
            },
            "growth_patterns": {
                "ground_covers": ["Clover", "Thyme", "Strawberry"],
                "tall_plants": ["Corn", "Sunflower", "Tree"],
                "compatibility": "complementary",
            },
        }

    def _generate_compatibility_axioms(self, rules: Dict[str, Any]) -> List[str]:
        """Generate Manchester syntax axioms from compatibility rules."""
        axioms = []

        for rule_type, rule_data in rules.items():
            if rule_type == "nitrogen_cycle":
                # Add nitrogen fixer axioms
                for fixer in rule_data["fixers"]:
                    axioms.extend(
                        [
                            f"Class: {fixer}",
                            f"ObjectPropertyAssertion: fixes_nitrogen {fixer} Nitrogen",
                        ]
                    )

                # Add nitrogen consumer axioms
                for consumer in rule_data["consumers"]:
                    axioms.extend(
                        [
                            f"Class: {consumer}",
                            f"ObjectPropertyAssertion: requires_nutrient {consumer} Nitrogen",
                        ]
                    )

                # Add compatibility relationships
                for fixer in rule_data["fixers"]:
                    for consumer in rule_data["consumers"]:
                        axioms.append(
                            f"ObjectPropertyAssertion: companion_with {fixer} {consumer}"
                        )

            elif rule_type == "allelopathy":
                # Add allelopathic relationships
                for inhibitor in rule_data["walnut_inhibitors"]:
                    for sensitive in rule_data["sensitive_plants"]:
                        axioms.append(
                            f"ObjectPropertyAssertion: incompatible_with {inhibitor} {sensitive}"
                        )

            elif rule_type == "pest_management":
                # Add pest management relationships
                for repeller in rule_data["pest_repellers"]:
                    for protected in rule_data["protected_plants"]:
                        axioms.append(
                            f"ObjectPropertyAssertion: protects_from_pests {repeller} {protected}"
                        )

        return axioms

    def _extract_relationships(self, axioms: List[str]) -> List[str]:
        """Extract unique relationship names from axioms."""
        relationships = set()

        for axiom in axioms:
            if axiom.startswith("ObjectProperty:"):
                prop_name = axiom.replace("ObjectProperty:", "").strip()
                relationships.add(prop_name)
            elif "ObjectPropertyAssertion:" in axiom:
                parts = axiom.split()
                if len(parts) >= 2:
                    prop_name = parts[1]
                    relationships.add(prop_name)

        return sorted(list(relationships))
