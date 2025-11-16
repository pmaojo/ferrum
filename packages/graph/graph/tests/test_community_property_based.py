"""Property-based tests for Community value object.

This module contains property-based tests for the Community value object
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from typing import Dict, Any, List

from domain.entities import Community
from domain.exceptions import ClusteringError


@given(
    id=st.text(min_size=1),
    centroid_embedding=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1),
    node_ids=st.lists(st.text(min_size=1), min_size=1),
    size=st.integers(min_value=1),
    tenant_id=st.text(min_size=1)
)
def test_community_property_based(
    id: str,
    centroid_embedding: List[float],
    node_ids: List[str],
    size: int,
    tenant_id: str
):
    """Test Community creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for Community creation
    and verifies that the Community is created correctly.
    """
    # Create a Community with the generated values
    community = Community(
        id=id,
        centroid_embedding=centroid_embedding,
        node_ids=node_ids,
        size=size,
        tenant_id=tenant_id
    )

    # Verify that the Community has the correct values
    assert community.id == id
    assert community.centroid_embedding == centroid_embedding
    assert community.node_ids == node_ids
    assert community.size == size
    assert community.tenant_id == tenant_id


@given(
    id=st.one_of(st.none(), st.text(min_size=0)),
    centroid_embedding=st.one_of(st.none(), st.just([]), st.just("not_a_list")),
    node_ids=st.one_of(st.none(), st.just([]), st.just("not_a_list")),
    size=st.one_of(st.none(), st.integers(max_value=0), st.just("not_an_int")),
    tenant_id=st.one_of(st.none(), st.text(min_size=0))
)
def test_community_property_based_invalid(
    id: Any,
    centroid_embedding: Any,
    node_ids: Any,
    size: Any,
    tenant_id: Any
):
    """Test Community validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for Community creation
    and verifies that appropriate validation errors are raised.
    """
    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "id": id,
        "centroid_embedding": centroid_embedding,
        "node_ids": node_ids,
        "size": size,
        "tenant_id": tenant_id
    }

    # Skip if all values are valid
    if (id and
        isinstance(centroid_embedding, list) and len(centroid_embedding) > 0 and
        isinstance(node_ids, list) and len(node_ids) > 0 and
        isinstance(size, int) and size > 0 and
        tenant_id):
        return

    # Verify that creating a Community with invalid values raises a ClusteringError
    with pytest.raises(ClusteringError):
        validate_community(**args)


def test_community_size_consistency():
    """Test that Community size is consistent with node_ids length."""
    # Create a Community with consistent size
    community = Community(
        id="community1",
        centroid_embedding=[0.1, 0.2, 0.3],
        node_ids=["node1", "node2", "node3"],
        size=3,
        tenant_id="tenant1"
    )

    # Verify that the size matches the number of node_ids
    assert community.size == len(community.node_ids)

    # Create a Community with inconsistent size
    # This is allowed by the NamedTuple but should be validated by the application
    community_inconsistent = Community(
        id="community2",
        centroid_embedding=[0.1, 0.2, 0.3],
        node_ids=["node1", "node2", "node3"],
        size=5,  # Inconsistent with node_ids length
        tenant_id="tenant1"
    )

    # Verify that the size does not match the number of node_ids
    assert community_inconsistent.size != len(community_inconsistent.node_ids)

    # Validate that our validation function catches this inconsistency
    with pytest.raises(ClusteringError) as excinfo:
        validate_community_size_consistency(community_inconsistent)

    # The error message contains the size and length values
    assert str(community_inconsistent.size) in str(excinfo.value)
    assert str(len(community_inconsistent.node_ids)) in str(excinfo.value)


def validate_community(
    id: Any,
    centroid_embedding: Any,
    node_ids: Any,
    size: Any,
    tenant_id: Any
) -> Community:
    """Validate Community parameters and create a Community if valid.

    Args:
        id: Unique identifier for the community
        centroid_embedding: Centroid embedding vector
        node_ids: List of node IDs in the community
        size: Number of nodes in the community
        tenant_id: Tenant ID for multi-tenancy

    Returns:
        A valid Community object

    Raises:
        ClusteringError: If any parameter is invalid
    """
    # Validate id
    if not id:
        raise ClusteringError(
            message="Community ID cannot be empty",
            algorithm="community_detection"
        )

    # Validate centroid_embedding
    if not isinstance(centroid_embedding, list) or not centroid_embedding:
        raise ClusteringError(
            message="Centroid embedding must be a non-empty list of floats",
            algorithm="community_detection"
        )

    # Validate node_ids
    if not isinstance(node_ids, list) or not node_ids:
        raise ClusteringError(
            message="Node IDs must be a non-empty list of strings",
            algorithm="community_detection"
        )

    # Validate size
    if not isinstance(size, int) or size <= 0:
        raise ClusteringError(
            message="Size must be a positive integer",
            algorithm="community_detection"
        )

    # Validate tenant_id
    if not tenant_id:
        raise ClusteringError(
            message="Tenant ID cannot be empty",
            algorithm="community_detection"
        )

    # Create the Community
    community = Community(
        id=id,
        centroid_embedding=centroid_embedding,
        node_ids=node_ids,
        size=size,
        tenant_id=tenant_id
    )

    # Validate size consistency
    validate_community_size_consistency(community)

    return community


def validate_community_size_consistency(community: Community) -> None:
    """Validate that Community size is consistent with node_ids length.

    Args:
        community: Community to validate

    Raises:
        ClusteringError: If size is inconsistent with node_ids length
    """
    if community.size != len(community.node_ids):
        raise ClusteringError(
            message=f"Community size {community.size} does not match node_ids length {len(community.node_ids)}",
            algorithm="community_detection"
        )


if __name__ == "__main__":
    pytest.main(["-v", __file__])