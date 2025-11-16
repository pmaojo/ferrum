"""
Pattern Matching and Suggestions Service

Analyzes code architecture against known patterns and best practices,
providing intelligent suggestions for improvements and pattern application.
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime

from ..entities.architectural_component import ArchitecturalComponent
from ..entities.validation_report import ValidationReport
from .architectural_pattern_library import ArchitecturalPatternLibrary, ArchitecturalPattern
from .best_practices_knowledge_graph import BestPracticesKnowledgeGraph, BestPractice, PracticeContext


class MatchConfidence(Enum):
    HIGH = "high"      # 0.8-1.0
    MEDIUM = "medium"  # 0.5-0.79
    LOW = "low"        # 0.2-0.49
    NONE = "none"      # 0.0-0.19


class SuggestionType(Enum):
    APPLY_PATTERN = "apply_pattern"
    FIX_VIOLATION = "fix_violation"
    IMPROVE_DESIGN = "improve_design"
    REFACTOR_CODE = "refactor_code"
    ADD_ABSTRACTION = "add_abstraction"
    EXTRACT_COMPONENT = "extract_component"


class SuggestionPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PatternMatch:
    """Represents a match between code and an architectural pattern"""
    pattern_id: str
    pattern_name: str
    confidence: float
    matched_components: List[str]  # Component IDs that match the pattern
    missing_components: List[str]  # Components needed to complete the pattern
    violations: List[str]  # Pattern violations found
    evidence: Dict[str, Any]  # Evidence supporting the match
    context: Dict[str, Any]  # Additional context information


@dataclass
class ImprovementSuggestion:
    """Represents a suggestion for code improvement"""
    id: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    rationale: str
    affected_components: List[str]
    implementation_steps: List[str]
    code_examples: Dict[str, str]  # language -> example code
    estimated_effort: str  # "low", "medium", "high"
    benefits: List[str]
    risks: List[str]
    related_patterns: List[str]
    related_practices: List[str]
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)


class PatternMatchingService:
    """Service for pattern matching and architectural suggestions"""
    
    def __init__(
        self,
        pattern_library: ArchitecturalPatternLibrary,
        practices_graph: BestPracticesKnowledgeGraph
    ):
        self.pattern_library = pattern_library
        self.practices_graph = practices_graph
        self.match_cache: Dict[str, List[PatternMatch]] = {}
        self.suggestion_cache: Dict[str, List[ImprovementSuggestion]] = {}
    
    def analyze_architecture(
        self,
        components: List[ArchitecturalComponent],
        project_context: Set[PracticeContext]
    ) -> Tuple[List[PatternMatch], List[ImprovementSuggestion]]:
        """Analyze architecture and provide pattern matches and suggestions"""
        
        # Find pattern matches
        pattern_matches = self._find_pattern_matches(components)
        
        # Generate improvement suggestions
        suggestions = self._generate_suggestions(
            components, pattern_matches, project_context
        )
        
        return pattern_matches, suggestions
    
    def _find_pattern_matches(
        self,
        components: List[ArchitecturalComponent]
    ) -> List[PatternMatch]:
        """Find patterns that match the current architecture"""
        matches = []
        
        # Create component index for efficient lookup
        component_index = {comp.iri: comp for comp in components}
        
        # Check each pattern in the library
        for pattern in self.pattern_library.patterns.values():
            match = self._match_pattern(pattern, components, component_index)
            if match and match.confidence > 0.2:  # Only include meaningful matches
                matches.append(match)
        
        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches
    
    def _match_pattern(
        self,
        pattern: ArchitecturalPattern,
        components: List[ArchitecturalComponent],
        component_index: Dict[str, ArchitecturalComponent]
    ) -> Optional[PatternMatch]:
        """Match a specific pattern against the architecture"""
        
        matched_components = []
        missing_components = []
        violations = []
        confidence = 0.0
        evidence = {}
        
        # Pattern-specific matching logic
        if pattern.id == "hexagonal_port_adapter":
            return self._match_port_adapter_pattern(
                pattern, components, component_index
            )
        elif pattern.id == "ddd_aggregate":
            return self._match_aggregate_pattern(
                pattern, components, component_index
            )
        elif pattern.id == "solid_srp":
            return self._match_srp_pattern(
                pattern, components, component_index
            )
        else:
            # Generic pattern matching based on OWL axioms
            return self._match_generic_pattern(
                pattern, components, component_index
            )
    
    def _match_port_adapter_pattern(
        self,
        pattern: ArchitecturalPattern,
        components: List[ArchitecturalComponent],
        component_index: Dict[str, ArchitecturalComponent]
    ) -> Optional[PatternMatch]:
        """Match port-adapter pattern specifically"""
        
        ports = [c for c in components if c.component_type.value == "PORT"]
        adapters = [c for c in components if c.component_type.value == "ADAPTER"]
        domain_services = [c for c in components if c.component_type.value == "USECASE"]
        
        matched_components = []
        violations = []
        confidence = 0.0
        
        # Check for port-adapter pairs
        port_adapter_pairs = 0
        for port in ports:
            # Find adapters implementing this port
            implementing_adapters = []
            for adapter in adapters:
                if self._implements_port(adapter, port):
                    implementing_adapters.append(adapter)
                    matched_components.extend([port.iri, adapter.iri])
                    port_adapter_pairs += 1
            
            if not implementing_adapters:
                violations.append(f"Port {port.name} has no implementing adapters")
        
        # Check domain services using ports
        domain_using_ports = 0
        for service in domain_services:
            for port in ports:
                if self._uses_port(service, port):
                    matched_components.append(service.iri)
                    domain_using_ports += 1
                    break
        
        # Calculate confidence
        if ports and adapters:
            confidence += 0.4 * (port_adapter_pairs / len(ports))
        if domain_services:
            confidence += 0.3 * (domain_using_ports / len(domain_services))
        if not violations:
            confidence += 0.3
        
        # Check for violations
        for service in domain_services:
            for adapter in adapters:
                if self._directly_depends_on(service, adapter):
                    violations.append(
                        f"Domain service {service.name} directly depends on adapter {adapter.name}"
                    )
                    confidence -= 0.2
        
        return PatternMatch(
            pattern_id=pattern.id,
            pattern_name=pattern.name,
            confidence=max(0.0, confidence),
            matched_components=list(set(matched_components)),
            missing_components=[],
            violations=violations,
            evidence={
                "ports_count": len(ports),
                "adapters_count": len(adapters),
                "port_adapter_pairs": port_adapter_pairs,
                "domain_services_using_ports": domain_using_ports
            },
            context={}
        )
    
    def _match_aggregate_pattern(
        self,
        pattern: ArchitecturalPattern,
        components: List[ArchitecturalComponent],
        component_index: Dict[str, ArchitecturalComponent]
    ) -> Optional[PatternMatch]:
        """Match DDD aggregate pattern"""
        
        entities = [c for c in components if c.component_type.value == "ENTITY"]
        
        matched_components = []
        violations = []
        confidence = 0.0
        
        # Look for aggregate roots (entities with specific naming or properties)
        aggregate_roots = []
        for entity in entities:
            if self._is_aggregate_root(entity):
                aggregate_roots.append(entity)
                matched_components.append(entity.iri)
        
        # Check aggregate boundaries
        proper_aggregates = 0
        for root in aggregate_roots:
            aggregate_entities = self._find_aggregate_entities(root, entities)
            if len(aggregate_entities) > 1:  # Root + other entities
                proper_aggregates += 1
                matched_components.extend([e.iri for e in aggregate_entities])
            
            # Check for boundary violations
            for entity in aggregate_entities:
                if entity != root and self._has_external_references(entity, entities):
                    violations.append(
                        f"Entity {entity.name} in aggregate {root.name} has external references"
                    )
        
        # Calculate confidence
        if entities:
            confidence = 0.6 * (len(aggregate_roots) / len(entities))
            if proper_aggregates > 0:
                confidence += 0.4 * (proper_aggregates / len(aggregate_roots))
        
        return PatternMatch(
            pattern_id=pattern.id,
            pattern_name=pattern.name,
            confidence=confidence,
            matched_components=list(set(matched_components)),
            missing_components=[],
            violations=violations,
            evidence={
                "entities_count": len(entities),
                "aggregate_roots_count": len(aggregate_roots),
                "proper_aggregates": proper_aggregates
            },
            context={}
        )
    
    def _match_srp_pattern(
        self,
        pattern: ArchitecturalPattern,
        components: List[ArchitecturalComponent],
        component_index: Dict[str, ArchitecturalComponent]
    ) -> Optional[PatternMatch]:
        """Match Single Responsibility Principle"""
        
        all_components = components
        matched_components = []
        violations = []
        confidence = 0.0
        
        # Analyze each component for SRP compliance
        srp_compliant = 0
        srp_violations = 0
        
        for component in all_components:
            responsibility_count = self._count_responsibilities(component)
            
            if responsibility_count <= 1:
                srp_compliant += 1
                matched_components.append(component.iri)
            else:
                srp_violations += 1
                violations.append(
                    f"Component {component.name} has {responsibility_count} responsibilities"
                )
        
        # Calculate confidence
        if all_components:
            confidence = srp_compliant / len(all_components)
        
        return PatternMatch(
            pattern_id=pattern.id,
            pattern_name=pattern.name,
            confidence=confidence,
            matched_components=matched_components,
            missing_components=[],
            violations=violations,
            evidence={
                "total_components": len(all_components),
                "srp_compliant": srp_compliant,
                "srp_violations": srp_violations
            },
            context={}
        )
    
    def _match_generic_pattern(
        self,
        pattern: ArchitecturalPattern,
        components: List[ArchitecturalComponent],
        component_index: Dict[str, ArchitecturalComponent]
    ) -> Optional[PatternMatch]:
        """Generic pattern matching using OWL axioms"""
        
        # This would use OWL reasoning to match patterns
        # For now, return a basic match
        return PatternMatch(
            pattern_id=pattern.id,
            pattern_name=pattern.name,
            confidence=0.1,  # Low confidence for generic matching
            matched_components=[],
            missing_components=[],
            violations=[],
            evidence={},
            context={}
        )
    
    def _generate_suggestions(
        self,
        components: List[ArchitecturalComponent],
        pattern_matches: List[PatternMatch],
        project_context: Set[PracticeContext]
    ) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions based on analysis"""
        
        suggestions = []
        
        # Suggestions based on pattern matches
        suggestions.extend(self._suggest_from_patterns(pattern_matches, components))
        
        # Suggestions based on best practices
        suggestions.extend(self._suggest_from_practices(components, project_context))
        
        # Suggestions based on violations
        suggestions.extend(self._suggest_violation_fixes(pattern_matches, components))
        
        # Sort by priority and confidence
        suggestions.sort(key=lambda s: (s.priority.value, -s.confidence))
        
        return suggestions
    
    def _suggest_from_patterns(
        self,
        pattern_matches: List[PatternMatch],
        components: List[ArchitecturalComponent]
    ) -> List[ImprovementSuggestion]:
        """Generate suggestions based on pattern matches"""
        
        suggestions = []
        
        for match in pattern_matches:
            if match.confidence < 0.8 and match.confidence > 0.3:
                # Pattern is partially implemented, suggest completion
                pattern = self.pattern_library.get_pattern(match.pattern_id)
                if pattern:
                    suggestion = ImprovementSuggestion(
                        id=f"complete_pattern_{match.pattern_id}",
                        suggestion_type=SuggestionType.APPLY_PATTERN,
                        priority=SuggestionPriority.MEDIUM,
                        title=f"Complete {pattern.name} Implementation",
                        description=f"Your architecture partially implements {pattern.name}. Consider completing the pattern for better design.",
                        rationale=pattern.intent,
                        affected_components=match.matched_components,
                        implementation_steps=self._get_pattern_completion_steps(pattern, match),
                        code_examples={lang: ex.code_snippet for ex in pattern.examples for lang in [ex.language]},
                        estimated_effort="medium",
                        benefits=pattern.consequences.get("benefits", []),
                        risks=pattern.consequences.get("liabilities", []),
                        related_patterns=[pattern.id],
                        related_practices=[],
                        confidence=match.confidence
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_from_practices(
        self,
        components: List[ArchitecturalComponent],
        project_context: Set[PracticeContext]
    ) -> List[ImprovementSuggestion]:
        """Generate suggestions based on best practices"""
        
        suggestions = []
        
        # Get relevant practices for the project context
        relevant_practices = []
        for context in project_context:
            relevant_practices.extend(
                self.practices_graph.search_practices(context=context)
            )
        
        # Analyze components against practices
        for practice in relevant_practices:
            if practice.practice_type.value == "anti_pattern":
                # Check if anti-pattern is present
                if self._detect_anti_pattern(practice, components):
                    suggestion = ImprovementSuggestion(
                        id=f"fix_antipattern_{practice.id}",
                        suggestion_type=SuggestionType.FIX_VIOLATION,
                        priority=SuggestionPriority.HIGH if practice.severity == "high" else SuggestionPriority.MEDIUM,
                        title=f"Fix {practice.name}",
                        description=f"Anti-pattern detected: {practice.description}",
                        rationale=practice.rationale,
                        affected_components=self._get_affected_components(practice, components),
                        implementation_steps=practice.implementation_steps,
                        code_examples=practice.code_examples,
                        estimated_effort=practice.effort_to_fix,
                        benefits=[f"Eliminates {practice.name}"],
                        risks=[],
                        related_patterns=practice.related_patterns,
                        related_practices=[practice.id],
                        confidence=0.8
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_violation_fixes(
        self,
        pattern_matches: List[PatternMatch],
        components: List[ArchitecturalComponent]
    ) -> List[ImprovementSuggestion]:
        """Generate suggestions to fix pattern violations"""
        
        suggestions = []
        
        for match in pattern_matches:
            if match.violations:
                pattern = self.pattern_library.get_pattern(match.pattern_id)
                if pattern:
                    for violation in match.violations:
                        suggestion = ImprovementSuggestion(
                            id=f"fix_violation_{match.pattern_id}_{hash(violation)}",
                            suggestion_type=SuggestionType.FIX_VIOLATION,
                            priority=SuggestionPriority.HIGH,
                            title=f"Fix {pattern.name} Violation",
                            description=violation,
                            rationale=f"Violation of {pattern.name} reduces code quality",
                            affected_components=match.matched_components,
                            implementation_steps=self._get_violation_fix_steps(violation, pattern),
                            code_examples=self._get_violation_fix_examples(violation, pattern),
                            estimated_effort="medium",
                            benefits=[f"Proper implementation of {pattern.name}"],
                            risks=[],
                            related_patterns=[pattern.id],
                            related_practices=[],
                            confidence=0.9
                        )
                        suggestions.append(suggestion)
        
        return suggestions
    
    # Helper methods for pattern matching
    def _implements_port(self, adapter: ArchitecturalComponent, port: ArchitecturalComponent) -> bool:
        """Check if adapter implements port"""
        for rel in adapter.relationships:
            if rel.predicate_iri.endswith("implementsPort") and rel.object_iri == port.iri:
                return True
        return False
    
    def _uses_port(self, service: ArchitecturalComponent, port: ArchitecturalComponent) -> bool:
        """Check if service uses port"""
        for rel in service.relationships:
            if rel.predicate_iri.endswith("usesPort") and rel.object_iri == port.iri:
                return True
        return False
    
    def _directly_depends_on(self, source: ArchitecturalComponent, target: ArchitecturalComponent) -> bool:
        """Check if source directly depends on target"""
        for rel in source.relationships:
            if rel.predicate_iri.endswith("dependsOn") and rel.object_iri == target.iri:
                return True
        return False
    
    def _is_aggregate_root(self, entity: ArchitecturalComponent) -> bool:
        """Check if entity is an aggregate root"""
        # Simple heuristic: check naming patterns or properties
        return (
            "root" in entity.name.lower() or
            "aggregate" in entity.name.lower() or
            any(prop.get("isAggregateRoot", False) for prop in [entity.properties])
        )
    
    def _find_aggregate_entities(
        self,
        root: ArchitecturalComponent,
        all_entities: List[ArchitecturalComponent]
    ) -> List[ArchitecturalComponent]:
        """Find entities belonging to the same aggregate as root"""
        aggregate_entities = [root]
        
        for entity in all_entities:
            if entity != root:
                # Check if entity belongs to the same aggregate
                for rel in entity.relationships:
                    if (rel.predicate_iri.endswith("belongsToAggregate") and
                        rel.object_iri == root.iri):
                        aggregate_entities.append(entity)
                        break
        
        return aggregate_entities
    
    def _has_external_references(
        self,
        entity: ArchitecturalComponent,
        all_entities: List[ArchitecturalComponent]
    ) -> bool:
        """Check if entity has references outside its aggregate"""
        # This would check for relationships to entities in other aggregates
        return False  # Simplified for now
    
    def _count_responsibilities(self, component: ArchitecturalComponent) -> int:
        """Count the number of responsibilities of a component"""
        # Simple heuristic based on relationships and properties
        responsibility_indicators = 0
        
        # Count different types of relationships as different responsibilities
        relationship_types = set()
        for rel in component.relationships:
            relationship_types.add(rel.predicate_iri.split("#")[-1])
        
        responsibility_indicators += len(relationship_types)
        
        # Add more sophisticated analysis based on component properties
        if "methods" in component.properties:
            methods = component.properties["methods"]
            if isinstance(methods, list) and len(methods) > 5:
                responsibility_indicators += 1
        
        return max(1, responsibility_indicators)
    
    def _detect_anti_pattern(
        self,
        practice: BestPractice,
        components: List[ArchitecturalComponent]
    ) -> bool:
        """Detect if an anti-pattern is present in the components"""
        # Use detection rules from the practice
        for rule in practice.detection_rules:
            if self._evaluate_detection_rule(rule, components):
                return True
        return False
    
    def _evaluate_detection_rule(
        self,
        rule: str,
        components: List[ArchitecturalComponent]
    ) -> bool:
        """Evaluate a detection rule against components"""
        # Simplified rule evaluation
        # In a real implementation, this would use SPARQL or OWL reasoning
        
        if "DomainComponent" in rule and "InfrastructureComponent" in rule:
            # Check for domain-infrastructure coupling
            domain_components = [c for c in components if "domain" in c.name.lower()]
            infra_components = [c for c in components if "adapter" in c.name.lower()]
            
            for domain in domain_components:
                for infra in infra_components:
                    if self._directly_depends_on(domain, infra):
                        return True
        
        return False
    
    def _get_affected_components(
        self,
        practice: BestPractice,
        components: List[ArchitecturalComponent]
    ) -> List[str]:
        """Get components affected by a practice"""
        # Return component IRIs that are affected by the practice
        return [c.iri for c in components[:3]]  # Simplified
    
    def _get_pattern_completion_steps(
        self,
        pattern: ArchitecturalPattern,
        match: PatternMatch
    ) -> List[str]:
        """Get steps to complete a partially implemented pattern"""
        steps = []
        
        if pattern.id == "hexagonal_port_adapter":
            if "no implementing adapters" in str(match.violations):
                steps.append("Create adapter implementations for unused ports")
            if match.confidence < 0.6:
                steps.append("Ensure domain services use ports instead of direct dependencies")
                steps.append("Apply dependency injection to wire adapters to ports")
        
        return steps or pattern.implementation_steps
    
    def _get_violation_fix_steps(
        self,
        violation: str,
        pattern: ArchitecturalPattern
    ) -> List[str]:
        """Get steps to fix a specific violation"""
        if "directly depends on adapter" in violation:
            return [
                "Extract interface (port) for the adapter",
                "Make domain service depend on the port interface",
                "Use dependency injection to provide adapter implementation"
            ]
        
        return ["Analyze the violation and apply appropriate pattern principles"]
    
    def _get_violation_fix_examples(
        self,
        violation: str,
        pattern: ArchitecturalPattern
    ) -> Dict[str, str]:
        """Get code examples for fixing a violation"""
        if pattern.examples:
            return {ex.language: ex.code_snippet for ex in pattern.examples}
        return {}
    
    def get_suggestion_by_id(self, suggestion_id: str) -> Optional[ImprovementSuggestion]:
        """Get a specific suggestion by ID"""
        for suggestions in self.suggestion_cache.values():
            for suggestion in suggestions:
                if suggestion.id == suggestion_id:
                    return suggestion
        return None
    
    def apply_suggestion(
        self,
        suggestion_id: str,
        components: List[ArchitecturalComponent]
    ) -> Dict[str, Any]:
        """Apply a suggestion and return the result"""
        suggestion = self.get_suggestion_by_id(suggestion_id)
        if not suggestion:
            return {"success": False, "error": "Suggestion not found"}
        
        # This would integrate with code generation tools
        # For now, return a mock result
        return {
            "success": True,
            "changes_made": suggestion.implementation_steps,
            "affected_files": [f"file_{i}.go" for i in range(len(suggestion.affected_components))],
            "next_steps": ["Review generated code", "Run tests", "Commit changes"]
        }