"""
Tests for Kthulu Graph Importer

Tests the core functionality of importing Kthulu CLI JSON and converting to OWL/RDF.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from domain.services.kthulu_graph_importer import KthuluGraphImporter, ImportResult
from domain.ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader,
    ArchitecturalComponent,
    ArchitecturalRelationship,
    ComponentType
)
from domain.entities.graph_delta import GraphDelta, ComponentChange, ChangeType
from domain.entities.ontology_version import OntologyVersion, VersionStatus


class TestKthuluGraphImporter:
    """Test cases for KthuluGraphImporter"""
    
    @pytest.fixture
    def mock_ontology_loader(self):
        """Mock ontology loader"""
        loader = Mock(spec=KthuluOntologyLoader)
        loader.create_component_iri.side_effect = lambda comp_type, name, namespace: f"http://kthulu.io/ontology#{namespace}.{comp_type.value}.{name}"
        loader.create_relationship_iri.side_effect = lambda rel_type: f"http://kthulu.io/ontology#{rel_type}"
        loader.validate_dip_rule.return_value = []
        loader.validate_module_isolation.return_value = []
        return loader
    
    @pytest.fixture
    def graph_importer(self, mock_ontology_loader):
        """Create graph importer with mocked dependencies"""
        return KthuluGraphImporter(mock_ontology_loader)
    
    @pytest.fixture
    def sample_kthulu_json(self):
        """Sample Kthulu CLI JSON output"""
        return {
            "version": "1.0",
            "nodes": [
                {
                    "name": "auth",
                    "type": "module",
                    "module": "auth",
                    "file_path": "internal/modules/auth",
                    "description": "Authentication module",
                    "hash": "abc123"
                },
                {
                    "name": "LoginUser",
                    "type": "usecase",
                    "module": "auth",
                    "file_path": "internal/modules/auth/usecase/login_user.go",
                    "description": "Login user use case",
                    "hash": "def456"
                },
                {
                    "name": "UserRepository",
                    "type": "port",
                    "module": "auth",
                    "file_path": "internal/modules/auth/ports/user_repository.go",
                    "description": "User repository port",
                    "hash": "ghi789"
                }
            ],
            "edges": [
                {
                    "from": "auth",
                    "to": "LoginUser",
                    "type": "definesUseCase"
                },
                {
                    "from": "LoginUser",
                    "to": "UserRepository",
                    "type": "usesPort"
                }
            ]
        }
    
    def test_parse_kthulu_json(self, graph_importer, sample_kthulu_json):
        """Test parsing Kthulu CLI JSON"""
        components, relationships = graph_importer._parse_kthulu_json(sample_kthulu_json)
        
        assert len(components) == 3
        assert len(relationships) == 2
        
        # Check components
        auth_module = next(c for c in components if c.name == "auth")
        assert auth_module.component_type == ComponentType.MODULE
        assert auth_module.namespace == "auth"
        assert auth_module.properties["file_path"] == "internal/modules/auth"
        assert auth_module.properties["source_hash"] == "abc123"
        
        login_usecase = next(c for c in components if c.name == "LoginUser")
        assert login_usecase.component_type == ComponentType.USECASE
        assert login_usecase.namespace == "auth"
        
        user_repo_port = next(c for c in components if c.name == "UserRepository")
        assert user_repo_port.component_type == ComponentType.PORT
        assert user_repo_port.namespace == "auth"
        
        # Check relationships
        defines_rel = next(r for r in relationships if r.relationship_type == "definesUseCase")
        assert "auth.Module.auth" in defines_rel.subject_iri
        assert "auth.UseCase.LoginUser" in defines_rel.object_iri
        
        uses_rel = next(r for r in relationships if r.relationship_type == "usesPort")
        assert "auth.UseCase.LoginUser" in uses_rel.subject_iri
        assert "auth.Port.UserRepository" in uses_rel.object_iri
    
    def test_full_import_success(self, graph_importer, sample_kthulu_json):
        """Test successful full import"""
        result = graph_importer.import_full_graph(
            tenant_id="test_tenant",
            graph_json=sample_kthulu_json,
            version_number="1.0",
            created_by="test_user",
            description="Test import"
        )
        
        assert result.success == True
        assert result.components_imported == 3
        assert result.relationships_imported == 2
        assert result.triples_generated > 0
        assert result.version is not None
        assert result.version.version_number == "1.0"
        assert result.version.tenant_id == "test_tenant"
        assert result.version.status == VersionStatus.ACTIVE
    
    def test_incremental_import_with_changes(self, graph_importer, sample_kthulu_json):
        """Test incremental import with changes"""
        # First, do a full import
        graph_importer.import_full_graph(
            tenant_id="test_tenant",
            graph_json=sample_kthulu_json,
            version_number="1.0",
            created_by="test_user"
        )
        
        # Now modify the JSON to add a new component
        modified_json = sample_kthulu_json.copy()
        modified_json["nodes"].append({
            "name": "PostgresUserRepository",
            "type": "adapter",
            "module": "auth",
            "file_path": "internal/modules/auth/adapters/postgres_user_repository.go",
            "description": "Postgres user repository adapter",
            "hash": "jkl012"
        })
        modified_json["edges"].append({
            "from": "PostgresUserRepository",
            "to": "UserRepository",
            "type": "implementsPort"
        })
        
        # Do incremental import
        result = graph_importer.import_incremental_changes(
            tenant_id="test_tenant",
            graph_json=modified_json,
            version_number="2.0",
            created_by="test_user",
            parent_version_id="test_tenant_1.0_*"
        )
        
        assert result.success == True
        assert result.delta is not None
        assert len(result.delta.added_components) == 1
        assert len(result.delta.added_relationships) == 1
        
        # Check the added component
        added_component = result.delta.added_components[0]
        assert added_component.name == "PostgresUserRepository"
        assert added_component.component_type == ComponentType.ADAPTER
    
    def test_delta_calculation(self, graph_importer, sample_kthulu_json):
        """Test delta calculation between two states"""
        # Parse initial state
        components1, relationships1 = graph_importer._parse_kthulu_json(sample_kthulu_json)
        current_components = {comp.iri: comp for comp in components1}
        current_relationships = {graph_importer._relationship_key(rel): rel for rel in relationships1}
        
        # Create modified state
        modified_json = sample_kthulu_json.copy()
        # Remove one component
        modified_json["nodes"] = [n for n in modified_json["nodes"] if n["name"] != "UserRepository"]
        # Add new component
        modified_json["nodes"].append({
            "name": "EmailService",
            "type": "adapter",
            "module": "auth",
            "file_path": "internal/modules/auth/adapters/email_service.go",
            "description": "Email service adapter"
        })
        
        components2, relationships2 = graph_importer._parse_kthulu_json(modified_json)
        
        # Calculate delta
        delta = graph_importer._calculate_delta(
            current_components,
            current_relationships,
            components2,
            relationships2,
            "v1",
            "v2"
        )
        
        assert delta.has_changes == True
        assert len(delta.added_components) == 1
        assert len(delta.removed_components) == 1
        
        # Check added component
        added_comp = delta.added_components[0]
        assert added_comp.name == "EmailService"
        assert added_comp.component_type == ComponentType.ADAPTER
        
        # Check removed component
        removed_comp = delta.removed_components[0]
        assert removed_comp.name == "UserRepository"
        assert removed_comp.component_type == ComponentType.PORT
    
    def test_generate_triples(self, graph_importer, sample_kthulu_json):
        """Test triple generation from components and relationships"""
        components, relationships = graph_importer._parse_kthulu_json(sample_kthulu_json)
        triples = graph_importer._generate_triples(components, relationships)
        
        assert len(triples) > 0
        
        # Check that we have type assertions for each component
        type_triples = [t for t in triples if t.predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"]
        assert len(type_triples) == 3  # One for each component
        
        # Check that we have name properties
        name_triples = [t for t in triples if t.predicate == "http://kthulu.io/ontology#hasName"]
        assert len(name_triples) == 3
        
        # Check that we have namespace properties
        namespace_triples = [t for t in triples if t.predicate == "http://kthulu.io/ontology#hasNamespace"]
        assert len(namespace_triples) == 3
        
        # Check relationship triples
        relationship_triples = [t for t in triples if "definesUseCase" in t.predicate or "usesPort" in t.predicate]
        assert len(relationship_triples) == 2
    
    def test_validate_delta(self, graph_importer, sample_kthulu_json):
        """Test delta validation"""
        # Create a delta with potential violations
        components, relationships = graph_importer._parse_kthulu_json(sample_kthulu_json)
        
        # Create a delta that adds a component
        new_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.Adapter.TestAdapter",
            component_type=ComponentType.ADAPTER,
            name="TestAdapter",
            namespace="auth"
        )
        
        delta = GraphDelta(
            source_version="v1",
            target_version="v2",
            component_changes=[
                ComponentChange(
                    change_type=ChangeType.ADDED,
                    component=new_component
                )
            ],
            relationship_changes=[],
            timestamp=datetime.now(),
            metadata={'tenant_id': 'test_tenant'}
        )
        
        # Validate the delta
        validation_report = graph_importer.validate_delta(delta)
        
        assert validation_report is not None
        assert validation_report.tenant_id == "test_tenant"
        # Since we're not adding any violations, it should be consistent
        assert validation_report.is_consistent == True
    
    def test_version_management(self, graph_importer, sample_kthulu_json):
        """Test version management functionality"""
        # Import first version
        result1 = graph_importer.import_full_graph(
            tenant_id="test_tenant",
            graph_json=sample_kthulu_json,
            version_number="1.0",
            created_by="user1"
        )
        
        # Import second version
        result2 = graph_importer.import_full_graph(
            tenant_id="test_tenant",
            graph_json=sample_kthulu_json,
            version_number="2.0",
            created_by="user2"
        )
        
        # Get version history
        history = graph_importer.get_version_history("test_tenant")
        assert len(history) == 2
        
        # Check versions
        version_numbers = [v.version_number for v in history]
        assert "1.0" in version_numbers
        assert "2.0" in version_numbers
        
        # Get snapshot
        snapshot = graph_importer.get_version_snapshot(result1.version.version_id)
        assert snapshot is not None
        assert snapshot.version.version_number == "1.0"
        assert len(snapshot.triples) > 0
    
    def test_checksum_calculation(self, graph_importer, sample_kthulu_json):
        """Test checksum calculation for data integrity"""
        checksum1 = graph_importer._calculate_checksum(sample_kthulu_json)
        checksum2 = graph_importer._calculate_checksum(sample_kthulu_json)
        
        # Same data should produce same checksum
        assert checksum1 == checksum2
        
        # Different data should produce different checksum
        modified_json = sample_kthulu_json.copy()
        modified_json["version"] = "2.0"
        checksum3 = graph_importer._calculate_checksum(modified_json)
        
        assert checksum1 != checksum3
    
    def test_component_comparison(self, graph_importer):
        """Test component comparison for change detection"""
        comp1 = ArchitecturalComponent(
            iri="http://test.com/comp1",
            component_type=ComponentType.MODULE,
            name="test",
            namespace="test",
            properties={"prop1": "value1"}
        )
        
        comp2 = ArchitecturalComponent(
            iri="http://test.com/comp1",
            component_type=ComponentType.MODULE,
            name="test",
            namespace="test",
            properties={"prop1": "value1"}
        )
        
        comp3 = ArchitecturalComponent(
            iri="http://test.com/comp1",
            component_type=ComponentType.MODULE,
            name="test_modified",
            namespace="test",
            properties={"prop1": "value1"}
        )
        
        # Same components should not differ
        assert graph_importer._components_differ(comp1, comp2) == False
        
        # Different components should differ
        assert graph_importer._components_differ(comp1, comp3) == True
        
        # Check changed properties
        changed_props = graph_importer._get_changed_properties(comp1, comp3)
        assert "name" in changed_props


if __name__ == "__main__":
    pytest.main([__file__])