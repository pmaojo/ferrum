"""
Kthulu Graph Importer

Service for importing and converting Kthulu CLI JSON output to OWL/RDF format
with support for incremental synchronization and conflict resolution.
"""

from typing import Dict, List, Optional, Tuple, Set
import logging
import hashlib
import json
from datetime import datetime
from dataclasses import dataclass

from ..ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader,
    ArchitecturalComponent,
    ArchitecturalRelationship,
    ComponentType
)
from ..entities.graph_delta import (
    GraphDelta,
    ComponentChange,
    RelationshipChange,
    ChangeType,
    ConflictResolution
)
from ..entities.ontology_version import OntologyVersion, VersionSnapshot, VersionStatus
from ..entities.triple import Triple
from ..entities.validation_report import ValidationReport
from ..exceptions import GraphRAGException

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a graph import operation"""
    success: bool
    components_imported: int
    relationships_imported: int
    triples_generated: int
    conflicts_resolved: int
    delta: Optional[GraphDelta] = None
    version: Optional[OntologyVersion] = None
    error_message: Optional[str] = None


class KthuluGraphImporter:
    """Service for importing Kthulu architecture graphs with versioning and conflict resolution"""
    
    def __init__(self, ontology_loader: Optional[KthuluOntologyLoader] = None):
        self.ontology_loader = ontology_loader or KthuluOntologyLoader()
        self._current_components: Dict[str, ArchitecturalComponent] = {}
        self._current_relationships: Dict[str, ArchitecturalRelationship] = {}
        self._version_history: Dict[str, OntologyVersion] = {}
        
    def import_full_graph(self, 
                         tenant_id: str,
                         graph_json: Dict,
                         version_number: str,
                         created_by: str,
                         description: Optional[str] = None) -> ImportResult:
        """
        Import a complete architecture graph from Kthulu CLI JSON
        
        Args:
            tenant_id: Tenant identifier
            graph_json: JSON output from kthulu-cli plan --graph --format=json
            version_number: Version identifier for this import
            created_by: User who initiated the import
            description: Optional description of this version
        """
        try:
            logger.info(f"Starting full graph import for tenant {tenant_id}, version {version_number}")
            
            # Parse components and relationships from JSON
            components, relationships = self._parse_kthulu_json(graph_json)
            
            # Generate triples
            triples = self._generate_triples(components, relationships)
            
            # Create version
            version = OntologyVersion(
                version_id=self._generate_version_id(tenant_id, version_number),
                tenant_id=tenant_id,
                version_number=version_number,
                status=VersionStatus.ACTIVE,
                created_at=datetime.now(),
                created_by=created_by,
                description=description,
                triples_count=len(triples),
                components_count=len(components),
                relationships_count=len(relationships),
                checksum=self._calculate_checksum(graph_json),
                metadata={
                    'source': 'kthulu-cli',
                    'import_type': 'full',
                    'kthulu_version': graph_json.get('version', 'unknown')
                }
            )
            
            # Update current state
            self._current_components = {comp.iri: comp for comp in components}
            self._current_relationships = {self._relationship_key(rel): rel for rel in relationships}
            self._version_history[version.version_id] = version
            
            result = ImportResult(
                success=True,
                components_imported=len(components),
                relationships_imported=len(relationships),
                triples_generated=len(triples),
                conflicts_resolved=0,
                version=version
            )
            
            logger.info(f"Full graph import completed successfully: {result.components_imported} components, {result.relationships_imported} relationships")
            return result
            
        except Exception as e:
            logger.error(f"Full graph import failed for tenant {tenant_id}: {e}")
            return ImportResult(
                success=False,
                components_imported=0,
                relationships_imported=0,
                triples_generated=0,
                conflicts_resolved=0,
                error_message=str(e)
            )
    
    def import_incremental_changes(self,
                                 tenant_id: str,
                                 graph_json: Dict,
                                 version_number: str,
                                 created_by: str,
                                 parent_version_id: Optional[str] = None,
                                 prefer_code_as_truth: bool = True) -> ImportResult:
        """
        Import incremental changes using delta comparison
        
        Args:
            tenant_id: Tenant identifier
            graph_json: Updated JSON from kthulu-cli
            version_number: New version identifier
            created_by: User who initiated the import
            parent_version_id: Previous version to compare against
            prefer_code_as_truth: Whether to prefer code over existing ontology in conflicts
        """
        try:
            logger.info(f"Starting incremental import for tenant {tenant_id}, version {version_number}")
            
            # Parse new components and relationships
            new_components, new_relationships = self._parse_kthulu_json(graph_json)
            
            # Calculate delta
            delta = self._calculate_delta(
                self._current_components,
                self._current_relationships,
                new_components,
                new_relationships,
                parent_version_id or "current",
                version_number
            )
            
            # Resolve conflicts if any
            conflicts_resolved = 0
            if delta.has_changes:
                conflicts_resolved = self._resolve_conflicts(delta, prefer_code_as_truth)
            
            # Apply changes
            self._apply_delta(delta)
            
            # Generate triples for changed components only
            affected_components = [comp for comp in new_components 
                                 if comp.iri in delta.get_affected_component_iris()]
            affected_relationships = [rel for rel in new_relationships
                                    if rel.subject_iri in delta.get_affected_component_iris() or
                                       rel.object_iri in delta.get_affected_component_iris()]
            
            triples = self._generate_triples(affected_components, affected_relationships)
            
            # Create new version
            version = OntologyVersion(
                version_id=self._generate_version_id(tenant_id, version_number),
                tenant_id=tenant_id,
                version_number=version_number,
                status=VersionStatus.ACTIVE,
                created_at=datetime.now(),
                created_by=created_by,
                parent_version_id=parent_version_id,
                triples_count=len(triples),
                components_count=len(new_components),
                relationships_count=len(new_relationships),
                checksum=self._calculate_checksum(graph_json),
                metadata={
                    'source': 'kthulu-cli',
                    'import_type': 'incremental',
                    'delta_summary': delta.to_summary(),
                    'conflicts_resolved': conflicts_resolved,
                    'prefer_code_as_truth': prefer_code_as_truth
                }
            )
            
            self._version_history[version.version_id] = version
            
            result = ImportResult(
                success=True,
                components_imported=len(delta.added_components) + len(delta.modified_components),
                relationships_imported=len(delta.added_relationships) + len(delta.modified_relationships),
                triples_generated=len(triples),
                conflicts_resolved=conflicts_resolved,
                delta=delta,
                version=version
            )
            
            logger.info(f"Incremental import completed: {delta.to_summary()}, {conflicts_resolved} conflicts resolved")
            return result
            
        except Exception as e:
            logger.error(f"Incremental import failed for tenant {tenant_id}: {e}")
            return ImportResult(
                success=False,
                components_imported=0,
                relationships_imported=0,
                triples_generated=0,
                conflicts_resolved=0,
                error_message=str(e)
            )
    
    def validate_delta(self, delta: GraphDelta) -> ValidationReport:
        """
        Validate a delta before applying it
        
        Args:
            delta: The delta to validate
            
        Returns:
            ValidationReport with validation results
        """
        try:
            logger.info(f"Validating delta: {delta.to_summary()}")
            
            # Create temporary state with delta applied
            temp_components = self._current_components.copy()
            temp_relationships = self._current_relationships.copy()
            
            # Apply delta to temporary state
            for change in delta.component_changes:
                if change.change_type == ChangeType.ADDED:
                    temp_components[change.component.iri] = change.component
                elif change.change_type == ChangeType.REMOVED:
                    temp_components.pop(change.component.iri, None)
                elif change.change_type == ChangeType.MODIFIED:
                    temp_components[change.component.iri] = change.component
            
            for change in delta.relationship_changes:
                rel_key = self._relationship_key(change.relationship)
                if change.change_type == ChangeType.ADDED:
                    temp_relationships[rel_key] = change.relationship
                elif change.change_type == ChangeType.REMOVED:
                    temp_relationships.pop(rel_key, None)
                elif change.change_type == ChangeType.MODIFIED:
                    temp_relationships[rel_key] = change.relationship
            
            # Validate temporary state
            components_list = list(temp_components.values())
            relationships_list = list(temp_relationships.values())
            
            violations = []
            
            # Validate DIP rule
            dip_violations = self.ontology_loader.validate_dip_rule(components_list, relationships_list)
            violations.extend(dip_violations)
            
            # Validate module isolation
            isolation_violations = self.ontology_loader.validate_module_isolation(components_list, relationships_list)
            violations.extend(isolation_violations)
            
            # Create validation report
            from ..entities.validation_report import ValidationReport, RuleViolation, RepairSuggestion
            
            rule_violations = []
            for violation in violations:
                rule_violations.append(RuleViolation(
                    rule_id="DELTA_VALIDATION",
                    violated_constraint=violation,
                    violating_components=[],
                    severity="ERROR" if "DIP" in violation else "WARNING",
                    description=violation,
                    repair_suggestion=RepairSuggestion(
                        action="Review delta changes",
                        description="Examine the proposed changes for architectural violations",
                        confidence=0.8
                    )
                ))
            
            report = ValidationReport(
                tenant_id=delta.metadata.get('tenant_id', 'unknown'),
                is_consistent=len(rule_violations) == 0,
                violated_rules=rule_violations,
                unsat_classes=[],
                repair_suggestions=[v.repair_suggestion.action for v in rule_violations],
                explanation=f"Delta validation completed. {len(rule_violations)} violations found.",
                metadata={
                    'validation_type': 'delta',
                    'delta_summary': delta.to_summary(),
                    'components_affected': len(delta.get_affected_component_iris())
                }
            )
            
            logger.info(f"Delta validation completed: {len(rule_violations)} violations found")
            return report
            
        except Exception as e:
            logger.error(f"Delta validation failed: {e}")
            raise GraphRAGException(f"Delta validation failed: {e}", "DELTA_VALIDATION_FAILED")
    
    def get_version_history(self, tenant_id: str) -> List[OntologyVersion]:
        """Get version history for a tenant"""
        return [version for version in self._version_history.values() 
                if version.tenant_id == tenant_id]
    
    def get_version_snapshot(self, version_id: str) -> Optional[VersionSnapshot]:
        """Get a complete snapshot of a specific version"""
        version = self._version_history.get(version_id)
        if not version:
            return None
        
        # For now, return current state - in full implementation would restore from storage
        triples = self._generate_triples(
            list(self._current_components.values()),
            list(self._current_relationships.values())
        )
        
        return VersionSnapshot(
            version=version,
            triples=triples,
            architecture_json=None,  # Would be stored in full implementation
            validation_report=None   # Would be stored in full implementation
        )
    
    def _parse_kthulu_json(self, graph_json: Dict) -> Tuple[List[ArchitecturalComponent], List[ArchitecturalRelationship]]:
        """Parse Kthulu CLI JSON into components and relationships"""
        components = []
        relationships = []
        
        # Parse nodes (components)
        nodes = graph_json.get('nodes', [])
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
                        'description': node.get('description', ''),
                        'source_hash': node.get('hash', '')
                    }
                )
                components.append(component)
        
        # Parse edges (relationships)
        edges = graph_json.get('edges', [])
        for edge in edges:
            relationship_type = edge.get('type', 'dependsOn')
            relationship = ArchitecturalRelationship(
                subject_iri=self._find_component_iri(components, edge.get('from', '')),
                predicate_iri=self.ontology_loader.create_relationship_iri(relationship_type),
                object_iri=self._find_component_iri(components, edge.get('to', '')),
                relationship_type=relationship_type
            )
            relationships.append(relationship)
        
        return components, relationships
    
    def _calculate_delta(self,
                        current_components: Dict[str, ArchitecturalComponent],
                        current_relationships: Dict[str, ArchitecturalRelationship],
                        new_components: List[ArchitecturalComponent],
                        new_relationships: List[ArchitecturalRelationship],
                        source_version: str,
                        target_version: str) -> GraphDelta:
        """Calculate delta between current and new state"""
        
        new_components_dict = {comp.iri: comp for comp in new_components}
        new_relationships_dict = {self._relationship_key(rel): rel for rel in new_relationships}
        
        component_changes = []
        relationship_changes = []
        
        # Find component changes
        # Added components
        for iri, component in new_components_dict.items():
            if iri not in current_components:
                component_changes.append(ComponentChange(
                    change_type=ChangeType.ADDED,
                    component=component
                ))
        
        # Removed components
        for iri, component in current_components.items():
            if iri not in new_components_dict:
                component_changes.append(ComponentChange(
                    change_type=ChangeType.REMOVED,
                    component=component
                ))
        
        # Modified components
        for iri, new_component in new_components_dict.items():
            if iri in current_components:
                current_component = current_components[iri]
                if self._components_differ(current_component, new_component):
                    changed_properties = self._get_changed_properties(current_component, new_component)
                    component_changes.append(ComponentChange(
                        change_type=ChangeType.MODIFIED,
                        component=new_component,
                        previous_component=current_component,
                        changed_properties=changed_properties
                    ))
        
        # Find relationship changes
        # Added relationships
        for key, relationship in new_relationships_dict.items():
            if key not in current_relationships:
                relationship_changes.append(RelationshipChange(
                    change_type=ChangeType.ADDED,
                    relationship=relationship
                ))
        
        # Removed relationships
        for key, relationship in current_relationships.items():
            if key not in new_relationships_dict:
                relationship_changes.append(RelationshipChange(
                    change_type=ChangeType.REMOVED,
                    relationship=relationship
                ))
        
        return GraphDelta(
            source_version=source_version,
            target_version=target_version,
            component_changes=component_changes,
            relationship_changes=relationship_changes,
            timestamp=datetime.now(),
            metadata={
                'calculation_method': 'iri_based_diff',
                'total_changes': len(component_changes) + len(relationship_changes)
            }
        )
    
    def _resolve_conflicts(self, delta: GraphDelta, prefer_code_as_truth: bool) -> int:
        """
        Resolve conflicts in the delta based on resolution strategy
        
        Args:
            delta: The delta containing potential conflicts
            prefer_code_as_truth: Whether to prefer code over existing ontology
            
        Returns:
            Number of conflicts resolved
        """
        conflicts_resolved = 0
        
        # For now, we implement simple conflict resolution
        # In a more sophisticated implementation, we would detect actual conflicts
        # and apply resolution strategies
        
        if prefer_code_as_truth:
            # When preferring code as truth, we accept all changes from the code
            # This is the default behavior, so no additional resolution needed
            logger.info("Using 'prefer code as truth' conflict resolution strategy")
        else:
            # When not preferring code, we would need more sophisticated logic
            # to determine which changes to accept or reject
            logger.warning("Non-code-preferred conflict resolution not fully implemented")
        
        return conflicts_resolved
    
    def _apply_delta(self, delta: GraphDelta) -> None:
        """Apply a delta to the current state"""
        
        # Apply component changes
        for change in delta.component_changes:
            if change.change_type == ChangeType.ADDED:
                self._current_components[change.component.iri] = change.component
            elif change.change_type == ChangeType.REMOVED:
                self._current_components.pop(change.component.iri, None)
            elif change.change_type == ChangeType.MODIFIED:
                self._current_components[change.component.iri] = change.component
        
        # Apply relationship changes
        for change in delta.relationship_changes:
            rel_key = self._relationship_key(change.relationship)
            if change.change_type == ChangeType.ADDED:
                self._current_relationships[rel_key] = change.relationship
            elif change.change_type == ChangeType.REMOVED:
                self._current_relationships.pop(rel_key, None)
            elif change.change_type == ChangeType.MODIFIED:
                self._current_relationships[rel_key] = change.relationship
    
    def _generate_triples(self, components: List[ArchitecturalComponent], 
                         relationships: List[ArchitecturalRelationship]) -> List[Triple]:
        """Generate RDF triples from components and relationships"""
        triples = []
        
        # Generate component triples
        for component in components:
            # Type assertion
            triples.append(Triple(
                subject=component.iri,
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object=f"http://kthulu.io/ontology#{component.component_type.value}"
            ))
            
            # Properties
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
            
            # Additional properties
            for prop_name, prop_value in component.properties.items():
                if prop_value:  # Only add non-empty properties
                    triples.append(Triple(
                        subject=component.iri,
                        predicate=f"http://kthulu.io/ontology#{prop_name}",
                        object=str(prop_value)
                    ))
        
        # Generate relationship triples
        for relationship in relationships:
            triples.append(Triple(
                subject=relationship.subject_iri,
                predicate=relationship.predicate_iri,
                object=relationship.object_iri
            ))
        
        return triples
    
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
    
    def _relationship_key(self, relationship: ArchitecturalRelationship) -> str:
        """Generate a unique key for a relationship"""
        return f"{relationship.subject_iri}|{relationship.predicate_iri}|{relationship.object_iri}"
    
    def _components_differ(self, comp1: ArchitecturalComponent, comp2: ArchitecturalComponent) -> bool:
        """Check if two components differ"""
        return (comp1.name != comp2.name or 
                comp1.namespace != comp2.namespace or
                comp1.component_type != comp2.component_type or
                comp1.properties != comp2.properties)
    
    def _get_changed_properties(self, old_comp: ArchitecturalComponent, 
                               new_comp: ArchitecturalComponent) -> Set[str]:
        """Get the set of properties that changed between two components"""
        changed = set()
        
        if old_comp.name != new_comp.name:
            changed.add('name')
        if old_comp.namespace != new_comp.namespace:
            changed.add('namespace')
        if old_comp.component_type != new_comp.component_type:
            changed.add('component_type')
        
        # Check properties
        old_props = old_comp.properties or {}
        new_props = new_comp.properties or {}
        
        all_prop_keys = set(old_props.keys()) | set(new_props.keys())
        for key in all_prop_keys:
            if old_props.get(key) != new_props.get(key):
                changed.add(f'properties.{key}')
        
        return changed
    
    def _generate_version_id(self, tenant_id: str, version_number: str) -> str:
        """Generate a unique version ID"""
        return f"{tenant_id}_{version_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _calculate_checksum(self, data: Dict) -> str:
        """Calculate checksum for data integrity"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()