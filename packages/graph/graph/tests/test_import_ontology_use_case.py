"""Tests for ImportOntologyUseCase."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List, Optional

from domain.entities import OntologyVersion, ScientificDomain, ValidationReport
from application.exceptions import (
    ValidationError,
    BusinessRuleViolationError,
    DependencyError,
    ApplicationError
)
from application.use_cases.ontology.import_ontology_use_case import (
    ImportOntologyUseCase,
    ImportOntologyResponse,
    ExternalContentFetcherPort,
    FormatDetectionServicePort,
    SimpleFormatDetectionService,
    SimpleExternalContentFetcher
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
    SubscriptionServicePort,
    OntologyParserPort
)
from application.use_cases.dto import ImportOntologyRequestDTO, OntologyDTO
from application.ports import OntologyValidatorPort, TracingPort


class TestImportOntologyUseCase:
    """Test cases for ImportOntologyUseCase."""

    @pytest.fixture
    def mock_ontology_repository(self):
        """Mock ontology repository."""
        repo = Mock(spec=OntologyRepositoryPort)
        repo.get_version_name.return_value = None
        return repo

    @pytest.fixture
    def mock_ontology_validator(self):
        """Mock ontology validator."""
        return Mock(spec=OntologyValidatorPort)

    @pytest.fixture
    def mock_ontology_parser(self):
        """Mock ontology parser."""
        return Mock(spec=OntologyParserPort)

    @pytest.fixture
    def mock_subscription_service(self):
        """Mock subscription service."""
        return Mock(spec=SubscriptionServicePort)

    @pytest.fixture
    def mock_content_fetcher(self):
        """Mock content fetcher."""
        return Mock(spec=ExternalContentFetcherPort)

    @pytest.fixture
    def mock_format_detector(self):
        """Mock format detector."""
        return Mock(spec=FormatDetectionServicePort)

    @pytest.fixture
    def mock_tracer(self):
        """Mock tracer."""
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def use_case(self, mock_ontology_repository, mock_ontology_validator,
                 mock_ontology_parser, mock_subscription_service,
                 mock_content_fetcher, mock_format_detector, mock_tracer):
        """Create use case instance with mocked dependencies."""
        return ImportOntologyUseCase(
            ontology_repository=mock_ontology_repository,
            ontology_validator=mock_ontology_validator,
            ontology_parser=mock_ontology_parser,
            subscription_service=mock_subscription_service,
            content_fetcher=mock_content_fetcher,
            format_detector=mock_format_detector,
            tracer=mock_tracer
        )

    @pytest.fixture
    def valid_url_request(self):
        """Valid import ontology request with URL."""
        return ImportOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Imported Biology Ontology",
            description="An ontology imported from external source",
            domain="biology",
            source_url="https://example.com/biology.owl",
            format="owl"
        )

    @pytest.fixture
    def valid_content_request(self):
        """Valid import ontology request with content."""
        return ImportOntologyRequestDTO(
            tenant_id="tenant-123",
            user_id="user-456",
            name="Imported Biology Ontology",
            description="An ontology imported from content",
            domain="biology",
            source_content="<owl:Ontology>...</owl:Ontology>",
            format="owl"
        )

    @pytest.fixture
    def sample_owl_content(self):
        """Sample OWL content for testing."""
        return """<?xml version="1.0"?>
<owl:Ontology xmlns:owl="http://www.w3.org/2002/07/owl#">
    <owl:Class rdf:about="#Person"/>
    <owl:Class rdf:about="#Animal"/>
    <owl:ObjectProperty rdf:about="#hasParent"/>
</owl:Ontology>"""

    @pytest.fixture
    def sample_axioms(self):
        """Sample axioms for testing."""
        return [
            "Class: Person",
            "Class: Animal",
            "ObjectProperty: hasParent"
        ]

    @pytest.fixture
    def sample_ontology_version(self, sample_axioms):
        """Sample ontology version for testing."""
        return OntologyVersion.create(
            tenant_id="tenant-123",
            domain=ScientificDomain.BIOLOGY,
            axioms=sample_axioms
        )

    @pytest.mark.asyncio
    async def test_import_ontology_from_url_success(self, use_case, valid_url_request,
                                                  sample_owl_content, sample_axioms,
                                                  sample_ontology_version,
                                                  mock_ontology_repository,
                                                  mock_ontology_validator,
                                                  mock_ontology_parser,
                                                  mock_subscription_service,
                                                  mock_content_fetcher,
                                                  mock_format_detector):
        """Test successful ontology import from URL."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_content_fetcher.validate_url.return_value = True
        mock_content_fetcher.fetch_from_url.return_value = sample_owl_content
        mock_format_detector.is_supported_format.return_value = True
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_url_request)

        # Verify
        assert response.success is True
        assert response.ontology is not None
        assert response.ontology.name == "Imported Biology Ontology"
        assert response.ontology.domain == "biology"
        assert response.ontology.axiom_count == 3
        assert response.ontology.version == "1.0.0"
        assert response.error_message is None

        # Verify mock calls
        mock_subscription_service.check_ontology_limit.assert_called_once_with("tenant-123")
        mock_ontology_repository.get_by_name_and_domain.assert_called_once_with(
            "Imported Biology Ontology", ScientificDomain.BIOLOGY, "tenant-123"
        )
        mock_content_fetcher.validate_url.assert_called_once_with("https://example.com/biology.owl")
        mock_content_fetcher.fetch_from_url.assert_called_once_with("https://example.com/biology.owl")
        mock_ontology_parser.parse_content.assert_called_once_with(sample_owl_content, "owl")
        mock_ontology_validator.validate.assert_called_once()
        mock_ontology_repository.create.assert_called_once()
        mock_ontology_repository.set_version_name.assert_called_once_with(
            sample_ontology_version.id,
            "Imported Biology Ontology",
            "tenant-123",
        )

    @pytest.mark.asyncio
    async def test_import_ontology_from_content_success(self, use_case, valid_content_request,
                                                      sample_axioms, sample_ontology_version,
                                                      mock_ontology_repository,
                                                      mock_ontology_validator,
                                                      mock_ontology_parser,
                                                      mock_subscription_service,
                                                      mock_format_detector):
        """Test successful ontology import from content."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_format_detector.is_supported_format.return_value = True
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is True
        assert response.ontology is not None
        assert response.ontology.name == "Imported Biology Ontology"
        assert response.ontology.domain == "biology"

        # Verify content was used directly (no URL fetching)
        mock_ontology_parser.parse_content.assert_called_once_with(
            "<owl:Ontology>...</owl:Ontology>", "owl"
        )
        mock_ontology_repository.set_version_name.assert_called_once_with(
            sample_ontology_version.id,
            "Imported Biology Ontology",
            "tenant-123",
        )

    @pytest.mark.asyncio
    async def test_import_ontology_with_format_detection(self, use_case, valid_url_request,
                                                       sample_owl_content, sample_axioms,
                                                       sample_ontology_version,
                                                       mock_ontology_repository,
                                                       mock_ontology_validator,
                                                       mock_ontology_parser,
                                                       mock_subscription_service,
                                                       mock_content_fetcher,
                                                       mock_format_detector):
        """Test ontology import with automatic format detection."""
        # Remove format from request to trigger auto-detection
        valid_url_request.format = None

        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_content_fetcher.validate_url.return_value = True
        mock_content_fetcher.fetch_from_url.return_value = sample_owl_content
        mock_format_detector.detect_format.return_value = "owl"
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_url_request)

        # Verify
        assert response.success is True
        assert response.import_warnings is not None
        assert any("Auto-detected format: owl" in warning for warning in response.import_warnings)

        # Verify format detection was called
        mock_format_detector.detect_format.assert_called_once_with(sample_owl_content, "biology.owl")

    @pytest.mark.asyncio
    async def test_import_ontology_with_consistency_warnings(self, use_case, valid_content_request,
                                                           sample_axioms, sample_ontology_version,
                                                           mock_ontology_repository,
                                                           mock_ontology_validator,
                                                           mock_ontology_parser,
                                                           mock_subscription_service,
                                                           mock_format_detector):
        """Test ontology import with consistency warnings."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_format_detector.is_supported_format.return_value = True
        mock_ontology_parser.parse_content.return_value = sample_axioms
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=["UnsatisfiableClass"],
            repair_suggestions=["Remove conflicting axiom"],
            tenant_id="tenant-123",
            ontology_version_id=sample_ontology_version.id
        )
        mock_ontology_repository.create.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is True  # Should succeed with warnings
        assert response.import_warnings is not None
        assert any("consistency issues" in warning for warning in response.import_warnings)
        assert any("UnsatisfiableClass" in warning for warning in response.import_warnings)

    @pytest.mark.asyncio
    async def test_import_ontology_validation_errors(self, use_case):
        """Test validation errors for invalid requests."""
        test_cases = [
            # Missing tenant_id
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    source_content="content"
                ),
                "expected_field": "tenant_id"
            },
            # Missing user_id
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="",
                    name="Test",
                    domain="biology",
                    source_content="content"
                ),
                "expected_field": "user_id"
            },
            # Missing name
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="",
                    domain="biology",
                    source_content="content"
                ),
                "expected_field": "name"
            },
            # Invalid domain
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="invalid_domain",
                    source_content="content"
                ),
                "expected_field": "domain"
            },
            # No source provided
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology"
                ),
                "expected_field": "source"
            },
            # Both sources provided
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    source_url="http://example.com",
                    source_content="content"
                ),
                "expected_field": "source"
            },
            # Invalid URL
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    source_url="invalid-url"
                ),
                "expected_field": "source_url"
            },
            # Empty content
            {
                "request": ImportOntologyRequestDTO(
                    tenant_id="tenant-123",
                    user_id="user-456",
                    name="Test",
                    domain="biology",
                    source_content=""
                ),
                "expected_field": "source_content"
            }
        ]

        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                await use_case.execute(test_case["request"])

            assert exc_info.value.field == test_case["expected_field"]

    @pytest.mark.asyncio
    async def test_import_ontology_subscription_limit_exceeded(self, use_case, valid_content_request,
                                                             mock_subscription_service):
        """Test subscription limit exceeded error."""
        # Setup mock to raise limit exceeded error
        mock_subscription_service.check_ontology_limit.side_effect = BusinessRuleViolationError(
            message="Ontology limit exceeded",
            rule_name="ontology_limit"
        )

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is False
        assert "Ontology limit exceeded" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_duplicate_name_domain(self, use_case, valid_content_request,
                                                       sample_ontology_version,
                                                       mock_ontology_repository,
                                                       mock_subscription_service):
        """Test duplicate ontology name and domain error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = sample_ontology_version

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is False
        assert "already exists" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_url_not_accessible(self, use_case, valid_url_request,
                                                     mock_ontology_repository,
                                                     mock_subscription_service,
                                                     mock_content_fetcher):
        """Test URL not accessible error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_content_fetcher.validate_url.return_value = False

        # Execute
        response = await use_case.execute(valid_url_request)

        # Verify
        assert response.success is False
        assert "not accessible" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_fetch_error(self, use_case, valid_url_request,
                                             mock_ontology_repository,
                                             mock_subscription_service,
                                             mock_content_fetcher):
        """Test URL fetch error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_content_fetcher.validate_url.return_value = True
        mock_content_fetcher.fetch_from_url.side_effect = Exception("Network error")

        # Execute
        response = await use_case.execute(valid_url_request)

        # Verify
        assert response.success is False
        assert "Failed to fetch content from URL" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_format_detection_error(self, use_case, valid_url_request,
                                                        sample_owl_content,
                                                        mock_ontology_repository,
                                                        mock_subscription_service,
                                                        mock_content_fetcher,
                                                        mock_format_detector):
        """Test format detection error."""
        # Remove format to trigger detection
        valid_url_request.format = None

        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_content_fetcher.validate_url.return_value = True
        mock_content_fetcher.fetch_from_url.return_value = sample_owl_content
        mock_format_detector.detect_format.side_effect = Exception("Cannot detect format")

        # Execute
        response = await use_case.execute(valid_url_request)

        # Verify
        assert response.success is False
        assert "Could not detect ontology format" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_parse_error(self, use_case, valid_content_request,
                                             mock_ontology_repository,
                                             mock_subscription_service,
                                             mock_format_detector,
                                             mock_ontology_parser):
        """Test ontology parse error."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_format_detector.is_supported_format.return_value = True
        mock_ontology_parser.parse_content.side_effect = Exception("Invalid OWL syntax")

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is False
        assert "Failed to parse ontology content" in response.error_message

    @pytest.mark.asyncio
    async def test_import_ontology_severe_consistency_issues(self, use_case, valid_content_request,
                                                           sample_axioms,
                                                           mock_ontology_repository,
                                                           mock_ontology_validator,
                                                           mock_ontology_parser,
                                                           mock_subscription_service,
                                                           mock_format_detector):
        """Test import failure with severe consistency issues."""
        # Setup mocks
        mock_subscription_service.check_ontology_limit.return_value = None
        mock_ontology_repository.get_by_name_and_domain.return_value = None
        mock_format_detector.is_supported_format.return_value = True
        mock_ontology_parser.parse_content.return_value = sample_axioms

        # Create many unsatisfiable classes to trigger failure
        many_unsat_classes = [f"UnsatisfiableClass{i}" for i in range(15)]
        mock_ontology_validator.validate.return_value = ValidationReport(
            is_consistent=False,
            unsat_classes=many_unsat_classes,
            repair_suggestions=["Fix many issues"],
            tenant_id="tenant-123",
            ontology_version_id="test-id"
        )

        # Execute
        response = await use_case.execute(valid_content_request)

        # Verify
        assert response.success is False
        assert "too many consistency issues" in response.error_message

    def test_validate_request_none(self, use_case):
        """Test validation with None request."""
        with pytest.raises(ValidationError) as exc_info:
            use_case.validate_request(None)

        assert "Request cannot be None" in str(exc_info.value)


class TestSimpleFormatDetectionService:
    """Test cases for SimpleFormatDetectionService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return SimpleFormatDetectionService()

    def test_detect_format_from_filename_owl(self, service):
        """Test format detection from OWL filename."""
        result = service.detect_format("some content", "ontology.owl")
        assert result == "owl"

    def test_detect_format_from_filename_rdf(self, service):
        """Test format detection from RDF filename."""
        result = service.detect_format("some content", "ontology.rdf")
        assert result == "rdf"

    def test_detect_format_from_filename_ttl(self, service):
        """Test format detection from Turtle filename."""
        result = service.detect_format("some content", "ontology.ttl")
        assert result == "ttl"

    def test_detect_format_from_filename_jsonld(self, service):
        """Test format detection from JSON-LD filename."""
        result = service.detect_format("some content", "ontology.jsonld")
        assert result == "json-ld"

    def test_detect_format_from_content_owl(self, service):
        """Test format detection from OWL content."""
        content = '<?xml version="1.0"?><owl:Ontology>...</owl:Ontology>'
        result = service.detect_format(content)
        assert result == "owl"

    def test_detect_format_from_content_rdf(self, service):
        """Test format detection from RDF content."""
        content = '<?xml version="1.0"?><rdf:RDF>...</rdf:RDF>'
        result = service.detect_format(content)
        assert result == "rdf"

    def test_detect_format_from_content_turtle(self, service):
        """Test format detection from Turtle content."""
        content = '@prefix owl: <http://www.w3.org/2002/07/owl#> .'
        result = service.detect_format(content)
        assert result == "ttl"

    def test_detect_format_from_content_jsonld(self, service):
        """Test format detection from JSON-LD content."""
        content = '{"@context": "http://example.com/context"}'
        result = service.detect_format(content)
        assert result == "json-ld"

    def test_detect_format_unknown_content(self, service):
        """Test format detection failure with unknown content."""
        with pytest.raises(ValidationError) as exc_info:
            service.detect_format("unknown content format")

        assert "Could not detect ontology format" in str(exc_info.value)

    def test_is_supported_format(self, service):
        """Test supported format checking."""
        assert service.is_supported_format("owl") is True
        assert service.is_supported_format("rdf") is True
        assert service.is_supported_format("ttl") is True
        assert service.is_supported_format("json-ld") is True
        assert service.is_supported_format("unknown") is False


class TestSimpleExternalContentFetcher:
    """Test cases for SimpleExternalContentFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance."""
        return SimpleExternalContentFetcher()

    @patch('urllib.request.urlopen')
    def test_fetch_from_url_success(self, mock_urlopen, fetcher):
        """Test successful URL fetching."""
        # Setup mock
        mock_response = Mock()
        mock_response.read.return_value = b"ontology content"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute
        result = fetcher.fetch_from_url("http://example.com/ontology.owl")

        # Verify
        assert result == "ontology content"
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_fetch_from_url_error(self, mock_urlopen, fetcher):
        """Test URL fetching error."""
        # Setup mock to raise error
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        # Execute and verify exception
        with pytest.raises(DependencyError) as exc_info:
            fetcher.fetch_from_url("http://example.com/ontology.owl")

        assert "Failed to fetch URL" in str(exc_info.value)
        assert exc_info.value.dependency_name == "urllib"

    @patch('urllib.request.urlopen')
    def test_validate_url_success(self, mock_urlopen, fetcher):
        """Test successful URL validation."""
        # Setup mock
        mock_response = Mock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute
        result = fetcher.validate_url("http://example.com/ontology.owl")

        # Verify
        assert result is True

    @patch('urllib.request.urlopen')
    def test_validate_url_failure(self, mock_urlopen, fetcher):
        """Test URL validation failure."""
        # Setup mock to raise error
        mock_urlopen.side_effect = Exception("Network error")

        # Execute
        result = fetcher.validate_url("http://example.com/ontology.owl")

        # Verify
        assert result is False