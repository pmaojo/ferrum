"""Ontology adapter interface.

Defines the contract that all ontology integration plugins must
implement in order to work with PermaGraph. The adapter exposes
operations for loading ontologies, importing architecture graphs and
exporting data in multiple formats.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from domain.entities.triple import Triple
from domain.entities.validation_report import ValidationReport


class OntologyAdapter(ABC):
    """Abstract adapter for ontology management operations."""
    
    @abstractmethod
    def load_base_ontology(self, tenant_id: str) -> bool:
        """Load the base ontology schema"""
        ...
    
    @abstractmethod
    def import_architecture_graph(self, tenant_id: str, graph_json: Dict) -> List[Triple]:
        """Import architecture from JSON and return triples"""
        ...
    
    @abstractmethod
    def validate_architecture(self, tenant_id: str) -> ValidationReport:
        """Validate the current architecture"""
        ...
    
    @abstractmethod
    def sync_incremental_changes(self, tenant_id: str, delta: Dict) -> ValidationReport:
        """Sync incremental changes and validate"""
        ...
    
    @abstractmethod
    def export_react_flow_format(self, tenant_id: str) -> Dict[str, Any]:
        """Export current architecture in React Flow format"""
        ...
    
    @abstractmethod
    def export_rdf_turtle(self, tenant_id: str) -> str:
        """Export current architecture as RDF Turtle"""
        ...

    @abstractmethod
    def get_module_triples(self, module: str) -> List[Dict[str, Any]]:
        """Return all triples belonging to a specific module."""
        ...
