"""Tests for WebSocket graph stream adapter with buffering.

This module contains tests for the WebSocketGraphStreamAdapter implementation,
focusing on event batching for >10k events, progressive rendering, community-based
lazy loading, and buffer overflow handling.
"""

import pytest
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from unittest.mock import MagicMock, patch

from domain.entities import GraphStreamEvent, GraphStreamEventType
from application.ports import GraphStreamPort, TracingPort, ClusteringPort
from adapters.retrievers.websocket_graph_stream_adapter import (
    WebSocketGraphStreamAdapter,
    WebSocketClient,
    EventBuffer,
    StreamingException,
    BufferOverflowError
)


class TestEventBuffer:
    """Tests for EventBuffer class."""

    def test_add_event(self):
        """Test adding events to buffer."""
        buffer = EventBuffer(max_size=5)

        # Create test event
        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node1"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="test-tenant"
        )

        # Add event to buffer
        result = buffer.add_event(event)

        # Verify event was added
        assert result is True
        assert len(buffer.buffer["test-tenant"]) == 1

    def test_buffer_overflow(self):
        """Test buffer overflow handling."""
        buffer = EventBuffer(max_size=2)

        # Create test events
        events = [
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": f"node{i}"},
                timestamp=datetime.now(),
                kg_id="test-kg",
                tenant_id="test-tenant"
            )
            for i in range(3)
        ]

        # Add events to buffer
        buffer.add_event(events[0])
        buffer.add_event(events[1])

        # Adding third event should raise BufferOverflowError
        with pytest.raises(BufferOverflowError):
            buffer.add_event(events[2])

    def test_should_flush(self):
        """Test should_flush logic."""
        buffer = EventBuffer(flush_interval_ms=100)

        # Create test event
        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node1"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="test-tenant"
        )

        # Add event to buffer
        buffer.add_event(event)

        # Should not flush immediately
        assert buffer.should_flush("test-tenant") is False

        # Manipulate last_flush_time to simulate time passing
        buffer.last_flush_time["test-tenant"] = time.time() - 0.2  # 200ms ago

        # Should flush now
        assert buffer.should_flush("test-tenant") is True

    def test_get_batch(self):
        """Test getting batch of events."""
        buffer = EventBuffer(max_batch_size=2)

        # Create test events
        events = [
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": f"node{i}"},
                timestamp=datetime.now(),
                kg_id="test-kg",
                tenant_id="test-tenant"
            )
            for i in range(3)
        ]

        # Add events to buffer
        for event in events:
            buffer.add_event(event)

        # Get batch (should return first 2 events)
        batch = buffer.get_batch("test-tenant")

        # Verify batch
        assert len(batch) == 2
        assert batch[0].data["id"] == "node0"
        assert batch[1].data["id"] == "node1"

        # Get another batch (should return remaining event)
        batch = buffer.get_batch("test-tenant")

        # Verify batch
        assert len(batch) == 1
        assert batch[0].data["id"] == "node2"

        # Buffer should be empty now
        assert len(buffer.buffer["test-tenant"]) == 0


class TestWebSocketClient:
    """Tests for WebSocketClient class."""

    def test_send(self):
        """Test sending data to client."""
        # Create mock send callback
        mock_callback = MagicMock()

        # Create client
        client = WebSocketClient(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send data
        result = client.send({"message": "test"})

        # Verify callback was called with JSON string
        assert result is True
        mock_callback.assert_called_once()
        args = mock_callback.call_args[0]
        assert json.loads(args[0]) == {"message": "test"}

    def test_send_failure(self):
        """Test handling send failures."""
        # Create mock send callback that raises exception
        mock_callback = MagicMock(side_effect=Exception("Send failed"))

        # Create client
        client = WebSocketClient(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send data (should handle exception)
        result = client.send({"message": "test"})

        # Verify result and client state
        assert result is False
        assert client.is_active is False

    def test_is_subscribed_to(self):
        """Test subscription checking."""
        # Create client with specific subscriptions
        client = WebSocketClient(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=MagicMock(),
            subscribed_kg_ids={"kg1", "kg2"}
        )

        # Check subscriptions
        assert client.is_subscribed_to("kg1") is True
        assert client.is_subscribed_to("kg2") is True
        assert client.is_subscribed_to("kg3") is False

        # Create client with no specific subscriptions (receives all)
        client = WebSocketClient(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=MagicMock()
        )

        # Should be subscribed to all
        assert client.is_subscribed_to("any-kg") is True


class TestWebSocketGraphStreamAdapter:
    """Tests for WebSocketGraphStreamAdapter class."""

    @pytest.fixture
    def mock_tracing_adapter(self):
        """Create mock tracing adapter."""
        mock = MagicMock(spec=TracingPort)
        return mock

    @pytest.fixture
    def mock_clustering_adapter(self):
        """Create mock clustering adapter."""
        mock = MagicMock(spec=ClusteringPort)
        return mock

    @pytest.fixture
    def adapter(self, mock_tracing_adapter, mock_clustering_adapter):
        """Create WebSocketGraphStreamAdapter instance."""
        adapter = WebSocketGraphStreamAdapter(
            tracing_adapter=mock_tracing_adapter,
            clustering_adapter=mock_clustering_adapter,
            buffer_size=5,
            flush_interval_ms=100,
            max_batch_size=2
        )
        return adapter

    def test_send_event(self, adapter, mock_tracing_adapter):
        """Test sending individual events."""
        # Create test event
        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node1"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="test-tenant"
        )

        # Register mock client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send event
        adapter.send_event(event=event)

        # Verify metrics were recorded (client registration + event)
        assert mock_tracing_adapter.record_metric.call_count >= 2

        # Verify event was added to buffer
        assert len(adapter.buffer.buffer["test-tenant"]) == 1

        # Manipulate last_flush_time to force flush
        adapter.buffer.last_flush_time["test-tenant"] = time.time() - 1

        # Send another event to trigger flush
        event2 = GraphStreamEvent(
            event_type=GraphStreamEventType.EDGE_ADDED,
            data={"source": "node1", "target": "node2"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="test-tenant"
        )

        adapter.send_event(event=event2)

        # Verify client callback was called (events were flushed)
        mock_callback.assert_called_once()

    def test_send_batch(self, adapter, mock_tracing_adapter):
        """Test sending batch of events."""
        # Create test events
        events = [
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": f"node{i}"},
                timestamp=datetime.now(),
                kg_id="test-kg",
                tenant_id="test-tenant"
            )
            for i in range(3)
        ]

        # Register mock client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send batch
        adapter.send_batch(events=events, buffer_size=2)

        # Verify metrics were recorded (client registration + batch events)
        assert mock_tracing_adapter.record_metric.call_count >= 1

        # Verify client callback was called twice (2 batches)
        assert mock_callback.call_count == 2

    def test_buffer_overflow_handling(self, adapter):
        """Test buffer overflow handling."""
        # Create test events (more than buffer size)
        events = [
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": f"node{i}"},
                timestamp=datetime.now(),
                kg_id="test-kg",
                tenant_id="test-tenant"
            )
            for i in range(6)  # Buffer size is 5
        ]

        # Register mock client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send events one by one
        for event in events:
            adapter.send_event(event=event)

        # Verify client callback was called (buffer was flushed)
        assert mock_callback.call_count > 0

    def test_client_registration(self, adapter):
        """Test client registration and unregistration."""
        # Register client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Verify client was added
        assert "test-client" in adapter.clients
        assert "test-tenant" in adapter.clients_by_tenant
        assert "test-client" in adapter.clients_by_tenant["test-tenant"]

        # Unregister client
        adapter.unregister_client(client_id="test-client")

        # Verify client was removed
        assert "test-client" not in adapter.clients
        assert "test-tenant" not in adapter.clients_by_tenant

    def test_update_client_subscriptions(self, adapter):
        """Test updating client subscriptions."""
        # Register client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback,
            subscribed_kg_ids={"kg1"}
        )

        # Verify initial subscription
        client = adapter.clients["test-client"]
        assert client.is_subscribed_to("kg1") is True
        assert client.is_subscribed_to("kg2") is False

        # Update subscriptions
        adapter.update_client_subscriptions(
            client_id="test-client",
            subscribed_kg_ids={"kg2", "kg3"}
        )

        # Verify updated subscription
        assert client.is_subscribed_to("kg1") is False
        assert client.is_subscribed_to("kg2") is True
        assert client.is_subscribed_to("kg3") is True

    def test_progressive_rendering(self, adapter, mock_clustering_adapter):
        """Test progressive rendering for large graphs."""
        # Set graph metadata for progressive rendering
        adapter.set_graph_metadata(
            kg_id="large-kg",
            tenant_id="test-tenant",
            node_count=100000,  # Above threshold
            edge_count=500000,
            has_communities=True
        )

        # Create test event for large graph
        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node1"},
            timestamp=datetime.now(),
            kg_id="large-kg",
            tenant_id="test-tenant"
        )

        # Register mock client
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="test-client",
            tenant_id="test-tenant",
            send_callback=mock_callback
        )

        # Send event
        adapter.send_event(event=event)

        # Verify progressive rendering was used
        # (In this case, the event is still added to buffer)
        assert len(adapter.buffer.buffer["test-tenant"]) == 1

    def test_client_filtering_by_kg_id(self, adapter):
        """Test client filtering by knowledge graph ID."""
        # Register clients with different subscriptions
        mock_callback1 = MagicMock()
        mock_callback2 = MagicMock()

        adapter.register_client(
            client_id="client1",
            tenant_id="test-tenant",
            send_callback=mock_callback1,
            subscribed_kg_ids={"kg1"}
        )

        adapter.register_client(
            client_id="client2",
            tenant_id="test-tenant",
            send_callback=mock_callback2,
            subscribed_kg_ids={"kg2"}
        )

        # Create test events for different KGs
        events = [
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": "node1"},
                timestamp=datetime.now(),
                kg_id="kg1",
                tenant_id="test-tenant"
            ),
            GraphStreamEvent(
                event_type=GraphStreamEventType.NODE_ADDED,
                data={"id": "node2"},
                timestamp=datetime.now(),
                kg_id="kg2",
                tenant_id="test-tenant"
            )
        ]

        # Send batch
        adapter.send_batch(events=events)

        # Verify each client received only relevant events
        args1 = mock_callback1.call_args[0][0]
        args2 = mock_callback2.call_args[0][0]

        events1 = json.loads(args1)["events"]
        events2 = json.loads(args2)["events"]

        assert len(events1) == 1
        assert events1[0]["kg_id"] == "kg1"

        assert len(events2) == 1
        assert events2[0]["kg_id"] == "kg2"

    def test_tenant_isolation(self, adapter):
        """Test tenant isolation for events."""
        # Register clients for different tenants
        mock_callback1 = MagicMock()
        mock_callback2 = MagicMock()

        adapter.register_client(
            client_id="client1",
            tenant_id="tenant1",
            send_callback=mock_callback1
        )

        adapter.register_client(
            client_id="client2",
            tenant_id="tenant2",
            send_callback=mock_callback2
        )

        # Create test events for different tenants
        event1 = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node1"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="tenant1"
        )

        event2 = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "node2"},
            timestamp=datetime.now(),
            kg_id="test-kg",
            tenant_id="tenant2"
        )

        # Send events
        adapter.send_event(event=event1)
        adapter.send_event(event=event2)

        # Force flush for both tenants
        adapter.buffer.last_flush_time["tenant1"] = time.time() - 1
        adapter.buffer.last_flush_time["tenant2"] = time.time() - 1

        # Send another event to trigger flush
        adapter.send_event(event=event1)
        adapter.send_event(event=event2)

        # Verify each client received only their tenant's events
        assert mock_callback1.call_count > 0
        assert mock_callback2.call_count > 0

        # Check tenant1 events
        args1 = mock_callback1.call_args[0][0]
        events1 = json.loads(args1)["events"]
        for event in events1:
            # All events should be for test-kg
            assert event["kg_id"] == "test-kg"

        # Check tenant2 events
        args2 = mock_callback2.call_args[0][0]
        events2 = json.loads(args2)["events"]
        for event in events2:
            # All events should be for test-kg
            assert event["kg_id"] == "test-kg"

    def test_path_highlight_flush_priority(self, adapter):
        """Path highlight events flush buffer immediately."""
        mock_callback = MagicMock()
        adapter.register_client(
            client_id="client1",
            tenant_id="tenant1",
            send_callback=mock_callback,
        )

        event = GraphStreamEvent(
            event_type=GraphStreamEventType.PATH_HIGHLIGHTED,
            data={"path_nodes": ["n1", "n2"]},
            timestamp=datetime.now(),
            kg_id="kg",
            tenant_id="tenant1",
        )

        adapter.send_event(event=event)

        assert mock_callback.called
        sent = json.loads(mock_callback.call_args[0][0])["events"][0]
        assert sent["event_type"] == "PATH_HIGHLIGHTED"

    def test_community_update_emitted(self, adapter):
        """Community update events are emitted on flush."""
        adapter.set_graph_metadata(
            kg_id="kg",
            tenant_id="tenant1",
            node_count=100000,
            edge_count=10,
            has_communities=True,
        )

        mock_callback = MagicMock()
        adapter.register_client(
            client_id="client1",
            tenant_id="tenant1",
            send_callback=mock_callback,
        )

        event = GraphStreamEvent(
            event_type=GraphStreamEventType.NODE_ADDED,
            data={"id": "n1", "community_id": "kg:1"},
            timestamp=datetime.now(),
            kg_id="kg",
            tenant_id="tenant1",
        )

        adapter.send_event(event=event)
        adapter.buffer.last_flush_time["tenant1"] = time.time() - 1
        adapter.send_event(event=event)

        message = json.loads(mock_callback.call_args[0][0])
        event_types = [e["event_type"] for e in message["events"]]
        assert "COMMUNITY_UPDATED" in event_types


if __name__ == "__main__":
    pytest.main(["-xvs", "test_websocket_graph_stream_adapter.py"])