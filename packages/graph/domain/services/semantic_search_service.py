"""
Semantic Search Service for Architecture Components

Provides semantic search capabilities across Kthulu architecture components
using SPARQL queries and semantic reasoning.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re
from abc import ABC, abstractmethod

from ..entities.architectural_component import ArchitecturalComponent, ComponentType
from ..entities.validation_report import ValidationReport
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from application.ports.base import LLMPort


class SearchScope(Enum):
    ALL = "all"
    MODULES = "modules"
    USECASES = "usecases"
    PORTS = "ports"
    ADAPTERS = "adapters"
    ENTITIES = "entities"
    EVENTS = "events"


@dataclass
class SearchResult:
    component: ArchitecturalComponent
    relevance_score: float
    match_type: str  # "exact", "semantic", "pattern"
    match_details: Dict[str, Any]
    related_components: List[ArchitecturalComponent]


@dataclass
class SemanticSearchQuery:
    query_text: str
    scope: SearchScope = SearchScope.ALL
    include_relationships: bool = True
    max_results: int = 50
    tenant_id: str = ""


class SemanticSearchService:
    """Service for semantic search across architecture components"""
    
    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort,
        llm: Optional[LLMPort] = None
    ):
        self.knowledge_graph = knowledge_graph
        self.llm = llm
        
    def search(self, query: SemanticSearchQuery) -> List[SearchResult]:
        """
        Perform semantic search across architecture components
        
        Args:
            query: Search query with parameters
            
        Returns:
            List of search results ordered by relevance
        """
        results = []
        
        # 1. Exact name/label matching
        exact_results = self._search_exact_matches(query)
        results.extend(exact_results)
        
        # 2. Pattern-based search (regex, wildcards)
        pattern_results = self._search_patterns(query)
        results.extend(pattern_results)
        
        # 3. Semantic search using SPARQL
        semantic_results = self._search_semantic(query)
        results.extend(semantic_results)
        
        # 4. LLM-enhanced search if available
        if self.llm:
            llm_results = self._search_with_llm(query)
            results.extend(llm_results)
        
        # Remove duplicates and sort by relevance
        unique_results = self._deduplicate_results(results)
        sorted_results = sorted(unique_results, key=lambda r: r.relevance_score, reverse=True)
        
        return sorted_results[:query.max_results]
    
    def _search_exact_matches(self, query: SemanticSearchQuery) -> List[SearchResult]:
        """Search for exact name/label matches"""
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module WHERE {{
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module .
            
            FILTER(
                CONTAINS(LCASE(?name), LCASE("{query.query_text}")) ||
                CONTAINS(LCASE(STR(?component)), LCASE("{query.query_text}"))
            )
            
            {self._get_type_filter(query.scope)}
        }}
        ORDER BY ?name
        """
        
        results = []
        sparql_results = self.knowledge_graph.execute_sparql_query(
            sparql_query, 
            query.tenant_id
        )
        
        for result in sparql_results:
            component = self._sparql_result_to_component(result)
            search_result = SearchResult(
                component=component,
                relevance_score=1.0,  # Highest score for exact matches
                match_type="exact",
                match_details={"matched_field": "name"},
                related_components=[]
            )
            results.append(search_result)
            
        return results
    
    def _search_patterns(self, query: SemanticSearchQuery) -> List[SearchResult]:
        """Search using pattern matching (wildcards, regex)"""
        # Convert wildcards to regex
        pattern = query.query_text.replace("*", ".*").replace("?", ".")
        
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module WHERE {{
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module .
            
            FILTER(REGEX(?name, "{pattern}", "i"))
            
            {self._get_type_filter(query.scope)}
        }}
        ORDER BY ?name
        """
        
        results = []
        sparql_results = self.knowledge_graph.execute_sparql_query(
            sparql_query,
            query.tenant_id
        )
        
        for result in sparql_results:
            component = self._sparql_result_to_component(result)
            search_result = SearchResult(
                component=component,
                relevance_score=0.8,  # High score for pattern matches
                match_type="pattern",
                match_details={"pattern": pattern},
                related_components=[]
            )
            results.append(search_result)
            
        return results
    
    def _search_semantic(self, query: SemanticSearchQuery) -> List[SearchResult]:
        """Search using semantic relationships and properties"""
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module ?property ?value WHERE {{
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module ;
                       ?property ?value .
            
            FILTER(
                CONTAINS(LCASE(STR(?value)), LCASE("{query.query_text}")) ||
                CONTAINS(LCASE(STR(?property)), LCASE("{query.query_text}"))
            )
            
            {self._get_type_filter(query.scope)}
        }}
        ORDER BY ?name
        """
        
        results = []
        sparql_results = self.knowledge_graph.execute_sparql_query(
            sparql_query,
            query.tenant_id
        )
        
        for result in sparql_results:
            component = self._sparql_result_to_component(result)
            search_result = SearchResult(
                component=component,
                relevance_score=0.6,  # Medium score for semantic matches
                match_type="semantic",
                match_details={
                    "matched_property": result.get("property", ""),
                    "matched_value": result.get("value", "")
                },
                related_components=[]
            )
            results.append(search_result)
            
        return results
    
    def _search_with_llm(self, query: SemanticSearchQuery) -> List[SearchResult]:
        """Enhanced search using LLM for intent understanding"""
        if not self.llm:
            return []
            
        # Get all components first
        all_components = self._get_all_components(query.tenant_id, query.scope)
        
        # Use LLM to understand search intent and match components
        prompt = f"""
        Given the search query: "{query.query_text}"
        
        Find the most relevant architecture components from this list:
        {[comp.name for comp in all_components[:20]]}  # Limit for prompt size
        
        Consider:
        - Semantic similarity
        - Architectural patterns
        - Domain concepts
        - Functional relationships
        
        Return a JSON list of component names with relevance scores (0-1).
        """
        
        try:
            llm_response = self.llm.generate_text(prompt)
            # Parse LLM response and create search results
            # This is a simplified implementation
            results = []
            # Implementation would parse LLM JSON response
            return results
        except Exception:
            return []
    
    def _get_type_filter(self, scope: SearchScope) -> str:
        """Generate SPARQL filter for component types"""
        if scope == SearchScope.ALL:
            return ""
        
        type_mapping = {
            SearchScope.MODULES: "kth:Module",
            SearchScope.USECASES: "kth:UseCase", 
            SearchScope.PORTS: "kth:Port",
            SearchScope.ADAPTERS: "kth:Adapter",
            SearchScope.ENTITIES: "kth:DomainEntity",
            SearchScope.EVENTS: "kth:DomainEvent"
        }
        
        if scope in type_mapping:
            return f"FILTER(?type = {type_mapping[scope]})"
        
        return ""
    
    def _sparql_result_to_component(self, result: Dict[str, Any]) -> ArchitecturalComponent:
        """Convert SPARQL result to ArchitecturalComponent"""
        # This would be implemented based on the actual SPARQL result structure
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
    
    def _get_all_components(self, tenant_id: str, scope: SearchScope) -> List[ArchitecturalComponent]:
        """Get all components for LLM-based search"""
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?component ?type ?name ?module WHERE {{
            ?component a ?type ;
                       rdfs:label ?name ;
                       kth:belongsToModule ?module .
            
            {self._get_type_filter(scope)}
        }}
        ORDER BY ?name
        """
        
        results = []
        sparql_results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        
        for result in sparql_results:
            component = self._sparql_result_to_component(result)
            results.append(component)
            
        return results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate search results"""
        seen_iris = set()
        unique_results = []
        
        for result in results:
            if result.component.iri not in seen_iris:
                seen_iris.add(result.component.iri)
                unique_results.append(result)
                
        return unique_results
    
    def search_by_relationship(
        self, 
        component_iri: str, 
        relationship_type: str,
        tenant_id: str,
        max_depth: int = 3
    ) -> List[SearchResult]:
        """
        Search for components related to a given component
        
        Args:
            component_iri: IRI of the source component
            relationship_type: Type of relationship to follow
            tenant_id: Tenant identifier
            max_depth: Maximum relationship depth to traverse
            
        Returns:
            List of related components
        """
        sparql_query = f"""
        PREFIX kth: <http://kthulu.io/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?related ?type ?name ?module ?distance WHERE {{
            <{component_iri}> kth:{relationship_type}{{1,{max_depth}}} ?related .
            ?related a ?type ;
                     rdfs:label ?name ;
                     kth:belongsToModule ?module .
        }}
        ORDER BY ?distance ?name
        """
        
        results = []
        sparql_results = self.knowledge_graph.execute_sparql_query(sparql_query, tenant_id)
        
        for result in sparql_results:
            component = self._sparql_result_to_component(result)
            search_result = SearchResult(
                component=component,
                relevance_score=1.0 / (result.get("distance", 1) + 1),  # Closer = higher score
                match_type="relationship",
                match_details={
                    "relationship_type": relationship_type,
                    "distance": result.get("distance", 1)
                },
                related_components=[]
            )
            results.append(search_result)
            
        return results