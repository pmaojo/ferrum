"""Tests for CompareOntologyVersionsUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict

from domain.entities import OntologyVersion, ScientificDomain
from application.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    BusinessRuleViolationError,
    ApplicationError
)
import importlib.util
import os

MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "application",
    "use_cases",
    "ontology",
    "compare_ontology_versions_use_case.py",
)
spec = importlib.util.spec_from_file_location("compare_module", MODULE_PATH)
compare_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare_module)

CompareOntologyVersionsUseCase = compare_module.CompareOntologyVersionsUseCase
CompareRelatedOntologyVersionsUseCase = (
    compare_module.CompareRelatedOntologyVersionsUseCase
)
CompareOntologyVersionsResponse = compare_module.CompareOntologyVersionsResponse
OntologyComparisonServicePort = compare_module.OntologyComparisonServicePort
SimpleOntologyComparisonService = compare_module.SimpleOntologyComparisonService
from application.use_cases.ontology.create_ontology_use_case import OntologyRepositoryPort
from application.use_cases.ontology.update_ontology_use_case import AuthorizationServicePort
from application.use_cases.dto import CompareOntologyVersionsRequestDTO, OntologyVersionDiffDTO
from application.ports import TracingPort


class TestCompareOntologyVersionsUseCase:
    """Test cases for CompareOntologyVersionsUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        return Mock(spec=OntologyRepositoryPort)

    @pytest.fixture
    def mock_comparison_service(self):
        """Mock comparison service."""
        return Mock(spec=OntologyComparisonServicePort)

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock(spec=AuthorizationServicePort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def use_case(self, mock_ontology_repository, mock_comparison_service,
                 mock_authorization_service, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return CompareOntologyVersionsUseCase(
            ontology_repository=mock_ontology_repository,
            comparison_service=mock_comparison_service,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def related_use_case(self, mock_ontology_repository, mock_comparison_service,
                        mock_authorization_service, mock_tracer):
        """Create related versions use case instance with mocked dependencies."""
        return CompareRelatedOntologyVersionsUseCase(
            ontology_repository=mock_ontology_repository,
            comparison_service=mock_comparison_service,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_request(self):
        """Valid compare ontology versions request."""
        return CompareOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            version1_id="version-1",
            version2_id="version-2"
        )

    @pytest.fixture
    def sample_axioms_v1(self):
        """Sample axioms for version 1."""
        return [
            "Class: Person",
            "Class: Animal",
            "ObjectProperty: hasParent"
        ]

    @pytest.fixture
    def sample_axioms_v2(self):
        """Sample axioms for version 2 (modified)."""
        return [
            "Class: Person",
            "Class: Animal",
            "Class: Plant",  # Added
            "ObjectProperty: hasParent",
            "ObjectProperty: hasChild"  # Added
            # "ObjectProperty: hasGrandparent" removed from v1 (if it existed)
        ]

    @pytest.fixture
    def ontology_version_1(self, sample_axioms_v1):
        """First ontology version for testing."""
        version = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms_v1
        )
        version.id = "version-1"  # Override for testing
        return version

    @pytest.fixture
    def ontology_version_2(self, sample_axioms_v2):
        """Second ontology version for testing."""
        version = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms_v2
        )
        version.id = "version-2"  # Override for testing
        return version

    @pytest.fixture
    def parent_child_versions(self, sample_axioms_v1, sample_axioms_v2):
        """Parent and child ontology versions for testing."""
        parent = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms_v1
        )
        parent.id = "parent-version"

        child = OntologyVersion.create_child_version(
            parent=parent,
            axioms=sample_axioms_v2
        )
        child.id = "child-version"

        return parent, child

    @pytest.fixture
    def sibling_versions(self, sample_axioms_v1, sample_axioms_v2):
        """Two sibling versions sharing a root."""
        root = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms_v1,
        )
        root.id = "root-version"

        version1 = OntologyVersion.create_child_version(parent=root, axioms=sample_axioms_v1)
        version1.id = "version-1"

        version2 = OntologyVersion.create_child_version(parent=root, axioms=sample_axioms_v2)
        version2.id = "version-2"

        return version1, version2, root

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_success(self, use_case, valid_request,
                                                   sibling_versions,
                                                   mock_ontology_repository,
                                                   mock_comparison_service,
                                                   mock_authorization_service):
        """Test successful ontology version comparison."""
        # Setup mocks
        version1, version2, root = sibling_versions
        mock_authorization_service.check_permission.return_value = None
        mapping = {version1.id: version1, version2.id: version2, root.id: root}
        mock_ontology_repository.get_by_id.side_effect = lambda vid, t: mapping.get(vid)

        mock_comparison_service.compare_axioms.return_value = {
            "added": ["Class: Plant", "ObjectProperty: hasChild"],
            "removed": [],
            "modified": []
        }
        mock_comparison_service.detect_semantic_changes.return_value = []
        mock_comparison_service.generate_diff_summary.return_value = "Changes: 2 axioms added."

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.comparison is not None
        assert response.comparison.added_axioms == ["Class: Plant", "ObjectProperty: hasChild"]
        assert response.comparison.removed_axioms == []
        assert response.comparison.modified_axioms == []
        assert response.comparison.summary == "Changes: 2 axioms added."
        assert response.error_message is None

        # Verify mock calls
        assert mock_authorization_service.check_permission.call_count == 2
        mock_authorization_service.check_permission.assert_any_call("user-456", "version-1", "read")
        mock_authorization_service.check_permission.assert_any_call("user-456", "version-2", "read")

        assert mock_ontology_repository.get_by_id.call_count >= 2

        mock_comparison_service.compare_axioms.assert_called_once()
        mock_comparison_service.detect_semantic_changes.assert_called_once()
        mock_comparison_service.generate_diff_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_with_modifications(self, use_case, valid_request,
                                                              sibling_versions,
                                                              mock_ontology_repository,
                                                              mock_comparison_service,
                                                              mock_authorization_service):
        """Test comparison with semantic modifications."""
        # Setup mocks
        version1, version2, root = sibling_versions
        mock_authorization_service.check_permission.return_value = None
        mapping = {version1.id: version1, version2.id: version2, root.id: root}
        mock_ontology_repository.get_by_id.side_effect = lambda vid, t: mapping.get(vid)

        mock_comparison_service.compare_axioms.return_value = {
            "added": ["Class: Plant"],
            "removed": ["Class: Mineral"],
            "modified": []
        }
        mock_comparison_service.detect_semantic_changes.return_value = [
            {
                "type": "modified",
                "old_axiom": "ObjectProperty: hasParent Domain: Person",
                "new_axiom": "ObjectProperty: hasParent Domain: Animal"
            }
        ]
        mock_comparison_service.generate_diff_summary.return_value = "Changes: 1 axiom added, 1 axiom removed, 1 axiom modified."

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is True
        assert response.comparison is not None
        assert response.comparison.added_axioms == ["Class: Plant"]
        assert response.comparison.removed_axioms == ["Class: Mineral"]
        assert len(response.comparison.modified_axioms) == 1
        assert response.comparison.modified_axioms[0]["old"] == "ObjectProperty: hasParent Domain: Person"
        assert response.comparison.modified_axioms[0]["new"] == "ObjectProperty: hasParent Domain: Animal"
        assert "modified" in response.comparison.summary

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Missing tenant_id
            {
                "request": CompareOntologyVersionsRequestDTO(
                    tenant_id="",
                    user_id="user-456",
                    version1_id="version-1",
                    version2_id="version-2"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": CompareOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="",
                    version1_id="version-1",
                    version2_id="version-2"
                ),
                "expected_field": "user_id"
            },
            # Missing version1_id
            {
                "request": CompareOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    version1_id="",
                    version2_id="version-2"
                ),
                "expected_field": "version1_id"
            },
            # Missing version2_id
            {
                "request": CompareOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    version1_id="version-1",
                    version2_id=""
                ),
                "expected_field": "version2_id"
            },
            # Same version IDs
            {
                "request": CompareOntologyVersionsRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    version1_id="version-1",
                    version2_id="version-1"
                ),
                "expected_field": "version_ids"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_authorization_error(self, use_case, valid_request,
                                                               mock_authorization_service):
        """Test authorization error."""
        # Setup mock to raise authorization error for first version
        mock_authorization_service.check_permission.side_effect = AuthorizationError(
            message="User not authorized",
            user_id="user-456"
        )

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "User not authorized" in response.error_message

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_not_found(self, use_case, valid_request,
                                                     mock_ontology_repository,
                                                     mock_authorization_service):
        """Test version not found error."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [None, None]  # Both versions not found

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "not found" in response.error_message

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_empty_axioms(self, use_case, valid_request,
                                                        mock_ontology_repository,
                                                        mock_authorization_service):
        """Test comparison with empty axioms."""
        # Create versions with empty axioms
        empty_version1 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: EmptyClass"]  # Minimal axiom to pass validation
        )
        empty_version1.axioms = []  # Make it empty after creation
        empty_version1.id = "version-1"

        empty_version2 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: EmptyClass"]
        )
        empty_version2.axioms = []
        empty_version2.id = "version-2"

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [empty_version1, empty_version2]

        # Execute
        response = await use_case.execute(valid_request)

        # Verify
        assert response.success is False
        assert "no axioms to compare" in response.error_message

    @pytest.mark.asyncio
    async def test_compare_ontology_versions_repository_error(self, use_case, valid_request,
                                                            ontology_version_1,
                                                            mock_ontology_repository,
                                                            mock_authorization_service):
        """Test repository error handling."""
        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [ontology_version_1, Exception("Database error")]

        # Execute and verify exception is raised
        with pytest.raises(ApplicationError) as exc_info:
            await use_case.execute(valid_request)

        assert "Failed to compare ontology versions" in str(exc_info.value)
        assert exc_info.value.error_code == "ONTOLOGY_VERSION_COMPARISON_FAILED"

    @pytest.mark.asyncio
    async def test_compare_versions_different_lineages_error(
        self,
        use_case,
        mock_ontology_repository,
        mock_authorization_service,
    ):
        version1 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: A"],
        )
        version1.id = "version-1"

        version2 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: B"],
        )
        version2.id = "version-2"

        request = CompareOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            version1_id=version1.id,
            version2_id=version2.id,
        )

        mock_authorization_service.check_permission.return_value = None
        mapping = {version1.id: version1, version2.id: version2}
        mock_ontology_repository.get_by_id.side_effect = lambda vid, t: mapping.get(vid)

        response = await use_case.execute(request)

        assert response.success is False
        assert "different lineages" in response.error_message

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)


class TestCompareRelatedOntologyVersionsUseCase:
    """Test cases for CompareRelatedOntologyVersionsUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        return Mock(spec=OntologyRepositoryPort)

    @pytest.fixture
    def mock_comparison_service(self):
        """Mock comparison service."""
        return Mock(spec=OntologyComparisonServicePort)

    @pytest.fixture
    def mock_authorization_service(self):
        """Mock authorization service."""
        return Mock(spec=AuthorizationServicePort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def related_use_case(self, mock_ontology_repository, mock_comparison_service,
                        mock_authorization_service, mock_tracer):
        """Create related versions use case instance with mocked dependencies."""
        return CompareRelatedOntologyVersionsUseCase(
            ontology_repository=mock_ontology_repository,
            comparison_service=mock_comparison_service,
            authorization_service=mock_authorization_service,
            tracer=mock_tracer
        )

    @pytest.fixture
    def parent_child_versions(self):
        """Parent and child ontology versions for testing."""
        parent_axioms = ["Class: Person", "Class: Animal"]
        parent = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=parent_axioms
        )
        parent.id = "parent-version"

        child_axioms = parent_axioms + ["Class: Plant"]
        child = OntologyVersion.create_child_version(
            parent=parent,
            axioms=child_axioms
        )
        child.id = "child-version"

        return parent, child

    @pytest.fixture
    def valid_related_request(self):
        """Valid request for comparing related versions."""
        return CompareOntologyVersionsRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            version1_id="parent-version",
            version2_id="child-version"
        )

    @pytest.mark.asyncio
    async def test_compare_related_versions_success(self, related_use_case, valid_related_request,
                                                  parent_child_versions,
                                                  mock_ontology_repository,
                                                  mock_comparison_service,
                                                  mock_authorization_service):
        """Test successful comparison of related versions."""
        parent, child = parent_child_versions

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [parent, child]

        mock_comparison_service.compare_axioms.return_value = {
            "added": ["Class: Plant"],
            "removed": [],
            "modified": []
        }

        # Execute
        response = await related_use_case.execute(valid_related_request)

        # Verify
        assert response.success is True
        assert response.comparison is not None
        assert response.comparison.added_axioms == ["Class: Plant"]
        assert response.comparison.removed_axioms == []
        assert "Child version evolution" in response.comparison.summary
        assert "1 axioms added" in response.comparison.summary

    @pytest.mark.asyncio
    async def test_compare_unrelated_versions_error(self, related_use_case, valid_related_request,
                                                  mock_ontology_repository,
                                                  mock_authorization_service):
        """Test error when comparing unrelated versions."""
        # Create two unrelated versions
        version1 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: Person"]
        )
        version1.id = "version-1"

        version2 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.PHYSICS,
            axioms=["Class: Particle"]
        )
        version2.id = "version-2"

        # Setup mocks
        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [version1, version2]

        # Execute
        response = await related_use_case.execute(valid_related_request)

        # Verify
        assert response.success is False
        assert "must be related" in response.error_message


class TestSimpleOntologyComparisonService:
    """Test cases for SimpleOntologyComparisonService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return SimpleOntologyComparisonService()

    def test_compare_axioms_added(self, service):
        """Test axiom comparison with additions."""
        axioms1 = ["Class: Person", "Class: Animal"]
        axioms2 = ["Class: Person", "Class: Animal", "Class: Plant"]

        result = service.compare_axioms(axioms1, axioms2)

        assert result["added"] == ["Class: Plant"]
        assert result["removed"] == []
        assert result["modified"] == []

    def test_compare_axioms_removed(self, service):
        """Test axiom comparison with removals."""
        axioms1 = ["Class: Person", "Class: Animal", "Class: Plant"]
        axioms2 = ["Class: Person", "Class: Animal"]

        result = service.compare_axioms(axioms1, axioms2)

        assert result["added"] == []
        assert result["removed"] == ["Class: Plant"]
        assert result["modified"] == []

    def test_compare_axioms_mixed_changes(self, service):
        """Test axiom comparison with mixed changes."""
        axioms1 = ["Class: Person", "Class: Animal", "Class: Mineral"]
        axioms2 = ["Class: Person", "Class: Plant", "Class: Vehicle"]

        result = service.compare_axioms(axioms1, axioms2)

        assert sorted(result["added"]) == ["Class: Plant", "Class: Vehicle"]
        assert sorted(result["removed"]) == ["Class: Animal", "Class: Mineral"]
        assert result["modified"] == []

    def test_compare_axioms_identical(self, service):
        """Test axiom comparison with identical sets."""
        axioms1 = ["Class: Person", "Class: Animal"]
        axioms2 = ["Class: Person", "Class: Animal"]

        result = service.compare_axioms(axioms1, axioms2)

        assert result["added"] == []
        assert result["removed"] == []
        assert result["modified"] == []

    def test_generate_diff_summary_no_changes(self, service):
        """Test summary generation with no changes."""
        diff = {"added": [], "removed": [], "modified": []}

        summary = service.generate_diff_summary(diff)

        assert "No differences found" in summary

    def test_generate_diff_summary_with_changes(self, service):
        """Test summary generation with changes."""
        diff = {
            "added": ["Class: Plant", "Class: Tree"],
            "removed": ["Class: Mineral"],
            "modified": []
        }

        summary = service.generate_diff_summary(diff)

        assert "2 axioms added" in summary
        assert "1 axiom removed" in summary

    @pytest.mark.asyncio
    async def test_compare_versions_cross_domain_error(self, use_case, valid_request,
                                                      mock_ontology_repository,
                                                      mock_authorization_service):
        """Test error when comparing versions from different domains."""
        version1 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=["Class: Person"],
        )
        version1.id = "version-1"

        version2 = OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.PHYSICS,
            axioms=["Class: Particle"],
        )
        version2.id = "version-2"

        mock_authorization_service.check_permission.return_value = None
        mock_ontology_repository.get_by_id.side_effect = [version1, version2]

        response = await use_case.execute(valid_request)

        assert response.success is False
        assert "same scientific domain" in response.error_message