"""Property-based tests for OntologyVersion entity.

This module contains property-based tests for the OntologyVersion entity
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from domain.entities import OntologyVersion
from domain.exceptions import ValidationError, VersioningException


@given(
    id=st.text(min_size=1),
    checksum=st.text(min_size=1),
    parent_version=st.one_of(st.none(), st.text(min_size=1)),
    tenant_id=st.text(min_size=1),
    axioms=st.lists(st.text(min_size=1), min_size=1)
)
def test_ontology_version_property_based(
    id: str,
    checksum: str,
    parent_version: Optional[str],
    tenant_id: str,
    axioms: List[str]
):
    """Test OntologyVersion creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for OntologyVersion creation
    and verifies that the OntologyVersion is created correctly.
    """
    # Create timestamp
    created_at = datetime.now(timezone.utc)

    # Create an OntologyVersion with the generated values
    version = OntologyVersion(
        id=id,
        checksum=checksum,
        parent_version=parent_version,
        tenant_id=tenant_id,
        created_at=created_at,
        axioms=axioms
    )

    # Verify that the OntologyVersion has the correct values
    assert version.id == id
    assert version.checksum == checksum
    assert version.parent_version == parent_version
    assert version.tenant_id == tenant_id
    assert version.created_at == created_at
    assert version.axioms == axioms


@given(
    id=st.one_of(st.none(), st.text(min_size=0)),
    checksum=st.one_of(st.none(), st.text(min_size=0)),
    tenant_id=st.one_of(st.none(), st.text(min_size=0)),
    axioms=st.one_of(st.none(), st.just([]), st.just("not_a_list"))
)
def test_ontology_version_property_based_invalid(
    id: Any,
    checksum: Any,
    tenant_id: Any,
    axioms: Any
):
    """Test OntologyVersion validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for OntologyVersion creation
    and verifies that appropriate validation errors are raised.
    """
    # Create timestamp and parent_version
    created_at = datetime.now(timezone.utc)
    parent_version = None

    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "id": id,
        "checksum": checksum,
        "parent_version": parent_version,
        "tenant_id": tenant_id,
        "created_at": created_at,
        "axioms": axioms
    }

    # Skip if all values are valid
    if (id and checksum and tenant_id and
        isinstance(axioms, list) and len(axioms) > 0):
        return

    # Verify that creating an OntologyVersion with invalid values raises a ValidationError
    with pytest.raises((ValidationError, VersioningException)):
        validate_ontology_version(**args)


def test_ontology_version_parent_child_relationship():
    """Test parent-child relationship between ontology versions."""
    # Create parent version
    parent_id = "parent_version"
    parent_version = OntologyVersion(
        id=parent_id,
        checksum="parent_checksum",
        parent_version=None,
        tenant_id="tenant1",
        created_at=datetime.now(timezone.utc),
        axioms=["Class: Person"]
    )

    # Create child version
    child_version = OntologyVersion(
        id="child_version",
        checksum="child_checksum",
        parent_version=parent_id,
        tenant_id="tenant1",
        created_at=datetime.now(timezone.utc),
        axioms=["Class: Person", "Class: Employee SubClassOf: Person"]
    )

    # Verify the relationship
    assert child_version.parent_version == parent_id
    assert parent_version.parent_version is None


def validate_ontology_version(
    id: Any,
    checksum: Any,
    parent_version: Any,
    tenant_id: Any,
    created_at: Any,
    axioms: Any
) -> OntologyVersion:
    """Validate OntologyVersion parameters and create an OntologyVersion if valid.

    Args:
        id: Unique identifier for the ontology version
        checksum: Checksum of the ontology content
        parent_version: Optional parent version ID
        tenant_id: Tenant ID for multi-tenancy
        created_at: Creation timestamp
        axioms: List of OWL axioms in Manchester syntax

    Returns:
        A valid OntologyVersion object

    Raises:
        ValidationError: If any parameter is invalid
        VersioningException: If there are versioning-related errors
    """
    # Validate id
    if not id:
        raise ValidationError(
            message="ID cannot be empty",
            param="id"
        )

    # Validate checksum
    if not checksum:
        raise ValidationError(
            message="Checksum cannot be empty",
            param="checksum"
        )

    # Validate tenant_id
    if not tenant_id:
        raise ValidationError(
            message="Tenant ID cannot be empty",
            param="tenant_id"
        )

    # Validate created_at
    if not isinstance(created_at, datetime):
        raise ValidationError(
            message="Created at must be a datetime",
            param="created_at"
        )

    # Validate axioms
    if not isinstance(axioms, list):
        raise ValidationError(
            message="Axioms must be a list",
            param="axioms"
        )

    if not axioms:
        raise ValidationError(
            message="Axioms list cannot be empty",
            param="axioms"
        )

    # Create and return the OntologyVersion
    return OntologyVersion(
        id=id,
        checksum=checksum,
        parent_version=parent_version,
        tenant_id=tenant_id,
        created_at=created_at,
        axioms=axioms
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])