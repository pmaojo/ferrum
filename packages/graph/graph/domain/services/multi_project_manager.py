import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import shutil
from .kthulu_ontology_service import KthuluOntologyService
from .synchronization_bridge import SynchronizationBridge
from .standards_export_service import StandardsExportService, ExportFormat
from .standards_import_service import StandardsImportService, ImportFormat
from ..agents.reasoner_agent import ReasonerAgent


class ProjectStatus(Enum):
    """Project status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    TEMPLATE = "template"
    IMPORTING = "importing"
    EXPORTING = "exporting"
    ERROR = "error"


@dataclass
class ProjectMetadata:
    """Project metadata structure"""

    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: Optional[str] = None
    tags: List[str] = None
    kthulu_version: Optional[str] = None
    ontology_version: Optional[str] = None
    triple_count: int = 0
    module_count: int = 0
    violation_count: int = 0
    last_sync: Optional[datetime] = None
    tenant_id: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []


@dataclass
class ProjectTemplate:
    """Project template structure"""

    template_id: str
    name: str
    description: str
    category: str
    ontology_content: str
    kthulu_config: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ProjectComparison:
    """Project comparison result"""

    project_a: str
    project_b: str
    common_modules: List[str]
    unique_to_a: List[str]
    unique_to_b: List[str]
    architectural_differences: List[Dict[str, Any]]
    similarity_score: float
    comparison_timestamp: datetime = None

    def __post_init__(self):
        if self.comparison_timestamp is None:
            self.comparison_timestamp = datetime.now()


class MultiProjectManager:
    """
    @kthulu:extend - Multi-project management service for Kthulu-PermaGraph integration

    Provides:
    - Project lifecycle management (create, clone, archive, delete)
    - Project isolation with tenant support
    - Project templates and scaffolding
    - Project comparison and analysis
    - Bulk operations across projects
    - Project switching and navigation
    - Cross-project dependency tracking
    """

    def __init__(
        self,
        ontology_service: KthuluOntologyService,
        sync_bridge: SynchronizationBridge,
        export_service: StandardsExportService,
        import_service: StandardsImportService,
        reasoner_agent: Optional[ReasonerAgent] = None,
        base_path: Optional[Path] = None,
    ):
        self.ontology_service = ontology_service
        self.sync_bridge = sync_bridge
        self.export_service = export_service
        self.import_service = import_service
        self.reasoner_agent = reasoner_agent
        self.base_path = base_path or Path("projects")

        # Project registry
        self.projects: Dict[str, ProjectMetadata] = {}
        self.templates: Dict[str, ProjectTemplate] = {}
        self.active_projects: Set[str] = set()

        # Tenant isolation
        self.tenant_projects: Dict[str, Set[str]] = {}

        self.logger = logging.getLogger(__name__)

        # Initialize
        self._load_project_registry()
        self._load_templates()

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        template_id: Optional[str] = None,
        owner: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ProjectMetadata:
        """Create a new project"""
        try:
            project_id = self._generate_project_id(name)

            self.logger.info(f"ð Creating new project: {project_id}")

            # Create project metadata
            metadata = ProjectMetadata(
                project_id=project_id,
                name=name,
                description=description,
                owner=owner,
                tenant_id=tenant_id,
                tags=tags or [],
            )

            # Create project directory
            project_path = self.base_path / project_id
            project_path.mkdir(parents=True, exist_ok=True)

            # Initialize from template if provided
            if template_id and template_id in self.templates:
                self._initialize_from_template(project_id, template_id)

            # Register project
            self.projects[project_id] = metadata
            self.active_projects.add(project_id)

            # Add to tenant if specified
            if tenant_id:
                if tenant_id not in self.tenant_projects:
                    self.tenant_projects[tenant_id] = set()
                self.tenant_projects[tenant_id].add(project_id)

            # Save registry
            self._save_project_registry()

            # Initialize ontology service for project
            self.ontology_service.initialize_project(project_id)

            self.logger.info(f"â Successfully created project {project_id}")
            return metadata

        except Exception as e:
            self.logger.error(f"â Error creating project: {e}")
            raise

    def clone_project(
        self,
        source_project_id: str,
        new_name: str,
        description: Optional[str] = None,
        owner: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> ProjectMetadata:
        """Clone an existing project"""
        try:
            if source_project_id not in self.projects:
                raise ValueError(f"Source project {source_project_id} not found")

            self.logger.info(f"ð Cloning project {source_project_id} to {new_name}")

            # Generate new project ID
            new_project_id = self._generate_project_id(new_name)

            # Get source metadata
            source_metadata = self.projects[source_project_id]

            # Create new metadata
            new_metadata = ProjectMetadata(
                project_id=new_project_id,
                name=new_name,
                description=description or f"Clone of {source_metadata.name}",
                owner=owner,
                tenant_id=tenant_id,
                tags=source_metadata.tags.copy(),
            )

            # Clone project directory
            source_path = self.base_path / source_project_id
            new_path = self.base_path / new_project_id

            if source_path.exists():
                shutil.copytree(source_path, new_path)

            # Clone ontology data
            source_graph = self.ontology_service.get_project_graph(source_project_id)
            if source_graph:
                self.ontology_service.store_project_graph(new_project_id, source_graph)

            # Register new project
            self.projects[new_project_id] = new_metadata
            self.active_projects.add(new_project_id)

            # Add to tenant if specified
            if tenant_id:
                if tenant_id not in self.tenant_projects:
                    self.tenant_projects[tenant_id] = set()
                self.tenant_projects[tenant_id].add(new_project_id)

            # Save registry
            self._save_project_registry()

            self.logger.info(f"â Successfully cloned project to {new_project_id}")
            return new_metadata

        except Exception as e:
            self.logger.error(f"â Error cloning project: {e}")
            raise

    def archive_project(self, project_id: str) -> bool:
        """Archive a project"""
        try:
            if project_id not in self.projects:
                raise ValueError(f"Project {project_id} not found")

            self.logger.info(f"ð¦ Archiving project {project_id}")

            # Update status
            self.projects[project_id].status = ProjectStatus.ARCHIVED
            self.projects[project_id].updated_at = datetime.now()

            # Remove from active projects
            self.active_projects.discard(project_id)

            # Create archive
            archive_path = (
                self.base_path
                / "archives"
                / f"{project_id}_{datetime.now().isoformat()}.tar.gz"
            )
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            project_path = self.base_path / project_id
            if project_path.exists():
                shutil.make_archive(
                    str(archive_path.with_suffix("")), "gztar", str(project_path)
                )

            # Save registry
            self._save_project_registry()

            self.logger.info(f"â Successfully archived project {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"â Error archiving project: {e}")
            return False

    def delete_project(self, project_id: str, force: bool = False) -> bool:
        """Delete a project"""
        try:
            if project_id not in self.projects:
                raise ValueError(f"Project {project_id} not found")

            metadata = self.projects[project_id]

            # Check if project can be deleted
            if not force and metadata.status == ProjectStatus.ACTIVE:
                raise ValueError("Cannot delete active project without force flag")

            self.logger.info(f"ðï¸ Deleting project {project_id}")

            # Create backup before deletion
            if not force:
                self.archive_project(project_id)

            # Remove from ontology service
            self.ontology_service.delete_project(project_id)

            # Remove project directory
            project_path = self.base_path / project_id
            if project_path.exists():
                shutil.rmtree(project_path)

            # Remove from registry
            del self.projects[project_id]
            self.active_projects.discard(project_id)

            # Remove from tenant
            if metadata.tenant_id and metadata.tenant_id in self.tenant_projects:
                self.tenant_projects[metadata.tenant_id].discard(project_id)

            # Save registry
            self._save_project_registry()

            self.logger.info(f"â Successfully deleted project {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"â Error deleting project: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Get project metadata"""
        return self.projects.get(project_id)

    def list_projects(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[ProjectMetadata]:
        """List projects with optional filtering"""
        projects = list(self.projects.values())

        # Filter by tenant
        if tenant_id:
            tenant_project_ids = self.tenant_projects.get(tenant_id, set())
            projects = [p for p in projects if p.project_id in tenant_project_ids]

        # Filter by status
        if status:
            projects = [p for p in projects if p.status == status]

        # Filter by owner
        if owner:
            projects = [p for p in projects if p.owner == owner]

        # Filter by tags
        if tags:
            projects = [p for p in projects if any(tag in p.tags for tag in tags)]

        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ProjectStatus] = None,
    ) -> Optional[ProjectMetadata]:
        """Update project metadata"""
        try:
            if project_id not in self.projects:
                return None

            metadata = self.projects[project_id]

            # Update fields
            if name is not None:
                metadata.name = name
            if description is not None:
                metadata.description = description
            if tags is not None:
                metadata.tags = tags
            if status is not None:
                metadata.status = status

            metadata.updated_at = datetime.now()

            # Save registry
            self._save_project_registry()

            return metadata

        except Exception as e:
            self.logger.error(f"â Error updating project: {e}")
            return None

    def compare_projects(self, project_a: str, project_b: str) -> ProjectComparison:
        """Compare two projects"""
        try:
            self.logger.info(f"ð Comparing projects {project_a} and {project_b}")

            # Get project graphs
            graph_a = self.ontology_service.get_project_graph(project_a)
            graph_b = self.ontology_service.get_project_graph(project_b)

            if not graph_a or not graph_b:
                raise ValueError("One or both projects have no ontology data")

            # Extract modules from both projects
            modules_a = self._extract_modules(graph_a)
            modules_b = self._extract_modules(graph_b)

            # Find common and unique modules
            common_modules = list(set(modules_a) & set(modules_b))
            unique_to_a = list(set(modules_a) - set(modules_b))
            unique_to_b = list(set(modules_b) - set(modules_a))

            # Calculate similarity score
            total_modules = len(set(modules_a) | set(modules_b))
            similarity_score = (
                len(common_modules) / total_modules if total_modules > 0 else 0.0
            )

            # Analyze architectural differences
            arch_differences = self._analyze_architectural_differences(graph_a, graph_b)

            comparison = ProjectComparison(
                project_a=project_a,
                project_b=project_b,
                common_modules=common_modules,
                unique_to_a=unique_to_a,
                unique_to_b=unique_to_b,
                architectural_differences=arch_differences,
                similarity_score=similarity_score,
            )

            self.logger.info(
                f"â Comparison complete: {similarity_score:.2%} similarity, "
                f"{len(common_modules)} common modules"
            )

            return comparison

        except Exception as e:
            self.logger.error(f"â Error comparing projects: {e}")
            raise

    def create_template(
        self, name: str, description: str, category: str, source_project_id: str
    ) -> ProjectTemplate:
        """Create a project template from existing project"""
        try:
            if source_project_id not in self.projects:
                raise ValueError(f"Source project {source_project_id} not found")

            self.logger.info(f"ð Creating template from project {source_project_id}")

            template_id = self._generate_template_id(name)

            # Export project ontology
            export_result = self.export_service.export_project_ontology(
                source_project_id, ExportFormat.TURTLE, include_metadata=True
            )

            if not export_result["success"]:
                raise ValueError("Failed to export project ontology")

            # Get Kthulu configuration
            kthulu_config = self._extract_kthulu_config(source_project_id)

            # Create template
            template = ProjectTemplate(
                template_id=template_id,
                name=name,
                description=description,
                category=category,
                ontology_content=export_result["content"],
                kthulu_config=kthulu_config,
                metadata=export_result["metadata"],
            )

            # Store template
            self.templates[template_id] = template
            self._save_templates()

            self.logger.info(f"â Successfully created template {template_id}")
            return template

        except Exception as e:
            self.logger.error(f"â Error creating template: {e}")
            raise

    def list_templates(self, category: Optional[str] = None) -> List[ProjectTemplate]:
        """List available project templates"""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return sorted(templates, key=lambda t: t.created_at, reverse=True)

    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get detailed project statistics"""
        try:
            if project_id not in self.projects:
                return {}

            metadata = self.projects[project_id]
            graph = self.ontology_service.get_project_graph(project_id)

            stats = {
                "project_id": project_id,
                "name": metadata.name,
                "status": metadata.status.value,
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat(),
                "triple_count": len(graph) if graph else 0,
                "module_count": 0,
                "usecase_count": 0,
                "adapter_count": 0,
                "port_count": 0,
                "violation_count": 0,
            }

            if graph:
                # Count different entity types
                from rdflib.namespace import RDF
                from rdflib import Namespace

                KTHULU = Namespace("http://kthulu.io/ontology#")

                stats["module_count"] = len(
                    list(graph.subjects(RDF.type, KTHULU.Module))
                )
                stats["usecase_count"] = len(
                    list(graph.subjects(RDF.type, KTHULU.UseCase))
                )
                stats["adapter_count"] = len(
                    list(graph.subjects(RDF.type, KTHULU.Adapter))
                )
                stats["port_count"] = len(list(graph.subjects(RDF.type, KTHULU.Port)))

            # Get validation info if available
            if self.reasoner_agent:
                validation_report = self.reasoner_agent.get_latest_validation_report(
                    project_id
                )
                if validation_report:
                    stats["violation_count"] = len(validation_report.violated_rules)
                    stats["is_consistent"] = validation_report.is_consistent

            return stats

        except Exception as e:
            self.logger.error(f"â Error getting project statistics: {e}")
            return {}

    def bulk_operation(
        self, operation: str, project_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Perform bulk operations on multiple projects"""
        results = {
            "operation": operation,
            "total_projects": len(project_ids),
            "successful": [],
            "failed": [],
            "errors": {},
        }

        for project_id in project_ids:
            try:
                if operation == "archive":
                    success = self.archive_project(project_id)
                elif operation == "delete":
                    success = self.delete_project(
                        project_id, kwargs.get("force", False)
                    )
                elif operation == "update_status":
                    metadata = self.update_project(
                        project_id, status=kwargs.get("status")
                    )
                    success = metadata is not None
                elif operation == "export":
                    export_result = self.export_service.export_project_ontology(
                        project_id, kwargs.get("format", ExportFormat.TURTLE)
                    )
                    success = export_result["success"]
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                if success:
                    results["successful"].append(project_id)
                else:
                    results["failed"].append(project_id)

            except Exception as e:
                results["failed"].append(project_id)
                results["errors"][project_id] = str(e)

        return results

    def _generate_project_id(self, name: str) -> str:
        """Generate unique project ID"""
        base_id = name.lower().replace(" ", "-").replace("_", "-")
        base_id = "".join(c for c in base_id if c.isalnum() or c == "-")

        # Ensure uniqueness
        counter = 1
        project_id = base_id
        while project_id in self.projects:
            project_id = f"{base_id}-{counter}"
            counter += 1

        return project_id

    def _generate_template_id(self, name: str) -> str:
        """Generate unique template ID"""
        base_id = name.lower().replace(" ", "-").replace("_", "-")
        base_id = "".join(c for c in base_id if c.isalnum() or c == "-")

        # Ensure uniqueness
        counter = 1
        template_id = base_id
        while template_id in self.templates:
            template_id = f"{base_id}-{counter}"
            counter += 1

        return template_id

    def _initialize_from_template(self, project_id: str, template_id: str) -> None:
        """Initialize project from template"""
        template = self.templates[template_id]

        # Import ontology content
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as tmp_file:
            tmp_file.write(template.ontology_content)
            tmp_path = Path(tmp_file.name)

        try:
            import_result = self.import_service.import_ontology(
                project_id, tmp_path, ImportFormat.TURTLE
            )

            if not import_result.success:
                raise ValueError(f"Failed to import template: {import_result.errors}")

        finally:
            tmp_path.unlink()

        # Apply Kthulu configuration
        self._apply_kthulu_config(project_id, template.kthulu_config)

    def _extract_modules(self, graph) -> List[str]:
        """Extract module names from graph"""
        from rdflib.namespace import RDF
        from rdflib import Namespace

        KTHULU = Namespace("http://kthulu.io/ontology#")

        modules = []
        for module in graph.subjects(RDF.type, KTHULU.Module):
            for name in graph.objects(module, KTHULU.hasName):
                modules.append(str(name))

        return modules

    def _analyze_architectural_differences(
        self, graph_a, graph_b
    ) -> List[Dict[str, Any]]:
        """Analyze architectural differences between graphs"""
        differences = []

        # This would contain more sophisticated analysis
        # For now, return basic difference count
        triples_a = set(graph_a)
        triples_b = set(graph_b)

        only_in_a = triples_a - triples_b
        only_in_b = triples_b - triples_a

        if only_in_a:
            differences.append(
                {
                    "type": "unique_triples_a",
                    "count": len(only_in_a),
                    "description": f"{len(only_in_a)} triples only in project A",
                }
            )

        if only_in_b:
            differences.append(
                {
                    "type": "unique_triples_b",
                    "count": len(only_in_b),
                    "description": f"{len(only_in_b)} triples only in project B",
                }
            )

        return differences

    def _extract_kthulu_config(self, project_id: str) -> Dict[str, Any]:
        """Extract Kthulu configuration from project"""
        # This would extract actual Kthulu configuration
        # For now, return a basic config
        return {
            "version": "0.1.0",
            "architecture": "hexagonal",
            "modules": [],
            "dependencies": [],
        }

    def _apply_kthulu_config(self, project_id: str, config: Dict[str, Any]) -> None:
        """Apply Kthulu configuration to project"""
        # This would apply the configuration to the actual Kthulu project
        # For now, just log the operation
        self.logger.info(f"ð Applied Kthulu config to project {project_id}")

    def _load_project_registry(self) -> None:
        """Load project registry from disk"""
        registry_path = self.base_path / "registry.json"

        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Load projects
                for project_data in data.get("projects", []):
                    metadata = ProjectMetadata(**project_data)
                    # Convert datetime strings back to datetime objects
                    if isinstance(metadata.created_at, str):
                        metadata.created_at = datetime.fromisoformat(
                            metadata.created_at
                        )
                    if isinstance(metadata.updated_at, str):
                        metadata.updated_at = datetime.fromisoformat(
                            metadata.updated_at
                        )
                    if metadata.last_sync and isinstance(metadata.last_sync, str):
                        metadata.last_sync = datetime.fromisoformat(metadata.last_sync)

                    self.projects[metadata.project_id] = metadata

                    if metadata.status == ProjectStatus.ACTIVE:
                        self.active_projects.add(metadata.project_id)

                # Load tenant mappings
                self.tenant_projects = data.get("tenant_projects", {})
                # Convert sets from lists
                for tenant_id, project_list in self.tenant_projects.items():
                    self.tenant_projects[tenant_id] = set(project_list)

            except Exception as e:
                self.logger.error(f"â Error loading project registry: {e}")

    def _save_project_registry(self) -> None:
        """Save project registry to disk"""
        registry_path = self.base_path / "registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Prepare data for serialization
            projects_data = []
            for metadata in self.projects.values():
                data = asdict(metadata)
                # Convert datetime objects to strings
                if data["created_at"]:
                    data["created_at"] = data["created_at"].isoformat()
                if data["updated_at"]:
                    data["updated_at"] = data["updated_at"].isoformat()
                if data["last_sync"]:
                    data["last_sync"] = data["last_sync"].isoformat()
                if data["status"]:
                    data["status"] = data["status"].value

                projects_data.append(data)

            # Convert tenant projects sets to lists
            tenant_projects_data = {}
            for tenant_id, project_set in self.tenant_projects.items():
                tenant_projects_data[tenant_id] = list(project_set)

            registry_data = {
                "projects": projects_data,
                "tenant_projects": tenant_projects_data,
                "last_updated": datetime.now().isoformat(),
            }

            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump(registry_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"â Error saving project registry: {e}")

    def _load_templates(self) -> None:
        """Load project templates from disk"""
        templates_path = self.base_path / "templates.json"

        if templates_path.exists():
            try:
                with open(templates_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for template_data in data.get("templates", []):
                    template = ProjectTemplate(**template_data)
                    if isinstance(template.created_at, str):
                        template.created_at = datetime.fromisoformat(
                            template.created_at
                        )

                    self.templates[template.template_id] = template

            except Exception as e:
                self.logger.error(f"â Error loading templates: {e}")

    def _save_templates(self) -> None:
        """Save project templates to disk"""
        templates_path = self.base_path / "templates.json"
        templates_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            templates_data = []
            for template in self.templates.values():
                data = asdict(template)
                if data["created_at"]:
                    data["created_at"] = data["created_at"].isoformat()
                templates_data.append(data)

            template_registry = {
                "templates": templates_data,
                "last_updated": datetime.now().isoformat(),
            }

            with open(templates_path, "w", encoding="utf-8") as f:
                json.dump(template_registry, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"â Error saving templates: {e}")
