"""
Tests for Synchronization Bridge Service

Tests the integration between Kthulu architecture and PermaGraph ontology
with focus on incremental synchronization and conflict resolution.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from domain.services.synchronization_bridge import SynchronizationBridge, SyncResult
from domain.services.kthulu_graph_importer import KthuluGraphImporter, ImportResult
from domain.services.kthulu_ontology_service import KthuluOntologyService
from domain.ontology.kthulu_ontology_loader import (
    KthuluOntologyLoader, 
    ArchitecturalComponent, 
    ComponentType
)
from domain.entities.graph_delta import GraphDelta, ComponentChange, ChangeType
from domain.entities.ontology_version import OntologyVersion, VersionStatus
from domain.entities.validation_report import ValidationReport, RuleViolation, RepairSuggestion


class TestSynchronizationBridge:
    """Test cases for SynchronizationBridge"""
    
    @pytest.fixture
    def mock_ontology_loader(self):
        """Mock ontology loader"""
        loader = Mock(spec=KthuluOntologyLoader)
        loader.load_ontology.return_value = True
        loader.create_component_iri.return_value = "http://kthulu.io/ontology#test.Module.auth"
        loader.create_relationship_iri.return_value = "http://kthulu.io/ontology#definesUseCase"
        return loader
    
    @pytest.fixture
    def mock_ontology_service(self, mock_ontology_loader):
        """Mock ontology service"""
        service = Mock(spec=KthuluOntologyService)
        service.initialize.return_value = True
        return service
    
    @pytest.fixture
    def sync_bridge(self, mock_ontology_loader, mock_ontology_service):
        """Create synchronization bridge with mocked dependencies"""
        bridge = SynchronizationBridge(
            ontology_loader=mock_ontology_loader,
            ontology_service=mock_ontology_service
        )
        return bridge
    
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
                    "description": "Authentication module"
                },
                {
                    "name": "LoginUser",
                    "type": "usecase",
                    "module": "auth",
                    "file_path": "internal/modules/auth/usecase/login_user.go",
                    "description": "Login user use case"
                }
            ],
            "edges": [
                {
                    "from": "auth",
                    "to": "LoginUser",
                    "type": "definesUseCase"
                }
            ]
        }
    
    def test_initialization_success(self, sync_bridge):
        """Test successful initialization"""
        assert sync_bridge.initialize() == True
        assert sync_bridge._initialized == True
    
    def test_initialization_failure(self, mock_ontology_loader):
        """Test initialization failure"""
        mock_ontology_service = Mock(spec=KthuluOntologyService)
        mock_ontology_service.initialize.return_value = False
        
        bridge = SynchronizationBridge(
            ontology_loader=mock_ontology_loader,
            ontology_service=mock_ontology_service
        )
        
        assert bridge.initialize() == False
        assert bridge._initialized == False
    
    def test_full_sync_success(self, sync_bridge, sample_kthulu_json):
        """Test successful full synchronization"""
        # Initialize bridge
        sync_bridge.initialize()
        
        # Mock successful import
        mock_version = OntologyVersion(
            version_id="test_v1",
            tenant_id="test_tenant",
            version_number="1.0",
            status=VersionStatus.ACTIVE,
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        mock_import_result = ImportResult(
            success=True,
            components_imported=2,
            relationships_imported=1,
            triples_generated=6,
            conflicts_resolved=0,
            version=mock_version
        )
        
        with patch.object(sync_bridge.graph_importer, 'import_full_graph', return_value=mock_import_result):
            result = sync_bridge.sync_full_architecture(
                tenant_id="test_tenant",
                kthulu_graph_json=sample_kthulu_json,
                version_number="1.0",
                created_by="test_user"
            )
        
        assert result.success == True
        assert result.sync_type == "full"
        assert result.import_result == mock_import_result
        assert result.conflicts_resolved == 0
    
    def test_full_sync_with_validation(self, sync_bridge, sample_kthulu_json):
        """Test full sync with validation enabled"""
        sync_bridge.initialize()
        
        # Mock import result
        mock_version = OntologyVersion(
            version_id="test_v1",
            tenant_id="test_tenant", 
            version_number="1.0",
            status=VersionStatus.ACTIVE,
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        mock_import_result = ImportResult(
            success=True,
            components_imported=2,
            relationships_imported=1,
            triples_generated=6,
            conflicts_resolved=0,
            version=mock_version
        )
        
        # Mock validation result
        from domain.services.kthulu_ontology_service import OntologyValidationResult
        mock_validation_result = OntologyValidationResult(
            is_consistent=True,
            violations=[],
            components_count=2,
            relationships_count=1,
            validation_timestamp=datetime.now()
        )
        
        with patch.object(sync_bridge.graph_importer, 'import_full_graph', return_value=mock_import_result), \
             patch.object(sync_bridge.ontology_service, 'import_architecture_from_json'), \
             patch.object(sync_bridge.ontology_service, 'validate_architecture', return_value=mock_validation_result):
            
            result = sync_bridge.sync_full_architecture(
                tenant_id="test_tenant",
                kthulu_graph_json=sample_kthulu_json,
                version_number="1.0",
                created_by="test_user",
                validate_after_sync=True
            )
        
        assert result.success == True
        assert result.validation_report is not None
        assert result.validation_report.is_consistent == True
    
    def test_incremental_sync_success(self, sync_bridge, sample_kthulu_json):
        """Test successful incremental synchronization"""
        sync_bridge.initialize()
        
        # Mock delta
        mock_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.Module.auth",
            component_type=ComponentType.MODULE,
            name="auth",
            namespace="auth"
        )
        
        mock_delta = GraphDelta(
            source_version="v1",
            target_version="v2",
            component_changes=[
                ComponentChange(
                    change_type=ChangeType.ADDED,
                    component=mock_component
                )
            ],
            relationship_changes=[],
            timestamp=datetime.now()
        )
        
        mock_version = OntologyVersion(
            version_id="test_v2",
            tenant_id="test_tenant",
            version_number="2.0", 
            status=VersionStatus.ACTIVE,
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        mock_import_result = ImportResult(
            success=True,
            components_imported=1,
            relationships_imported=0,
            triples_generated=3,
            conflicts_resolved=0,
            delta=mock_delta,
            version=mock_version
        )
        
        with patch.object(sync_bridge.graph_importer, 'import_incremental_changes', return_value=mock_import_result):
            result = sync_bridge.sync_incremental_changes(
                tenant_id="test_tenant",
                kthulu_graph_json=sample_kthulu_json,
                version_number="2.0",
                created_by="test_user"
            )
        
        assert result.success == True
        assert result.sync_type == "incremental"
        assert result.import_result.delta is not None
        assert len(result.import_result.delta.component_changes) == 1
    
    def test_incremental_sync_with_conflicts(self, sync_bridge, sample_kthulu_json):
        """Test incremental sync with conflict resolution"""
        sync_bridge.initialize()
        
        mock_import_result = ImportResult(
            success=True,
            components_imported=1,
            relationships_imported=0,
            triples_generated=3,
            conflicts_resolved=2  # Conflicts were resolved
        )
        
        with patch.object(sync_bridge.graph_importer, 'import_incremental_changes', return_value=mock_import_result):
            result = sync_bridge.sync_incremental_changes(
                tenant_id="test_tenant",
                kthulu_graph_json=sample_kthulu_json,
                version_number="2.0",
                created_by="test_user",
                prefer_code_as_truth=True
            )
        
        assert result.success == True
        assert result.conflicts_resolved == 2
    
    def test_delta_validation(self, sync_bridge, sample_kthulu_json):
        """Test delta validation before sync"""
        sync_bridge.initialize()
        
        # Mock components and relationships
        mock_component = ArchitecturalComponent(
            iri="http://kthulu.io/ontology#auth.Module.auth",
            component_type=ComponentType.MODULE,
            name="auth",
            namespace="auth"
        )
        
        mock_validation_report = ValidationReport(
            tenant_id="test_tenant",
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation="Delta validation passed"
        )
        
        with patch.object(sync_bridge.graph_importer, '_parse_kthulu_json', return_value=([mock_component], [])), \
             patch.object(sync_bridge.graph_importer, '_calculate_delta'), \
             patch.object(sync_bridge.graph_importer, 'validate_delta', return_value=mock_validation_report):
            
            result = sync_bridge.validate_delta_before_sync("test_tenant", sample_kthulu_json)
        
        assert result.is_consistent == True
        assert result.tenant_id == "test_tenant"
    
    def test_sync_history(self, sync_bridge):
        """Test getting sync history"""
        sync_bridge.initialize()
        
        mock_versions = [
            OntologyVersion(
                version_id="v1",
                tenant_id="test_tenant",
                version_number="1.0",
                status=VersionStatus.ACTIVE,
                created_at=datetime.now(),
                created_by="user1"
            ),
            OntologyVersion(
                version_id="v2", 
                tenant_id="test_tenant",
                version_number="2.0",
                status=VersionStatus.ACTIVE,
                created_at=datetime.now(),
                created_by="user2"
            )
        ]
        
        with patch.object(sync_bridge.graph_importer, 'get_version_history', return_value=mock_versions):
            history = sync_bridge.get_sync_history("test_tenant")
        
        assert len(history) == 2
        assert history[0].version_number == "1.0"
        assert history[1].version_number == "2.0"
    
    def test_sync_statistics(self, sync_bridge):
        """Test getting sync statistics"""
        sync_bridge.initialize()
        
        mock_stats = {
            'total_versions': 3,
            'active_versions': 1,
            'draft_versions': 1,
            'archived_versions': 1,
            'latest_version_id': 'v3',
            'latest_components_count': 10,
            'latest_relationships_count': 15,
            'latest_triples_count': 50
        }
        
        with patch.object(sync_bridge, 'get_sync_history') as mock_history:
            mock_history.return_value = [
                OntologyVersion(
                    version_id="v3",
                    tenant_id="test_tenant",
                    version_number="3.0",
                    status=VersionStatus.ACTIVE,
                    created_at=datetime.now(),
                    created_by="user",
                    components_count=10,
                    relationships_count=15,
                    triples_count=50
                )
            ]
            
            stats = sync_bridge.get_sync_statistics("test_tenant")
        
        assert stats['total_versions'] == 1
        assert stats['latest_components_count'] == 10
    
    def test_conflict_detection(self, sync_bridge, sample_kthulu_json):
        """Test conflict detection"""
        sync_bridge.initialize()
        
        from domain.entities.graph_delta import ConflictResolution
        mock_conflicts = [
            ConflictResolution(
                conflict_type="NAMING_CONFLICT",
                resolution_strategy="PREFER_CODE",
                description="Component auth has different types in same namespace"
            )
        ]
        
        with patch.object(sync_bridge.graph_importer, '_parse_kthulu_json'), \
             patch.object(sync_bridge, 'detect_conflicts', return_value=mock_conflicts):
            
            conflicts = sync_bridge.detect_conflicts("test_tenant", sample_kthulu_json)
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "NAMING_CONFLICT"
    
    def test_sync_not_initialized(self, sync_bridge, sample_kthulu_json):
        """Test sync operations when bridge is not initialized"""
        # Don't initialize the bridge
        
        result = sync_bridge.sync_full_architecture(
            tenant_id="test_tenant",
            kthulu_graph_json=sample_kthulu_json,
            version_number="1.0",
            created_by="test_user"
        )
        
        assert result.success == False
        assert "not initialized" in result.error_message
    
    def test_sync_with_import_failure(self, sync_bridge, sample_kthulu_json):
        """Test sync when import fails"""
        sync_bridge.initialize()
        
        mock_import_result = ImportResult(
            success=False,
            components_imported=0,
            relationships_imported=0,
            triples_generated=0,
            conflicts_resolved=0,
            error_message="Import failed"
        )
        
        with patch.object(sync_bridge.graph_importer, 'import_full_graph', return_value=mock_import_result):
            result = sync_bridge.sync_full_architecture(
                tenant_id="test_tenant",
                kthulu_graph_json=sample_kthulu_json,
                version_number="1.0",
                created_by="test_user"
            )
        
        assert result.success == False
        assert result.error_message == "Import failed"


if __name__ == "__main__":
    pytest.main([__file__])