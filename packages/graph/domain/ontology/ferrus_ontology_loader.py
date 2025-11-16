"""Ferrus Architecture Ontology Loader

Defines component types and layer classifications for the Ferrus
hexagonal architecture used in Rust projects."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ComponentType(Enum):
    """Enumeration of Ferrus architecture component types."""

    MODULE = "Module"
    USECASE = "UseCase"
    PORT = "Port"
    ADAPTER = "Adapter"
    DOMAIN_ENTITY = "DomainEntity"
    DOMAIN_EVENT = "DomainEvent"
    HANDLER = "Handler"
    SERVICE = "Service"


class LayerType(Enum):
    """Enumeration of architectural layers in Ferrus."""

    DOMAIN = "DomainComponent"
    APPLICATION = "ApplicationComponent"
    INFRASTRUCTURE = "InfrastructureComponent"


@dataclass
class ArchitecturalComponent:
    """Represents a component in the Ferrus architecture."""

    iri: str
    component_type: ComponentType
    name: str
    namespace: str
    layer: Optional[LayerType] = None
    properties: Dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.properties is None:
            self.properties = {}

        if self.component_type in [ComponentType.DOMAIN_ENTITY, ComponentType.DOMAIN_EVENT]:
            self.layer = LayerType.DOMAIN
        elif self.component_type in [ComponentType.USECASE, ComponentType.SERVICE, ComponentType.PORT]:
            self.layer = LayerType.APPLICATION
        elif self.component_type in [ComponentType.ADAPTER, ComponentType.HANDLER]:
            self.layer = LayerType.INFRASTRUCTURE


class FerrusOntologyLoader:
    """Utility for creating IRIs for Ferrus ontology entities."""

    NAMESPACE = "http://ferrus.io/ontology#"

    def create_component_iri(self, component_type: ComponentType, name: str, namespace: str) -> str:
        """Create a unique IRI for a component."""
        return f"{self.NAMESPACE}{namespace}.{component_type.value}.{name}"

    def create_relationship_iri(self, relationship_type: str) -> str:
        """Create an IRI for a relationship type."""
        return f"{self.NAMESPACE}{relationship_type}"
