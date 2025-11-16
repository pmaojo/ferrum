"""
Dependency Path Visualization Service

Provides dependency path analysis and visualization for Kthulu architecture components.
Supports finding shortest paths, circular dependencies, and impact analysis.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from collections import defaultdict, deque

from ..entities.architectural_component import ArchitecturalComponent, ComponentType
from application.ports.knowledge_graph_port import KnowledgeGraphPort


class PathType(Enum):
    SHORTEST = "shortest"
    ALL_SIMPLE = "all_simple"
    CIRCULAR = "circular"
    CRITICAL = "critical"


@dataclass
class DependencyPath:
    source: ArchitecturalComponent
    target: ArchitecturalComponent
    path: List[ArchitecturalComponent]
    path_type: PathType
    weight: float
    relationships: List[str]  # Types of relationships in the path
    metadata: Dict[str, Any]


@dataclass
class DependencyGraph:
    nodes: List[ArchitecturalComponent]
    edges: List[Tuple[str, str, str]]  # (source_iri, target_iri, relationship_type)
    cycles: List[List[str]]  # Circular dependencies
    critical_paths: List[DependencyPath]
    metrics: Dict[str, Any]


class DependencyPathService:
    """Service for dependency path analysis and visualization"""
    
    def __init__(self, knowledge_graph: KnowledgeGraphPort):
        self.knowledge_graph = knowledge_graph
        
    def find_dependency_paths(
        self,
        source_iri: str,
        target_iri: str,
        tenant_id: str,
        path_type: PathType = PathType.SHORTEST,
        max_paths: int = 10
    ) -> List[DependencyPath]:
        """
        Find dependency paths between two components
        
        Args:
            source_iri: Source component IRI
            target_iri: Target component IRI
            tenant_id: Tenant identifier
            path_type: Type of paths to find
            max_paths: Maximum number of paths to return
            
        Returns:
            List of dependency paths
        """
        # Build dependency graph
        graph = self._build_dependency_graph(tenant_id)
        
        if path_type == PathType.SHORTEST:
            return self._find_shortest_paths(graph, source_iri, target_iri, max_paths)
        elif path_type == PathType.ALL_SIMPLE:
            return self._find_all_simple_paths(graph, source_iri, target_iri, max_paths)
        elif path_type == PathType.CIRCULAR:
            return self._find_circular_paths(graph, source_iri, max_paths)
        elif path_type == PathType.CRITICAL:
            return self._find_critical_paths(graph, source_iri, target_iri, max_paths)
        
        return []
    
    def analyze_dependency_graph(self, tenant_id: str) -> DependencyGraph:
        """
        Analyze the complete dependency graph for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Complete dependency graph analysis
        """
        # Get all components and relationships
        components = self._get_all_components(tenant_id)
        relationships = self._get_all_relationships(tenant_id)
        
        # Build NetworkX graph
        nx_graph = self._build_networkx_graph(components, relationships)
        
        # Find cycles
        cycles = list(nx.simple_cycles(nx_graph))
        
        # Find critical paths (longest paths, bottlenecks)
        critical_paths = self._find_critical_paths_in_graph(nx_graph, components)
        
        # Calculate metrics
        metrics = self._calculate_graph_metrics(nx_graph, components)
        
        return DependencyGraph(
            nodes=components,
            edges=relationships,
            cycles=cycles,
            critical_paths=critical_paths,
            metrics=metrics
        )
    
    def get_component_dependencies(
        self,
        component_iri: str,
        tenant_id: str,
        direction: str = "both"  # "incoming", "outgoing", "both"
    ) -> Dict[str, List[ArchitecturalComponent]]:
        """
        Get all dependencies for a specific component
        
        Args:
            component_iri: Component IRI
            tenant_id: Tenant identifier
            direction: Direction of dependencies to include
            
        Returns:
            Dictionary with incoming and outgoing dependencies
        """
        result = {"incoming": [], "outgoing": []}
        
        if direction in ["incoming", "both"]:
            incoming_query = f"""
            PREFIX kth: <http://kthulu.io/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?component ?type ?name ?module ?relationship WHERE {{
                ?component ?relationship <{component_iri}> ;
                          a ?type ;
                          rdfs:label ?name ;
                          kth:belongsToModule ?module .
                
                FILTER(?relationship != rdf:type && ?relationship != rdfs:label)
            }}
            """
            
            incoming_results = self.knowledge_graph.execute_sparql_query(
                incoming_query, tenant_id
            )
            result["incoming"] = [
                self._sparql_result_to_component(r) for r in incoming_results
            ]
        
        if direction in ["outgoing", "both"]:
            outgoing_query = f"""
            PREFIX kth: <http://kthulu.io/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?component ?type ?name ?module ?relationship WHERE {{
                <{component_iri}> ?relationship ?component .
                ?component a ?type ;
                          rdfs:label ?name ;
                          kth:belongsToModule ?module .
                
                FILTER(?relationship != rdf:type && ?relationship != rdfs:label)
            }}
            """
            
            outgoing_results = self.knowledge_graph.execute_sparql_query(
                outgoing_query, tenant_id
            )
            result["outgoing"] = [
                self._sparql_result_to_component(r) for r in outgoing_results
            ]
        
        return result
    
    def find_dependency_cycles(self, tenant_id: str) -> List[List[ArchitecturalComponent]]:
        """
        Find all circular dependencies in the architecture
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of dependency cycles
        """
        components = self._get_all_components(tenant_id)
        relationships = self._get_all_relationships(tenant_id)
        
        # Build NetworkX directed graph
        nx_graph = self._build_networkx_graph(components, relationships)
        
        # Find strongly connected components with more than one node
        cycles = []
        for cycle_iris in nx.simple_cycles(nx_graph):
            if len(cycle_iris) > 1:
                cycle_components = [
                    next(c for c in components if c.iri == iri)
                    for iri in cycle_iris
                ]
                cycles.append(cycle_components)
        
        return cycles
    
    def calculate_impact_score(
        self,
        component_iri: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Calculate the impact score of a component based on its dependencies
        
        Args:
            component_iri: Component IRI
            tenant_id: Tenant identifier
            
        Returns:
            Impact analysis with scores and affected components
        """
        graph = self._build_dependency_graph(tenant_id)
        
        # Calculate various impact metrics
        incoming_deps = len(list(graph.predecessors(component_iri)))
        outgoing_deps = len(list(graph.successors(component_iri)))
        
        # Calculate transitive dependencies
        transitive_incoming = len(nx.ancestors(graph, component_iri))
        transitive_outgoing = len(nx.descendants(graph, component_iri))
        
        # Calculate centrality measures
        betweenness = nx.betweenness_centrality(graph).get(component_iri, 0)
        closeness = nx.closeness_centrality(graph).get(component_iri, 0)
        pagerank = nx.pagerank(graph).get(component_iri, 0)
        
        # Calculate impact score (weighted combination)
        impact_score = (
            incoming_deps * 0.3 +
            outgoing_deps * 0.2 +
            transitive_incoming * 0.2 +
            transitive_outgoing * 0.1 +
            betweenness * 0.1 +
            pagerank * 0.1
        )
        
        return {
            "impact_score": impact_score,
            "direct_incoming": incoming_deps,
            "direct_outgoing": outgoing_deps,
            "transitive_incoming": transitive_incoming,
            "transitive_outgoing": transitive_outgoing,
            "betweenness_centrality": betweenness,
            "closeness_centrality": closeness,
            "pagerank": pagerank,
            "affected_components": list(nx.descendants(graph, component_iri))
        }
    
    def _build_dependency_graph(self, tenant_id: str) -> nx.DiGraph:
        """Build NetworkX directed graph from knowledge graph"""
        components = self._get_all_components(tenant_id)
        relationships = self._get_all_relationships(tenant_id)
        
        return self._build_networkx_graph(components, relationships)
    
    def _build_networkx_graph(
        self,
        components: List[ArchitecturalComponent],
        relationships: List[Tuple[str, str, str]]
    ) -> nx.DiGraph:
        """Build NetworkX graph from components and relationships"""
        graph = nx.DiGraph()
        
        # Add nodes
        for component in components:
            graph.add_node(
                component.iri,
                component_type=component.component_type,
                name=component.name,
                module=component.module_namespace
            )
        
        # Add edges
        for source, target, rel_type in relationships:
            graph.add_edge(source, target, relationship_type=rel_type)
        
        return graph
    
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
    
    def _find_shortest_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str,
        max_paths: int
    ) -> List[DependencyPath]:
        """Find shortest paths between two nodes"""
        try:
            paths = list(nx.all_shortest_paths(graph, source, target))[:max_paths]
            
            result = []
            for path_iris in paths:
                path_components = [
                    self._iri_to_component(graph, iri) for iri in path_iris
                ]
                
                relationships = []
                for i in range(len(path_iris) - 1):
                    edge_data = graph.get_edge_data(path_iris[i], path_iris[i + 1])
                    relationships.append(edge_data.get("relationship_type", "unknown"))
                
                dep_path = DependencyPath(
                    source=path_components[0],
                    target=path_components[-1],
                    path=path_components,
                    path_type=PathType.SHORTEST,
                    weight=len(path_components) - 1,
                    relationships=relationships,
                    metadata={"length": len(path_components)}
                )
                result.append(dep_path)
            
            return result
        except nx.NetworkXNoPath:
            return []
    
    def _find_all_simple_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        target: str,
        max_paths: int
    ) -> List[DependencyPath]:
        """Find all simple paths between two nodes"""
        try:
            paths = list(nx.all_simple_paths(graph, source, target))[:max_paths]
            
            result = []
            for path_iris in paths:
                path_components = [
                    self._iri_to_component(graph, iri) for iri in path_iris
                ]
                
                relationships = []
                for i in range(len(path_iris) - 1):
                    edge_data = graph.get_edge_data(path_iris[i], path_iris[i + 1])
                    relationships.append(edge_data.get("relationship_type", "unknown"))
                
                dep_path = DependencyPath(
                    source=path_components[0],
                    target=path_components[-1],
                    path=path_components,
                    path_type=PathType.ALL_SIMPLE,
                    weight=len(path_components) - 1,
                    relationships=relationships,
                    metadata={"length": len(path_components)}
                )
                result.append(dep_path)
            
            return result
        except nx.NetworkXNoPath:
            return []
    
    def _find_circular_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        max_paths: int
    ) -> List[DependencyPath]:
        """Find circular dependency paths starting from a node"""
        result = []
        
        # Find cycles that include the source node
        for cycle in nx.simple_cycles(graph):
            if source in cycle and len(cycle) > 1:
                # Rotate cycle to start with source
                start_idx = cycle.index(source)
                rotated_cycle = cycle[start_idx:] + cycle[:start_idx] + [source]
                
                path_components = [
                    self._iri_to_component(graph, iri) for iri in rotated_cycle
                ]
                
                relationships = []
                for i in range(len(rotated_cycle) - 1):
                    edge_data = graph.get_edge_data(rotated_cycle[i], rotated_cycle[i + 1])
                    relationships.append(edge_data.get("relationship_type", "unknown"))
                
                dep_path = DependencyPath(
                    source=path_components[0],
                    target=path_components[0],  # Circular
                    path=path_components,
                    path_type=PathType.CIRCULAR,
                    weight=len(path_components) - 1,
                    relationships=relationships,
                    metadata={"cycle_length": len(cycle)}
                )
                result.append(dep_path)
                
                if len(result) >= max_paths:
                    break
        
        return result
    
    def _find_critical_paths_in_graph(
        self,
        graph: nx.DiGraph,
        components: List[ArchitecturalComponent]
    ) -> List[DependencyPath]:
        """Find critical paths in the entire graph"""
        # Find paths with high betweenness centrality
        betweenness = nx.edge_betweenness_centrality(graph)
        
        # Sort edges by betweenness centrality
        critical_edges = sorted(
            betweenness.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 critical edges
        
        result = []
        for (source, target), centrality in critical_edges:
            try:
                shortest_path = nx.shortest_path(graph, source, target)
                path_components = [
                    self._iri_to_component(graph, iri) for iri in shortest_path
                ]
                
                relationships = []
                for i in range(len(shortest_path) - 1):
                    edge_data = graph.get_edge_data(shortest_path[i], shortest_path[i + 1])
                    relationships.append(edge_data.get("relationship_type", "unknown"))
                
                dep_path = DependencyPath(
                    source=path_components[0],
                    target=path_components[-1],
                    path=path_components,
                    path_type=PathType.CRITICAL,
                    weight=centrality,
                    relationships=relationships,
                    metadata={"betweenness_centrality": centrality}
                )
                result.append(dep_path)
            except nx.NetworkXNoPath:
                continue
        
        return result
    
    def _calculate_graph_metrics(
        self,
        graph: nx.DiGraph,
        components: List[ArchitecturalComponent]
    ) -> Dict[str, Any]:
        """Calculate various graph metrics"""
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "density": nx.density(graph),
            "is_dag": nx.is_directed_acyclic_graph(graph),
            "strongly_connected_components": len(list(nx.strongly_connected_components(graph))),
            "weakly_connected_components": len(list(nx.weakly_connected_components(graph))),
            "average_clustering": nx.average_clustering(graph.to_undirected()),
            "diameter": nx.diameter(graph.to_undirected()) if nx.is_connected(graph.to_undirected()) else None
        }
    
    def _iri_to_component(self, graph: nx.DiGraph, iri: str) -> ArchitecturalComponent:
        """Convert IRI to ArchitecturalComponent using graph node data"""
        node_data = graph.nodes[iri]
        return ArchitecturalComponent(
            iri=iri,
            component_type=node_data.get("component_type", ComponentType.MODULE),
            name=node_data.get("name", ""),
            module_namespace=node_data.get("module", ""),
            properties={},
            relationships=[]
        )
    
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