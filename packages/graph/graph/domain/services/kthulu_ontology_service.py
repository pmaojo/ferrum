"""
Kthulu Ontology Service

This service provides high-level operations for managing the Kthulu architecture ontology
within the PermaGraph system, including validation, reasoning, and synchronization.
"""

from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader, 
    ArchitecturalComponent, 
    ArchitecturalRelationship,
    ComponentType,
    LayerType
)
from ..entities.validation_report import ValidationReport, RuleViolation
from ..entities.triple import Triple
from ..exceptions import GraphRAGException

logger = logging.getLogger(__name__)


@dataclass
class OntologyValidationResult:
    """Result of ontology validation"""
    is_consistent: bool
    violations: List[RuleViolation]
    components_count: int
    relationships_count: int
    validation_timestamp: datetime
    
    
@dataclass
class ArchitectureGraph:
    """Represents the complete architecture graph"""
    components: List[ArchitecturalComponent]
    relationships: List[ArchitecturalRelationship]
    metadata: Dict[str, str]


class KthuluOntologyService:
    """Service for managing Kthulu architecture ontology operations"""
    
    def __init__(self, ontology_loader: Optional[KthuluOntologyLoader] = None):
        self.ontology_loader = ontology_loader or KthuluOntologyLoader()
        self._is_loaded = False
        self._current_graph: Optional[ArchitectureGraph] = None
        
    def initialize(self) -> bool:
        """Initialize the ontology service by loading the base ontology"""
        try:
            success = self.ontology_loader.load_ontology()
            if success:
                self._is_loaded = True
                logger.info("Kthulu ontology service initialized successfully")
            else:
                logger.error("Failed to initialize Kthulu ontology service")
            return success
        except Exception as e:
            logger.error(f"Error initializing ontology service: {e}")
            return False
    
    def import_architecture_from_json(self, architecture_json: Dict) -> ArchitectureGraph:
        """
        Import architecture from Kthulu CLI JSON output
        Expected format from: kthulu-cli plan --graph --format=json
        """
        if not self._is_loaded:
            raise GraphRAGException("Ontology service not initialized", "ONTOLOGY_NOT_INITIALIZED")
        
        try:
            components = []
            relationships = []
            
            # Parse nodes (components)
            nodes = architecture_json.get('nodes', [])
            for node in nodes:
                component_type = self._map_node_type_to_component_type(node.get('type', ''))
                if component_type:
                    component = ArchitecturalComponent(
                        iri=self.ontology_loader.create_component_iri(
                            component_type, 
                            node.get('name', ''), 
                            node.get('module', '')
                        ),
                        component_type=component_type,
                        name=node.get('name', ''),
                        namespace=node.get('module', ''),
                        properties={
                            'file_path': node.get('file_path', ''),
                            'description': node.get('description', '')
                        }
                    )
                    components.append(component)
            
            # Parse edges (relationships)
            edges = architecture_json.get('edges', [])
            for edge in edges:
                relationship_type = edge.get('type', 'dependsOn')
                relationship = ArchitecturalRelationship(
                    subject_iri=self._find_component_iri(components, edge.get('from', '')),
                    predicate_iri=self.ontology_loader.create_relationship_iri(relationship_type),
                    object_iri=self._find_component_iri(components, edge.get('to', '')),
                    relationship_type=relationship_type
                )
                relationships.append(relationship)
            
            # Create architecture graph
            self._current_graph = ArchitectureGraph(
                components=components,
                relationships=relationships,
                metadata={
                    'source': 'kthulu-cli',
                    'import_timestamp': datetime.now().isoformat(),
                    'version': architecture_json.get('version', '1.0')
                }
            )
            
            logger.info(f"Imported architecture with {len(components)} components and {len(relationships)} relationships")
            return self._current_graph
            
        except Exception as e:
            logger.error(f"Failed to import architecture from JSON: {e}")
            raise GraphRAGException(f"Architecture import failed: {e}", "ARCHITECTURE_IMPORT_FAILED")
    
    def validate_architecture(self, graph: Optional[ArchitectureGraph] = None) -> OntologyValidationResult:
        """Validate the architecture against Kthulu principles"""
        if not self._is_loaded:
            raise GraphRAGException("Ontology service not initialized", "ONTOLOGY_NOT_INITIALIZED")
        
        target_graph = graph or self._current_graph
        if not target_graph:
            raise GraphRAGException("No architecture graph available for validation", "NO_ARCHITECTURE_GRAPH")
        
        try:
            violations = []
            
            # Validate Dependency Inversion Principle (DIP)
            dip_violations = self.ontology_loader.validate_dip_rule(
                target_graph.components, 
                target_graph.relationships
            )
            for violation in dip_violations:
                violations.append(RuleViolation(
                    rule_name="Dependency Inversion Principle",
                    violation_type="DIP_VIOLATION",
                    description=violation,
                    severity="ERROR",
                    component_iri="",
                    suggested_fix="Create a port interface to decouple domain from infrastructure"
                ))
            
            # Validate Module Isolation
            isolation_violations = self.ontology_loader.validate_module_isolation(
                target_graph.components,
                target_graph.relationships
            )
            for violation in isolation_violations:
                violations.append(RuleViolation(
                    rule_name="Module Isolation",
                    violation_type="MODULE_ISOLATION_VIOLATION", 
                    description=violation,
                    severity="WARNING",
                    component_iri="",
                    suggested_fix="Access other modules only through their public ports"
                ))
            
            # Additional validations can be added here
            # - Aggregate integrity
            # - Port usage consistency
            # - Event handling patterns
            
            result = OntologyValidationResult(
                is_consistent=len([v for v in violations if v.severity == "ERROR"]) == 0,
                violations=violations,
                components_count=len(target_graph.components),
                relationships_count=len(target_graph.relationships),
                validation_timestamp=datetime.now()
            )
            
            logger.info(f"Architecture validation completed: {len(violations)} violations found")
            return result
            
        except Exception as e:
            logger.error(f"Architecture validation failed: {e}")
            raise GraphRAGException(f"Validation failed: {e}", "VALIDATION_FAILED")
    
    def export_to_triples(self, graph: Optional[ArchitectureGraph] = None) -> List[Triple]:
        """Export architecture graph to RDF triples"""
        if not self._is_loaded:
            raise GraphRAGException("Ontology service not initialized", "ONTOLOGY_NOT_INITIALIZED")
        
        target_graph = graph or self._current_graph
        if not target_graph:
            raise GraphRAGException("No architecture graph available for export", "NO_ARCHITECTURE_GRAPH")
        
        try:
            triples = []
            
            # Export component type assertions
            for component in target_graph.components:
                triples.append(Triple(
                    subject=component.iri,
                    predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    object=f"http://kthulu.io/ontology#{component.component_type.value}"
                ))
                
                # Export component properties
                triples.append(Triple(
                    subject=component.iri,
                    predicate="http://kthulu.io/ontology#hasName",
                    object=component.name
                ))
                
                triples.append(Triple(
                    subject=component.iri,
                    predicate="http://kthulu.io/ontology#hasNamespace", 
                    object=component.namespace
                ))
            
            # Export relationships
            for relationship in target_graph.relationships:
                triples.append(Triple(
                    subject=relationship.subject_iri,
                    predicate=relationship.predicate_iri,
                    object=relationship.object_iri
                ))
            
            logger.info(f"Exported {len(triples)} triples from architecture graph")
            return triples
            
        except Exception as e:
            logger.error(f"Failed to export triples: {e}")
            raise GraphRAGException(f"Triple export failed: {e}", "TRIPLE_EXPORT_FAILED")
    
    def export_to_turtle(self, graph: Optional[ArchitectureGraph] = None) -> str:
        """Export architecture graph to Turtle format"""
        target_graph = graph or self._current_graph
        if not target_graph:
            raise GraphRAGException("No architecture graph available for export", "NO_ARCHITECTURE_GRAPH")
        
        return self.ontology_loader.export_turtle(
            target_graph.components,
            target_graph.relationships
        )
    
    def get_component_by_name(self, name: str, component_type: Optional[ComponentType] = None) -> Optional[ArchitecturalComponent]:
        """Find a component by name and optionally by type"""
        if not self._current_graph:
            return None
        
        for component in self._current_graph.components:
            if component.name == name:
                if component_type is None or component.component_type == component_type:
                    return component
        return None
    
    def get_components_by_module(self, module_namespace: str) -> List[ArchitecturalComponent]:
        """Get all components belonging to a specific module"""
        if not self._current_graph:
            return []
        
        return [comp for comp in self._current_graph.components 
                if comp.namespace == module_namespace]
    
    def get_component_relationships(self, component_iri: str) -> List[ArchitecturalRelationship]:
        """Get all relationships involving a specific component"""
        if not self._current_graph:
            return []
        
        return [rel for rel in self._current_graph.relationships
                if rel.subject_iri == component_iri or rel.object_iri == component_iri]
    
    def _map_node_type_to_component_type(self, node_type: str) -> Optional[ComponentType]:
        """Map Kthulu CLI node types to ontology component types"""
        type_mapping = {
            'module': ComponentType.MODULE,
            'usecase': ComponentType.USECASE,
            'use_case': ComponentType.USECASE,
            'port': ComponentType.PORT,
            'adapter': ComponentType.ADAPTER,
            'entity': ComponentType.DOMAIN_ENTITY,
            'domain_entity': ComponentType.DOMAIN_ENTITY,
            'event': ComponentType.DOMAIN_EVENT,
            'domain_event': ComponentType.DOMAIN_EVENT,
        }
        return type_mapping.get(node_type.lower())
    
    def _find_component_iri(self, components: List[ArchitecturalComponent], component_name: str) -> str:
        """Find component IRI by name"""
        for component in components:
            if component.name == component_name:
                return component.iri
        
        # If not found, create a placeholder IRI
        return f"http://kthulu.io/ontology#unknown.{component_name}"
    
    def get_ontology_statistics(self) -> Dict[str, int]:
        """Get statistics about the current ontology state"""
        if not self._current_graph:
            return {}
        
        stats = {
            'total_components': len(self._current_graph.components),
            'total_relationships': len(self._current_graph.relationships),
        }
        
        # Count by component type
        for component_type in ComponentType:
            count = len([c for c in self._current_graph.components 
                        if c.component_type == component_type])
            stats[f'{component_type.value.lower()}_count'] = count
        
        # Count by layer
        domain_count = len([c for c in self._current_graph.components 
                           if c.layer == LayerType.DOMAIN])
        infrastructure_count = len([c for c in self._current_graph.components 
                                  if c.layer == LayerType.INFRASTRUCTURE])
        
        stats['domain_components'] = domain_count
        stats['infrastructure_components'] = infrastructure_count
        
        return stats