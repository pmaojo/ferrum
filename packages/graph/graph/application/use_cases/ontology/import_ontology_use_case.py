"""Use case for importing ontologies from external sources."""

import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from application.exceptions import (
    ApplicationError,
    BusinessRuleViolationError,
    DependencyError,
    ValidationError,
)
from application.ports import (
    OntologyValidatorPort,
    SubscriptionServicePort,
    TracingPort,
)
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    ImportOntologyRequestDTO,
    OntologyDTO,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyParserPort,
    OntologyRepositoryPort,
)
from domain.entities import OntologyVersion, ScientificDomain


# External content fetcher port
class ExternalContentFetcherPort:
    """Port for fetching content from external sources."""

    def fetch_from_url(self, url: str) -> str:
        """Fetch content from a URL.

        Args:
            url: URL to fetch content from

        Returns:
            Content as string

        Raises:
            DependencyError: If fetching fails
        """
        ...

    def validate_url(self, url: str) -> bool:
        """Validate if URL is accessible and safe.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and accessible
        """
        ...


# Format detection service port
class FormatDetectionServicePort:
    """Port for detecting ontology formats."""

    def detect_format(self, content: str, filename: Optional[str] = None) -> str:
        """Detect the format of ontology content.

        Args:
            content: Ontology content
            filename: Optional filename for additional hints

        Returns:
            Detected format (owl, rdf, ttl, json-ld)

        Raises:
            ValidationError: If format cannot be detected
        """
        ...

    def is_supported_format(self, format: str) -> bool:
        """Check if a format is supported.

        Args:
            format: Format string to check

        Returns:
            True if format is supported
        """
        ...


@dataclass
class ImportOntologyResponse(BaseResponseDTO):
    """Response from ontology import."""

    ontology: Optional[OntologyDTO] = None
    import_warnings: List[str] = None


class ImportOntologyUseCase(
    BaseUseCase[ImportOntologyRequestDTO, ImportOntologyResponse]
):
    """Use case for importing ontologies with format detection and parsing."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        ontology_validator: OntologyValidatorPort,
        ontology_parser: OntologyParserPort,
        subscription_service: SubscriptionServicePort,
        content_fetcher: ExternalContentFetcherPort,
        format_detector: FormatDetectionServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            ontology_validator: Service for ontology validation
            ontology_parser: Service for parsing ontology content
            subscription_service: Service for subscription limit checking
            content_fetcher: Service for fetching external content
            format_detector: Service for format detection
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.ontology_validator = ontology_validator
        self.ontology_parser = ontology_parser
        self.subscription_service = subscription_service
        self.content_fetcher = content_fetcher
        self.format_detector = format_detector
        self.tracer = tracer

    def _validate_request_internal(self, request: ImportOntologyRequestDTO) -> None:
        """Validate the import ontology request.

        Args:
            request: The request to validate

        Raises:
            ValidationError: If validation fails
        """
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.name or not request.name.strip():
            raise ValidationError(
                message="Ontology name is required and cannot be empty", field="name"
            )

        if len(request.name) > 255:
            raise ValidationError(
                message="Ontology name cannot exceed 255 characters", field="name"
            )

        if not request.domain or not request.domain.strip():
            raise ValidationError(
                message="Domain is required and cannot be empty", field="domain"
            )

        # Validate domain is a valid ScientificDomain value
        try:
            ScientificDomain(request.domain)
        except ValueError:
            valid_domains = [d.value for d in ScientificDomain]
            raise ValidationError(
                message=f"Domain must be one of: {', '.join(valid_domains)}",
                field="domain",
            )

        # Must have either source_url or source_content
        if not request.source_url and not request.source_content:
            raise ValidationError(
                message="Either source_url or source_content must be provided",
                field="source",
            )

        # Cannot have both source_url and source_content
        if request.source_url and request.source_content:
            raise ValidationError(
                message="Cannot provide both source_url and source_content",
                field="source",
            )

        # Validate URL format if provided
        if request.source_url:
            if not self._is_valid_url(request.source_url):
                raise ValidationError(message="Invalid URL format", field="source_url")

        # Validate content if provided
        if request.source_content:
            if not request.source_content.strip():
                raise ValidationError(
                    message="Source content cannot be empty", field="source_content"
                )

        # Validate format if provided
        if request.format:
            if not self.format_detector.is_supported_format(request.format):
                raise ValidationError(
                    message=f"Unsupported format: {request.format}", field="format"
                )

        if request.description and len(request.description) > 1000:
            raise ValidationError(
                message="Description cannot exceed 1000 characters", field="description"
            )

    async def _execute_internal(
        self, request: ImportOntologyRequestDTO
    ) -> ImportOntologyResponse:
        """Execute the ontology import.

        Args:
            request: The validated request

        Returns:
            Response containing the imported ontology

        Raises:
            BusinessRuleViolationError: If business rules are violated
            DependencyError: If external dependencies fail
            ValidationError: If ontology content is invalid
        """
        start_time = datetime.utcnow()
        warnings = []

        with self.tracer.start_span(
            name="import_ontology", tenant_id=request.tenant_id, user_id=request.user_id
        ) as span:
            try:
                # Check subscription limits
                self.subscription_service.check_ontology_limit(request.tenant_id)

                # Convert domain string to enum
                domain = ScientificDomain(request.domain)

                # Check if ontology with same name and domain already exists
                existing_ontology = self.ontology_repository.get_by_name_and_domain(
                    request.name, domain, request.tenant_id
                )
                if existing_ontology:
                    raise BusinessRuleViolationError(
                        message=f"Ontology with name '{request.name}' and domain '{request.domain}' already exists",
                        rule_name="unique_ontology_name_domain_per_tenant",
                    )

                # Get ontology content
                content = await self._get_ontology_content(request, warnings)

                # Detect format if not provided
                detected_format = request.format
                if not detected_format:
                    try:
                        detected_format = self.format_detector.detect_format(
                            content,
                            (
                                self._extract_filename_from_url(request.source_url)
                                if request.source_url
                                else None
                            ),
                        )
                        warnings.append(f"Auto-detected format: {detected_format}")
                    except Exception as e:
                        raise ValidationError(
                            message=f"Could not detect ontology format: {str(e)}",
                            field="format",
                        )

                # Parse ontology content into axioms
                try:
                    axioms = self.ontology_parser.parse_content(
                        content, detected_format
                    )
                except Exception as e:
                    raise ValidationError(
                        message=f"Failed to parse ontology content: {str(e)}",
                        field="content",
                    )

                # Create ontology version
                ontology = OntologyVersion.create(
                    tenant_id=request.tenant_id, domain=domain, axioms=axioms
                )

                if request.competency_questions:
                    ontology.metadata["competency_questions"] = request.competency_questions

                # Validate ontology consistency
                validation_result = self.ontology_validator.validate(
                    triples=[],  # Empty triples for ontology-only validation
                    ontology_version_id=ontology.id,
                )

                if not validation_result.is_consistent:
                    # For imports, we might want to allow inconsistent ontologies with warnings
                    warnings.append("Imported ontology has consistency issues")
                    warnings.extend(
                        [
                            f"Unsatisfiable class: {cls}"
                            for cls in validation_result.unsat_classes
                        ]
                    )

                    # Optionally, we could still fail the import for severely inconsistent ontologies
                    if len(validation_result.unsat_classes) > 10:  # Arbitrary threshold
                        raise ValidationError(
                            message=f"Ontology has too many consistency issues: {', '.join(validation_result.unsat_classes[:5])}...",
                            field="content",
                            validation_errors=[
                                {
                                    "type": "consistency_error",
                                    "unsat_classes": validation_result.unsat_classes,
                                    "repair_suggestions": validation_result.repair_suggestions,
                                }
                            ],
                        )

                # Save to repository
                created_ontology = self.ontology_repository.create(ontology)
                # Persist ontology name for this version
                self.ontology_repository.set_version_name(
                    created_ontology.id,
                    request.name,
                    request.tenant_id,
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_imported",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=request.domain,
                    format=detected_format,
                    source_type="url" if request.source_url else "content",
                )

                # Create response DTO
                ontology_dto = OntologyDTO(
                    id=created_ontology.id,
                    name=request.name,
                    description=request.description,
                    domain=created_ontology.domain.value,
                    version="1.0.0",  # Imported ontologies start at version 1.0.0
                    parent_version_id=None,
                    tenant_id=created_ontology.tenant_id,
                    created_at=created_ontology.created_at,
                    checksum=created_ontology.checksum,
                    axiom_count=len(created_ontology.axioms),
                    competency_questions=request.competency_questions,
                )

                return ImportOntologyResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    ontology=ontology_dto,
                    import_warnings=warnings if warnings else None,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_import_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(
                    e, (ValidationError, BusinessRuleViolationError, DependencyError)
                ):
                    return ImportOntologyResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                        import_warnings=warnings if warnings else None,
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to import ontology: {str(e)}",
                    error_code="ONTOLOGY_IMPORT_FAILED",
                ) from e

    async def _get_ontology_content(
        self, request: ImportOntologyRequestDTO, warnings: List[str]
    ) -> str:
        """Get ontology content from URL or direct content.

        Args:
            request: The import request
            warnings: List to append warnings to

        Returns:
            Ontology content as string

        Raises:
            DependencyError: If URL fetching fails
            ValidationError: If content is invalid
        """
        if request.source_url:
            # Validate URL accessibility
            if not self.content_fetcher.validate_url(request.source_url):
                raise DependencyError(
                    message=f"URL is not accessible: {request.source_url}",
                    dependency_name="external_url",
                )

            # Fetch content from URL
            try:
                content = self.content_fetcher.fetch_from_url(request.source_url)
                warnings.append(f"Content fetched from URL: {request.source_url}")
                return content
            except Exception as e:
                raise DependencyError(
                    message=f"Failed to fetch content from URL: {str(e)}",
                    dependency_name="external_url",
                    dependency_error=str(e),
                )
        else:
            # Use provided content
            return request.source_content

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if URL format is valid
        """
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
                "ftp",
            ]
        except Exception:
            return False

    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """Extract filename from URL for format detection hints.

        Args:
            url: URL to extract filename from

        Returns:
            Filename if extractable, None otherwise
        """
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            if path:
                filename = path.split("/")[-1]
                if "." in filename:
                    return filename
        except Exception:
            pass
        return None


class SimpleFormatDetectionService:
    """Simple implementation of format detection service."""

    SUPPORTED_FORMATS = ["owl", "rdf", "ttl", "json-ld"]

    def detect_format(self, content: str, filename: Optional[str] = None) -> str:
        """Detect format based on content and filename."""
        content_lower = content.lower().strip()

        # Check filename extension first
        if filename:
            filename_lower = filename.lower()
            if filename_lower.endswith(".owl"):
                return "owl"
            elif filename_lower.endswith(".rdf"):
                return "rdf"
            elif filename_lower.endswith(".ttl"):
                return "ttl"
            elif filename_lower.endswith(".jsonld") or filename_lower.endswith(
                ".json-ld"
            ):
                return "json-ld"

        # Check content patterns
        if content_lower.startswith("<?xml") and "owl:ontology" in content_lower:
            return "owl"
        elif content_lower.startswith("<?xml") and (
            "rdf:rdf" in content_lower or "rdf:description" in content_lower
        ):
            return "rdf"
        elif "@prefix" in content_lower or content_lower.startswith("@base"):
            return "ttl"
        elif content_lower.startswith("{") and '"@context"' in content_lower:
            return "json-ld"
        elif "owl:ontology" in content_lower:
            return "owl"
        elif "rdf:" in content_lower:
            return "rdf"

        # Default fallback
        raise ValidationError(
            message="Could not detect ontology format from content", field="format"
        )

    def is_supported_format(self, format: str) -> bool:
        """Check if format is supported."""
        return format.lower() in self.SUPPORTED_FORMATS


class SimpleExternalContentFetcher:
    """Simple implementation of external content fetcher."""

    def fetch_from_url(self, url: str) -> str:
        """Fetch content from URL using urllib."""
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8")
                return content
        except urllib.error.URLError as e:
            raise DependencyError(
                message=f"Failed to fetch URL: {str(e)}",
                dependency_name="urllib",
                dependency_error=str(e),
            )
        except Exception as e:
            raise DependencyError(
                message=f"Unexpected error fetching URL: {str(e)}",
                dependency_name="urllib",
                dependency_error=str(e),
            )

    def validate_url(self, url: str) -> bool:
        """Validate URL accessibility with a HEAD request."""
        import urllib.error
        import urllib.request

        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False
