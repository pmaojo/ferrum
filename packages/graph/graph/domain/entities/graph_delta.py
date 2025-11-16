"""
Graph Delta Entity

Represents changes between two versions of an architecture graph.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
from enum import Enum

from .triple import Triple
from ..ontology.kthulu_ontology_loader import ArchitecturalComponent, ArchitecturalRelationship


class ChangeType(Enum):
    """Types of changes in a graph delta"""
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"


@dataclass
class ComponentChange:
    """Represents a change to an architectural component"""
    change_type: ChangeType
    component: ArchitecturalComponent
    previous_component: Optional[ArchitecturalComponent] = None
    changed_properties: Optional[Set[str]] = None
    
    def __post_init__(self):
        if self.changed_properties is None:
            self.changed_properties = set()


@dataclass
class RelationshipChange:
    """Represents a change to an architectural relationship"""
    change_type: ChangeType
    relationship: ArchitecturalRelationship
    previous_relationship: Optional[ArchitecturalRelationship] = None


@dataclass
class GraphDelta:
    """Represents the difference between two architecture graphs"""
    source_version: str
    target_version: str
    component_changes: List[ComponentChange]
    relationship_changes: List[RelationshipChange]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def has_changes(self) -> bool:
        """Check if delta contains any changes"""
        return len(self.component_changes) > 0 or len(self.relationship_changes) > 0
    
    @property
    def added_components(self) -> List[ArchitecturalComponent]:
        """Get all added components"""
        return [change.component for change in self.component_changes 
                if change.change_type == ChangeType.ADDED]
    
    @property
    def removed_components(self) -> List[ArchitecturalComponent]:
        """Get all removed components"""
        return [change.component for change in self.component_changes 
                if change.change_type == ChangeType.REMOVED]
    
    @property
    def modified_components(self) -> List[ArchitecturalComponent]:
        """Get all modified components"""
        return [change.component for change in self.component_changes 
                if change.change_type == ChangeType.MODIFIED]
    
    @property
    def added_relationships(self) -> List[ArchitecturalRelationship]:
        """Get all added relationships"""
        return [change.relationship for change in self.relationship_changes 
                if change.change_type == ChangeType.ADDED]
    
    @property
    def removed_relationships(self) -> List[ArchitecturalRelationship]:
        """Get all removed relationships"""
        return [change.relationship for change in self.relationship_changes 
                if change.change_type == ChangeType.REMOVED]
    
    @property
    def modified_relationships(self) -> List[ArchitecturalRelationship]:
        """Get all modified relationships"""
        return [change.relationship for change in self.relationship_changes 
                if change.change_type == ChangeType.MODIFIED]
    
    def get_affected_component_iris(self) -> Set[str]:
        """Get IRIs of all components affected by this delta"""
        iris = set()
        
        for change in self.component_changes:
            iris.add(change.component.iri)
            if change.previous_component:
                iris.add(change.previous_component.iri)
        
        for change in self.relationship_changes:
            iris.add(change.relationship.subject_iri)
            iris.add(change.relationship.object_iri)
            if change.previous_relationship:
                iris.add(change.previous_relationship.subject_iri)
                iris.add(change.previous_relationship.object_iri)
        
        return iris
    
    def to_summary(self) -> str:
        """Generate a human-readable summary of the delta"""
        added_comps = len(self.added_components)
        removed_comps = len(self.removed_components)
        modified_comps = len(self.modified_components)
        added_rels = len(self.added_relationships)
        removed_rels = len(self.removed_relationships)
        modified_rels = len(self.modified_relationships)
        
        summary_parts = []
        
        if added_comps > 0:
            summary_parts.append(f"{added_comps} components added")
        if removed_comps > 0:
            summary_parts.append(f"{removed_comps} components removed")
        if modified_comps > 0:
            summary_parts.append(f"{modified_comps} components modified")
        if added_rels > 0:
            summary_parts.append(f"{added_rels} relationships added")
        if removed_rels > 0:
            summary_parts.append(f"{removed_rels} relationships removed")
        if modified_rels > 0:
            summary_parts.append(f"{modified_rels} relationships modified")
        
        if not summary_parts:
            return "No changes detected"
        
        return ", ".join(summary_parts)


@dataclass
class ConflictResolution:
    """Represents a conflict resolution strategy"""
    conflict_type: str
    resolution_strategy: str  # "PREFER_CODE", "PREFER_ONTOLOGY", "MERGE", "MANUAL"
    description: str
    resolved_component: Optional[ArchitecturalComponent] = None
    resolved_relationship: Optional[ArchitecturalRelationship] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}