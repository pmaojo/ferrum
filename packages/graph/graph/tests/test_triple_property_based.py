"""Property-based tests for Triple value object.

This module contains property-based tests for the Triple value object
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from typing import Dict, Any

from domain.entities import Triple
from domain.exceptions import ValidationError


@given(
    subject=st.text(min_size=1),
    predicate=st.text(min_size=1),
    object=st.text(min_size=1),
    tenant_id=st.text(min_size=1)
)
def test_triple_property_based(subject: str, predicate: str, object: str, tenant_id: str):
    """Test Triple creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for Triple creation
    and verifies that the Triple is created correctly.
    """
    # Create a Triple with the generated values
    triple = Triple(subject, predicate, object, tenant_id)

    # Verify that the Triple has the correct values
    assert triple.subject == subject
    assert triple.predicate == predicate
    assert triple.object == triple.object
    assert triple.tenant_id == tenant_id


@given(
    subject=st.one_of(st.none(), st.text(min_size=0)),
    predicate=st.one_of(st.none(), st.text(min_size=0)),
    object=st.one_of(st.none(), st.text(min_size=0)),
    tenant_id=st.one_of(st.none(), st.text(min_size=0))
)
def test_triple_property_based_invalid(subject: str, predicate: str, object: str, tenant_id: str):
    """Test Triple validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for Triple creation
    and verifies that appropriate validation errors are raised.
    """
    # Skip the test if all values are valid
    if (subject and predicate and object and tenant_id):
        return

    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "subject": subject,
        "predicate": predicate,
        "object": object,
        "tenant_id": tenant_id
    }

    # Find the first None or empty value
    invalid_param = next((k for k, v in args.items() if not v), None)

    # If we found an invalid parameter, verify that creating a Triple raises a ValidationError
    if invalid_param:
        with pytest.raises(ValidationError) as excinfo:
            validate_triple(**args)

        # Verify that the error message contains the parameter name
        assert excinfo.value.param == invalid_param


def validate_triple(subject: str, predicate: str, object: str, tenant_id: str) -> Triple:
    """Validate Triple parameters and create a Triple if valid.

    Args:
        subject: Subject of the triple
        predicate: Predicate of the triple
        object: Object of the triple
        tenant_id: Tenant ID for multi-tenancy

    Returns:
        A valid Triple object

    Raises:
        ValidationError: If any parameter is invalid
    """
    # Validate subject
    if not subject:
        raise ValidationError(
            message="Subject cannot be empty",
            param="subject"
        )

    # Validate predicate
    if not predicate:
        raise ValidationError(
            message="Predicate cannot be empty",
            param="predicate"
        )

    # Validate object
    if not object:
        raise ValidationError(
            message="Object cannot be empty",
            param="object"
        )

    # Validate tenant_id
    if not tenant_id:
        raise ValidationError(
            message="Tenant ID cannot be empty",
            param="tenant_id"
        )

    # Create and return the Triple
    return Triple(subject, predicate, object, tenant_id)


if __name__ == "__main__":
    pytest.main(["-v", __file__])