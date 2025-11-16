"""
Architectural Pattern Detection Service

Detects and analyzes architectural patterns in Kthulu projects,
including hexagonal architecture patterns, DDD patterns, and anti-patterns.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from abc import ABC, abstractmethod

from ..entities.architectural_component import ArchitecturalComponent, ComponentType
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from application.ports.base import LLMPort


class PatternType(Enum):
    HEXAGONAL_ARCHITECTURE = "hexagonal_architecture"
    REPOSITORY_PATTERN = "repository_pattern"
    ADAPTER_PATTERN = "adapter_pattern"
    COMMAND_PATTERN = "command_pattern"
    EVENT_SOURCING = "event_sourcing"
    CQRS = "cqrs"
    AGGREGATE_PATTERN = "aggregate_pattern"
    DOMAIN_SERVICE = "domain_service"
    APPLICATION_SERVICE = "application_service"
    FACTORY_PATTERN = "factory_pattern"
    OBSERVER_PATTERN = "observer_pattern"
    STRATEGY_PATTERN = "strategy_pattern"
    # Anti-patterns
    GOD_OBJECT = "god_object"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    ANEMIC_DOMAIN_MODEL = "anemic_domain_model"
    FEATURE_ENVY = "feature_envy"
    INAPPROPRIATE_INTIMACY = "inappropriate_intimacy"


class PatternConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PatternInstance:
    pattern_type: PatternType
    confidence: PatternConfidence
    components: List[ArchitecturalComponent]
    description: str
    evidence: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]


@dataclass
class PatternAnalysisResult:
    detected_patterns: List[PatternInstance]
    anti_patterns: List[PatternInstance]
    pattern_coverage: Dict[str, float]
    architecture_quality_score: float
    recommendations: List[str]


class PatternDetector(ABC):
    """Abstract base class for pattern detectors"""
    
    @abstractmethod
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        pass


class HexagonalArchitectureDetector(PatternDetector):
    """Detects hexagonal architecture patterns"""
    
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        patterns = []
        
        # Group components by type
        modules = [c for c in components if c.component_type == ComponentType.MODULE]
        usecases = [c for c in components if c.component_type == ComponentType.USECASE]
        ports = [c for c in components if c.component_type == ComponentType.PORT]
        adapters = [c for c in components if c.component_type == ComponentType.ADAPTER]
        
        # Check for hexagonal structure in each module
        for module in modules:
            module_components = [c for c in components if c.module_namespace == module.name]
            module_usecases = [c for c in module_components if c.component_type == ComponentType.USECASE]
            module_ports = [c for c in module_components if c.component_type == ComponentType.PORT]
            module_adapters = [c for c in module_components if c.component_type == ComponentType.ADAPTER]
            
            if module_usecases and module_ports and module_adapters:
                # Check if adapters implement ports
                adapter_port_relationships = [
                    r for r in relationships
                    if r[2] == "implementsPort" and
                    any(a.iri == r[0] for a in module_adapters) and
                    any(p.iri == r[1] for p in module_ports)
                ]
                
                # Check if use cases use ports
                usecase_port_relationships = [
                    r for r in relationships
                    if r[2] == "usesPort" and
                    any(u.iri == r[0] for u in module_usecases) and
                    any(p.iri == r[1] for p in module_ports)
                ]
                
                if adapter_port_relationships and usecase_port_relationships:
                    confidence = PatternConfidence.HIGH
                    evidence = [
                        f"Module has {len(module_usecases)} use cases",
                        f"Module has {len(module_ports)} ports",
                        f"Module has {len(module_adapters)} adapters",
                        f"Found {len(adapter_port_relationships)} adapter-port relationships",
                        f"Found {len(usecase_port_relationships)} usecase-port relationships"
                    ]
                    
                    pattern = PatternInstance(
                        pattern_type=PatternType.HEXAGONAL_ARCHITECTURE,
                        confidence=confidence,
                        components=module_components,
                        description=f"Hexagonal architecture pattern detected in module {module.name}",
                        evidence=evidence,
                        recommendations=[
                            "Ensure all external dependencies go through ports",
                            "Keep domain logic in use cases",
                            "Implement adapters for all external integrations"
                        ],
                        metadata={"module": module.name}
                    )
                    patterns.append(pattern)
        
        return patterns


class RepositoryPatternDetector(PatternDetector):
    """Detects repository pattern implementations"""
    
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        patterns = []
        
        # Look for components with "Repository" in their name
        repository_components = [
            c for c in components
            if "repository" in c.name.lower() or "repo" in c.name.lower()
        ]
        
        for repo in repository_components:
            # Check if it's a port (interface)
            if repo.component_type == ComponentType.PORT:
                # Find adapters that implement this repository port
                implementing_adapters = [
                    c for c in components
                    if c.component_type == ComponentType.ADAPTER and
                    any(r[0] == c.iri and r[1] == repo.iri and r[2] == "implementsPort"
                        for r in relationships)
                ]
                
                # Find use cases that use this repository
                using_usecases = [
                    c for c in components
                    if c.component_type == ComponentType.USECASE and
                    any(r[0] == c.iri and r[1] == repo.iri and r[2] == "usesPort"
                        for r in relationships)
                ]
                
                if implementing_adapters and using_usecases:
                    confidence = PatternConfidence.HIGH
                    evidence = [
                        f"Repository port: {repo.name}",
                        f"Implementing adapters: {[a.name for a in implementing_adapters]}",
                        f"Using use cases: {[u.name for u in using_usecases]}"
                    ]
                    
                    pattern_components = [repo] + implementing_adapters + using_usecases
                    
                    pattern = PatternInstance(
                        pattern_type=PatternType.REPOSITORY_PATTERN,
                        confidence=confidence,
                        components=pattern_components,
                        description=f"Repository pattern detected for {repo.name}",
                        evidence=evidence,
                        recommendations=[
                            "Ensure repository interface is domain-focused",
                            "Keep persistence details in adapters",
                            "Consider using domain-specific query methods"
                        ],
                        metadata={"repository_name": repo.name}
                    )
                    patterns.append(pattern)
        
        return patterns


class EventSourcingDetector(PatternDetector):
    """Detects event sourcing patterns"""
    
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        patterns = []
        
        # Look for domain events
        events = [c for c in components if c.component_type == ComponentType.EVENT]
        
        if len(events) >= 3:  # Threshold for event sourcing
            # Find use cases that emit events
            event_emitting_usecases = []
            for event in events:
                emitting_usecases = [
                    c for c in components
                    if c.component_type == ComponentType.USECASE and
                    any(r[0] == c.iri and r[1] == event.iri and r[2] == "emitsEvent"
                        for r in relationships)
                ]
                event_emitting_usecases.extend(emitting_usecases)
            
            # Find adapters that handle events
            event_handling_adapters = []
            for event in events:
                handling_adapters = [
                    c for c in components
                    if c.component_type == ComponentType.ADAPTER and
                    any(r[0] == c.iri and r[1] == event.iri and r[2] == "handlesEvent"
                        for r in relationships)
                ]
                event_handling_adapters.extend(handling_adapters)
            
            if event_emitting_usecases and event_handling_adapters:
                confidence = PatternConfidence.MEDIUM
                if len(events) >= 5:
                    confidence = PatternConfidence.HIGH
                
                evidence = [
                    f"Found {len(events)} domain events",
                    f"Found {len(set(event_emitting_usecases))} use cases emitting events",
                    f"Found {len(set(event_handling_adapters))} adapters handling events"
                ]
                
                pattern_components = events + list(set(event_emitting_usecases)) + list(set(event_handling_adapters))
                
                pattern = PatternInstance(
                    pattern_type=PatternType.EVENT_SOURCING,
                    confidence=confidence,
                    components=pattern_components,
                    description="Event sourcing pattern detected",
                    evidence=evidence,
                    recommendations=[
                        "Ensure events are immutable",
                        "Consider event versioning strategy",
                        "Implement event store for persistence",
                        "Consider snapshots for performance"
                    ],
                    metadata={"event_count": len(events)}
                )
                patterns.append(pattern)
        
        return patterns


class GodObjectDetector(PatternDetector):
    """Detects God Object anti-pattern"""
    
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        patterns = []
        
        # Calculate relationship counts for each component
        component_relationship_counts = {}
        for component in components:
            incoming_count = sum(1 for r in relationships if r[1] == component.iri)
            outgoing_count = sum(1 for r in relationships if r[0] == component.iri)
            total_count = incoming_count + outgoing_count
            
            component_relationship_counts[component.iri] = {
                "component": component,
                "incoming": incoming_count,
                "outgoing": outgoing_count,
                "total": total_count
            }
        
        # Find components with unusually high relationship counts
        if component_relationship_counts:
            avg_relationships = sum(c["total"] for c in component_relationship_counts.values()) / len(component_relationship_counts)
            threshold = avg_relationships * 2.5  # Components with 2.5x average relationships
            
            for comp_data in component_relationship_counts.values():
                if comp_data["total"] > threshold and comp_data["total"] > 10:  # Absolute minimum threshold
                    confidence = PatternConfidence.MEDIUM
                    if comp_data["total"] > threshold * 1.5:
                        confidence = PatternConfidence.HIGH
                    
                    evidence = [
                        f"Component has {comp_data['total']} total relationships",
                        f"Average relationships per component: {avg_relationships:.1f}",
                        f"Incoming relationships: {comp_data['incoming']}",
                        f"Outgoing relationships: {comp_data['outgoing']}"
                    ]
                    
                    pattern = PatternInstance(
                        pattern_type=PatternType.GOD_OBJECT,
                        confidence=confidence,
                        components=[comp_data["component"]],
                        description=f"God Object anti-pattern detected in {comp_data['component'].name}",
                        evidence=evidence,
                        recommendations=[
                            "Consider breaking this component into smaller, focused components",
                            "Apply Single Responsibility Principle",
                            "Extract related functionality into separate modules",
                            "Review and reduce coupling"
                        ],
                        metadata={"relationship_count": comp_data["total"]}
                    )
                    patterns.append(pattern)
        
        return patterns


class CircularDependencyDetector(PatternDetector):
    """Detects circular dependency anti-patterns"""
    
    def detect(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]],
        tenant_id: str
    ) -> List[PatternInstance]:
        patterns = []
        
        # Build NetworkX graph
        graph = nx.DiGraph()
        for component in components:
            graph.add_node(component.iri, component=component)
        
        for source, target, rel_type in relationships:
            graph.add_edge(source, target, relationship_type=rel_type)
        
        # Find cycles
        cycles = list(nx.simple_cycles(graph))
        
        for cycle in cycles:
            if len(cycle) > 1:  # Ignore self-loops
                cycle_components = [graph.nodes[iri]["component"] for iri in cycle]
                
                # Determine confidence based on cycle length and component types
                confidence = PatternConfidence.HIGH
                if len(cycle) > 5:
                    confidence = PatternConfidence.MEDIUM  # Longer cycles might be less problematic
                
                # Check if cycle involves domain components calling infrastructure
                has_dip_violation = False
                cycle_relationships = []
                for i in range(len(cycle)):
                    source_iri = cycle[i]
                    target_iri = cycle[(i + 1) % len(cycle)]
                    edge_data = graph.get_edge_data(source_iri, target_iri)
                    if edge_data:
                        cycle_relationships.append(edge_data.get("relationship_type", "unknown"))
                        
                        source_comp = graph.nodes[source_iri]["component"]
                        target_comp = graph.nodes[target_iri]["component"]
                        if (source_comp.component_type in [ComponentType.USECASE, ComponentType.ENTITY] and
                            target_comp.component_type == ComponentType.ADAPTER):
                            has_dip_violation = True
                
                evidence = [
                    f"Circular dependency involves {len(cycle)} components",
                    f"Components: {[c.name for c in cycle_components]}",
                    f"Relationship types: {cycle_relationships}"
                ]
                
                if has_dip_violation:
                    evidence.append("Cycle includes DIP violation (domain → infrastructure)")
                    confidence = PatternConfidence.VERY_HIGH
                
                recommendations = [
                    "Break circular dependency by introducing abstraction",
                    "Consider dependency inversion",
                    "Review component responsibilities"
                ]
                
                if has_dip_violation:
                    recommendations.append("Fix DIP violation by using ports/interfaces")
                
                pattern = PatternInstance(
                    pattern_type=PatternType.CIRCULAR_DEPENDENCY,
                    confidence=confidence,
                    components=cycle_components,
                    description=f"Circular dependency detected involving {len(cycle)} components",
                    evidence=evidence,
                    recommendations=recommendations,
                    metadata={
                        "cycle_length": len(cycle),
                        "has_dip_violation": has_dip_violation,
                        "cycle_iris": cycle
                    }
                )
                patterns.append(pattern)
        
        return patterns


class ArchitecturalPatternService:
    """Service for detecting and analyzing architectural patterns"""
    
    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort,
        llm: Optional[LLMPort] = None
    ):
        self.knowledge_graph = knowledge_graph
        self.llm = llm
        
        # Initialize pattern detectors
        self.pattern_detectors = [
            HexagonalArchitectureDetector(),
            RepositoryPatternDetector(),
            EventSourcingDetector()
        ]
        
        self.anti_pattern_detectors = [
            GodObjectDetector(),
            CircularDependencyDetector()
        ]
    
    def analyze_patterns(self, tenant_id: str) -> PatternAnalysisResult:
        """
        Analyze architectural patterns in the system
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Complete pattern analysis result
        """
        # Get all components and relationships
        components = self._get_all_components(tenant_id)
        relationships = self._get_all_relationships(tenant_id)
        
        # Detect positive patterns
        detected_patterns = []
        for detector in self.pattern_detectors:
            patterns = detector.detect(components, relationships, tenant_id)
            detected_patterns.extend(patterns)
        
        # Detect anti-patterns
        anti_patterns = []
        for detector in self.anti_pattern_detectors:
            patterns = detector.detect(components, relationships, tenant_id)
            anti_patterns.extend(patterns)
        
        # Calculate pattern coverage
        pattern_coverage = self._calculate_pattern_coverage(detected_patterns, components)
        
        # Calculate architecture quality score
        quality_score = self._calculate_quality_score(detected_patterns, anti_patterns, components)
        
        # Generate overall recommendations
        recommendations = self._generate_overall_recommendations(
            detected_patterns, anti_patterns, quality_score
        )
        
        return PatternAnalysisResult(
            detected_patterns=detected_patterns,
            anti_patterns=anti_patterns,
            pattern_coverage=pattern_coverage,
            architecture_quality_score=quality_score,
            recommendations=recommendations
        )
    
    def detect_specific_pattern(
        self,
        pattern_type: PatternType,
        tenant_id: str
    ) -> List[PatternInstance]:
        """
        Detect instances of a specific pattern type
        
        Args:
            pattern_type: Type of pattern to detect
            tenant_id: Tenant identifier
            
        Returns:
            List of detected pattern instances
        """
        components = self._get_all_components(tenant_id)
        relationships = self._get_all_relationships(tenant_id)
        
        # Find appropriate detector
        all_detectors = self.pattern_detectors + self.anti_pattern_detectors
        
        for detector in all_detectors:
            patterns = detector.detect(components, relationships, tenant_id)
            matching_patterns = [p for p in patterns if p.pattern_type == pattern_type]
            if matching_patterns:
                return matching_patterns
        
        return []
    
    def get_pattern_recommendations(
        self,
        components: List[ArchitecturalComponent],
        tenant_id: str
    ) -> List[str]:
        """
        Get recommendations for improving architectural patterns
        
        Args:
            components: List of components to analyze
            tenant_id: Tenant identifier
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze current patterns
        analysis = self.analyze_patterns(tenant_id)
        
        # Component-specific recommendations
        component_types = [c.component_type for c in components]
        
        if ComponentType.USECASE in component_types and ComponentType.PORT not in component_types:
            recommendations.append("Consider introducing ports for external dependencies")
        
        if ComponentType.PORT in component_types and ComponentType.ADAPTER not in component_types:
            recommendations.append("Implement adapters for your ports to complete hexagonal architecture")
        
        if ComponentType.EVENT in component_types:
            event_count = sum(1 for c in component_types if c == ComponentType.EVENT)
            if event_count >= 3:
                recommendations.append("Consider implementing event sourcing pattern")
        
        # Anti-pattern specific recommendations
        for anti_pattern in analysis.anti_patterns:
            if anti_pattern.pattern_type == PatternType.CIRCULAR_DEPENDENCY:
                recommendations.append("Break circular dependencies using dependency inversion")
            elif anti_pattern.pattern_type == PatternType.GOD_OBJECT:
                recommendations.append("Refactor large components following Single Responsibility Principle")
        
        return recommendations
    
    def _get_all_components(self, tenant_id: str) -> List[ArchitecturalComponent]:
        """Get all architectural components for a tenant"""
        sparql_query = """
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module WHERE {
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module .
            
            FILTER(?type IN (kth:Module, kth:UseCase, kth:Port, kth:Adapter, kth:DomainEntity, kth:DomainEvent))
        }
        ORDER BY ?name
        """
        
        results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        return [self._sparql_result_to_component(r) for r in results]
    
    def _get_all_relationships(self, tenant_id: str) -> List[Tuple[str, str, str]]:
        """Get all relationships between components"""
        sparql_query = """
        PREFIX kth: <http://kthulu.io/ontology#>
        
        SELECT ?source ?target ?relationship WHERE {
            ?source ?relationship ?target .
            
            FILTER(?relationship IN (
                kth:dependsOnModule,
                kth:usesPort,
                kth:implementsPort,
                kth:definesUseCase,
                kth:emitsEvent,
                kth:handlesEvent,
                kth:calls
            ))
        }
        """
        
        results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        return [
            (r["source"], r["target"], r["relationship"])
            for r in results
        ]
    
    def _calculate_pattern_coverage(
        self,
        patterns: List[PatternInstance],
        components: List[ArchitecturalComponent]
    ) -> Dict[str, float]:
        """Calculate what percentage of components are covered by patterns"""
        if not components:
            return {}
        
        total_components = len(components)
        covered_components = set()
        
        pattern_coverage = {}
        
        for pattern in patterns:
            pattern_type_name = pattern.pattern_type.value
            if pattern_type_name not in pattern_coverage:
                pattern_coverage[pattern_type_name] = 0
            
            pattern_component_count = len(pattern.components)
            for component in pattern.components:
                covered_components.add(component.iri)
            
            pattern_coverage[pattern_type_name] += pattern_component_count
        
        # Convert to percentages
        for pattern_type in pattern_coverage:
            pattern_coverage[pattern_type] = (pattern_coverage[pattern_type] / total_components) * 100
        
        # Add overall coverage
        pattern_coverage["overall"] = (len(covered_components) / total_components) * 100
        
        return pattern_coverage
    
    def _calculate_quality_score(
        self,
        patterns: List[PatternInstance],
        anti_patterns: List[PatternInstance],
        components: List[ArchitecturalComponent]
    ) -> float:
        """Calculate overall architecture quality score (0-100)"""
        if not components:
            return 0.0
        
        base_score = 50.0  # Start with neutral score
        
        # Add points for good patterns
        for pattern in patterns:
            confidence_multiplier = {
                PatternConfidence.LOW: 0.5,
                PatternConfidence.MEDIUM: 1.0,
                PatternConfidence.HIGH: 1.5,
                PatternConfidence.VERY_HIGH: 2.0
            }.get(pattern.confidence, 1.0)
            
            pattern_points = {
                PatternType.HEXAGONAL_ARCHITECTURE: 15,
                PatternType.REPOSITORY_PATTERN: 10,
                PatternType.EVENT_SOURCING: 12,
                PatternType.ADAPTER_PATTERN: 8,
                PatternType.COMMAND_PATTERN: 6
            }.get(pattern.pattern_type, 5)
            
            base_score += pattern_points * confidence_multiplier
        
        # Subtract points for anti-patterns
        for anti_pattern in anti_patterns:
            confidence_multiplier = {
                PatternConfidence.LOW: 0.5,
                PatternConfidence.MEDIUM: 1.0,
                PatternConfidence.HIGH: 1.5,
                PatternConfidence.VERY_HIGH: 2.0
            }.get(anti_pattern.confidence, 1.0)
            
            penalty_points = {
                PatternType.GOD_OBJECT: 15,
                PatternType.CIRCULAR_DEPENDENCY: 20,
                PatternType.ANEMIC_DOMAIN_MODEL: 12,
                PatternType.FEATURE_ENVY: 8
            }.get(anti_pattern.pattern_type, 10)
            
            base_score -= penalty_points * confidence_multiplier
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, base_score))
    
    def _generate_overall_recommendations(
        self,
        patterns: List[PatternInstance],
        anti_patterns: List[PatternInstance],
        quality_score: float
    ) -> List[str]:
        """Generate overall architectural recommendations"""
        recommendations = []
        
        if quality_score < 30:
            recommendations.append("Architecture needs significant improvement - consider major refactoring")
        elif quality_score < 60:
            recommendations.append("Architecture has room for improvement - focus on addressing anti-patterns")
        elif quality_score < 80:
            recommendations.append("Good architecture - consider implementing additional patterns")
        else:
            recommendations.append("Excellent architecture - maintain current patterns and practices")
        
        # Pattern-specific recommendations
        pattern_types = {p.pattern_type for p in patterns}
        
        if PatternType.HEXAGONAL_ARCHITECTURE not in pattern_types:
            recommendations.append("Consider implementing hexagonal architecture pattern")
        
        if PatternType.REPOSITORY_PATTERN not in pattern_types:
            recommendations.append("Consider implementing repository pattern for data access")
        
        # Anti-pattern specific recommendations
        anti_pattern_types = {p.pattern_type for p in anti_patterns}
        
        if PatternType.CIRCULAR_DEPENDENCY in anti_pattern_types:
            recommendations.append("Priority: Fix circular dependencies")
        
        if PatternType.GOD_OBJECT in anti_pattern_types:
            recommendations.append("Priority: Refactor large, complex components")
        
        return recommendations
    
    def _sparql_result_to_component(self, result: Dict[str, Any]) -> ArchitecturalComponent:
        """Convert SPARQL result to ArchitecturalComponent"""
        return ArchitecturalComponent(
            iri=result.get("component", ""),
            component_type=self._map_type_to_enum(result.get("type", "")),
            name=result.get("name", ""),
            module_namespace=result.get("module", ""),
            properties={},
            relationships=[]
        )
    
    def _map_type_to_enum(self, type_iri: str) -> ComponentType:
        """Map OWL type IRI to ComponentType enum"""
        type_mapping = {
            "http://kthulu.io/ontology#Module": ComponentType.MODULE,
            "http://kthulu.io/ontology#UseCase": ComponentType.USECASE,
            "http://kthulu.io/ontology#Port": ComponentType.PORT,
            "http://kthulu.io/ontology#Adapter": ComponentType.ADAPTER,
            "http://kthulu.io/ontology#DomainEntity": ComponentType.ENTITY,
            "http://kthulu.io/ontology#DomainEvent": ComponentType.EVENT
        }
        return type_mapping.get(type_iri, ComponentType.MODULE)