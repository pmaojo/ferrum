"""
Impact Analysis Service for Proposed Changes

Analyzes the potential impact of proposed architectural changes
on the Kthulu system, including dependency analysis, risk assessment,
and change propagation prediction.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from datetime import datetime

from ..entities.architectural_component import ArchitecturalComponent, ComponentType
from ..entities.validation_report import ValidationReport
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from application.ports.base import LLMPort
from .dependency_path_service import DependencyPathService


class ChangeType(Enum):
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    MODIFY_COMPONENT = "modify_component"
    ADD_RELATIONSHIP = "add_relationship"
    REMOVE_RELATIONSHIP = "remove_relationship"
    MODIFY_RELATIONSHIP = "modify_relationship"
    REFACTOR_MODULE = "refactor_module"


class ImpactLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProposedChange:
    change_id: str
    change_type: ChangeType
    target_component: Optional[ArchitecturalComponent]
    source_component: Optional[ArchitecturalComponent]
    relationship_type: Optional[str]
    description: str
    metadata: Dict[str, Any]


@dataclass
class ImpactedComponent:
    component: ArchitecturalComponent
    impact_level: ImpactLevel
    impact_reasons: List[str]
    required_changes: List[str]
    risk_factors: List[str]
    estimated_effort: float  # Hours or story points


@dataclass
class ImpactAnalysisResult:
    change: ProposedChange
    directly_impacted: List[ImpactedComponent]
    transitively_impacted: List[ImpactedComponent]
    potential_violations: List[str]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    estimated_total_effort: float
    confidence_score: float
    analysis_timestamp: datetime


class ImpactAnalysisService:
    """Service for analyzing the impact of proposed architectural changes"""
    
    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort,
        dependency_service: DependencyPathService,
        llm: Optional[LLMPort] = None
    ):
        self.knowledge_graph = knowledge_graph
        self.dependency_service = dependency_service
        self.llm = llm
        
    def analyze_change_impact(
        self,
        change: ProposedChange,
        tenant_id: str
    ) -> ImpactAnalysisResult:
        """
        Analyze the impact of a proposed change
        
        Args:
            change: The proposed change to analyze
            tenant_id: Tenant identifier
            
        Returns:
            Complete impact analysis result
        """
        # Get current architecture state
        current_graph = self.dependency_service.analyze_dependency_graph(tenant_id)
        
        # Analyze direct impacts
        directly_impacted = self._analyze_direct_impact(change, current_graph, tenant_id)
        
        # Analyze transitive impacts
        transitively_impacted = self._analyze_transitive_impact(
            change, directly_impacted, current_graph, tenant_id
        )
        
        # Check for potential architectural violations
        potential_violations = self._check_potential_violations(change, tenant_id)
        
        # Perform risk assessment
        risk_assessment = self._assess_risks(change, directly_impacted, transitively_impacted)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            change, directly_impacted, transitively_impacted, risk_assessment
        )
        
        # Calculate total effort estimate
        total_effort = sum(comp.estimated_effort for comp in directly_impacted + transitively_impacted)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            change, directly_impacted, transitively_impacted
        )
        
        return ImpactAnalysisResult(
            change=change,
            directly_impacted=directly_impacted,
            transitively_impacted=transitively_impacted,
            potential_violations=potential_violations,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            estimated_total_effort=total_effort,
            confidence_score=confidence_score,
            analysis_timestamp=datetime.now()
        )
    
    def analyze_batch_changes(
        self,
        changes: List[ProposedChange],
        tenant_id: str
    ) -> List[ImpactAnalysisResult]:
        """
        Analyze the impact of multiple proposed changes
        
        Args:
            changes: List of proposed changes
            tenant_id: Tenant identifier
            
        Returns:
            List of impact analysis results
        """
        results = []
        
        # Analyze each change individually first
        individual_results = []
        for change in changes:
            result = self.analyze_change_impact(change, tenant_id)
            individual_results.append(result)
        
        # Analyze interaction effects between changes
        interaction_effects = self._analyze_change_interactions(individual_results, tenant_id)
        
        # Adjust results based on interactions
        for i, result in enumerate(individual_results):
            adjusted_result = self._adjust_for_interactions(result, interaction_effects, i)
            results.append(adjusted_result)
        
        return results
    
    def predict_change_propagation(
        self,
        change: ProposedChange,
        tenant_id: str,
        max_depth: int = 5
    ) -> Dict[str, List[ArchitecturalComponent]]:
        """
        Predict how a change will propagate through the architecture
        
        Args:
            change: The proposed change
            tenant_id: Tenant identifier
            max_depth: Maximum propagation depth to analyze
            
        Returns:
            Dictionary mapping propagation levels to affected components
        """
        if not change.target_component:
            return {}
        
        propagation_map = {}
        visited = set()
        current_level = [change.target_component]
        
        for depth in range(max_depth):
            if not current_level:
                break
                
            propagation_map[f"level_{depth}"] = current_level.copy()
            next_level = []
            
            for component in current_level:
                if component.iri in visited:
                    continue
                    
                visited.add(component.iri)
                
                # Get dependencies of current component
                deps = self.dependency_service.get_component_dependencies(
                    component.iri, tenant_id, "both"
                )
                
                # Add unvisited dependencies to next level
                for dep_list in deps.values():
                    for dep in dep_list:
                        if dep.iri not in visited:
                            next_level.append(dep)
            
            current_level = next_level
        
        return propagation_map
    
    def estimate_change_effort(
        self,
        change: ProposedChange,
        impacted_components: List[ImpactedComponent]
    ) -> Dict[str, Any]:
        """
        Estimate the effort required to implement a change
        
        Args:
            change: The proposed change
            impacted_components: List of impacted components
            
        Returns:
            Effort estimation breakdown
        """
        base_effort = self._get_base_effort_for_change_type(change.change_type)
        
        # Calculate effort based on impacted components
        component_effort = 0
        for comp in impacted_components:
            component_effort += comp.estimated_effort
        
        # Apply complexity multipliers
        complexity_multiplier = self._calculate_complexity_multiplier(change, impacted_components)
        
        # Apply risk multipliers
        risk_multiplier = self._calculate_risk_multiplier(impacted_components)
        
        total_effort = (base_effort + component_effort) * complexity_multiplier * risk_multiplier
        
        return {
            "base_effort": base_effort,
            "component_effort": component_effort,
            "complexity_multiplier": complexity_multiplier,
            "risk_multiplier": risk_multiplier,
            "total_effort": total_effort,
            "effort_breakdown": {
                "development": total_effort * 0.6,
                "testing": total_effort * 0.25,
                "documentation": total_effort * 0.1,
                "deployment": total_effort * 0.05
            }
        }
    
    def _analyze_direct_impact(
        self,
        change: ProposedChange,
        current_graph: Any,
        tenant_id: str
    ) -> List[ImpactedComponent]:
        """Analyze components directly impacted by the change"""
        directly_impacted = []
        
        if change.change_type == ChangeType.ADD_COMPONENT:
            # New component might affect existing components it connects to
            if change.target_component:
                # Find components that might be affected by the new component
                similar_components = self._find_similar_components(
                    change.target_component, tenant_id
                )
                for comp in similar_components:
                    impacted = ImpactedComponent(
                        component=comp,
                        impact_level=ImpactLevel.LOW,
                        impact_reasons=["New similar component added"],
                        required_changes=["Review for potential duplication"],
                        risk_factors=["Potential code duplication"],
                        estimated_effort=2.0
                    )
                    directly_impacted.append(impacted)
        
        elif change.change_type == ChangeType.REMOVE_COMPONENT:
            if change.target_component:
                # Find all components that depend on the component being removed
                deps = self.dependency_service.get_component_dependencies(
                    change.target_component.iri, tenant_id, "incoming"
                )
                
                for comp in deps["incoming"]:
                    impacted = ImpactedComponent(
                        component=comp,
                        impact_level=ImpactLevel.HIGH,
                        impact_reasons=["Depends on component being removed"],
                        required_changes=["Update dependencies", "Find alternative implementation"],
                        risk_factors=["Breaking change", "Compilation errors"],
                        estimated_effort=8.0
                    )
                    directly_impacted.append(impacted)
        
        elif change.change_type == ChangeType.MODIFY_COMPONENT:
            if change.target_component:
                # Find components that use the modified component
                deps = self.dependency_service.get_component_dependencies(
                    change.target_component.iri, tenant_id, "incoming"
                )
                
                for comp in deps["incoming"]:
                    impact_level = self._determine_modification_impact_level(change, comp)
                    impacted = ImpactedComponent(
                        component=comp,
                        impact_level=impact_level,
                        impact_reasons=["Uses modified component"],
                        required_changes=["Review interface changes", "Update usage if needed"],
                        risk_factors=["Interface changes", "Behavioral changes"],
                        estimated_effort=self._estimate_modification_effort(impact_level)
                    )
                    directly_impacted.append(impacted)
        
        elif change.change_type == ChangeType.ADD_RELATIONSHIP:
            # Both source and target components are directly impacted
            if change.source_component and change.target_component:
                source_impacted = ImpactedComponent(
                    component=change.source_component,
                    impact_level=ImpactLevel.MEDIUM,
                    impact_reasons=["New outgoing relationship"],
                    required_changes=["Implement new dependency"],
                    risk_factors=["Increased coupling"],
                    estimated_effort=4.0
                )
                directly_impacted.append(source_impacted)
                
                target_impacted = ImpactedComponent(
                    component=change.target_component,
                    impact_level=ImpactLevel.LOW,
                    impact_reasons=["New incoming relationship"],
                    required_changes=["Ensure interface availability"],
                    risk_factors=["Increased responsibility"],
                    estimated_effort=2.0
                )
                directly_impacted.append(target_impacted)
        
        elif change.change_type == ChangeType.REMOVE_RELATIONSHIP:
            # Both source and target components are directly impacted
            if change.source_component and change.target_component:
                source_impacted = ImpactedComponent(
                    component=change.source_component,
                    impact_level=ImpactLevel.HIGH,
                    impact_reasons=["Removing dependency"],
                    required_changes=["Find alternative implementation", "Remove usage"],
                    risk_factors=["Breaking change", "Lost functionality"],
                    estimated_effort=6.0
                )
                directly_impacted.append(source_impacted)
        
        return directly_impacted
    
    def _analyze_transitive_impact(
        self,
        change: ProposedChange,
        directly_impacted: List[ImpactedComponent],
        current_graph: Any,
        tenant_id: str
    ) -> List[ImpactedComponent]:
        """Analyze components transitively impacted by the change"""
        transitively_impacted = []
        processed_iris = {comp.component.iri for comp in directly_impacted}
        
        # Add the target component to processed set
        if change.target_component:
            processed_iris.add(change.target_component.iri)
        
        # For each directly impacted component, find its dependencies
        for impacted in directly_impacted:
            deps = self.dependency_service.get_component_dependencies(
                impacted.component.iri, tenant_id, "incoming"
            )
            
            for comp in deps["incoming"]:
                if comp.iri not in processed_iris:
                    # Calculate transitive impact level (usually lower than direct)
                    transitive_level = self._reduce_impact_level(impacted.impact_level)
                    
                    transitive_impacted_comp = ImpactedComponent(
                        component=comp,
                        impact_level=transitive_level,
                        impact_reasons=[f"Transitively affected through {impacted.component.name}"],
                        required_changes=["Review for potential impact", "Update tests"],
                        risk_factors=["Indirect behavioral changes"],
                        estimated_effort=self._estimate_transitive_effort(transitive_level)
                    )
                    transitively_impacted.append(transitive_impacted_comp)
                    processed_iris.add(comp.iri)
        
        return transitively_impacted
    
    def _check_potential_violations(
        self,
        change: ProposedChange,
        tenant_id: str
    ) -> List[str]:
        """Check for potential architectural violations the change might introduce"""
        violations = []
        
        if change.change_type == ChangeType.ADD_RELATIONSHIP:
            if (change.source_component and change.target_component and
                change.relationship_type == "calls"):
                
                # Check for potential DIP violations
                if (change.source_component.component_type in [ComponentType.USECASE, ComponentType.ENTITY] and
                    change.target_component.component_type == ComponentType.ADAPTER):
                    violations.append("Potential DIP violation: Domain component calling infrastructure")
                
                # Check for circular dependencies
                existing_path = self.dependency_service.find_dependency_paths(
                    change.target_component.iri,
                    change.source_component.iri,
                    tenant_id
                )
                if existing_path:
                    violations.append("Potential circular dependency")
        
        elif change.change_type == ChangeType.ADD_COMPONENT:
            if change.target_component:
                # Check for naming conflicts
                similar_components = self._find_similar_components(change.target_component, tenant_id)
                if similar_components:
                    violations.append("Potential naming conflict with existing components")
        
        return violations
    
    def _assess_risks(
        self,
        change: ProposedChange,
        directly_impacted: List[ImpactedComponent],
        transitively_impacted: List[ImpactedComponent]
    ) -> Dict[str, Any]:
        """Assess risks associated with the change"""
        risk_factors = []
        
        # Collect all risk factors
        for comp in directly_impacted + transitively_impacted:
            risk_factors.extend(comp.risk_factors)
        
        # Count risk occurrences
        risk_counts = {}
        for risk in risk_factors:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        # Calculate overall risk level
        total_components = len(directly_impacted) + len(transitively_impacted)
        high_impact_count = sum(1 for comp in directly_impacted + transitively_impacted 
                               if comp.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL])
        
        if high_impact_count > total_components * 0.5:
            overall_risk = "HIGH"
        elif high_impact_count > total_components * 0.2:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"
        
        return {
            "overall_risk": overall_risk,
            "risk_factors": risk_counts,
            "total_impacted_components": total_components,
            "high_impact_components": high_impact_count,
            "risk_score": high_impact_count / max(total_components, 1)
        }
    
    def _generate_recommendations(
        self,
        change: ProposedChange,
        directly_impacted: List[ImpactedComponent],
        transitively_impacted: List[ImpactedComponent],
        risk_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for implementing the change"""
        recommendations = []
        
        if risk_assessment["overall_risk"] == "HIGH":
            recommendations.append("Consider breaking this change into smaller, incremental changes")
            recommendations.append("Implement comprehensive testing strategy")
            recommendations.append("Plan for rollback strategy")
        
        if len(directly_impacted) > 10:
            recommendations.append("High number of directly impacted components - consider refactoring approach")
        
        # Change-specific recommendations
        if change.change_type == ChangeType.REMOVE_COMPONENT:
            recommendations.append("Ensure all dependencies are properly handled before removal")
            recommendations.append("Consider deprecation period before complete removal")
        
        elif change.change_type == ChangeType.ADD_RELATIONSHIP:
            recommendations.append("Verify interface compatibility between components")
            recommendations.append("Update documentation to reflect new relationships")
        
        # Risk-specific recommendations
        if "Breaking change" in risk_assessment["risk_factors"]:
            recommendations.append("Plan for API versioning or backward compatibility")
        
        if "Circular dependency" in risk_assessment["risk_factors"]:
            recommendations.append("Review architecture to eliminate circular dependencies")
        
        return recommendations
    
    def _find_similar_components(
        self,
        component: ArchitecturalComponent,
        tenant_id: str
    ) -> List[ArchitecturalComponent]:
        """Find components similar to the given component"""
        # This is a simplified implementation
        # In practice, this would use more sophisticated similarity matching
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module WHERE {{
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module .
            
            FILTER(
                ?type = <{component.component_type.value}> &&
                CONTAINS(LCASE(?name), LCASE("{component.name}"))
            )
        }}
        """
        
        results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        return [self._sparql_result_to_component(r) for r in results]
    
    def _determine_modification_impact_level(
        self,
        change: ProposedChange,
        dependent_component: ArchitecturalComponent
    ) -> ImpactLevel:
        """Determine the impact level of a modification on a dependent component"""
        # This would analyze the specific type of modification
        # For now, return a default based on component types
        if dependent_component.component_type == ComponentType.USECASE:
            return ImpactLevel.HIGH
        elif dependent_component.component_type == ComponentType.ADAPTER:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW
    
    def _estimate_modification_effort(self, impact_level: ImpactLevel) -> float:
        """Estimate effort based on impact level"""
        effort_mapping = {
            ImpactLevel.LOW: 2.0,
            ImpactLevel.MEDIUM: 4.0,
            ImpactLevel.HIGH: 8.0,
            ImpactLevel.CRITICAL: 16.0
        }
        return effort_mapping.get(impact_level, 4.0)
    
    def _reduce_impact_level(self, direct_level: ImpactLevel) -> ImpactLevel:
        """Reduce impact level for transitive impacts"""
        reduction_mapping = {
            ImpactLevel.CRITICAL: ImpactLevel.HIGH,
            ImpactLevel.HIGH: ImpactLevel.MEDIUM,
            ImpactLevel.MEDIUM: ImpactLevel.LOW,
            ImpactLevel.LOW: ImpactLevel.LOW
        }
        return reduction_mapping.get(direct_level, ImpactLevel.LOW)
    
    def _estimate_transitive_effort(self, impact_level: ImpactLevel) -> float:
        """Estimate effort for transitive impacts (usually lower)"""
        return self._estimate_modification_effort(impact_level) * 0.5
    
    def _get_base_effort_for_change_type(self, change_type: ChangeType) -> float:
        """Get base effort estimate for different change types"""
        effort_mapping = {
            ChangeType.ADD_COMPONENT: 8.0,
            ChangeType.REMOVE_COMPONENT: 4.0,
            ChangeType.MODIFY_COMPONENT: 6.0,
            ChangeType.ADD_RELATIONSHIP: 2.0,
            ChangeType.REMOVE_RELATIONSHIP: 3.0,
            ChangeType.MODIFY_RELATIONSHIP: 4.0,
            ChangeType.REFACTOR_MODULE: 16.0
        }
        return effort_mapping.get(change_type, 4.0)
    
    def _calculate_complexity_multiplier(
        self,
        change: ProposedChange,
        impacted_components: List[ImpactedComponent]
    ) -> float:
        """Calculate complexity multiplier based on change and impacts"""
        base_multiplier = 1.0
        
        # More impacted components = higher complexity
        component_count = len(impacted_components)
        if component_count > 20:
            base_multiplier += 0.5
        elif component_count > 10:
            base_multiplier += 0.3
        elif component_count > 5:
            base_multiplier += 0.1
        
        # Cross-module changes are more complex
        modules = set()
        for comp in impacted_components:
            modules.add(comp.component.module_namespace)
        
        if len(modules) > 3:
            base_multiplier += 0.3
        elif len(modules) > 1:
            base_multiplier += 0.1
        
        return base_multiplier
    
    def _calculate_risk_multiplier(self, impacted_components: List[ImpactedComponent]) -> float:
        """Calculate risk multiplier based on impacted components"""
        base_multiplier = 1.0
        
        # Count high-risk components
        high_risk_count = sum(1 for comp in impacted_components 
                             if comp.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL])
        
        risk_ratio = high_risk_count / max(len(impacted_components), 1)
        
        if risk_ratio > 0.5:
            base_multiplier += 0.4
        elif risk_ratio > 0.3:
            base_multiplier += 0.2
        elif risk_ratio > 0.1:
            base_multiplier += 0.1
        
        return base_multiplier
    
    def _calculate_confidence_score(
        self,
        change: ProposedChange,
        directly_impacted: List[ImpactedComponent],
        transitively_impacted: List[ImpactedComponent]
    ) -> float:
        """Calculate confidence score for the analysis"""
        base_confidence = 0.8
        
        # Reduce confidence for complex changes
        total_impacted = len(directly_impacted) + len(transitively_impacted)
        if total_impacted > 20:
            base_confidence -= 0.2
        elif total_impacted > 10:
            base_confidence -= 0.1
        
        # Reduce confidence for certain change types
        if change.change_type in [ChangeType.REFACTOR_MODULE, ChangeType.MODIFY_COMPONENT]:
            base_confidence -= 0.1
        
        return max(0.1, base_confidence)
    
    def _analyze_change_interactions(
        self,
        individual_results: List[ImpactAnalysisResult],
        tenant_id: str
    ) -> Dict[str, Any]:
        """Analyze interactions between multiple changes"""
        # This is a simplified implementation
        # In practice, this would be much more sophisticated
        interactions = {
            "conflicting_changes": [],
            "synergistic_changes": [],
            "cumulative_risk": 0.0
        }
        
        # Check for conflicts (changes affecting same components)
        for i, result1 in enumerate(individual_results):
            for j, result2 in enumerate(individual_results[i+1:], i+1):
                impacted1 = {comp.component.iri for comp in result1.directly_impacted}
                impacted2 = {comp.component.iri for comp in result2.directly_impacted}
                
                if impacted1.intersection(impacted2):
                    interactions["conflicting_changes"].append((i, j))
        
        # Calculate cumulative risk
        total_risk = sum(result.risk_assessment["risk_score"] for result in individual_results)
        interactions["cumulative_risk"] = min(1.0, total_risk * 1.2)  # Interaction amplifies risk
        
        return interactions
    
    def _adjust_for_interactions(
        self,
        result: ImpactAnalysisResult,
        interactions: Dict[str, Any],
        result_index: int
    ) -> ImpactAnalysisResult:
        """Adjust individual result based on interaction effects"""
        # Increase effort estimates for conflicting changes
        for conflict in interactions["conflicting_changes"]:
            if result_index in conflict:
                result.estimated_total_effort *= 1.3
                result.recommendations.append("This change conflicts with other proposed changes")
        
        # Adjust confidence based on cumulative risk
        if interactions["cumulative_risk"] > 0.7:
            result.confidence_score *= 0.8
        
        return result
    
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