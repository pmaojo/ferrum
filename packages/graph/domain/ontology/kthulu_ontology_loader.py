"""
Kthulu Architecture Ontology Loader

This module provides functionality to load and work with the Kthulu architecture ontology,
including validation rules and semantic reasoning capabilities.
"""

from typing import Dict, List, Optional, Set
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from owlready2 import get_ontology, Thing, ObjectProperty, DataProperty, FunctionalProperty
    from owlready2.namespace import Namespace
    OWLREADY2_AVAILABLE = True
except ImportError:
    OWLREADY2_AVAILABLE = False
    # Create dummy classes for type hints when owlready2 is not available
    class ObjectProperty:
        pass
    class DataProperty:
        pass
    logging.warning("owlready2 not available. Install with: pip install owlready2")

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Enumeration of Kthulu architecture component types"""
    MODULE = "Module"
    USECASE = "UseCase"
    PORT = "Port"
    ADAPTER = "Adapter"
    DOMAIN_ENTITY = "DomainEntity"
    DOMAIN_EVENT = "DomainEvent"


class LayerType(Enum):
    """Enumeration of architectural layers"""
    DOMAIN = "DomainComponent"
    INFRASTRUCTURE = "InfrastructureComponent"


@dataclass
class ArchitecturalComponent:
    """Represents a component in the Kthulu architecture"""
    iri: str
    component_type: ComponentType
    name: str
    namespace: str
    layer: Optional[LayerType] = None
    properties: Dict[str, str] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        
        # Determine layer based on component type
        if self.component_type in [ComponentType.USECASE, ComponentType.PORT, 
                                 ComponentType.DOMAIN_ENTITY, ComponentType.DOMAIN_EVENT]:
            self.layer = LayerType.DOMAIN
        elif self.component_type == ComponentType.ADAPTER:
            self.layer = LayerType.INFRASTRUCTURE


@dataclass
class ArchitecturalRelationship:
    """Represents a relationship between architectural components"""
    subject_iri: str
    predicate_iri: str
    object_iri: str
    relationship_type: str


class KthuluOntologyLoader:
    """Loads and manages the Kthulu architecture ontology"""
    
    NAMESPACE = "http://kthulu.io/ontology#"
    
    def __init__(self, ontology_path: Optional[Path] = None):
        self.ontology_path = ontology_path or self._get_default_ontology_path()
        self.ontology = None
        self.namespace = None
        self._components: Dict[str, ArchitecturalComponent] = {}
        self._relationships: List[ArchitecturalRelationship] = []
        
    def _get_default_ontology_path(self) -> Path:
        """Get the default path to the Kthulu ontology file"""
        current_dir = Path(__file__).parent
        return current_dir / "kthulu_architecture.owl"
    
    def load_ontology(self) -> bool:
        """Load the Kthulu architecture ontology"""
        if not OWLREADY2_AVAILABLE:
            logger.error("Cannot load ontology: owlready2 not available")
            return False
            
        try:
            if not self.ontology_path.exists():
                logger.error(f"Ontology file not found: {self.ontology_path}")
                return False
                
            # Load the ontology
            self.ontology = get_ontology(f"file://{self.ontology_path.absolute()}")
            self.ontology.load()
            
            # Get the namespace
            self.namespace = self.ontology.get_namespace(self.NAMESPACE)
            
            logger.info(f"Successfully loaded Kthulu ontology from {self.ontology_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            return False
    
    def get_classes(self) -> Dict[str, type]:
        """Get all classes defined in the ontology"""
        if not self.ontology:
            return {}
            
        classes = {}
        for cls in self.ontology.classes():
            class_name = cls.name
            classes[class_name] = cls
            
        return classes
    
    def get_object_properties(self) -> Dict[str, ObjectProperty]:
        """Get all object properties defined in the ontology"""
        if not self.ontology:
            return {}
            
        properties = {}
        for prop in self.ontology.object_properties():
            properties[prop.name] = prop
            
        return properties
    
    def get_data_properties(self) -> Dict[str, DataProperty]:
        """Get all data properties defined in the ontology"""
        if not self.ontology:
            return {}
            
        properties = {}
        for prop in self.ontology.data_properties():
            properties[prop.name] = prop
            
        return properties
    
    def validate_dip_rule(self, components: List[ArchitecturalComponent], 
                         relationships: List[ArchitecturalRelationship]) -> List[str]:
        """
        Validate Dependency Inversion Principle (DIP) rule:
        Domain components should not call infrastructure components
        """
        violations = []
        
        for rel in relationships:
            if rel.relationship_type == "calls":
                subject_comp = next((c for c in components if c.iri == rel.subject_iri), None)
                object_comp = next((c for c in components if c.iri == rel.object_iri), None)
                
                if (subject_comp and object_comp and 
                    subject_comp.layer == LayerType.DOMAIN and 
                    object_comp.layer == LayerType.INFRASTRUCTURE):
                    
                    violations.append(
                        f"DIP Violation: Domain component {subject_comp.name} "
                        f"calls infrastructure component {object_comp.name}"
                    )
        
        return violations
    
    def validate_module_isolation(self, components: List[ArchitecturalComponent],
                                relationships: List[ArchitecturalRelationship]) -> List[str]:
        """
        Validate module isolation rule:
        Components should primarily interact within their module boundaries
        """
        violations = []
        
        # Group components by module
        modules = {}
        for comp in components:
            module_name = comp.namespace.split('.')[0] if '.' in comp.namespace else comp.namespace
            if module_name not in modules:
                modules[module_name] = []
            modules[module_name].append(comp)
        
        # Check for cross-module direct dependencies (excluding ports)
        for rel in relationships:
            if rel.relationship_type in ["calls", "uses"]:
                subject_comp = next((c for c in components if c.iri == rel.subject_iri), None)
                object_comp = next((c for c in components if c.iri == rel.object_iri), None)
                
                if (subject_comp and object_comp and 
                    subject_comp.namespace != object_comp.namespace and
                    object_comp.component_type != ComponentType.PORT):
                    
                    violations.append(
                        f"Module Isolation Violation: {subject_comp.name} from module "
                        f"{subject_comp.namespace} directly accesses {object_comp.name} "
                        f"from module {object_comp.namespace}"
                    )
        
        return violations
    
    def create_component_iri(self, component_type: ComponentType, name: str, 
                           namespace: str) -> str:
        """Create a unique IRI for a component"""
        return f"{self.NAMESPACE}{namespace}.{component_type.value}.{name}"
    
    def create_relationship_iri(self, relationship_type: str) -> str:
        """Create an IRI for a relationship type"""
        return f"{self.NAMESPACE}{relationship_type}"
    
    def export_turtle(self, components: List[ArchitecturalComponent],
                     relationships: List[ArchitecturalRelationship]) -> str:
        """Export components and relationships as Turtle RDF"""
        turtle_lines = [
            "@prefix kth: <http://kthulu.io/ontology#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            ""
        ]
        
        # Export components
        for comp in components:
            turtle_lines.extend([
                f"<{comp.iri}> rdf:type kth:{comp.component_type.value} ;",
                f"    kth:hasName \"{comp.name}\" ;",
                f"    kth:hasNamespace \"{comp.namespace}\" .",
                ""
            ])
        
        # Export relationships
        for rel in relationships:
            predicate = rel.predicate_iri.split('#')[-1]
            turtle_lines.extend([
                f"<{rel.subject_iri}> kth:{predicate} <{rel.object_iri}> .",
                ""
            ])
        
        return "\n".join(turtle_lines)


# Validation rules as OWL restrictions (for reference)
DIP_VALIDATION_RULE = """
# DIP Rule: Domain components cannot call infrastructure components
kth:DomainComponent rdfs:subClassOf [
    rdf:type owl:Restriction ;
    owl:onProperty kth:calls ;
    owl:allValuesFrom [
        rdf:type owl:Class ;
        owl:complementOf kth:InfrastructureComponent
    ]
] .
"""

MODULE_ISOLATION_RULE = """
# Module Isolation Rule: Use cases should only use entities from their own module
kth:UseCase rdfs:subClassOf [
    rdf:type owl:Restriction ;
    owl:onProperty kth:usesEntity ;
    owl:allValuesFrom [
        rdf:type owl:Restriction ;
        owl:onProperty kth:belongsToModule ;
        owl:hasSelf true
    ]
] .
"""


def create_sample_architecture() -> tuple[List[ArchitecturalComponent], List[ArchitecturalRelationship]]:
    """Create a sample architecture for testing"""
    loader = KthuluOntologyLoader()
    
    components = [
        # Auth module
        ArchitecturalComponent(
            iri=loader.create_component_iri(ComponentType.MODULE, "auth", "auth"),
            component_type=ComponentType.MODULE,
            name="auth",
            namespace="auth"
        ),
        ArchitecturalComponent(
            iri=loader.create_component_iri(ComponentType.USECASE, "LoginUser", "auth"),
            component_type=ComponentType.USECASE,
            name="LoginUser",
            namespace="auth"
        ),
        ArchitecturalComponent(
            iri=loader.create_component_iri(ComponentType.PORT, "UserRepository", "auth"),
            component_type=ComponentType.PORT,
            name="UserRepository",
            namespace="auth"
        ),
        ArchitecturalComponent(
            iri=loader.create_component_iri(ComponentType.ADAPTER, "PostgresUserRepository", "auth"),
            component_type=ComponentType.ADAPTER,
            name="PostgresUserRepository",
            namespace="auth"
        ),
    ]
    
    relationships = [
        ArchitecturalRelationship(
            subject_iri=loader.create_component_iri(ComponentType.MODULE, "auth", "auth"),
            predicate_iri=loader.create_relationship_iri("definesUseCase"),
            object_iri=loader.create_component_iri(ComponentType.USECASE, "LoginUser", "auth"),
            relationship_type="definesUseCase"
        ),
        ArchitecturalRelationship(
            subject_iri=loader.create_component_iri(ComponentType.USECASE, "LoginUser", "auth"),
            predicate_iri=loader.create_relationship_iri("usesPort"),
            object_iri=loader.create_component_iri(ComponentType.PORT, "UserRepository", "auth"),
            relationship_type="usesPort"
        ),
        ArchitecturalRelationship(
            subject_iri=loader.create_component_iri(ComponentType.ADAPTER, "PostgresUserRepository", "auth"),
            predicate_iri=loader.create_relationship_iri("implementsPort"),
            object_iri=loader.create_component_iri(ComponentType.PORT, "UserRepository", "auth"),
            relationship_type="implementsPort"
        ),
    ]
    
    return components, relationships


if __name__ == "__main__":
    # Example usage
    loader = KthuluOntologyLoader()
    
    if loader.load_ontology():
        logger.info("Ontology loaded successfully!")

        classes = loader.get_classes()
        logger.info("Found %d classes:", len(classes))
        for name, cls in classes.items():
            logger.info("  - %s", name)

        properties = loader.get_object_properties()
        logger.info("Found %d object properties:", len(properties))
        for name, prop in properties.items():
            logger.info("  - %s", name)

        # Test with sample architecture
        components, relationships = create_sample_architecture()

        # Validate DIP rule
        dip_violations = loader.validate_dip_rule(components, relationships)
        logger.info("DIP violations: %d", len(dip_violations))
        for violation in dip_violations:
            logger.info("  - %s", violation)

        # Export as Turtle
        turtle_output = loader.export_turtle(components, relationships)
        logger.info("Turtle export:")
        logger.info(turtle_output)
    else:
        logger.error("Failed to load ontology")