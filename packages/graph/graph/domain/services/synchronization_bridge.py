"""
Synchronization Bridge Service

Orchestrates synchronization between Kthulu code and PermaGraph ontology
with support for incremental updates, conflict resolution, and versioning.
Integrates with existing PermaGraph ingestion infrastructure.
"""

from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass

from .kthulu_graph_importer import KthuluGraphImporter, ImportResult
from .kthulu_ontology_service import KthuluOntologyService
from ..code_ingestion_service import CodeIngestionService
from ..ingestion_service import IngestionService
from ..ontology.kthulu_ontology_loader import KthuluOntologyLoader
from ..entities.graph_delta import GraphDelta, ConflictResolution
from ..entities.ontology_version import OntologyVersion, VersionSnapshot, VersionStatus
from ..entities.validation_report import ValidationReport
from ..entities.triple import Triple
from ..exceptions import GraphRAGException
from infrastructure.kthulu_doc_parser import KthuluDocParser

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a synchronization operation"""
    success: bool
    sync_type: str  # "full", "incremental"
    import_result: Optional[ImportResult] = None
    validation_report: Optional[ValidationReport] = None
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    error_message: Optional[str] = None
    
    @property
    def has_errors(self) -> bool:
        """Check if sync result has errors"""
        return not self.success or (self.validation_report and not self.validation_report.is_consistent)


class SynchronizationBridge:
    """
    Bridge service for synchronizing Kthulu architecture with PermaGraph ontology
    
    This service provides:
    - Full and incremental synchronization
    - Conflict detection and resolution
    - Version management
    - Validation integration
    - Integration with existing PermaGraph ingestion infrastructure
    """
    
    def __init__(self,
                 ontology_loader: Optional[KthuluOntologyLoader] = None,
                 ontology_service: Optional[KthuluOntologyService] = None,
                 ingestion_service: Optional[IngestionService] = None,
                 doc_parser: Optional[KthuluDocParser] = None):
        self.ontology_loader = ontology_loader or KthuluOntologyLoader()
        self.ontology_service = ontology_service or KthuluOntologyService(self.ontology_loader)
        self.graph_importer = KthuluGraphImporter(self.ontology_loader)
        self.ingestion_service = ingestion_service  # Use existing ingestion infrastructure
        self.doc_parser = doc_parser or KthuluDocParser(ontology_loader=self.ontology_loader)
        self._requirements_by_version: Dict[str, List[Triple]] = {}
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize the synchronization bridge"""
        try:
            if not self.ontology_service.initialize():
                logger.error("Failed to initialize ontology service")
                return False
            
            self._initialized = True
            logger.info("Synchronization bridge initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize synchronization bridge: {e}")
            return False
    
    def sync_full_architecture(self,
                              tenant_id: str,
                              kthulu_graph_json: Dict,
                              version_number: str,
                              created_by: str,
                              description: Optional[str] = None,
                              validate_after_sync: bool = True) -> SyncResult:
        """
        Perform full synchronization of Kthulu architecture
        
        Args:
            tenant_id: Tenant identifier
            kthulu_graph_json: Complete architecture from kthulu-cli plan --graph --format=json
            version_number: Version identifier for this sync
            created_by: User who initiated the sync
            description: Optional description
            validate_after_sync: Whether to validate after synchronization
        """
        if not self._initialized:
            return SyncResult(
                success=False,
                sync_type="full",
                error_message="Synchronization bridge not initialized"
            )
        
        try:
            logger.info(f"Starting full architecture sync for tenant {tenant_id}")

            # Parse requirement documentation before importing the graph
            requirement_triples: List[Triple] = []
            try:
                requirement_triples = self.doc_parser.parse_requirements()
                logger.info(f"Parsed {len(requirement_triples)} requirement triples")
            except Exception as parse_err:
                logger.warning(f"Failed to parse requirement docs: {parse_err}")

            # Import the full graph
            import_result = self.graph_importer.import_full_graph(
                tenant_id=tenant_id,
                graph_json=kthulu_graph_json,
                version_number=version_number,
                created_by=created_by,
                description=description
            )

            if import_result.success and import_result.version:
                self._requirements_by_version[
                    import_result.version.version_id
                ] = requirement_triples
            
            if not import_result.success:
                return SyncResult(
                    success=False,
                    sync_type="full",
                    import_result=import_result,
                    error_message=import_result.error_message
                )
            
            # Validate if requested
            validation_report = None
            if validate_after_sync:
                try:
                    # Import to ontology service for validation
                    architecture_graph = self.ontology_service.import_architecture_from_json(kthulu_graph_json)
                    validation_result = self.ontology_service.validate_architecture(architecture_graph)
                    
                    # Convert to ValidationReport
                    from ..entities.validation_report import ValidationReport, RuleViolation, RepairSuggestion
                    
                    rule_violations = []
                    for violation in validation_result.violations:
                        rule_violations.append(RuleViolation(
                            rule_id=violation.rule_name,
                            violated_constraint=violation.violation_type,
                            violating_components=[violation.component_iri] if violation.component_iri else [],
                            severity=violation.severity,
                            description=violation.description,
                            repair_suggestion=RepairSuggestion(
                                action=violation.suggested_fix,
                                description=violation.description,
                                confidence=0.8
                            )
                        ))
                    
                    validation_report = ValidationReport(
                        tenant_id=tenant_id,
                        is_consistent=validation_result.is_consistent,
                        violated_rules=rule_violations,
                        unsat_classes=[],
                        repair_suggestions=[v.repair_suggestion.action for v in rule_violations],
                        explanation=f"Full sync validation: {len(rule_violations)} violations found",
                        ontology_version_id=import_result.version.version_id if import_result.version else None,
                        metadata={
                            'sync_type': 'full',
                            'components_count': validation_result.components_count,
                            'relationships_count': validation_result.relationships_count
                        }
                    )
                    
                except Exception as e:
                    logger.warning(f"Validation failed after full sync: {e}")
                    # Continue with sync success even if validation fails
            
            result = SyncResult(
                success=True,
                sync_type="full",
                import_result=import_result,
                validation_report=validation_report,
                conflicts_detected=0,
                conflicts_resolved=0
            )
            
            logger.info(f"Full architecture sync completed successfully for tenant {tenant_id}")
            return result
            
        except Exception as e:
            logger.error(f"Full architecture sync failed for tenant {tenant_id}: {e}")
            return SyncResult(
                success=False,
                sync_type="full",
                error_message=str(e)
            )
    
    def sync_incremental_changes(self,
                                tenant_id: str,
                                kthulu_graph_json: Dict,
                                version_number: str,
                                created_by: str,
                                parent_version_id: Optional[str] = None,
                                prefer_code_as_truth: bool = True,
                                validate_delta: bool = True,
                                validate_after_sync: bool = True) -> SyncResult:
        """
        Perform incremental synchronization using delta comparison
        
        Args:
            tenant_id: Tenant identifier
            kthulu_graph_json: Updated architecture from kthulu-cli
            version_number: New version identifier
            created_by: User who initiated the sync
            parent_version_id: Previous version to compare against
            prefer_code_as_truth: Whether to prefer code over existing ontology in conflicts
            validate_delta: Whether to validate the delta before applying
            validate_after_sync: Whether to validate after synchronization
        """
        if not self._initialized:
            return SyncResult(
                success=False,
                sync_type="incremental",
                error_message="Synchronization bridge not initialized"
            )
        
        try:
            logger.info(f"Starting incremental sync for tenant {tenant_id}")

            # Parse requirement documentation before importing changes
            requirement_triples: List[Triple] = []
            try:
                requirement_triples = self.doc_parser.parse_requirements()
                logger.info(f"Parsed {len(requirement_triples)} requirement triples")
            except Exception as parse_err:
                logger.warning(f"Failed to parse requirement docs: {parse_err}")

            # Import with incremental changes
            import_result = self.graph_importer.import_incremental_changes(
                tenant_id=tenant_id,
                graph_json=kthulu_graph_json,
                version_number=version_number,
                created_by=created_by,
                parent_version_id=parent_version_id,
                prefer_code_as_truth=prefer_code_as_truth
            )

            if import_result.success and import_result.version:
                self._requirements_by_version[
                    import_result.version.version_id
                ] = requirement_triples
            
            if not import_result.success:
                return SyncResult(
                    success=False,
                    sync_type="incremental",
                    import_result=import_result,
                    error_message=import_result.error_message
                )
            
            conflicts_detected = 0
            conflicts_resolved = import_result.conflicts_resolved
            
            # Validate delta if requested and available
            delta_validation_report = None
            if validate_delta and import_result.delta:
                try:
                    delta_validation_report = self.graph_importer.validate_delta(import_result.delta)
                    if not delta_validation_report.is_consistent:
                        logger.warning(f"Delta validation found issues: {len(delta_validation_report.violated_rules)} violations")
                        conflicts_detected = len(delta_validation_report.violated_rules)
                except Exception as e:
                    logger.warning(f"Delta validation failed: {e}")
            
            # Validate final state if requested
            validation_report = None
            if validate_after_sync:
                try:
                    # Import to ontology service for validation
                    architecture_graph = self.ontology_service.import_architecture_from_json(kthulu_graph_json)
                    validation_result = self.ontology_service.validate_architecture(architecture_graph)
                    
                    # Convert to ValidationReport (similar to full sync)
                    from ..entities.validation_report import ValidationReport, RuleViolation, RepairSuggestion
                    
                    rule_violations = []
                    for violation in validation_result.violations:
                        rule_violations.append(RuleViolation(
                            rule_id=violation.rule_name,
                            violated_constraint=violation.violation_type,
                            violating_components=[violation.component_iri] if violation.component_iri else [],
                            severity=violation.severity,
                            description=violation.description,
                            repair_suggestion=RepairSuggestion(
                                action=violation.suggested_fix,
                                description=violation.description,
                                confidence=0.8
                            )
                        ))
                    
                    validation_report = ValidationReport(
                        tenant_id=tenant_id,
                        is_consistent=validation_result.is_consistent,
                        violated_rules=rule_violations,
                        unsat_classes=[],
                        repair_suggestions=[v.repair_suggestion.action for v in rule_violations],
                        explanation=f"Incremental sync validation: {len(rule_violations)} violations found",
                        ontology_version_id=import_result.version.version_id if import_result.version else None,
                        metadata={
                            'sync_type': 'incremental',
                            'delta_summary': import_result.delta.to_summary() if import_result.delta else 'No delta',
                            'components_count': validation_result.components_count,
                            'relationships_count': validation_result.relationships_count,
                            'delta_validation_performed': validate_delta,
                            'conflicts_detected': conflicts_detected,
                            'conflicts_resolved': conflicts_resolved
                        }
                    )
                    
                except Exception as e:
                    logger.warning(f"Validation failed after incremental sync: {e}")
            
            result = SyncResult(
                success=True,
                sync_type="incremental",
                import_result=import_result,
                validation_report=validation_report,
                conflicts_detected=conflicts_detected,
                conflicts_resolved=conflicts_resolved
            )
            
            logger.info(f"Incremental sync completed: {import_result.delta.to_summary() if import_result.delta else 'No changes'}")
            return result
            
        except Exception as e:
            logger.error(f"Incremental sync failed for tenant {tenant_id}: {e}")
            return SyncResult(
                success=False,
                sync_type="incremental",
                error_message=str(e)
            )
    
    def validate_delta_before_sync(self, tenant_id: str, kthulu_graph_json: Dict) -> ValidationReport:
        """
        Validate a potential delta without applying it
        
        Args:
            tenant_id: Tenant identifier
            kthulu_graph_json: Proposed new architecture state
            
        Returns:
            ValidationReport with delta validation results
        """
        if not self._initialized:
            raise GraphRAGException("Synchronization bridge not initialized", "BRIDGE_NOT_INITIALIZED")
        
        try:
            # Parse the new graph
            components, relationships = self.graph_importer._parse_kthulu_json(kthulu_graph_json)
            
            # Calculate delta against current state
            delta = self.graph_importer._calculate_delta(
                self.graph_importer._current_components,
                self.graph_importer._current_relationships,
                components,
                relationships,
                "current",
                "proposed"
            )
            
            # Validate the delta
            return self.graph_importer.validate_delta(delta)
            
        except Exception as e:
            logger.error(f"Delta validation failed for tenant {tenant_id}: {e}")
            raise GraphRAGException(f"Delta validation failed: {e}", "DELTA_VALIDATION_FAILED")
    
    def get_sync_history(self, tenant_id: str) -> List[OntologyVersion]:
        """Get synchronization history for a tenant"""
        return self.graph_importer.get_version_history(tenant_id)
    
    def get_version_snapshot(self, version_id: str) -> Optional[VersionSnapshot]:
        """Get a complete snapshot of a specific version"""
        snapshot = self.graph_importer.get_version_snapshot(version_id)
        if snapshot:
            req_triples = self._requirements_by_version.get(version_id, [])
            snapshot.triples.extend(req_triples)
        return snapshot
    
    def rollback_to_version(self, tenant_id: str, version_id: str) -> SyncResult:
        """
        Rollback to a previous version
        
        Args:
            tenant_id: Tenant identifier
            version_id: Version to rollback to
            
        Returns:
            SyncResult indicating success/failure of rollback
        """
        try:
            snapshot = self.get_version_snapshot(version_id)
            if not snapshot:
                return SyncResult(
                    success=False,
                    sync_type="rollback",
                    error_message=f"Version {version_id} not found"
                )
            
            # For now, we'll mark this as not implemented
            # In a full implementation, we would restore the state from the snapshot
            logger.warning("Rollback functionality not fully implemented")
            
            return SyncResult(
                success=False,
                sync_type="rollback",
                error_message="Rollback functionality not yet implemented"
            )
            
        except Exception as e:
            logger.error(f"Rollback failed for tenant {tenant_id}, version {version_id}: {e}")
            return SyncResult(
                success=False,
                sync_type="rollback",
                error_message=str(e)
            )
    
    def get_sync_statistics(self, tenant_id: str) -> Dict[str, int]:
        """Get synchronization statistics for a tenant"""
        try:
            versions = self.get_sync_history(tenant_id)
            
            stats = {
                'total_versions': len(versions),
                'active_versions': len([v for v in versions if v.status == VersionStatus.ACTIVE]),
                'draft_versions': len([v for v in versions if v.status == VersionStatus.DRAFT]),
                'archived_versions': len([v for v in versions if v.status == VersionStatus.ARCHIVED])
            }
            
            if versions:
                latest_version = max(versions, key=lambda v: v.created_at)
                stats.update({
                    'latest_version_id': latest_version.version_id,
                    'latest_components_count': latest_version.components_count,
                    'latest_relationships_count': latest_version.relationships_count,
                    'latest_triples_count': latest_version.triples_count
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get sync statistics for tenant {tenant_id}: {e}")
            return {}
    
    def detect_conflicts(self, tenant_id: str, kthulu_graph_json: Dict) -> List[ConflictResolution]:
        """
        Detect potential conflicts between code and ontology
        
        Args:
            tenant_id: Tenant identifier
            kthulu_graph_json: Proposed new architecture state
            
        Returns:
            List of detected conflicts with resolution suggestions
        """
        try:
            # For now, we'll implement basic conflict detection
            # In a more sophisticated implementation, we would analyze:
            # - Semantic conflicts (e.g., same component with different types)
            # - Structural conflicts (e.g., circular dependencies)
            # - Naming conflicts (e.g., duplicate names in different contexts)
            
            conflicts = []
            
            # Parse the new graph
            components, relationships = self.graph_importer._parse_kthulu_json(kthulu_graph_json)
            
            # Check for naming conflicts
            component_names = {}
            for component in components:
                key = f"{component.namespace}.{component.name}"
                if key in component_names:
                    existing_comp = component_names[key]
                    if existing_comp.component_type != component.component_type:
                        conflicts.append(ConflictResolution(
                            conflict_type="NAMING_CONFLICT",
                            resolution_strategy="PREFER_CODE",
                            description=f"Component {component.name} has different types in same namespace",
                            resolved_component=component,
                            metadata={
                                'existing_type': existing_comp.component_type.value,
                                'new_type': component.component_type.value
                            }
                        ))
                else:
                    component_names[key] = component
            
            logger.info(f"Conflict detection completed for tenant {tenant_id}: {len(conflicts)} conflicts found")
            return conflicts
            
        except Exception as e:
            logger.error(f"Conflict detection failed for tenant {tenant_id}: {e}")
            return []