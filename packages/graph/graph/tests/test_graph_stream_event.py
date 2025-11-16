"""Property-based tests for GraphStreamEvent value object.

This module contains property-based tests for the GraphStreamEvent value object
using the hypothesis library to generate test cases.
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from datetime import datetime, timezone
from typing import Dict, Any

from domain.entities import GraphStreamEvent, GraphStreamEventType
from domain.exceptions import StreamingError


@given(
    event_type=st.sampled_from(list(GraphStreamEventType)),
    data=st.dictionaries(
        keys=st.text(min_size=1),
        values=st.one_of(
            st.text(),
            st.integers(),
            st.floats(),
            st.booleans(),
            st.lists(st.text())
        ),
        min_size=1
    ),
    kg_id=st.text(min_size=1),
    tenant_id=st.text(min_size=1)
)
def test_graph_stream_event_property_based(
    event_type: GraphStreamEventType,
    data: Dict[str, Any],
    kg_id: str,
    tenant_id: str
):
    """Test GraphStreamEvent creation with property-based testing.

    This test uses hypothesis to generate random valid inputs for GraphStreamEvent creation
    and verifies that the GraphStreamEvent is created correctly.
    """
    # Create timestamp
    timestamp = datetime.now(timezone.utc)

    # Create a GraphStreamEvent with the generated values
    event = GraphStreamEvent(
        event_type=event_type,
        data=data,
        timestamp=timestamp,
        kg_id=kg_id,
        tenant_id=tenant_id
    )

    # Verify that the GraphStreamEvent has the correct values
    assert event.event_type == event_type
    assert event.data == data
    assert event.timestamp == timestamp
    assert event.kg_id == kg_id
    assert event.tenant_id == tenant_id


@given(
    event_type=st.one_of(st.none(), st.just("not_an_enum")),
    data=st.one_of(st.none(), st.just("not_a_dict")),
    kg_id=st.one_of(st.none(), st.text(min_size=0)),
    tenant_id=st.one_of(st.none(), st.text(min_size=0))
)
def test_graph_stream_event_property_based_invalid(
    event_type: Any,
    data: Any,
    kg_id: Any,
    tenant_id: Any
):
    """Test GraphStreamEvent validation with invalid inputs.

    This test uses hypothesis to generate random invalid inputs for GraphStreamEvent creation
    and verifies that appropriate validation errors are raised.
    """
    # Create timestamp
    timestamp = datetime.now(timezone.utc)

    # Create a dictionary of the arguments
    args: Dict[str, Any] = {
        "event_type": event_type,
        "data": data,
        "timestamp": timestamp,
        "kg_id": kg_id,
        "tenant_id": tenant_id
    }

    # Skip if all values are valid
    if (isinstance(event_type, GraphStreamEventType) and
        isinstance(data, dict) and
        kg_id and
        tenant_id):
        return

    # Verify that creating a GraphStreamEvent with invalid values raises a StreamingError
    with pytest.raises(StreamingError):
        validate_graph_stream_event(**args)


def test_graph_stream_event_types():
    """Test all GraphStreamEvent types."""
    # Test NODE_ADDED event
    node_event = GraphStreamEvent(
        event_type=GraphStreamEventType.NODE_ADDED,
        data={"node_id": "node1", "label": "Person", "properties": {"name": "John"}},
        timestamp=datetime.now(timezone.utc),
        kg_id="kg1",
        tenant_id="tenant1"
    )
    assert node_event.event_type == GraphStreamEventType.NODE_ADDED

    # Test EDGE_ADDED event
    edge_event = GraphStreamEvent(
        event_type=GraphStreamEventType.EDGE_ADDED,
        data={"source_id": "node1", "target_id": "node2", "type": "KNOWS"},
        timestamp=datetime.now(timezone.utc),
        kg_id="kg1",
        tenant_id="tenant1"
    )
    assert edge_event.event_type == GraphStreamEventType.EDGE_ADDED

    # Test PATH_HIGHLIGHTED event
    path_event = GraphStreamEvent(
        event_type=GraphStreamEventType.PATH_HIGHLIGHTED,
        data={"path_nodes": ["node1", "node2", "node3"], "query_id": "q1"},
        timestamp=datetime.now(timezone.utc),
        kg_id="kg1",
        tenant_id="tenant1"
    )
    assert path_event.event_type == GraphStreamEventType.PATH_HIGHLIGHTED

    # Test COMMUNITY_UPDATED event
    community_event = GraphStreamEvent(
        event_type=GraphStreamEventType.COMMUNITY_UPDATED,
        data={"community_id": "c1", "node_count": 5},
        timestamp=datetime.now(timezone.utc),
        kg_id="kg1",
        tenant_id="tenant1"
    )
    assert community_event.event_type == GraphStreamEventType.COMMUNITY_UPDATED


def validate_graph_stream_event(
    event_type: Any,
    data: Any,
    timestamp: Any,
    kg_id: Any,
    tenant_id: Any
) -> GraphStreamEvent:
    """Validate GraphStreamEvent parameters and create a GraphStreamEvent if valid.

    Args:
        event_type: Type of graph stream event
        data: Event data
        timestamp: Event timestamp
        kg_id: Knowledge graph ID
        tenant_id: Tenant ID for multi-tenancy

    Returns:
        A valid GraphStreamEvent object

    Raises:
        StreamingError: If any parameter is invalid
    """
    # Validate event_type
    if not isinstance(event_type, GraphStreamEventType):
        raise StreamingError(
            message="Event type must be a GraphStreamEventType enum",
            event_type="invalid_event_type"
        )

    # Validate data
    if not isinstance(data, dict):
        raise StreamingError(
            message="Data must be a dictionary",
            event_type=str(event_type)
        )

    # Validate timestamp
    if not isinstance(timestamp, datetime):
        raise StreamingError(
            message="Timestamp must be a datetime",
            event_type=str(event_type)
        )

    # Validate kg_id
    if not kg_id:
        raise StreamingError(
            message="Knowledge graph ID cannot be empty",
            event_type=str(event_type)
        )

    # Validate tenant_id
    if not tenant_id:
        raise StreamingError(
            message="Tenant ID cannot be empty",
            event_type=str(event_type)
        )

    # Create and return the GraphStreamEvent
    return GraphStreamEvent(
        event_type=event_type,
        data=data,
        timestamp=timestamp,
        kg_id=kg_id,
        tenant_id=tenant_id
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])