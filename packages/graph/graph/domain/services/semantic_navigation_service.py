"""
Semantic Navigation Service

Main service that integrates semantic search, dependency path visualization,
impact analysis, and architectural pattern detection for advanced navigation
of Kthulu architecture components.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from ..entities.architectural_component import ArchitecturalComponent
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from application.ports.base import LLMPort
from .semantic_search_service import SemanticSearchService, SemanticSearchQuery, SearchResult
from .dependency_path_service import DependencyPathService, DependencyPath, PathType
from .impact_analysis_service import ImpactAnalysisService, ProposedChange, ImpactAnalysisResult
from .architectural_pattern_service import ArchitecturalPatternService, PatternAnalysisResult


@dataclass
class NavigationContext:
    current_component: Optional[ArchitecturalComponent]
    search_history: List[str]
    visited_components: Set[str]
    navigation_path: List[str]
    filters: Dict[str, Any]
    preferences: Dict[str, Any]


@dataclass
class SemanticNavigationResult:
    search_results: List[SearchResult]
    dependency_paths: List[DependencyPath]
    impact_analysis: Optional[ImpactAnalysisResult]
    detected_patterns: List[Any]  # PatternInstance
    recommendations: List[str]
    navigation_suggestions: List[str]
    metadata: Dict[str, Any]


class SemanticNavigationService:
    """
    Main service for advanced semantic navigation of architecture components
    """
    
    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort,
        llm: Optional[LLMPort] = None
    ):
        self.knowledge_graph = knowledge_graph
        self.llm = llm
        
        # Initialize sub-services
        self.search_service = SemanticSearchService(knowledge_graph, llm)
        self.dependency_service = DependencyPathService(knowledge_graph)
        self.impact_service = ImpactAnalysisService(knowledge_graph, self.dependency_service, llm)
        self.pattern_service = ArchitecturalPatternService(knowledge_graph, llm)
        
        # Navigation state
        self.navigation_contexts: Dict[str, NavigationContext] = {}
    
    def navigate_semantic_architecture(
        self,
        query: str,
        tenant_id: str,
        context_id: str = "default",
        include_patterns: bool = True,
        include_impact: bool = False,
        max_results: int = 20
    ) -> SemanticNavigationResult:
        """
        Perform comprehensive semantic navigation
        
        Args:
            query: Natural language query or component name
            tenant_id: Tenant identifier
            context_id: Navigation context identifier
            include_patterns: Whether to include pattern analysis
            include_impact: Whether to include impact analysis
            max_results: Maximum number of results
            
        Returns:
            Complete semantic navigation result
        """
        # Get or create navigation context
        context = self._get_navigation_context(context_id)
        
        # Update search history
        context.search_history.append(query)
        if len(context.search_history) > 50:  # Limit history size
            context.search_history = context.search_history[-50:]
        
        # Perform semantic search
        search_query = SemanticSearchQuery(
            query_text=query,
            max_results=max_results,
            tenant_id=tenant_id
        )
        search_results = self.search_service.search(search_query)
        
        # Find dependency paths for top results
        dependency_paths = []
        if search_results and context.current_component:
            for result in search_results[:5]:  # Top 5 results
                paths = self.dependency_service.find_dependency_paths(
                    context.current_component.iri,
                    result.component.iri,
                    tenant_id,
                    PathType.SHORTEST,
                    max_paths=3
                )
                dependency_paths.extend(paths)
        
        # Perform impact analysis if requested
        impact_analysis = None
        if include_impact and search_results:
            # Create a hypothetical change for the top search result
            top_result = search_results[0]
            proposed_change = ProposedChange(
                change_id=f"nav_{datetime.now().isoformat()}",
                change_type="modify_component",  # Assuming modification
                target_component=top_result.component,
                source_component=None,
                relationship_type=None,
                description=f"Hypothetical change to {top_result.component.name}",
                metadata={"navigation_query": query}
            )
            impact_analysis = self.impact_service.analyze_change_impact(proposed_change, tenant_id)
        
        # Detect architectural patterns if requested
        detected_patterns = []
        if include_patterns:
            pattern_analysis = self.pattern_service.analyze_patterns(tenant_id)
            # Filter patterns related to search results
            for pattern in pattern_analysis.detected_patterns + pattern_analysis.anti_patterns:
                if any(comp.iri in [r.component.iri for r in search_results] 
                       for comp in pattern.components):
                    detected_patterns.append(pattern)
        
        # Generate recommendations and navigation suggestions
        recommendations = self._generate_navigation_recommendations(
            search_results, dependency_paths, detected_patterns, context
        )
        
        navigation_suggestions = self._generate_navigation_suggestions(
            search_results, context, tenant_id
        )
        
        # Update navigation context
        if search_results:
            context.current_component = search_results[0].component
            context.visited_components.add(search_results[0].component.iri)
            context.navigation_path.append(search_results[0].component.iri)
        
        return SemanticNavigationResult(
            search_results=search_results,
            dependency_paths=dependency_paths,
            impact_analysis=impact_analysis,
            detected_patterns=detected_patterns,
            recommendations=recommendations,
            navigation_suggestions=navigation_suggestions,
            metadata={
                "query": query,
                "tenant_id": tenant_id,
                "context_id": context_id,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def explore_component_neighborhood(
        self,
        component_iri: str,
        tenant_id: str,
        depth: int = 2,
        include_patterns: bool = True
    ) -> Dict[str, Any]:
        """
        Explore the neighborhood of a specific component
        
        Args:
            component_iri: Component IRI to explore
            tenant_id: Tenant identifier
            depth: Exploration depth
            include_patterns: Whether to include pattern analysis
            
        Returns:
            Component neighborhood exploration result
        """
        # Get component dependencies
        dependencies = self.dependency_service.get_component_dependencies(
            component_iri, tenant_id, "both"
        )
        
        # Get dependency graph analysis
        graph_analysis = self.dependency_service.analyze_dependency_graph(tenant_id)
        
        # Calculate impact score
        impact_score = self.dependency_service.calculate_impact_score(component_iri, tenant_id)
        
        # Find related patterns
        related_patterns = []
        if include_patterns:
            pattern_analysis = self.pattern_service.analyze_patterns(tenant_id)
            for pattern in pattern_analysis.detected_patterns + pattern_analysis.anti_patterns:
                if any(comp.iri == component_iri for comp in pattern.components):
                    related_patterns.append(pattern)
        
        # Find similar components
        component = self._get_component_by_iri(component_iri, tenant_id)
        similar_components = []
        if component:
            search_query = SemanticSearchQuery(
                query_text=component.name,
                tenant_id=tenant_id,
                max_results=10
            )
            search_results = self.search_service.search(search_query)
            similar_components = [r.component for r in search_results 
                                if r.component.iri != component_iri]
        
        return {
            "component": component,
            "dependencies": dependencies,
            "impact_score": impact_score,
            "related_patterns": related_patterns,
            "similar_components": similar_components,
            "cycles": [cycle for cycle in graph_analysis.cycles 
                      if component_iri in cycle],
            "critical_paths": [path for path in graph_analysis.critical_paths
                             if component_iri in [comp.iri for comp in path.path]],
            "recommendations": self._generate_component_recommendations(
                component, dependencies, impact_score, related_patterns
            )
        }
    
    def find_architectural_hotspots(
        self,
        tenant_id: str,
        hotspot_type: str = "all"  # "complexity", "coupling", "patterns", "all"
    ) -> Dict[str, Any]:
        """
        Find architectural hotspots that need attention
        
        Args:
            tenant_id: Tenant identifier
            hotspot_type: Type of hotspots to find
            
        Returns:
            Architectural hotspots analysis
        """
        hotspots = {
            "complexity_hotspots": [],
            "coupling_hotspots": [],
            "pattern_hotspots": [],
            "anti_pattern_hotspots": []
        }
        
        if hotspot_type in ["complexity", "all"]:
            # Find components with high complexity (many relationships)
            graph_analysis = self.dependency_service.analyze_dependency_graph(tenant_id)
            
            # Calculate complexity scores for all components
            complexity_scores = {}
            for component in graph_analysis.nodes:
                impact_score = self.dependency_service.calculate_impact_score(
                    component.iri, tenant_id
                )
                complexity_scores[component.iri] = {
                    "component": component,
                    "score": impact_score["impact_score"],
                    "details": impact_score
                }
            
            # Get top 10 most complex components
            sorted_by_complexity = sorted(
                complexity_scores.values(),
                key=lambda x: x["score"],
                reverse=True
            )
            hotspots["complexity_hotspots"] = sorted_by_complexity[:10]
        
        if hotspot_type in ["coupling", "all"]:
            # Find highly coupled components
            graph_analysis = self.dependency_service.analyze_dependency_graph(tenant_id)
            
            coupling_scores = {}
            for component in graph_analysis.nodes:
                deps = self.dependency_service.get_component_dependencies(
                    component.iri, tenant_id, "both"
                )
                coupling_score = len(deps["incoming"]) + len(deps["outgoing"])
                coupling_scores[component.iri] = {
                    "component": component,
                    "score": coupling_score,
                    "incoming": len(deps["incoming"]),
                    "outgoing": len(deps["outgoing"])
                }
            
            # Get top 10 most coupled components
            sorted_by_coupling = sorted(
                coupling_scores.values(),
                key=lambda x: x["score"],
                reverse=True
            )
            hotspots["coupling_hotspots"] = sorted_by_coupling[:10]
        
        if hotspot_type in ["patterns", "all"]:
            # Find pattern-related hotspots
            pattern_analysis = self.pattern_service.analyze_patterns(tenant_id)
            
            # Components involved in multiple patterns
            component_pattern_count = {}
            for pattern in pattern_analysis.detected_patterns:
                for component in pattern.components:
                    if component.iri not in component_pattern_count:
                        component_pattern_count[component.iri] = {
                            "component": component,
                            "patterns": []
                        }
                    component_pattern_count[component.iri]["patterns"].append(pattern)
            
            # Sort by pattern involvement
            pattern_hotspots = sorted(
                component_pattern_count.values(),
                key=lambda x: len(x["patterns"]),
                reverse=True
            )
            hotspots["pattern_hotspots"] = pattern_hotspots[:10]
            
            # Anti-pattern hotspots
            hotspots["anti_pattern_hotspots"] = pattern_analysis.anti_patterns
        
        return hotspots
    
    def get_navigation_recommendations(
        self,
        current_component_iri: str,
        tenant_id: str,
        context_id: str = "default"
    ) -> List[str]:
        """
        Get navigation recommendations based on current context
        
        Args:
            current_component_iri: Current component IRI
            tenant_id: Tenant identifier
            context_id: Navigation context identifier
            
        Returns:
            List of navigation recommendations
        """
        context = self._get_navigation_context(context_id)
        context.current_component = self._get_component_by_iri(current_component_iri, tenant_id)
        
        recommendations = []
        
        if context.current_component:
            # Get component dependencies
            deps = self.dependency_service.get_component_dependencies(
                current_component_iri, tenant_id, "both"
            )
            
            # Recommend exploring dependencies
            if deps["outgoing"]:
                recommendations.append(
                    f"Explore {len(deps['outgoing'])} components that {context.current_component.name} depends on"
                )
            
            if deps["incoming"]:
                recommendations.append(
                    f"Explore {len(deps['incoming'])} components that depend on {context.current_component.name}"
                )
            
            # Recommend exploring patterns
            pattern_analysis = self.pattern_service.analyze_patterns(tenant_id)
            related_patterns = [
                pattern for pattern in pattern_analysis.detected_patterns + pattern_analysis.anti_patterns
                if any(comp.iri == current_component_iri for comp in pattern.components)
            ]
            
            if related_patterns:
                recommendations.append(
                    f"Explore {len(related_patterns)} architectural patterns involving this component"
                )
            
            # Recommend exploring similar components
            search_query = SemanticSearchQuery(
                query_text=context.current_component.name,
                tenant_id=tenant_id,
                max_results=5
            )
            similar_results = self.search_service.search(search_query)
            similar_components = [r.component for r in similar_results 
                               if r.component.iri != current_component_iri]
            
            if similar_components:
                recommendations.append(
                    f"Explore {len(similar_components)} similar components"
                )
            
            # Recommend based on search history
            if len(context.search_history) > 1:
                recent_searches = context.search_history[-3:]
                recommendations.append(
                    f"Continue exploring based on recent searches: {', '.join(recent_searches)}"
                )
        
        return recommendations
    
    def _get_navigation_context(self, context_id: str) -> NavigationContext:
        """Get or create navigation context"""
        if context_id not in self.navigation_contexts:
            self.navigation_contexts[context_id] = NavigationContext(
                current_component=None,
                search_history=[],
                visited_components=set(),
                navigation_path=[],
                filters={},
                preferences={}
            )
        return self.navigation_contexts[context_id]
    
    def _get_component_by_iri(self, component_iri: str, tenant_id: str) -> Optional[ArchitecturalComponent]:
        """Get component by IRI"""
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?type ?name ?module WHERE {{
            <{component_iri}> a ?type ;
                              rdfs:label ?name ;
                              kth:belongsToModule ?module .
        }}
        """
        
        results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        if results:
            result = results[0]
            return ArchitecturalComponent(
                iri=component_iri,
                component_type=self._map_type_to_enum(result.get("type", "")),
                name=result.get("name", ""),
                module_namespace=result.get("module", ""),
                properties={},
                relationships=[]
            )
        return None
    
    def _generate_navigation_recommendations(
        self,
        search_results: List[SearchResult],
        dependency_paths: List[DependencyPath],
        detected_patterns: List[Any],
        context: NavigationContext
    ) -> List[str]:
        """Generate navigation-specific recommendations"""
        recommendations = []
        
        if search_results:
            recommendations.append(f"Found {len(search_results)} relevant components")
            
            # Recommend exploring top results
            top_results = search_results[:3]
            for result in top_results:
                if result.component.iri not in context.visited_components:
                    recommendations.append(f"Explore {result.component.name} ({result.match_type} match)")
        
        if dependency_paths:
            recommendations.append(f"Found {len(dependency_paths)} dependency paths")
            
            # Recommend exploring shortest paths
            shortest_paths = [p for p in dependency_paths if p.path_type == PathType.SHORTEST]
            if shortest_paths:
                recommendations.append("Explore shortest dependency paths for better understanding")
        
        if detected_patterns:
            recommendations.append(f"Found {len(detected_patterns)} architectural patterns")
            recommendations.append("Review pattern implementations for best practices")
        
        return recommendations
    
    def _generate_navigation_suggestions(
        self,
        search_results: List[SearchResult],
        context: NavigationContext,
        tenant_id: str
    ) -> List[str]:
        """Generate navigation suggestions"""
        suggestions = []
        
        if search_results:
            # Suggest related searches
            top_result = search_results[0]
            suggestions.append(f"Search for components similar to {top_result.component.name}")
            suggestions.append(f"Explore dependencies of {top_result.component.name}")
            
            # Suggest pattern exploration
            if top_result.component.component_type.value in ["usecase", "adapter"]:
                suggestions.append("Search for hexagonal architecture patterns")
            
            if top_result.component.component_type.value == "event":
                suggestions.append("Search for event sourcing patterns")
        
        # Suggest based on search history
        if len(context.search_history) > 1:
            recent_terms = set()
            for search in context.search_history[-5:]:
                recent_terms.update(search.lower().split())
            
            if len(recent_terms) > 1:
                suggestions.append(f"Try combining recent search terms: {', '.join(list(recent_terms)[:3])}")
        
        return suggestions
    
    def _generate_component_recommendations(
        self,
        component: Optional[ArchitecturalComponent],
        dependencies: Dict[str, List[ArchitecturalComponent]],
        impact_score: Dict[str, Any],
        related_patterns: List[Any]
    ) -> List[str]:
        """Generate component-specific recommendations"""
        recommendations = []
        
        if not component:
            return recommendations
        
        # Impact-based recommendations
        if impact_score["impact_score"] > 10:
            recommendations.append("High-impact component - changes require careful consideration")
        
        if impact_score["betweenness_centrality"] > 0.1:
            recommendations.append("Central component in architecture - critical for system connectivity")
        
        # Dependency-based recommendations
        if len(dependencies["outgoing"]) > 10:
            recommendations.append("High outgoing dependencies - consider reducing coupling")
        
        if len(dependencies["incoming"]) > 15:
            recommendations.append("Many components depend on this - ensure stability")
        
        # Pattern-based recommendations
        for pattern in related_patterns:
            if hasattr(pattern, 'recommendations'):
                recommendations.extend(pattern.recommendations[:2])  # Limit to 2 per pattern
        
        return recommendations
    
    def _map_type_to_enum(self, type_iri: str):
        """Map OWL type IRI to ComponentType enum"""
        from ..entities.architectural_component import ComponentType
        
        type_mapping = {
            "http://kthulu.io/ontology#Module": ComponentType.MODULE,
            "http://kthulu.io/ontology#UseCase": ComponentType.USECASE,
            "http://kthulu.io/ontology#Port": ComponentType.PORT,
            "http://kthulu.io/ontology#Adapter": ComponentType.ADAPTER,
            "http://kthulu.io/ontology#DomainEntity": ComponentType.ENTITY,
            "http://kthulu.io/ontology#DomainEvent": ComponentType.EVENT
        }
        return type_mapping.get(type_iri, ComponentType.MODULE)