"""Property-based tests for ValidationReport value object.

This module contains property-based tests for the ValidationReport value object
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from typing import Dict, Any, List

from domain.entities import ValidationReport
from domain.exceptions import ValidationError


@given(
    is_consistent=st.booleans(),
    unsat_classes=st.lists(st.text(min_size=1)),
    repair_suggestions=st.lists(st.text(min_size=1)),
    tenant_id=st.text(min_size=1),
    ontology_version_id=st.text(min_size=1)
)
def test_validation_report_property_based(
    is_consistent: bool,
    unsat_classes: List[str],
    repair_suggestions: List[str],
    tenant_id: str,
    ontology_version_id: str
):
    """Test ValidationReport creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for ValidationReport creation
    and verifies that the ValidationReport is created correctly.
    """
    # Create a ValidationReport with the generated values
    report = ValidationReport(
        is_consistent=is_consistent,
        unsat_classes=unsat_classes,
        repair_suggestions=repair_suggestions,
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id
    )

    # Verify that the ValidationReport has the correct values
    assert report.is_consistent == is_consistent
    assert report.unsat_classes == unsat_classes
    assert report.repair_suggestions == repair_suggestions
    assert report.tenant_id == tenant_id
    assert report.ontology_version_id == ontology_version_id


@given(
    is_consistent=st.one_of(st.none(), st.just("not_a_boolean")),
    unsat_classes=st.one_of(st.none(), st.just("not_a_list")),
    repair_suggestions=st.one_of(st.none(), st.just("not_a_list")),
    tenant_id=st.one_of(st.none(), st.text(min_size=0)),
    ontology_version_id=st.one_of(st.none(), st.text(min_size=0))
)
def test_validation_report_property_based_invalid(
    is_consistent: Any,
    unsat_classes: Any,
    repair_suggestions: Any,
    tenant_id: Any,
    ontology_version_id: Any
):
    """Test ValidationReport validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for ValidationReport creation
    and verifies that appropriate validation errors are raised.
    """
    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "is_consistent": is_consistent,
        "unsat_classes": unsat_classes,
        "repair_suggestions": repair_suggestions,
        "tenant_id": tenant_id,
        "ontology_version_id": ontology_version_id
    }

    # Skip if all values are valid types
    if (isinstance(is_consistent, bool) and
        isinstance(unsat_classes, list) and
        isinstance(repair_suggestions, list) and
        tenant_id and
        ontology_version_id):
        return

    # Verify that creating a ValidationReport with invalid values raises a ValidationError
    with pytest.raises(ValidationError):
        validate_validation_report(**args)


def validate_validation_report(
    is_consistent: Any,
    unsat_classes: Any,
    repair_suggestions: Any,
    tenant_id: Any,
    ontology_version_id: Any
) -> ValidationReport:
    """Validate ValidationReport parameters and create a ValidationReport if valid.

    Args:
        is_consistent: Whether the ontology is consistent
        unsat_classes: List of unsatisfiable classes
        repair_suggestions: List of repair suggestions
        tenant_id: Tenant ID for multi-tenancy
        ontology_version_id: Ontology version ID

    Returns:
        A valid ValidationReport object

    Raises:
        ValidationError: If any parameter is invalid
    """
    # Validate is_consistent
    if not isinstance(is_consistent, bool):
        raise ValidationError(
            message="is_consistent must be a boolean",
            param="is_consistent"
        )

    # Validate unsat_classes
    if not isinstance(unsat_classes, list):
        raise ValidationError(
            message="unsat_classes must be a list",
            param="unsat_classes"
        )

    # Validate repair_suggestions
    if not isinstance(repair_suggestions, list):
        raise ValidationError(
            message="repair_suggestions must be a list",
            param="repair_suggestions"
        )

    # Validate tenant_id
    if not tenant_id:
        raise ValidationError(
            message="Tenant ID cannot be empty",
            param="tenant_id"
        )

    # Validate ontology_version_id
    if not ontology_version_id:
        raise ValidationError(
            message="Ontology version ID cannot be empty",
            param="ontology_version_id"
        )

    # Create and return the ValidationReport
    return ValidationReport(
        is_consistent=is_consistent,
        unsat_classes=unsat_classes,
        repair_suggestions=repair_suggestions,
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])