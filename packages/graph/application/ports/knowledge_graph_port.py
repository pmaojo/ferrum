"""
Knowledge Graph Port

Abstract interface for knowledge graph operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from domain.entities.triple import Triple


class KnowledgeGraphPort(ABC):
    """Port for knowledge graph storage and retrieval operations"""
    
    @abstractmethod
    def add_triple(self, tenant_id: str, triple: Triple) -> bool:
        """Add a triple to the knowledge graph"""
        ...
    
    @abstractmethod
    def remove_triple(self, tenant_id: str, triple: Triple) -> bool:
        """Remove a triple from the knowledge graph"""
        ...
    
    @abstractmethod
    def query_triples(self, tenant_id: str, subject: Optional[str] = None,
                     predicate: Optional[str] = None, object: Optional[str] = None) -> List[Triple]:
        """Query triples by pattern"""
        ...
    
    @abstractmethod
    def execute_sparql(self, tenant_id: str, query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query"""
        ...
    
    @abstractmethod
    def clear_graph(self, tenant_id: str) -> bool:
        """Clear all triples for a tenant"""
        ...
