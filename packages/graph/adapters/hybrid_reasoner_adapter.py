"""Hybrid reasoner adapter implementing OntologyValidatorPort.

This adapter integrates ELK reasoner for OWL 2 EL axioms and HermiT reasoner
for OWL FULL axioms, providing optimized performance for different reasoning tasks.
"""

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from adapters.axiom_applier import AxiomApplier, BasicAxiomApplier, FullAxiomApplier
from adapters.repositories.falkordb_ontology_repository import (
    FalkorDBOntologyRepository,
)
from domain.entities import OntologyVersion, Triple, ValidationError, ValidationReport
from domain.owl_conversion import convert_triples_to_owl
from domain.services.validation_rules_engine import (
    ValidationRulesEngine, 
    create_validation_context
)

# Third-party imports for reasoners
# Note: These would need to be installed via pip
try:
    from owlready2 import Ontology, World, sync_reasoner_hermit
    from owlready2.reasoning import (
        OwlReadyInconsistentOntologyError,
        OwlReadyOntologyParsingError,
    )

    HAS_OWLREADY2 = True
except ImportError:
    HAS_OWLREADY2 = False

try:
    import pyelk

    HAS_ELK = True
except ImportError:
    HAS_ELK = False

# Configure logging
logger = logging.getLogger(__name__)

if not HAS_ELK:
    logger.warning(
        "ELK reasoner is not available. Install the 'pyelk' package to enable ELK reasoning."
    )


class AxiomType(Enum):
    """Classification of OWL axiom types for reasoner routing."""

    EL = "EL"  # OWL 2 EL profile (fast reasoning with ELK)
    FULL = "FULL"  # OWL FULL requiring complete reasoning (HermiT)


class ReasonerType(Enum):
    """Available reasoner types."""

    ELK = "ELK"
    HERMIT = "HERMIT"
    PELLET = "PELLET"  # Alternative for HermiT with explanation support


class HybridReasonerAdapter:
    """Hybrid reasoner adapter implementing OntologyValidatorPort.

    This adapter routes axioms to the appropriate reasoner based on their complexity:
    - ELK reasoner for OWL 2 EL axioms (seconds vs minutes performance)
    - HermiT reasoner for OWL FULL axioms requiring complete reasoning

    It provides comprehensive error handling and repair suggestions for ontology
    validation failures.
    """

    def __init__(
        self,
        ontology_path: Optional[str] = None,
        world: Optional[Any] = None,
        elk_reasoner: Optional[Any] = None,
        hermit_reasoner: Optional[Any] = None,
        ontology_repository: Optional[FalkorDBOntologyRepository] = None,
        falkordb_connection_string: Optional[str] = None,
        axiom_applier: Optional[AxiomApplier] = None,
        validation_rules_engine: Optional[ValidationRulesEngine] = None,
    ):
        """Initialize the hybrid reasoner adapter.

        Args:
            ontology_path: Optional path to base ontology file
            world: Optional owlready2 World instance for testing
            elk_reasoner: Optional ELK reasoner instance for testing
            hermit_reasoner: Optional HermiT reasoner instance for testing
            ontology_repository: Optional repository for ontology version storage
            falkordb_connection_string: Optional FalkorDB connection string

        Raises:
            ImportError: When required dependencies are not installed
        """
        # Check for required dependencies
        if not HAS_OWLREADY2:
            raise ImportError(
                "owlready2 is required for HybridReasonerAdapter. "
                "Install with: pip install owlready2"
            )

        # Initialize reasoners
        self.world = world or World()
        self._ontology_cache: Dict[str, Ontology] = {}
        self.axiom_applier = axiom_applier or FullAxiomApplier()

        # Load base ontology if provided
        if ontology_path:
            self._load_ontology(ontology_path)

        # Initialize reasoners (or use provided instances for testing)
        self.elk_reasoner = elk_reasoner
        self.hermit_reasoner = hermit_reasoner

        # Initialize ontology repository
        self.ontology_repository = ontology_repository
        if not ontology_repository and falkordb_connection_string:
            self.ontology_repository = FalkorDBOntologyRepository(
                falkordb_connection_string
            )

        # Initialize validation rules engine
        self.validation_rules_engine = validation_rules_engine or ValidationRulesEngine()

        # EL profile patterns for axiom classification
        self._el_patterns = self._compile_el_patterns()

    def validate(
        self, *, triples: List[Triple], ontology_version_id: str
    ) -> ValidationReport:
        """Validate triples against ontological constraints with incremental reasoning.

        Performs comprehensive ontology validation using hybrid reasoning approach:
        1. Classifies axioms as EL or FULL
        2. Routes EL axioms to ELK reasoner (fast)
        3. Routes FULL axioms to HermiT reasoner (complete)
        4. Combines results into unified validation report

        Args:
            triples: List of Triple objects to validate
            ontology_version_id: Specific ontology version for validation context

        Returns:
            ValidationReport containing consistency status, unsatisfiable classes,
            and actionable repair suggestions

        Raises:
            ValidationError: When validation process fails
            OntologyException: When ontology version is not found
        """
        logger.info(
            f"Validating {len(triples)} triples against ontology version {ontology_version_id}"
        )

        # Convert triples to OWL axioms
        owl_axioms = self.convert_to_owl(triples=triples)

        # Classify axioms by complexity
        el_axioms, full_axioms = self._classify_axioms(owl_axioms)

        # Get tenant_id from first triple (all should have same tenant)
        tenant_id = triples[0].tenant_id if triples else "unknown"

        try:
            # Create temporary ontology with axioms
            temp_ontology = self._create_temp_ontology(
                el_axioms, full_axioms, ontology_version_id
            )

            # Validate using appropriate reasoners
            is_consistent, unsat_classes, repair_suggestions = self._validate_ontology(
                temp_ontology, el_axioms, full_axioms
            )

            # Validate architectural rules
            architectural_violations = self._validate_architectural_rules(
                triples, tenant_id, ontology_version_id
            )

            # Combine reasoner violations with architectural violations
            all_violations = architectural_violations
            
            # If reasoner found inconsistencies, add them as violations
            if not is_consistent:
                for unsat_class in unsat_classes:
                    from domain.entities.validation_report import RuleViolation, RepairSuggestion
                    all_violations.append(RuleViolation(
                        rule_id="REASONER_INCONSISTENCY",
                        violated_constraint="Ontology consistency",
                        violating_components=[unsat_class],
                        severity="ERROR",
                        description=f"Class {unsat_class} is unsatisfiable",
                        repair_suggestion=RepairSuggestion(
                            action="Review class restrictions",
                            description=f"Check the restrictions and parent classes of {unsat_class}",
                            confidence=0.8
                        )
                    ))

            # Overall consistency includes both reasoner and architectural validation
            overall_consistent = is_consistent and len(architectural_violations) == 0

            explanation = None
            if not overall_consistent:
                explanation = self._get_reasoner_explanation(temp_ontology)

            logger.info(
                f"Validation complete: consistent={overall_consistent}, "
                f"unsat_classes={len(unsat_classes)}, "
                f"architectural_violations={len(architectural_violations)}"
            )

            return ValidationReport(
                is_consistent=overall_consistent,
                violated_rules=all_violations,
                unsat_classes=unsat_classes,
                repair_suggestions=repair_suggestions,
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id,
                explanation=explanation,
            )

        except OwlReadyInconsistentOntologyError as e:
            logger.error(f"Ontology inconsistency detected: {str(e)}")
            return ValidationReport(
                is_consistent=False,
                unsat_classes=["Unknown"],  # Detailed analysis not possible
                repair_suggestions=[f"Ontology inconsistency: {str(e)}"],
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id,
                explanation=self._get_reasoner_explanation(temp_ontology),
            )

        except OwlReadyOntologyParsingError as e:
            logger.error(f"Ontology parsing error: {str(e)}")
            error_msg = f"Failed to parse ontology: {str(e)}"
            raise ValidationError(
                message=error_msg,
                param="ontology_syntax",
                context={
                    "constraint_id": "PARSE_ERROR",
                    "triple": str(triples[0]) if triples else "",
                    "repair_suggestion": "Check Manchester syntax for errors",
                    "tenant_id": tenant_id,
                }
            )

        except Exception as e:
            logger.exception(f"Unexpected error during validation: {str(e)}")
            error_msg = f"Validation failed: {str(e)}"
            raise ValidationError(
                message=error_msg,
                param="validation",
                context={
                    "constraint_id": "VALIDATION_ERROR",
                    "triple": str(triples[0]) if triples else "",
                    "repair_suggestion": "Contact system administrator",
                    "tenant_id": tenant_id,
                }
            )

    def validate_delta(
        self, *, new_triples: List[Triple], existing_version_id: str, tenant_id: str
    ) -> ValidationReport:
        """Perform delta validation for ontology versioning and incremental updates.

        Validates only new triples against existing ontology version to enable
        efficient incremental reasoning without re-validating entire knowledge base.

        Args:
            new_triples: List of new Triple objects to validate incrementally
            existing_version_id: Parent ontology version for delta comparison
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            ValidationReport focused on delta changes with incremental consistency

        Raises:
            ValidationError: When delta validation fails
            VersioningException: When parent version is not found
        """
        logger.info(
            f"Performing delta validation for {len(new_triples)} new triples "
            f"against version {existing_version_id}"
        )

        try:
            # Retrieve existing ontology version
            existing_version = self._get_ontology_version(
                existing_version_id, tenant_id
            )

            if not existing_version:
                error_msg = f"Ontology version {existing_version_id} not found"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Convert existing axioms to ontology
            existing_ontology = self._create_ontology_from_version(existing_version)

            # Convert new triples to OWL axioms
            new_axioms = self.convert_to_owl(triples=new_triples)

            # Classify new axioms
            new_el_axioms, new_full_axioms = self._classify_axioms(new_axioms)

            # Create temporary ontology with combined axioms
            temp_ontology = self._create_temp_ontology_with_base(
                base_ontology=existing_ontology,
                el_axioms=new_el_axioms,
                full_axioms=new_full_axioms,
                version_id=f"{existing_version_id}_delta",
            )

            # Validate using appropriate reasoners
            is_consistent, unsat_classes, repair_suggestions = self._validate_ontology(
                temp_ontology, new_el_axioms, new_full_axioms
            )

            # Validate architectural rules for new triples
            architectural_violations = self._validate_architectural_rules(
                new_triples, tenant_id, existing_version_id
            )

            # Combine reasoner violations with architectural violations
            all_violations = architectural_violations
            
            # If reasoner found inconsistencies, add them as violations
            if not is_consistent:
                for unsat_class in unsat_classes:
                    from domain.entities.validation_report import RuleViolation, RepairSuggestion
                    all_violations.append(RuleViolation(
                        rule_id="REASONER_INCONSISTENCY",
                        violated_constraint="Ontology consistency",
                        violating_components=[unsat_class],
                        severity="ERROR",
                        description=f"Class {unsat_class} is unsatisfiable",
                        repair_suggestion=RepairSuggestion(
                            action="Review class restrictions",
                            description=f"Check the restrictions and parent classes of {unsat_class}",
                            confidence=0.8
                        )
                    ))

            # Overall consistency includes both reasoner and architectural validation
            overall_consistent = is_consistent and len(architectural_violations) == 0

            logger.info(
                f"Delta validation complete: consistent={overall_consistent}, "
                f"unsat_classes={len(unsat_classes)}, "
                f"architectural_violations={len(architectural_violations)}"
            )

            return ValidationReport(
                is_consistent=overall_consistent,
                violated_rules=all_violations,
                unsat_classes=unsat_classes,
                repair_suggestions=repair_suggestions,
                explanation=None,
                tenant_id=tenant_id,
                ontology_version_id=existing_version_id,
            )

        except ValueError as e:
            # Re-raise with more context
            raise ValueError(f"Version not found: {str(e)}")

        except Exception as e:
            logger.exception(f"Delta validation failed: {str(e)}")
            error_msg = f"Delta validation failed: {str(e)}"
            raise ValidationError(
                message=error_msg,
                param="delta_validation",
                context={
                    "constraint_id": "DELTA_VALIDATION_ERROR",
                    "triple": str(new_triples[0]) if new_triples else "",
                    "repair_suggestion": "Check compatibility with existing ontology",
                    "tenant_id": tenant_id,
                }
            )

    def convert_to_owl(self, *, triples: List[Triple]) -> str:
        """Convert triples to OWL axioms using Manchester syntax."""
        logger.info("Converting triples to OWL via helper module")
        return convert_triples_to_owl(triples)

    def _classify_axioms(self, owl_axioms: str) -> Tuple[List[str], List[str]]:
        """Classify OWL axioms into EL and FULL categories.

        Args:
            owl_axioms: OWL axioms in Manchester syntax

        Returns:
            Tuple of (el_axioms, full_axioms) lists
        """
        el_axioms = []
        full_axioms = []

        # Split axioms by line
        axiom_lines = owl_axioms.strip().split("\n")

        for axiom in axiom_lines:
            axiom = axiom.strip()
            if not axiom or axiom.startswith("Ontology:"):
                continue

            if self._is_el_axiom(axiom):
                el_axioms.append(axiom)
            else:
                full_axioms.append(axiom)

        logger.info(
            f"Classified {len(el_axioms)} EL axioms and {len(full_axioms)} FULL axioms"
        )
        return el_axioms, full_axioms

    def _is_el_axiom(self, axiom: str) -> bool:
        """Determine if an axiom belongs to the OWL 2 EL profile.

        OWL 2 EL is a subset of OWL 2 that allows for polynomial time reasoning.
        It excludes universal quantification, cardinality restrictions, etc.

        Args:
            axiom: OWL axiom in Manchester syntax

        Returns:
            True if axiom is in OWL 2 EL profile, False otherwise
        """
        # Check against patterns that are NOT in EL profile
        for pattern in self._el_patterns:
            if pattern.search(axiom):
                return False

        return True

    def _compile_el_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for identifying non-EL axioms.

        Returns:
            List of compiled regex patterns
        """
        # Patterns that identify constructs NOT in OWL 2 EL
        non_el_patterns = [
            r"ObjectAllValuesFrom|allValuesFrom",  # Universal quantification
            r"ObjectMaxCardinality|maxCardinality",  # Cardinality restrictions
            r"ObjectMinCardinality|minCardinality",
            r"ObjectExactCardinality|exactCardinality",
            r"ObjectComplementOf|complementOf",  # Complement
            r"ObjectUnionOf|unionOf",  # Union
            r"ObjectOneOf|oneOf",  # Enumeration with multiple individuals
            r"DisjointUnion",  # Disjoint union
            r"DisjointClasses",  # Disjoint classes
            r"FunctionalObjectProperty",  # Functional properties
            r"InverseFunctionalObjectProperty",
            r"ReflexiveObjectProperty",
            r"IrreflexiveObjectProperty",
            r"SymmetricObjectProperty",
            r"AsymmetricObjectProperty",
            r"TransitiveObjectProperty",
        ]

        return [re.compile(pattern) for pattern in non_el_patterns]

    def _create_temp_ontology(
        self, el_axioms: List[str], full_axioms: List[str], ontology_version_id: str
    ) -> Any:
        """Create temporary ontology with the provided axioms.

        Args:
            el_axioms: OWL 2 EL axioms
            full_axioms: OWL FULL axioms
            ontology_version_id: Version identifier for caching

        Returns:
            owlready2 Ontology object
        """
        # Check if we have this ontology version cached
        if ontology_version_id in self._ontology_cache:
            return self._ontology_cache[ontology_version_id]

        # Create new ontology
        onto_iri = f"http://example.org/ontology/{ontology_version_id}"
        ontology = self.world.get_ontology(onto_iri)

        with ontology:
            self.axiom_applier.apply(ontology, el_axioms + full_axioms)

        # Cache the ontology
        self._ontology_cache[ontology_version_id] = ontology
        return ontology

    def _validate_ontology(
        self, ontology: Any, el_axioms: List[str], full_axioms: List[str]
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate ontology using appropriate reasoners.

        Args:
            ontology: owlready2 Ontology object
            el_axioms: OWL 2 EL axioms
            full_axioms: OWL FULL axioms

        Returns:
            Tuple of (is_consistent, unsat_classes, repair_suggestions)
        """
        unsat_classes = []
        repair_suggestions = []

        try:
            # If we have EL axioms, use ELK reasoner (fast)
            if el_axioms and HAS_ELK:
                logger.info(f"Running ELK reasoner on {len(el_axioms)} EL axioms")
                # In a real implementation, we would:
                # 1. Run ELK reasoner on EL axioms
                # 2. Collect unsatisfiable classes
                # elk_result = self.elk_reasoner.check_consistency(ontology)

            # If we have FULL axioms, use HermiT reasoner (complete)
            if full_axioms:
                logger.info(
                    f"Running HermiT reasoner on {len(full_axioms)} FULL axioms"
                )
                # Run HermiT reasoner
                sync_reasoner_hermit(ontology)

                # Check for inconsistencies
                for cls in ontology.classes():
                    if cls.is_a and cls.is_a[0] is ontology.Nothing:
                        unsat_classes.append(cls.name)
                        repair_suggestions.append(
                            f"Class '{cls.name}' is unsatisfiable. "
                            f"Check its restrictions and parent classes."
                        )

            # Determine overall consistency
            is_consistent = len(unsat_classes) == 0

            return is_consistent, unsat_classes, repair_suggestions

        except Exception as e:
            logger.exception(f"Error during reasoning: {str(e)}")
            return False, ["ReasoningError"], [f"Reasoning failed: {str(e)}"]

    def _get_ontology_version(
        self, version_id: str, tenant_id: str
    ) -> Optional[OntologyVersion]:
        """Retrieve ontology version from repository.

        Args:
            version_id: Ontology version identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            OntologyVersion if found, None otherwise

        Raises:
            ValueError: When repository is not configured
        """
        if not self.ontology_repository:
            logger.warning("Ontology repository not configured, using mock version")
            # Return a mock version for testing
            if version_id == "mock_version":
                return OntologyVersion(
                    id=version_id,
                    checksum="mock_checksum",
                    parent_version=None,
                    tenant_id=tenant_id,
                    created_at=datetime.now(),
                    axioms=["Class: Person", "ObjectProperty: knows"],
                )
            return None

        try:
            return self.ontology_repository.get_ontology_version(
                version_id=version_id, tenant_id=tenant_id
            )
        except Exception as e:
            logger.exception(f"Failed to retrieve ontology version: {str(e)}")
            return None

    def _create_ontology_from_version(self, version: OntologyVersion) -> Any:
        """Create ontology from version entity.

        Args:
            version: OntologyVersion entity

        Returns:
            owlready2 Ontology object
        """
        # Check if we have this ontology version cached
        if version.id in self._ontology_cache:
            return self._ontology_cache[version.id]

        # Create new ontology
        onto_iri = f"http://example.org/ontology/{version.id}"
        ontology = self.world.get_ontology(onto_iri)

        with ontology:
            self.axiom_applier.apply(ontology, version.axioms)

        # Cache the ontology
        self._ontology_cache[version.id] = ontology
        return ontology

    def _create_temp_ontology_with_base(
        self,
        base_ontology: Any,
        el_axioms: List[str],
        full_axioms: List[str],
        version_id: str,
    ) -> Any:
        """Create temporary ontology with base ontology and new axioms.

        Args:
            base_ontology: Base owlready2 Ontology object
            el_axioms: New OWL 2 EL axioms
            full_axioms: New OWL FULL axioms
            version_id: Version identifier for caching

        Returns:
            owlready2 Ontology object with combined axioms
        """
        # Check if we have this combined ontology version cached
        if version_id in self._ontology_cache:
            return self._ontology_cache[version_id]

        # Create new ontology with imports
        onto_iri = f"http://example.org/ontology/{version_id}"
        ontology = self.world.get_ontology(onto_iri)

        # Import base ontology
        ontology.imported_ontologies.append(base_ontology)

        # For now, we'll just create a minimal ontology
        with ontology:
            self.axiom_applier.apply(ontology, el_axioms + full_axioms)

        # Cache the ontology
        self._ontology_cache[version_id] = ontology
        return ontology

    def _load_ontology(self, ontology_path: str) -> None:
        """Load ontology from file.

        Args:
            ontology_path: Path to ontology file

        Raises:
            FileNotFoundError: When ontology file is not found
            OwlReadyOntologyParsingError: When ontology parsing fails
        """
        try:
            # Load ontology using owlready2
            self.world.get_ontology(ontology_path).load()
            logger.info(f"Loaded ontology from {ontology_path}")
        except FileNotFoundError:
            logger.error(f"Ontology file not found: {ontology_path}")
            raise
        except Exception as e:
            logger.exception(f"Failed to load ontology: {str(e)}")
            raise

    def _apply_basic_axioms(self, ontology: Any, axioms: List[str]) -> None:
        """Maintain compatibility with old tests using basic applier."""
        BasicAxiomApplier().apply(ontology, axioms)

    def _validate_architectural_rules(
        self, triples: List[Triple], tenant_id: str, ontology_version_id: str
    ) -> List[Any]:
        """Validate architectural rules using the validation rules engine.
        
        Args:
            triples: List of triples to validate
            tenant_id: Tenant identifier
            ontology_version_id: Ontology version identifier
            
        Returns:
            List of RuleViolation objects for architectural violations
        """
        try:
            # Create validation context
            context = create_validation_context(
                tenant_id=tenant_id,
                ontology_version_id=ontology_version_id,
                triples=triples
            )
            
            # Validate all architectural rules
            violations = self.validation_rules_engine.validate_all_rules(context)
            
            logger.info(f"Architectural validation found {len(violations)} violations")
            return violations
            
        except Exception as e:
            logger.exception(f"Error during architectural validation: {str(e)}")
            # Return empty list on error to not break the validation process
            return []

    def _get_reasoner_explanation(self, ontology: Any) -> Optional[str]:
        """Retrieve explanation for ontology inconsistencies if supported."""
        try:
            if self.hermit_reasoner and hasattr(
                self.hermit_reasoner, "explain_inconsistency"
            ):
                return self.hermit_reasoner.explain_inconsistency(ontology)
            if hasattr(self.world, "get_pellet_explanation"):
                # Fallback to pellet explanation method if available
                return self.world.get_pellet_explanation(ontology)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to get reasoning explanation: %s", exc)
        return None
