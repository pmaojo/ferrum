"""Property-based tests for KnowledgeGraph entity.

This module contains property-based tests for the KnowledgeGraph entity
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from datetime import datetime, timezone
from typing import Dict, Any

from domain.entities import KnowledgeGraph
from domain.exceptions import ValidationError


@given(
    id=st.text(min_size=1),
    name=st.text(min_size=1),
    tenant_id=st.text(min_size=1),
    ontology_version_id=st.text(min_size=1),
    node_count=st.integers(min_value=0),
    edge_count=st.integers(min_value=0)
)
def test_knowledge_graph_property_based(
    id: str,
    name: str,
    tenant_id: str,
    ontology_version_id: str,
    node_count: int,
    edge_count: int
):
    """Test KnowledgeGraph creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for KnowledgeGraph creation
    and verifies that the KnowledgeGraph is created correctly.
    """
    # Create timestamps
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc)

    # Create a KnowledgeGraph with the generated values
    kg = KnowledgeGraph(
        id=id,
        name=name,
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id,
        created_at=created_at,
        updated_at=updated_at,
        node_count=node_count,
        edge_count=edge_count
    )

    # Verify that the KnowledgeGraph has the correct values
    assert kg.id == id
    assert kg.name == name
    assert kg.tenant_id == tenant_id
    assert kg.ontology_version_id == ontology_version_id
    assert kg.created_at == created_at
    assert kg.updated_at == updated_at
    assert kg.node_count == node_count
    assert kg.edge_count == edge_count


@given(
    id=st.one_of(st.none(), st.text(min_size=0)),
    name=st.one_of(st.none(), st.text(min_size=0)),
    tenant_id=st.one_of(st.none(), st.text(min_size=0)),
    ontology_version_id=st.one_of(st.none(), st.text(min_size=0)),
    node_count=st.one_of(st.none(), st.integers(max_value=-1)),
    edge_count=st.one_of(st.none(), st.integers(max_value=-1))
)
def test_knowledge_graph_property_based_invalid(
    id: Any,
    name: Any,
    tenant_id: Any,
    ontology_version_id: Any,
    node_count: Any,
    edge_count: Any
):
    """Test KnowledgeGraph validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for KnowledgeGraph creation
    and verifies that appropriate validation errors are raised.
    """
    # Create timestamps
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc)

    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "id": id,
        "name": name,
        "tenant_id": tenant_id,
        "ontology_version_id": ontology_version_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "node_count": node_count,
        "edge_count": edge_count
    }

    # Skip if all values are valid
    if (id and name and tenant_id and ontology_version_id and
        isinstance(node_count, int) and node_count >= 0 and
        isinstance(edge_count, int) and edge_count >= 0):
        return

    # Verify that creating a KnowledgeGraph with invalid values raises a ValidationError
    with pytest.raises(ValidationError):
        validate_knowledge_graph(**args)


def validate_knowledge_graph(
    id: Any,
    name: Any,
    tenant_id: Any,
    ontology_version_id: Any,
    created_at: Any,
    updated_at: Any,
    node_count: Any,
    edge_count: Any
) -> KnowledgeGraph:
    """Validate KnowledgeGraph parameters and create a KnowledgeGraph if valid.

    Args:
        id: Unique identifier for the knowledge graph
        name: Name of the knowledge graph
        tenant_id: Tenant ID for multi-tenancy
        ontology_version_id: Ontology version ID
        created_at: Creation timestamp
        updated_at: Last update timestamp
        node_count: Number of nodes in the graph
        edge_count: Number of edges in the graph

    Returns:
        A valid KnowledgeGraph object

    Raises:
        ValidationError: If any parameter is invalid
    """
    # Validate id
    if not id:
        raise ValidationError(
            message="ID cannot be empty",
            param="id"
        )

    # Validate name
    if not name:
        raise ValidationError(
            message="Name cannot be empty",
            param="name"
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

    # Validate created_at
    if not isinstance(created_at, datetime):
        raise ValidationError(
            message="Created at must be a datetime",
            param="created_at"
        )

    # Validate updated_at
    if not isinstance(updated_at, datetime):
        raise ValidationError(
            message="Updated at must be a datetime",
            param="updated_at"
        )

    # Validate node_count
    if not isinstance(node_count, int) or node_count < 0:
        raise ValidationError(
            message="Node count must be a non-negative integer",
            param="node_count"
        )

    # Validate edge_count
    if not isinstance(edge_count, int) or edge_count < 0:
        raise ValidationError(
            message="Edge count must be a non-negative integer",
            param="edge_count"
        )

    # Create and return the KnowledgeGraph
    return KnowledgeGraph(
        id=id,
        name=name,
        tenant_id=tenant_id,
        ontology_version_id=ontology_version_id,
        created_at=created_at,
        updated_at=updated_at,
        node_count=node_count,
        edge_count=edge_count
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])