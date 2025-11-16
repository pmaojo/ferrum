"""Kthulu ontology adapter plugin.

Implements the :class:`OntologyAdapter` interface to integrate the
Kthulu ontology service with the PermaGraph infrastructure, providing a
bridge between the domain service and external systems.
"""

from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
from datetime import datetime

from domain.services.kthulu_ontology_service import (
    KthuluOntologyService,
    OntologyValidationResult
)
from domain.services.synchronization_bridge import SynchronizationBridge
from domain.ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader,
    ComponentType
)
from domain.entities.triple import Triple
from domain.entities.validation_report import ValidationReport
from application.ports.ontology_adapter import OntologyAdapter
from application.ports.knowledge_graph_port import KnowledgeGraphPort

logger = logging.getLogger(__name__)


class KthuluOntologyAdapter(OntologyAdapter):
    """Adapter for Kthulu architecture ontology operations"""
    
    def __init__(self, 
                 knowledge_graph_port: Optional[KnowledgeGraphPort] = None,
                 ontology_path: Optional[Path] = None):
        self.knowledge_graph_port = knowledge_graph_port
        self.ontology_loader = KthuluOntologyLoader(ontology_path)
        self.ontology_service = KthuluOntologyService(self.ontology_loader)
        self.sync_bridge = SynchronizationBridge(self.ontology_loader, self.ontology_service)
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the ontology adapter"""
        try:
            success = self.sync_bridge.initialize()
            if success:
                self._initialized = True
                logger.info("Kthulu ontology adapter initialized successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize Kthulu ontology adapter: {e}")
            return False
    
    def load_base_ontology(self, tenant_id: str) -> bool:
        """Load the base Kthulu architecture ontology"""
        if not self._initialized:
            logger.error("Adapter not initialized")
            return False
        
        try:
            # The base ontology is already loaded during initialization
            # Here we could store it in the knowledge graph if needed
            if self.knowledge_graph_port:
                # Export ontology as triples and store
                # This would be the TBox (schema) part
                base_triples = self._export_base_ontology_triples()
                for triple in base_triples:
                    self.knowledge_graph_port.add_triple(tenant_id, triple)
            
            logger.info(f"Base ontology loaded for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load base ontology for tenant {tenant_id}: {e}")
            return False
    
    def import_architecture_graph(self, tenant_id: str, graph_json: Dict) -> List[Triple]:
        """Import architecture from Kthulu CLI JSON and return triples"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            # Use synchronization bridge for full import
            sync_result = self.sync_bridge.sync_full_architecture(
                tenant_id=tenant_id,
                kthulu_graph_json=graph_json,
                version_number=f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_by="system",
                description="Full architecture import via adapter"
            )
            
            if not sync_result.success:
                raise RuntimeError(f"Architecture import failed: {sync_result.error_message}")
            
            # Get triples from import result
            if sync_result.import_result and sync_result.import_result.version:
                snapshot = self.sync_bridge.get_version_snapshot(sync_result.import_result.version.version_id)
                if snapshot:
                    triples = snapshot.triples
                else:
                    # Fallback: generate triples from current state
                    architecture_graph = self.ontology_service.import_architecture_from_json(graph_json)
                    triples = self.ontology_service.export_to_triples(architecture_graph)
            else:
                # Fallback: generate triples from current state
                architecture_graph = self.ontology_service.import_architecture_from_json(graph_json)
                triples = self.ontology_service.export_to_triples(architecture_graph)
            
            # Store in knowledge graph if available
            if self.knowledge_graph_port:
                for triple in triples:
                    self.knowledge_graph_port.add_triple(tenant_id, triple)
            
            logger.info(f"Imported architecture graph for tenant {tenant_id}: {len(triples)} triples")
            return triples
            
        except Exception as e:
            logger.error(f"Failed to import architecture graph for tenant {tenant_id}: {e}")
            raise
    
    def validate_architecture(self, tenant_id: str) -> ValidationReport:
        """Validate the current architecture against Kthulu principles"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            # Perform validation
            validation_result = self.ontology_service.validate_architecture()

            # Run OWL reasoner to detect unsatisfiable classes
            unsat_classes: List[str] = []
            try:
                from owlready2 import sync_reasoner_hermit

                if self.ontology_loader and self.ontology_loader.ontology:
                    sync_reasoner_hermit(self.ontology_loader.ontology)
                    onto = self.ontology_loader.ontology
                    for cls in onto.classes():
                        eq_names = [getattr(c, "name", "") for c in cls.equivalent_to]
                        isa_names = [getattr(c, "name", "") for c in cls.is_a]
                        if "Nothing" in eq_names or "Nothing" in isa_names:
                            unsat_classes.append(cls.name)
            except Exception as reasoner_err:
                logger.warning(f"OWL reasoning skipped or failed: {reasoner_err}")

            # Convert to ValidationReport format
            validation_report = ValidationReport(
                tenant_id=tenant_id,
                is_consistent=validation_result.is_consistent,
                violated_rules=validation_result.violations,
                unsat_classes=unsat_classes,
                repair_suggestions=[v.suggested_fix for v in validation_result.violations],
                explanation=self._generate_validation_explanation(validation_result),
                timestamp=validation_result.validation_timestamp,
                metadata={
                    'components_count': validation_result.components_count,
                    'relationships_count': validation_result.relationships_count,
                    'ontology_type': 'kthulu_architecture'
                }
            )

            logger.info(f"Architecture validation completed for tenant {tenant_id}")
            return validation_report
            
        except Exception as e:
            logger.error(f"Architecture validation failed for tenant {tenant_id}: {e}")
            raise
    
    def sync_incremental_changes(self, tenant_id: str, delta: Dict) -> ValidationReport:
        """Sync incremental changes and validate"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            # Use synchronization bridge for incremental sync
            sync_result = self.sync_bridge.sync_incremental_changes(
                tenant_id=tenant_id,
                kthulu_graph_json=delta,
                version_number=f"incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_by="system",
                prefer_code_as_truth=True,
                validate_delta=True,
                validate_after_sync=True
            )
            
            if not sync_result.success:
                raise RuntimeError(f"Incremental sync failed: {sync_result.error_message}")
            
            # Return validation report from sync result
            if sync_result.validation_report:
                validation_report = sync_result.validation_report
            else:
                # Fallback: perform validation manually
                validation_report = self.validate_architecture(tenant_id)
            
            # Store triples in knowledge graph if available
            if self.knowledge_graph_port and sync_result.import_result and sync_result.import_result.version:
                snapshot = self.sync_bridge.get_version_snapshot(sync_result.import_result.version.version_id)
                if snapshot:
                    for triple in snapshot.triples:
                        self.knowledge_graph_port.add_triple(tenant_id, triple)
            
            logger.info(f"Incremental sync completed for tenant {tenant_id}: {sync_result.conflicts_resolved} conflicts resolved")
            return validation_report
            
        except Exception as e:
            logger.error(f"Incremental sync failed for tenant {tenant_id}: {e}")
            raise
    
    def export_react_flow_format(self, tenant_id: str) -> Dict[str, Any]:
        """Export current architecture in React Flow format"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            current_graph = self.ontology_service._current_graph
            if not current_graph:
                return {'nodes': [], 'edges': []}
            
            # Convert components to React Flow nodes
            nodes = []
            for component in current_graph.components:
                node = {
                    'id': component.iri,
                    'type': self._map_component_type_to_node_type(component.component_type),
                    'data': {
                        'label': component.name,
                        'namespace': component.namespace,
                        'componentType': component.component_type.value,
                        'layer': component.layer.value if component.layer else None,
                        'properties': component.properties
                    },
                    'position': {'x': 0, 'y': 0}  # Position would be calculated by layout algorithm
                }
                nodes.append(node)
            
            # Convert relationships to React Flow edges
            edges = []
            for relationship in current_graph.relationships:
                edge = {
                    'id': f"{relationship.subject_iri}-{relationship.object_iri}",
                    'source': relationship.subject_iri,
                    'target': relationship.object_iri,
                    'type': relationship.relationship_type,
                    'data': {
                        'relationshipType': relationship.relationship_type,
                        'predicate': relationship.predicate_iri
                    }
                }
                edges.append(edge)
            
            result = {
                'nodes': nodes,
                'edges': edges,
                'metadata': current_graph.metadata
            }
            
            logger.info(f"Exported React Flow format for tenant {tenant_id}: {len(nodes)} nodes, {len(edges)} edges")
            return result
            
        except Exception as e:
            logger.error(f"Failed to export React Flow format for tenant {tenant_id}: {e}")
            raise
    
    def export_rdf_turtle(self, tenant_id: str) -> str:
        """Export current architecture as RDF Turtle"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        try:
            turtle_output = self.ontology_service.export_to_turtle()
            logger.info(f"Exported RDF Turtle for tenant {tenant_id}")
            return turtle_output
            
        except Exception as e:
            logger.error(f"Failed to export RDF Turtle for tenant {tenant_id}: {e}")
            raise
    
    def get_ontology_statistics(self, tenant_id: str) -> Dict[str, int]:
        """Get statistics about the ontology"""
        if not self._initialized:
            return {}
        
        return self.ontology_service.get_ontology_statistics()
    
    def get_component_by_name(self, tenant_id: str, name: str,
                            component_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a component by name"""
        if not self._initialized:
            return None
        
        try:
            comp_type = ComponentType(component_type) if component_type else None
            component = self.ontology_service.get_component_by_name(name, comp_type)
            
            if component:
                return {
                    'iri': component.iri,
                    'name': component.name,
                    'type': component.component_type.value,
                    'namespace': component.namespace,
                    'layer': component.layer.value if component.layer else None,
                    'properties': component.properties
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get component by name for tenant {tenant_id}: {e}")
            return None
    
    def _export_base_ontology_triples(self) -> List[Triple]:
        """Export the base ontology schema as triples"""
        # This would export the TBox (schema) part of the ontology
        # For now, return empty list - in full implementation would parse OWL file
        return []
    
    def _generate_validation_explanation(self, validation_result: OntologyValidationResult) -> str:
        """Generate a human-readable explanation of validation results"""
        if validation_result.is_consistent:
            return f"Architecture is consistent with {validation_result.components_count} components and {validation_result.relationships_count} relationships."
        
        error_count = len([v for v in validation_result.violations if v.severity == "ERROR"])
        warning_count = len([v for v in validation_result.violations if v.severity == "WARNING"])
        
        explanation = f"Architecture validation found {error_count} errors and {warning_count} warnings. "
        
        if error_count > 0:
            explanation += "Critical violations include dependency inversion principle breaches. "
        
        if warning_count > 0:
            explanation += "Warnings include module isolation concerns. "
        
        explanation += "Review the detailed violations for specific remediation steps."
        
        return explanation
    
    def validate_delta_before_sync(self, tenant_id: str, graph_json: Dict) -> ValidationReport:
        """Validate a delta before applying it"""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        
        return self.sync_bridge.validate_delta_before_sync(tenant_id, graph_json)
    
    def get_sync_history(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get synchronization history for a tenant"""
        if not self._initialized:
            return []
        
        versions = self.sync_bridge.get_sync_history(tenant_id)
        return [version.to_dict() for version in versions]
    
    def get_sync_statistics(self, tenant_id: str) -> Dict[str, int]:
        """Get synchronization statistics for a tenant"""
        if not self._initialized:
            return {}
        
        return self.sync_bridge.get_sync_statistics(tenant_id)

    def detect_conflicts(self, tenant_id: str, graph_json: Dict) -> List[Dict[str, Any]]:
        """Detect potential conflicts between code and ontology"""
        if not self._initialized:
            return []
        
        conflicts = self.sync_bridge.detect_conflicts(tenant_id, graph_json)
        return [
            {
                'conflict_type': conflict.conflict_type,
                'resolution_strategy': conflict.resolution_strategy,
                'description': conflict.description,
                'metadata': conflict.metadata
            }
            for conflict in conflicts
        ]

    def get_module_triples(self, module: str) -> List[Dict[str, Any]]:
        """Return triples that belong to the given module."""
        if not self._initialized:
            return []

        current_graph = self.ontology_service._current_graph
        if not current_graph:
            return []

        triples = self.ontology_service.export_to_triples(current_graph)
        module_triples = [t.to_dict() for t in triples if f"{module}." in t.subject or f"{module}." in t.object]
        return module_triples
    
    def _map_component_type_to_node_type(self, component_type: ComponentType) -> str:
        """Map component type to React Flow node type"""
        type_mapping = {
            ComponentType.MODULE: 'module',
            ComponentType.USECASE: 'usecase',
            ComponentType.PORT: 'port',
            ComponentType.ADAPTER: 'adapter',
            ComponentType.DOMAIN_ENTITY: 'entity',
            ComponentType.DOMAIN_EVENT: 'event'
        }
        return type_mapping.get(component_type, 'default')
