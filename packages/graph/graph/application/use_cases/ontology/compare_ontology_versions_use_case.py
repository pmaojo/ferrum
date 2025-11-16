"""Use case for comparing ontology versions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from application.exceptions import (
    ApplicationError,
    AuthorizationError,
    BusinessRuleViolationError,
    NotFoundError,
    ValidationError,
)
from application.ports import TracingPort
from application.use_cases.base_use_case import BaseUseCase
from application.use_cases.dto import (
    BaseResponseDTO,
    CompareOntologyVersionsRequestDTO,
    OntologyVersionDiffDTO,
)
from application.use_cases.ontology.create_ontology_use_case import (
    OntologyRepositoryPort,
)
from application.use_cases.ontology.update_ontology_use_case import (
    AuthorizationServicePort,
)
from domain.entities import OntologyVersion
from domain.utils.version_lineage import share_common_ancestor


# Ontology comparison service port
class OntologyComparisonServicePort:
    """Port for ontology comparison operations."""

    def compare_axioms(
        self, axioms1: List[str], axioms2: List[str]
    ) -> Dict[str, List[str]]:
        """Compare two sets of axioms and return differences.

        Args:
            axioms1: First set of axioms
            axioms2: Second set of axioms

        Returns:
            Dictionary with 'added', 'removed', and 'modified' keys
        """
        ...

    def generate_diff_summary(self, diff: Dict[str, List[str]]) -> str:
        """Generate a human-readable summary of the differences.

        Args:
            diff: Difference dictionary from compare_axioms

        Returns:
            Human-readable summary string
        """
        ...

    def detect_semantic_changes(
        self, axioms1: List[str], axioms2: List[str]
    ) -> List[Dict[str, str]]:
        """Detect semantic changes between axiom sets.

        Args:
            axioms1: First set of axioms
            axioms2: Second set of axioms

        Returns:
            List of semantic change descriptions
        """
        ...


@dataclass
class CompareOntologyVersionsResponse(BaseResponseDTO):
    """Response from ontology version comparison."""

    comparison: Optional[OntologyVersionDiffDTO] = None


class CompareOntologyVersionsUseCase(
    BaseUseCase[CompareOntologyVersionsRequestDTO, CompareOntologyVersionsResponse]
):
    """Use case for comparing ontology versions with diff generation logic."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        comparison_service: OntologyComparisonServicePort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies.

        Args:
            ontology_repository: Repository for ontology operations
            comparison_service: Service for ontology comparison
            authorization_service: Service for authorization checks
            tracer: Tracing service for observability
        """
        super().__init__()
        self.ontology_repository = ontology_repository
        self.comparison_service = comparison_service
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(
        self, request: CompareOntologyVersionsRequestDTO
    ) -> None:
        """Validate the compare ontology versions request.

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

        if not request.version1_id or not request.version1_id.strip():
            raise ValidationError(
                message="Version 1 ID is required and cannot be empty",
                field="version1_id",
            )

        if not request.version2_id or not request.version2_id.strip():
            raise ValidationError(
                message="Version 2 ID is required and cannot be empty",
                field="version2_id",
            )

        if request.version1_id == request.version2_id:
            raise ValidationError(
                message="Cannot compare a version with itself", field="version_ids"
            )

    async def _execute_internal(
        self, request: CompareOntologyVersionsRequestDTO
    ) -> CompareOntologyVersionsResponse:
        """Execute the ontology version comparison.

        Args:
            request: The validated request

        Returns:
            Response containing the comparison results

        Raises:
            NotFoundError: If either version doesn't exist
            AuthorizationError: If user doesn't have permission
            BusinessRuleViolationError: If versions are not comparable
        """
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="compare_ontology_versions",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check authorization for both versions
                self.authorization_service.check_permission(
                    request.user_id, request.version1_id, "read"
                )
                self.authorization_service.check_permission(
                    request.user_id, request.version2_id, "read"
                )

                # Get both ontology versions
                version1 = self.ontology_repository.get_by_id(
                    request.version1_id, request.tenant_id
                )
                if not version1:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.version1_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.version1_id,
                    )

                version2 = self.ontology_repository.get_by_id(
                    request.version2_id, request.tenant_id
                )
                if not version2:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.version2_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.version2_id,
                    )

                # Validate that versions are comparable
                self._validate_versions_comparable(version1, version2)

                # Perform comparison
                comparison_result = self._compare_versions(version1, version2)

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="ontology_versions_compared",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain1=version1.domain.value,
                    domain2=version2.domain.value,
                    changes_count=len(comparison_result.added_axioms)
                    + len(comparison_result.removed_axioms),
                )

                return CompareOntologyVersionsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    comparison=comparison_result,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="ontology_version_comparison_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(
                    e,
                    (
                        ValidationError,
                        NotFoundError,
                        AuthorizationError,
                        BusinessRuleViolationError,
                    ),
                ):
                    return CompareOntologyVersionsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to compare ontology versions: {str(e)}",
                    error_code="ONTOLOGY_VERSION_COMPARISON_FAILED",
                ) from e

    def _validate_versions_comparable(
        self, version1: OntologyVersion, version2: OntologyVersion
    ) -> None:
        """Validate that two versions can be meaningfully compared.

        Args:
            version1: First ontology version
            version2: Second ontology version

        Raises:
            BusinessRuleViolationError: If versions are not comparable
        """
        # Versions should be from the same tenant (already validated by getting them)

        # Versions must be from the same domain for meaningful comparison
        if version1.domain != version2.domain:
            raise BusinessRuleViolationError(
                message="Ontology versions must belong to the same scientific domain",
                rule_name="same_domain_required",
            )

        # Check if versions are related (parent-child relationship)
        if version1.is_parent_of(version2) or version2.is_parent_of(version1):
            # Related versions are always comparable
            return

        lookup = lambda vid: self.ontology_repository.get_by_id(vid, version1.tenant_id)
        if not share_common_ancestor(version1, version2, lookup):
            raise BusinessRuleViolationError(
                message="Versions belong to different lineages and cannot be compared",
                rule_name="versions_not_related",
            )

        # Validate that both versions have axioms to compare
        if not version1.axioms:
            raise BusinessRuleViolationError(
                message=f"Version {version1.id} has no axioms to compare",
                rule_name="version_has_axioms",
            )

        if not version2.axioms:
            raise BusinessRuleViolationError(
                message=f"Version {version2.id} has no axioms to compare",
                rule_name="version_has_axioms",
            )

    def _compare_versions(
        self, version1: OntologyVersion, version2: OntologyVersion
    ) -> OntologyVersionDiffDTO:
        """Compare two ontology versions and generate diff.

        Args:
            version1: First ontology version (baseline)
            version2: Second ontology version (comparison target)

        Returns:
            OntologyVersionDiffDTO with comparison results
        """
        # Use comparison service to get basic diff
        diff = self.comparison_service.compare_axioms(version1.axioms, version2.axioms)

        # Detect semantic changes
        semantic_changes = self.comparison_service.detect_semantic_changes(
            version1.axioms, version2.axioms
        )

        # Generate summary
        summary = self.comparison_service.generate_diff_summary(diff)

        # Create modified axioms mapping from semantic changes
        modified_axioms = []
        for change in semantic_changes:
            if change.get("type") == "modified":
                modified_axioms.append(
                    {
                        "old": change.get("old_axiom", ""),
                        "new": change.get("new_axiom", ""),
                    }
                )

        return OntologyVersionDiffDTO(
            added_axioms=diff.get("added", []),
            removed_axioms=diff.get("removed", []),
            modified_axioms=modified_axioms,
            summary=summary,
        )


class SimpleOntologyComparisonService:
    """Simple implementation of ontology comparison service."""

    def compare_axioms(
        self, axioms1: List[str], axioms2: List[str]
    ) -> Dict[str, List[str]]:
        """Compare two sets of axioms using set operations."""
        set1 = set(axioms1)
        set2 = set(axioms2)

        added = list(set2 - set1)
        removed = list(set1 - set2)

        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "modified": [],  # Simple implementation doesn't detect modifications
        }

    def generate_diff_summary(self, diff: Dict[str, List[str]]) -> str:
        """Generate a human-readable summary."""
        added_count = len(diff.get("added", []))
        removed_count = len(diff.get("removed", []))
        modified_count = len(diff.get("modified", []))

        if added_count == 0 and removed_count == 0 and modified_count == 0:
            return "No differences found between the ontology versions."

        summary_parts = []

        if added_count > 0:
            summary_parts.append(
                f"{added_count} axiom{'s' if added_count != 1 else ''} added"
            )

        if removed_count > 0:
            summary_parts.append(
                f"{removed_count} axiom{'s' if removed_count != 1 else ''} removed"
            )

        if modified_count > 0:
            summary_parts.append(
                f"{modified_count} axiom{'s' if modified_count != 1 else ''} modified"
            )

        return "Changes: " + ", ".join(summary_parts) + "."

    def detect_semantic_changes(
        self, axioms1: List[str], axioms2: List[str]
    ) -> List[Dict[str, str]]:
        """Simple semantic change detection."""
        # This is a placeholder implementation
        # A real implementation would use OWL reasoning to detect semantic equivalences
        return []


class CompareRelatedOntologyVersionsUseCase(
    BaseUseCase[CompareOntologyVersionsRequestDTO, CompareOntologyVersionsResponse]
):
    """Specialized use case for comparing related ontology versions (parent-child)."""

    def __init__(
        self,
        ontology_repository: OntologyRepositoryPort,
        comparison_service: OntologyComparisonServicePort,
        authorization_service: AuthorizationServicePort,
        tracer: TracingPort,
    ):
        """Initialize the use case with required dependencies."""
        super().__init__()
        self.ontology_repository = ontology_repository
        self.comparison_service = comparison_service
        self.authorization_service = authorization_service
        self.tracer = tracer

    def _validate_request_internal(
        self, request: CompareOntologyVersionsRequestDTO
    ) -> None:
        """Validate the request - same as parent class."""
        if not request.tenant_id or not request.tenant_id.strip():
            raise ValidationError(
                message="Tenant ID is required and cannot be empty", field="tenant_id"
            )

        if not request.user_id or not request.user_id.strip():
            raise ValidationError(
                message="User ID is required and cannot be empty", field="user_id"
            )

        if not request.version1_id or not request.version1_id.strip():
            raise ValidationError(
                message="Version 1 ID is required and cannot be empty",
                field="version1_id",
            )

        if not request.version2_id or not request.version2_id.strip():
            raise ValidationError(
                message="Version 2 ID is required and cannot be empty",
                field="version2_id",
            )

        if request.version1_id == request.version2_id:
            raise ValidationError(
                message="Cannot compare a version with itself", field="version_ids"
            )

    async def _execute_internal(
        self, request: CompareOntologyVersionsRequestDTO
    ) -> CompareOntologyVersionsResponse:
        """Execute comparison with additional validation for related versions."""
        start_time = datetime.utcnow()

        with self.tracer.start_span(
            name="compare_related_ontology_versions",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        ) as span:
            try:
                # Check authorization
                self.authorization_service.check_permission(
                    request.user_id, request.version1_id, "read"
                )
                self.authorization_service.check_permission(
                    request.user_id, request.version2_id, "read"
                )

                # Get both versions
                version1 = self.ontology_repository.get_by_id(
                    request.version1_id, request.tenant_id
                )
                if not version1:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.version1_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.version1_id,
                    )

                version2 = self.ontology_repository.get_by_id(
                    request.version2_id, request.tenant_id
                )
                if not version2:
                    raise NotFoundError(
                        message=f"Ontology version with ID '{request.version2_id}' not found",
                        resource_type="ontology_version",
                        resource_id=request.version2_id,
                    )

                # Validate that versions are related
                if not (
                    version1.is_parent_of(version2) or version2.is_parent_of(version1)
                ):
                    raise BusinessRuleViolationError(
                        message="Versions must be related (parent-child) for this comparison type",
                        rule_name="versions_must_be_related",
                    )

                # Determine parent and child for proper comparison direction
                if version1.is_parent_of(version2):
                    parent_version, child_version = version1, version2
                else:
                    parent_version, child_version = version2, version1

                # Perform comparison (parent as baseline, child as target)
                comparison_result = self._compare_parent_child(
                    parent_version, child_version
                )

                # Record metrics
                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                self.tracer.record_metric(
                    name="related_ontology_versions_compared",
                    value=1,
                    tenant_id=request.tenant_id,
                    domain=parent_version.domain.value,
                    changes_count=len(comparison_result.added_axioms)
                    + len(comparison_result.removed_axioms),
                )

                return CompareOntologyVersionsResponse(
                    success=True,
                    processing_time_ms=processing_time,
                    comparison=comparison_result,
                )

            except Exception as e:
                # Record error metrics
                self.tracer.record_metric(
                    name="related_ontology_version_comparison_errors",
                    value=1,
                    tenant_id=request.tenant_id,
                    error_type=type(e).__name__,
                )

                processing_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # Re-raise application exceptions as-is
                if isinstance(
                    e,
                    (
                        ValidationError,
                        NotFoundError,
                        AuthorizationError,
                        BusinessRuleViolationError,
                    ),
                ):
                    return CompareOntologyVersionsResponse(
                        success=False,
                        processing_time_ms=processing_time,
                        error_message=str(e),
                    )

                # Wrap other exceptions
                raise ApplicationError(
                    message=f"Failed to compare related ontology versions: {str(e)}",
                    error_code="RELATED_ONTOLOGY_VERSION_COMPARISON_FAILED",
                ) from e

    def _compare_parent_child(
        self, parent: OntologyVersion, child: OntologyVersion
    ) -> OntologyVersionDiffDTO:
        """Compare parent and child versions with enhanced context."""
        # Use comparison service
        diff = self.comparison_service.compare_axioms(parent.axioms, child.axioms)

        # Generate enhanced summary for parent-child relationship
        added_count = len(diff.get("added", []))
        removed_count = len(diff.get("removed", []))

        if added_count == 0 and removed_count == 0:
            summary = f"Child version is identical to parent version."
        else:
            summary = f"Child version evolution: {added_count} axioms added, {removed_count} axioms removed from parent."

        return OntologyVersionDiffDTO(
            added_axioms=diff.get("added", []),
            removed_axioms=diff.get("removed", []),
            modified_axioms=[],  # Simple implementation
            summary=summary,
        )
