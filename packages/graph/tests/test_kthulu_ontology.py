"""
Tests for Kthulu Architecture Ontology Implementation
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json

from domain.ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader, 
    ArchitecturalComponent, 
    ArchitecturalRelationship,
    ComponentType,
    LayerType,
    create_sample_architecture
)
from domain.services.kthulu_ontology_service import (
    KthuluOntologyService,
    ArchitectureGraph
)
from plugins.ontology.kthulu_adapter import KthuluOntologyAdapter


class TestKthuluOntologyLoader:
    """Test the ontology loader functionality"""
    
    def test_create_component_iri(self):
        """Test IRI creation for components"""
        loader = KthuluOntologyLoader()
        
        iri = loader.create_component_iri(
            ComponentType.USECASE, 
            "LoginUser", 
            "auth"
        )
        
        expected = "http://kthulu.io/ontology#auth.UseCase.LoginUser"
        assert iri == expected
    
    def test_create_relationship_iri(self):
        """Test IRI creation for relationships"""
        loader = KthuluOntologyLoader()
        
        iri = loader.create_relationship_iri("definesUseCase")
        expected = "http://kthulu.io/ontology#definesUseCase"
        assert iri == expected
    
    def test_validate_dip_rule(self):
        """Test DIP rule validation"""
        loader = KthuluOntologyLoader()
        
        # Create components with DIP violation
        domain_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.UseCase.LoginUser",
            component_type=ComponentType.USECASE,
            name="LoginUser",
            namespace="auth"
        )
        
        infra_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.Adapter.PostgresRepo",
            component_type=ComponentType.ADAPTER,
            name="PostgresRepo",
            namespace="auth"
        )
        
        # Create violating relationship
        violation_relationship = ArchitecturalRelationship(
            subject_iri=domain_component.iri,
            predicate_iri="http://kthulu.io/ontology#calls",
            object_iri=infra_component.iri,
            relationship_type="calls"
        )
        
        violations = loader.validate_dip_rule(
            [domain_component, infra_component],
            [violation_relationship]
        )
        
        assert len(violations) == 1
        assert "DIP Violation" in violations[0]
        assert "LoginUser" in violations[0]
        assert "PostgresRepo" in violations[0]
    
    def test_validate_module_isolation(self):
        """Test module isolation validation"""
        loader = KthuluOntologyLoader()
        
        # Create components from different modules
        auth_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.UseCase.LoginUser",
            component_type=ComponentType.USECASE,
            name="LoginUser",
            namespace="auth"
        )
        
        user_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#user.Entity.User",
            component_type=ComponentType.DOMAIN_ENTITY,
            name="User",
            namespace="user"
        )
        
        # Create cross-module relationship (not through port)
        cross_module_relationship = ArchitecturalRelationship(
            subject_iri=auth_component.iri,
            predicate_iri="http://kthulu.io/ontology#uses",
            object_iri=user_component.iri,
            relationship_type="uses"
        )
        
        violations = loader.validate_module_isolation(
            [auth_component, user_component],
            [cross_module_relationship]
        )
        
        assert len(violations) == 1
        assert "Module Isolation Violation" in violations[0]
    
    def test_export_turtle(self):
        """Test Turtle export functionality"""
        loader = KthuluOntologyLoader()
        components, relationships = create_sample_architecture()
        
        turtle_output = loader.export_turtle(components, relationships)
        
        assert "@prefix kth: <http://kthulu.io/ontology#>" in turtle_output
        assert "rdf:type kth:Module" in turtle_output
        assert "kth:hasName" in turtle_output
        assert "kth:definesUseCase" in turtle_output


class TestKthuluOntologyService:
    """Test the ontology service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_loader = Mock(spec=KthuluOntologyLoader)
        self.mock_loader.load_ontology.return_value = True
        self.service = KthuluOntologyService(self.mock_loader)
    
    def test_initialize_success(self):
        """Test successful initialization"""
        result = self.service.initialize()
        
        assert result is True
        assert self.service._is_loaded is True
        self.mock_loader.load_ontology.assert_called_once()
    
    def test_initialize_failure(self):
        """Test initialization failure"""
        self.mock_loader.load_ontology.return_value = False
        
        result = self.service.initialize()
        
        assert result is False
        assert self.service._is_loaded is False
    
    def test_import_architecture_from_json(self):
        """Test importing architecture from JSON"""
        self.service._is_loaded = True
        
        # Mock the IRI creation
        self.mock_loader.create_component_iri.side_effect = lambda ct, name, ns: f"http://kthulu.io/ontology#{ns}.{ct.value}.{name}"
        self.mock_loader.create_relationship_iri.side_effect = lambda rt: f"http://kthulu.io/ontology#{rt}"
        
        # Sample JSON from Kthulu CLI
        architecture_json = {
            "nodes": [
                {
                    "name": "auth",
                    "type": "module",
                    "module": "auth",
                    "file_path": "internal/modules/auth",
                    "description": "Authentication module"
                },
                {
                    "name": "LoginUser",
                    "type": "usecase",
                    "module": "auth",
                    "file_path": "internal/modules/auth/usecase/login_user.go"
                }
            ],
            "edges": [
                {
                    "from": "auth",
                    "to": "LoginUser",
                    "type": "definesUseCase"
                }
            ],
            "version": "1.0"
        }
        
        result = self.service.import_architecture_from_json(architecture_json)
        
        assert isinstance(result, ArchitectureGraph)
        assert len(result.components) == 2
        assert len(result.relationships) == 1
        assert result.metadata['source'] == 'kthulu-cli'
        assert result.metadata['version'] == '1.0'
    
    def test_validate_architecture(self):
        """Test architecture validation"""
        self.service._is_loaded = True
        
        # Create a mock graph
        components, relationships = create_sample_architecture()
        self.service._current_graph = ArchitectureGraph(
            components=components,
            relationships=relationships,
            metadata={}
        )
        
        # Mock validation methods
        self.mock_loader.validate_dip_rule.return_value = []
        self.mock_loader.validate_module_isolation.return_value = []
        
        result = self.service.validate_architecture()
        
        assert result.is_consistent is True
        assert len(result.violations) == 0
        assert result.components_count == len(components)
        assert result.relationships_count == len(relationships)
    
    def test_export_to_triples(self):
        """Test exporting to triples"""
        self.service._is_loaded = True
        
        # Create a simple graph
        components = [
            ArchitecturalComponent(
                iri="http://kthulu.io/ontology#auth.Module.auth",
                component_type=ComponentType.MODULE,
                name="auth",
                namespace="auth"
            )
        ]
        
        self.service._current_graph = ArchitectureGraph(
            components=components,
            relationships=[],
            metadata={}
        )
        
        triples = self.service.export_to_triples()
        
        assert len(triples) >= 3  # At least type, name, and namespace triples
        
        # Check for type assertion
        type_triple = next((t for t in triples if t.predicate.endswith("#type")), None)
        assert type_triple is not None
        assert type_triple.object.endswith("#Module")


class TestKthuluOntologyAdapter:
    """Test the ontology adapter functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_kg_port = Mock()
        self.adapter = KthuluOntologyAdapter(
            knowledge_graph_port=self.mock_kg_port
        )
    
    @patch('adapters.ontology.kthulu_ontology_adapter.KthuluOntologyService')
    def test_initialize_success(self, mock_service_class):
        """Test successful adapter initialization"""
        mock_service = Mock()
        mock_service.initialize.return_value = True
        mock_service_class.return_value = mock_service
        
        adapter = KthuluOntologyAdapter()
        result = adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
    
    def test_import_architecture_graph(self):
        """Test importing architecture graph"""
        # Mock the service
        mock_service = Mock()
        mock_graph = Mock()
        mock_triples = [Mock(), Mock()]
        
        mock_service.import_architecture_from_json.return_value = mock_graph
        mock_service.export_to_triples.return_value = mock_triples
        
        self.adapter.ontology_service = mock_service
        self.adapter._initialized = True
        
        graph_json = {"nodes": [], "edges": []}
        result = self.adapter.import_architecture_graph("tenant1", graph_json)
        
        assert result == mock_triples
        mock_service.import_architecture_from_json.assert_called_once_with(graph_json)
        mock_service.export_to_triples.assert_called_once_with(mock_graph)
    
    def test_export_react_flow_format(self):
        """Test exporting to React Flow format"""
        # Create mock graph
        component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.Module.auth",
            component_type=ComponentType.MODULE,
            name="auth",
            namespace="auth"
        )
        
        relationship = ArchitecturalRelationship(
            subject_iri="http://kthulu.io/ontology#auth.Module.auth",
            predicate_iri="http://kthulu.io/ontology#definesUseCase",
            object_iri="http://kthulu.io/ontology#auth.UseCase.LoginUser",
            relationship_type="definesUseCase"
        )
        
        mock_graph = ArchitectureGraph(
            components=[component],
            relationships=[relationship],
            metadata={"version": "1.0"}
        )
        
        # Mock the service
        mock_service = Mock()
        mock_service._current_graph = mock_graph
        
        self.adapter.ontology_service = mock_service
        self.adapter._initialized = True
        
        result = self.adapter.export_react_flow_format("tenant1")
        
        assert 'nodes' in result
        assert 'edges' in result
        assert 'metadata' in result
        assert len(result['nodes']) == 1
        assert len(result['edges']) == 1
        assert result['nodes'][0]['data']['label'] == 'auth'
        assert result['edges'][0]['type'] == 'definesUseCase'

    @patch('owlready2.sync_reasoner_hermit', lambda ontology: None)
    def test_validate_architecture_unsat_classes(self):
        """Ensure unsatisfiable classes are reported"""
        # Prepare minimal loaded adapter
        self.adapter.ontology_loader.load_ontology()
        self.adapter._initialized = True
        self.adapter.ontology_service._is_loaded = True
        self.adapter.ontology_service._current_graph = ArchitectureGraph(
            components=[], relationships=[], metadata={}
        )

        # Create an intentionally unsatisfiable class
        from owlready2 import Thing, Nothing

        onto = self.adapter.ontology_loader.ontology
        with onto:
            class BadClass(Thing):
                equivalent_to = [Nothing]

        report = self.adapter.validate_architecture("tenant1")
        assert len(report.unsat_classes) > 0
        assert "BadClass" in report.unsat_classes


if __name__ == "__main__":
    # Run a simple test to verify the ontology file exists and is valid
    loader = KthuluOntologyLoader()
    
    print("Testing Kthulu Ontology Implementation...")
    
    # Test ontology file exists
    ontology_path = Path(__file__).parent.parent / "domain" / "ontology" / "kthulu_architecture.owl"
    print(f"Ontology file exists: {ontology_path.exists()}")
    
    # Test sample architecture creation
    components, relationships = create_sample_architecture()
    print(f"Sample architecture: {len(components)} components, {len(relationships)} relationships")
    
    # Test validation
    dip_violations = loader.validate_dip_rule(components, relationships)
    print(f"DIP violations: {len(dip_violations)}")
    
    # Test Turtle export
    turtle_output = loader.export_turtle(components, relationships)
    print(f"Turtle export length: {len(turtle_output)} characters")
    
    print("Basic tests completed successfully!")