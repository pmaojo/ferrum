"""
Architectural Component Entity

Represents components in a software architecture including modules,
use cases, ports, adapters, entities, and events.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class ComponentType(Enum):
    """Types of architectural components"""
    MODULE = "module"
    USECASE = "usecase"
    PORT = "port"
    ADAPTER = "adapter"
    ENTITY = "entity"
    EVENT = "event"
    SERVICE = "service"
    REPOSITORY = "repository"
    FACTORY = "factory"
    VALUE_OBJECT = "value_object"


@dataclass
class ComponentRelationship:
    """Relationship between architectural components"""
    source_iri: str
    target_iri: str
    relationship_type: str
    properties: Dict[str, Any]


@dataclass
class ArchitecturalComponent:
    """Represents an architectural component in the system"""
    iri: str
    component_type: ComponentType
    name: str
    module_namespace: str
    properties: Dict[str, Any]
    relationships: List[ComponentRelationship]
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def add_relationship(
        self,
        target_iri: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a relationship to another component"""
        relationship = ComponentRelationship(
            source_iri=self.iri,
            target_iri=target_iri,
            relationship_type=relationship_type,
            properties=properties or {}
        )
        self.relationships.append(relationship)
    
    def get_relationships_by_type(self, relationship_type: str) -> List[ComponentRelationship]:
        """Get all relationships of a specific type"""
        return [r for r in self.relationships if r.relationship_type == relationship_type]
    
    def has_relationship_to(self, target_iri: str, relationship_type: str) -> bool:
        """Check if component has a specific relationship to another component"""
        return any(
            r.target_iri == target_iri and r.relationship_type == relationship_type
            for r in self.relationships
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary representation"""
        return {
            "iri": self.iri,
            "component_type": self.component_type.value,
            "name": self.name,
            "module_namespace": self.module_namespace,
            "description": self.description,
            "properties": self.properties,
            "tags": self.tags,
            "relationships": [
                {
                    "source_iri": r.source_iri,
                    "target_iri": r.target_iri,
                    "relationship_type": r.relationship_type,
                    "properties": r.properties
                }
                for r in self.relationships
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitecturalComponent':
        """Create component from dictionary representation"""
        relationships = [
            ComponentRelationship(
                source_iri=r["source_iri"],
                target_iri=r["target_iri"],
                relationship_type=r["relationship_type"],
                properties=r["properties"]
            )
            for r in data.get("relationships", [])
        ]
        
        return cls(
            iri=data["iri"],
            component_type=ComponentType(data["component_type"]),
            name=data["name"],
            module_namespace=data["module_namespace"],
            description=data.get("description"),
            properties=data.get("properties", {}),
            tags=data.get("tags", []),
            relationships=relationships
        )


def create_component(
    iri: str,
    component_type: ComponentType,
    name: str,
    module_namespace: str,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> ArchitecturalComponent:
    """Factory function to create an architectural component"""
    return ArchitecturalComponent(
        iri=iri,
        component_type=component_type,
        name=name,
        module_namespace=module_namespace,
        description=description,
        properties=properties or {},
        relationships=[],
        tags=tags or []
    )