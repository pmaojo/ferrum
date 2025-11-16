"""Validation rules engine for Kthulu architecture constraints.

This module implements specific architectural validation rules:
1. DIP (Dependency Inversion Principle) validation
2. Bounded context validation for module isolation
3. Aggregate integrity constraints with cardinality
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from domain.entities import Triple, ValidationReport
from domain.entities.validation_report import RuleViolation, RepairSuggestion

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Types of architectural validation rules."""
    DIP_VIOLATION = "DIP_VIOLATION"
    BOUNDED_CONTEXT_VIOLATION = "BOUNDED_CONTEXT_VIOLATION"
    AGGREGATE_INTEGRITY_VIOLATION = "AGGREGATE_INTEGRITY_VIOLATION"


@dataclass
class ValidationContext:
    """Context information for validation rules."""
    tenant_id: str
    ontology_version_id: str
    triples: List[Triple]
    
    # Derived data structures for efficient rule checking
    component_types: Dict[str, str]  # component_iri -> type (DomainComponent/InfrastructureComponent)
    calls_relationships: List[Tuple[str, str]]  # (caller_iri, callee_iri)
    module_memberships: Dict[str, str]  # component_iri -> module_iri
    entity_aggregates: Dict[str, List[str]]  # entity_iri -> list of aggregate_iris


class ValidationRulesEngine:
    """Engine for validating Kthulu architectural constraints."""
    
    def __init__(self):
        """Initialize the validation rules engine."""
        self.rules = {
            RuleType.DIP_VIOLATION: self._validate_dip_rule,
            RuleType.BOUNDED_CONTEXT_VIOLATION: self._validate_bounded_context_rule,
            RuleType.AGGREGATE_INTEGRITY_VIOLATION: self._validate_aggregate_integrity_rule,
        }
    
    def validate_all_rules(self, context: ValidationContext) -> List[RuleViolation]:
        """Validate all architectural rules against the given context.
        
        Args:
            context: ValidationContext containing triples and metadata
            
        Returns:
            List of RuleViolation objects for any detected violations
        """
        logger.info(f"Validating {len(context.triples)} triples against architectural rules")
        
        violations = []
        
        # Build derived data structures for efficient rule checking
        self._build_context_data(context)
        
        # Run each validation rule
        for rule_type, rule_func in self.rules.items():
            try:
                rule_violations = rule_func(context)
                violations.extend(rule_violations)
                logger.debug(f"Rule {rule_type.value} found {len(rule_violations)} violations")
            except Exception as e:
                logger.exception(f"Error validating rule {rule_type.value}: {str(e)}")
                # Create a violation for the rule engine failure
                violations.append(RuleViolation(
                    rule_id=f"{rule_type.value}_ENGINE_ERROR",
                    violated_constraint="Rule engine failure",
                    violating_components=[],
                    severity="ERROR",
                    description=f"Failed to validate {rule_type.value}: {str(e)}",
                    repair_suggestion=RepairSuggestion(
                        action="Check system logs and contact administrator",
                        description="Rule engine encountered an unexpected error",
                        confidence=0.0
                    )
                ))
        
        logger.info(f"Validation complete: found {len(violations)} total violations")
        return violations
    
    def _build_context_data(self, context: ValidationContext) -> None:
        """Build derived data structures for efficient rule checking.
        
        Args:
            context: ValidationContext to populate with derived data
        """
        context.component_types = {}
        context.calls_relationships = []
        context.module_memberships = {}
        context.entity_aggregates = {}
        
        # Process triples to build lookup structures
        for triple in context.triples:
            # Identify component types
            if triple.predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                if triple.object in [
                    "http://kthulu.io/ontology#UseCase",
                    "http://kthulu.io/ontology#DomainEntity", 
                    "http://kthulu.io/ontology#Port",
                    "http://kthulu.io/ontology#DomainEvent"
                ]:
                    context.component_types[triple.subject] = "DomainComponent"
                elif triple.object in [
                    "http://kthulu.io/ontology#Adapter"
                ]:
                    context.component_types[triple.subject] = "InfrastructureComponent"
            
            # Track calls relationships
            elif triple.predicate == "http://kthulu.io/ontology#calls":
                context.calls_relationships.append((triple.subject, triple.object))
            
            # Track module memberships
            elif triple.predicate in [
                "http://kthulu.io/ontology#definesUseCase",
                "http://kthulu.io/ontology#hasPort",
                "http://kthulu.io/ontology#hasEntity"
            ]:
                context.module_memberships[triple.object] = triple.subject
            
            # Track entity-aggregate relationships
            elif triple.predicate == "http://kthulu.io/ontology#partOfAggregate":
                if triple.subject not in context.entity_aggregates:
                    context.entity_aggregates[triple.subject] = []
                context.entity_aggregates[triple.subject].append(triple.object)
        
        logger.debug(f"Built context: {len(context.component_types)} components, "
                    f"{len(context.calls_relationships)} calls, "
                    f"{len(context.module_memberships)} module memberships, "
                    f"{len(context.entity_aggregates)} entity-aggregate relationships")
    
    def _validate_dip_rule(self, context: ValidationContext) -> List[RuleViolation]:
        """Validate Dependency Inversion Principle (DIP).
        
        Rule: DomainComponent ⊑ ¬(calls some InfrastructureComponent)
        Domain components should not directly call infrastructure components.
        
        Args:
            context: ValidationContext with component and relationship data
            
        Returns:
            List of RuleViolation objects for DIP violations
        """
        violations = []
        
        for caller_iri, callee_iri in context.calls_relationships:
            caller_type = context.component_types.get(caller_iri)
            callee_type = context.component_types.get(callee_iri)
            
            # Check if domain component calls infrastructure component
            if (caller_type == "DomainComponent" and 
                callee_type == "InfrastructureComponent"):
                
                violations.append(RuleViolation(
                    rule_id="DIP_VIOLATION",
                    violated_constraint="DomainComponent ⊑ ¬(calls some InfrastructureComponent)",
                    violating_components=[caller_iri, callee_iri],
                    severity="HIGH",
                    description=f"Domain component {self._get_component_name(caller_iri)} "
                               f"directly calls infrastructure component {self._get_component_name(callee_iri)}. "
                               f"This violates the Dependency Inversion Principle.",
                    repair_suggestion=RepairSuggestion(
                        action="Create a port interface",
                        description=f"Create a port interface that {self._get_component_name(caller_iri)} "
                                   f"can depend on, and have {self._get_component_name(callee_iri)} "
                                   f"implement this port. This inverts the dependency direction.",
                        confidence=0.9
                    )
                ))
        
        return violations
    
    def _validate_bounded_context_rule(self, context: ValidationContext) -> List[RuleViolation]:
        """Validate bounded context isolation for modules.
        
        Rule: UseCase ⊑ ∀usesEntity.(belongsToModule value SelfModule)
        Use cases should only use entities from their own module.
        
        Args:
            context: ValidationContext with module membership data
            
        Returns:
            List of RuleViolation objects for bounded context violations
        """
        violations = []
        
        # Find cross-module entity usage
        for triple in context.triples:
            if triple.predicate == "http://kthulu.io/ontology#usesEntity":
                usecase_iri = triple.subject
                entity_iri = triple.object
                
                usecase_module = context.module_memberships.get(usecase_iri)
                entity_module = context.module_memberships.get(entity_iri)
                
                # Check if use case and entity belong to different modules
                if (usecase_module and entity_module and 
                    usecase_module != entity_module):
                    
                    violations.append(RuleViolation(
                        rule_id="BOUNDED_CONTEXT_VIOLATION",
                        violated_constraint="UseCase ⊑ ∀usesEntity.(belongsToModule value SelfModule)",
                        violating_components=[usecase_iri, entity_iri],
                        severity="MEDIUM",
                        description=f"Use case {self._get_component_name(usecase_iri)} "
                                   f"from module {self._get_component_name(usecase_module)} "
                                   f"uses entity {self._get_component_name(entity_iri)} "
                                   f"from different module {self._get_component_name(entity_module)}. "
                                   f"This violates bounded context isolation.",
                        repair_suggestion=RepairSuggestion(
                            action="Use domain events or create a shared kernel",
                            description=f"Either emit a domain event from {self._get_component_name(usecase_module)} "
                                       f"that {self._get_component_name(entity_module)} can handle, "
                                       f"or move the shared entity to a common shared kernel module.",
                            confidence=0.8
                        )
                    ))
        
        return violations
    
    def _validate_aggregate_integrity_rule(self, context: ValidationContext) -> List[RuleViolation]:
        """Validate aggregate integrity constraints.
        
        Rule: DomainEntity ⊑ (≤1 partOfAggregate.AggregateRoot)
        Each domain entity can belong to at most one aggregate.
        
        Args:
            context: ValidationContext with entity-aggregate relationships
            
        Returns:
            List of RuleViolation objects for aggregate integrity violations
        """
        violations = []
        
        # Check for entities belonging to multiple aggregates
        for entity_iri, aggregates in context.entity_aggregates.items():
            if len(aggregates) > 1:
                violations.append(RuleViolation(
                    rule_id="AGGREGATE_INTEGRITY_VIOLATION",
                    violated_constraint="DomainEntity ⊑ (≤1 partOfAggregate.AggregateRoot)",
                    violating_components=[entity_iri] + aggregates,
                    severity="HIGH",
                    description=f"Domain entity {self._get_component_name(entity_iri)} "
                               f"belongs to multiple aggregates: "
                               f"{', '.join(self._get_component_name(agg) for agg in aggregates)}. "
                               f"Each entity must belong to at most one aggregate.",
                    repair_suggestion=RepairSuggestion(
                        action="Refactor entity ownership",
                        description=f"Choose the primary aggregate for {self._get_component_name(entity_iri)} "
                                   f"and use references (IDs) from other aggregates instead of direct ownership. "
                                   f"Consider if the entity should be split into multiple entities.",
                        confidence=0.7
                    )
                ))
        
        return violations
    
    def _get_component_name(self, component_iri: str) -> str:
        """Extract a readable name from a component IRI.
        
        Args:
            component_iri: Full IRI of the component
            
        Returns:
            Human-readable component name
        """
        if "#" in component_iri:
            return component_iri.split("#")[-1]
        elif "/" in component_iri:
            return component_iri.split("/")[-1]
        else:
            return component_iri


def create_validation_context(
    tenant_id: str,
    ontology_version_id: str, 
    triples: List[Triple]
) -> ValidationContext:
    """Create a validation context from triples.
    
    Args:
        tenant_id: Tenant identifier
        ontology_version_id: Ontology version identifier
        triples: List of triples to validate
        
    Returns:
        ValidationContext ready for rule validation
    """
    return ValidationContext(
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id,
        triples=triples,
        component_types={},
        calls_relationships=[],
        module_memberships={},
        entity_aggregates={}
    )