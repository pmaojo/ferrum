"""Tests for Memgraph Lab visualization adapter."""

import pytest
pytest.importorskip("requests")
from unittest.mock import MagicMock, patch, call
import json
from datetime import datetime
import requests

from domain.entities import Triple, GraphStreamEvent, GraphStreamEventType, Community
from domain.graph_visualizer import GraphVisualizer, VisualizationException
from adapters.retrievers.memgraph_lab_visualization_adapter import MemgraphLabVisualizationAdapter


@pytest.fixture
def mock_visualizer():
    """Create a mock GraphVisualizer."""
    visualizer = MagicMock(spec=GraphVisualizer)

    # Mock render_graph_overview method
    visualizer.render_graph_overview.return_value = {
        "communities": [
            {
                "id": "community1",
                "size": 100,
                "position": {"x": 100, "y": 100},
                "tenant_id": "tenant1"
            },
            {
                "id": "community2",
                "size": 50,
                "position": {"x": 200, "y": 200},
                "tenant_id": "tenant1"
            }
        ],
        "styles": {
            "node": {"color": "#1f77b4", "radius": 8},
            "edge": {"color": "#999", "width": 1.5},
            "community": {"color": "#ff7f0e", "opacity": 0.3}
        },
        "stats": {
            "total_nodes": 150,
            "total_communities": 2
        }
    }

    # Mock render_community_detail method
    visualizer.render_community_detail.return_value = {
        "nodes": [
            {
                "id": "node1",
                "position": {"x": 100, "y": 100},
                "attributes": {"label": "Node 1"},
                "community_id": "community1"
            },
            {
                "id": "node2",
                "position": {"x": 200, "y": 200},
                "attributes": {"label": "Node 2"},
                "community_id": "community1"
            }
        ],
        "edges": [
            {
                "source": "node1",
                "target": "node2",
                "type": "RELATED_TO",
                "attributes": {"label": "related to"}
            }
        ],
        "community_id": "community1",
        "tenant_id": "tenant1"
    }

    return visualizer


@pytest.fixture
def mock_stream_adapter():
    """Create a mock GraphStreamPort."""
    return MagicMock()


@pytest.fixture
def mock_tracer():
    """Create a mock TracingPort."""
    return MagicMock()


@pytest.fixture
def mock_response():
    """Create a mock requests.Response."""
    response = MagicMock(spec=requests.Response)
    response.status_code = 200
    response.json.return_value = {"status": "ok", "id": "view1"}
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def memgraph_lab_adapter(mock_visualizer, mock_stream_adapter, mock_tracer, mock_response):
    """Create a MemgraphLabVisualizationAdapter with mocked dependencies."""
    with patch("requests.get", return_value=mock_response), \
         patch("requests.post", return_value=mock_response), \
         patch("threading.Thread"):
        adapter = MemgraphLabVisualizationAdapter(
            memgraph_lab_url="http://localhost:3000",
            visualizer=mock_visualizer,
            stream_adapter=mock_stream_adapter,
            tracer=mock_tracer,
            auto_refresh_interval_ms=0  # Disable auto-refresh for testing
        )
        return adapter


def test_initialization_with_valid_url(mock_visualizer, mock_response):
    """Test adapter initialization with valid URL."""
    with patch("requests.get", return_value=mock_response), \
         patch("threading.Thread"):
        adapter = MemgraphLabVisualizationAdapter(
            memgraph_lab_url="http://localhost:3000",
            visualizer=mock_visualizer,
            auto_refresh_interval_ms=0
        )

        assert adapter.memgraph_lab_url == "http://localhost:3000"
        assert adapter.visualizer == mock_visualizer


def test_initialization_with_invalid_url(mock_visualizer):
    """Test adapter initialization with invalid URL."""
    with patch("requests.get", side_effect=requests.ConnectionError("Connection refused")), \
         patch("threading.Thread"):
        with pytest.raises(ConnectionError) as excinfo:
            MemgraphLabVisualizationAdapter(
                memgraph_lab_url="http://invalid-url",
                visualizer=mock_visualizer,
                auto_refresh_interval_ms=0
            )

        assert "Failed to connect to Memgraph Lab" in str(excinfo.value)


def test_initialization_with_empty_url(mock_visualizer):
    """Test adapter initialization with empty URL."""
    with pytest.raises(ValueError) as excinfo:
        MemgraphLabVisualizationAdapter(
            memgraph_lab_url="",
            visualizer=mock_visualizer,
            auto_refresh_interval_ms=0
        )

    assert "memgraph_lab_url cannot be empty" in str(excinfo.value)


def test_create_visualization(memgraph_lab_adapter, mock_response, mock_visualizer):
    """Test creating a visualization."""
    with patch("requests.post", return_value=mock_response) as mock_post:
        view_id = memgraph_lab_adapter.create_visualization(
            kg_id="kg1",
            tenant_id="tenant1",
            name="Test Visualization"
        )

        # Check result
        assert view_id == "view1"

        # Check if visualization was stored in active_visualizations
        assert "tenant1" in memgraph_lab_adapter.active_visualizations
        assert "kg1" in memgraph_lab_adapter.active_visualizations["tenant1"]
        assert memgraph_lab_adapter.active_visualizations["tenant1"]["kg1"] == "view1"

        # Check if API was called correctly
        mock_post.assert_called()
        args, kwargs = mock_post.call_args_list[0]
        assert args[0] == "http://localhost:3000/api/views"
        assert kwargs["json"]["name"] == "Test Visualization"
        assert kwargs["json"]["metadata"]["kg_id"] == "kg1"
        assert kwargs["json"]["metadata"]["tenant_id"] == "tenant1"

        # Check if visualization was initialized
        mock_visualizer.render_graph_overview.assert_called_once_with(
            kg_id="kg1",
            tenant_id="tenant1"
        )


def test_create_visualization_with_connection_error(memgraph_lab_adapter):
    """Test creating a visualization with connection error."""
    with patch("requests.post", side_effect=requests.ConnectionError("Connection refused")):
        with pytest.raises(ConnectionError) as excinfo:
            memgraph_lab_adapter.create_visualization(
                kg_id="kg1",
                tenant_id="tenant1"
            )

        assert "Failed to connect to Memgraph Lab" in str(excinfo.value)


def test_update_visualization(memgraph_lab_adapter, mock_response):
    """Test updating a visualization with triples."""
    with patch("requests.post", return_value=mock_response) as mock_post:
        # Create test triples
        triples = [
            Triple(subject="entity1", predicate="relatedTo", object="entity2", tenant_id="tenant1"),
            Triple(subject="entity2", predicate="hasProperty", object="value1", tenant_id="tenant1")
        ]

        # Update visualization
        result = memgraph_lab_adapter.update_visualization(
            view_id="view1",
            triples=triples
        )

        # Check result
        assert result is True

        # Check if API was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:3000/api/views/view1/data"
        assert "nodes" in kwargs["json"]
        assert "relationships" in kwargs["json"]
        assert kwargs["json"]["merge"] is True


def test_handle_edge_click_highlights_path(memgraph_lab_adapter):
    memgraph_lab_adapter.active_visualizations = {"tenant1": {"kg1": "view1"}}
    with patch.object(memgraph_lab_adapter, "highlight_path") as mock_highlight:
        memgraph_lab_adapter._handle_edge_click({
            "source": "node1",
            "target": "node2",
            "kg_id": "kg1",
            "tenant_id": "tenant1",
        })

        mock_highlight.assert_called_once_with(view_id="view1", path_nodes=["node1", "node2"])


def test_handle_render_complete_sends_event(memgraph_lab_adapter, mock_stream_adapter):
    event = {"kg_id": "kg1", "tenant_id": "tenant1"}
    memgraph_lab_adapter._handle_render_complete(event)

    mock_stream_adapter.send_event.assert_called_once()
    sent_event = mock_stream_adapter.send_event.call_args.kwargs["event"]
    assert sent_event.event_type == GraphStreamEventType.RENDER_COMPLETED
    assert sent_event.data == event


def test_highlight_path(memgraph_lab_adapter, mock_response):
    """Test highlighting a path in the visualization."""
    with patch("requests.post", return_value=mock_response) as mock_post:
        # Highlight path
        highlight_id = memgraph_lab_adapter.highlight_path(
            view_id="view1",
            path_nodes=["node1", "node2", "node3"]
        )

        # Check if highlight_id was generated
        assert highlight_id is not None

        # Check if API was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:3000/api/views/view1/highlights"
        assert kwargs["json"]["nodes"] == ["node1", "node2", "node3"]
        assert "style" in kwargs["json"]


def test_start_query_trace(memgraph_lab_adapter, mock_tracer):
    """Test starting a query trace."""
    # Start query trace
    query_id = memgraph_lab_adapter.start_query_trace(
        query="MATCH (n) RETURN n",
        kg_id="kg1",
        tenant_id="tenant1"
    )

    # Check if query_id was generated
    assert query_id is not None
    assert query_id in memgraph_lab_adapter.query_traces

    # Check if trace was initialized correctly
    trace = memgraph_lab_adapter.query_traces[query_id]
    assert len(trace) == 1
    assert trace[0]["event"] == "query_start"
    assert trace[0]["query"] == "MATCH (n) RETURN n"
    assert trace[0]["kg_id"] == "kg1"
    assert trace[0]["tenant_id"] == "tenant1"

    # Check if metric was recorded
    mock_tracer.record_metric.assert_called_once()
    args, kwargs = mock_tracer.record_metric.call_args
    assert kwargs["name"] == "query_trace_started"
    assert kwargs["tenant_id"] == "tenant1"
    assert kwargs["kg_id"] == "kg1"


def test_add_trace_event(memgraph_lab_adapter):
    """Test adding an event to a query trace."""
    # Start query trace
    query_id = memgraph_lab_adapter.start_query_trace(
        query="MATCH (n) RETURN n",
        kg_id="kg1",
        tenant_id="tenant1"
    )

    # Add trace event
    memgraph_lab_adapter.add_trace_event(
        query_id=query_id,
        event_type="node_visit",
        data={"node_id": "node1"}
    )

    # Check if event was added correctly
    trace = memgraph_lab_adapter.query_traces[query_id]
    assert len(trace) == 2
    assert trace[1]["event"] == "node_visit"
    assert trace[1]["data"]["node_id"] == "node1"


def test_add_trace_event_with_invalid_query_id(memgraph_lab_adapter):
    """Test adding an event to an invalid query trace."""
    with pytest.raises(ValueError) as excinfo:
        memgraph_lab_adapter.add_trace_event(
            query_id="invalid_id",
            event_type="node_visit",
            data={"node_id": "node1"}
        )

    assert "Invalid query_id" in str(excinfo.value)


def test_end_query_trace(memgraph_lab_adapter, mock_tracer):
    """Test ending a query trace."""
    # Start query trace
    query_id = memgraph_lab_adapter.start_query_trace(
        query="MATCH (n) RETURN n",
        kg_id="kg1",
        tenant_id="tenant1"
    )

    # Add trace event
    memgraph_lab_adapter.add_trace_event(
        query_id=query_id,
        event_type="node_visit",
        data={"node_id": "node1"}
    )

    # End query trace
    result = memgraph_lab_adapter.end_query_trace(
        query_id=query_id,
        result={"count": 1}
    )

    # Check result
    assert result["query_id"] == query_id
    assert result["events"] == 3  # start, node_visit, end
    assert "execution_time_ms" in result
    assert result["kg_id"] == "kg1"
    assert result["tenant_id"] == "tenant1"

    # Check if end event was added correctly
    trace = memgraph_lab_adapter.query_traces[query_id]
    assert len(trace) == 3
    assert trace[2]["event"] == "query_end"
    assert trace[2]["result"] == {"count": 1}

    # Check if metric was recorded
    mock_tracer.record_metric.assert_called()
    args, kwargs = mock_tracer.record_metric.call_args_list[1]
    assert kwargs["name"] == "query_execution_time_ms"
    assert kwargs["tenant_id"] == "tenant1"
    assert kwargs["kg_id"] == "kg1"
    assert kwargs["events"] == 3


def test_end_query_trace_with_visualization(memgraph_lab_adapter, mock_response):
    """Test ending a query trace with visualization."""
    with patch("requests.post", return_value=mock_response) as mock_post:
        # Start query trace
        query_id = memgraph_lab_adapter.start_query_trace(
            query="MATCH (n) RETURN n",
            kg_id="kg1",
            tenant_id="tenant1"
        )

        # Add node visit events
        memgraph_lab_adapter.add_trace_event(
            query_id=query_id,
            event_type="node_visit",
            data={"node_id": "node1"}
        )
        memgraph_lab_adapter.add_trace_event(
            query_id=query_id,
            event_type="node_visit",
            data={"node_id": "node2"}
        )

        # End query trace with visualization
        result = memgraph_lab_adapter.end_query_trace(
            query_id=query_id,
            result={"count": 1},
            view_id="view1"
        )

        # Check if highlight path was called
        mock_post.assert_called()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:3000/api/views/view1/highlights"
        assert kwargs["json"]["nodes"] == ["node1", "node2"]


def test_get_visualization_url(memgraph_lab_adapter):
    """Test getting visualization URL."""
    url = memgraph_lab_adapter.get_visualization_url("view1")
    assert url == "http://localhost:3000/view/view1"


def test_convert_triples_to_memgraph_format(memgraph_lab_adapter):
    """Test converting triples to Memgraph Lab format."""
    # Create test triples
    triples = [
        Triple(subject="entity1", predicate="relatedTo", object="entity2", tenant_id="tenant1"),
        Triple(subject="entity2", predicate="hasProperty", object="value1", tenant_id="tenant1")
    ]

    # Convert triples
    nodes, relationships = memgraph_lab_adapter._convert_triples_to_memgraph_format(triples)

    # Check nodes
    assert len(nodes) == 3
    node_ids = [node["id"] for node in nodes]
    assert "entity1" in node_ids
    assert "entity2" in node_ids
    assert "value1" in node_ids

    # Check relationships
    assert len(relationships) == 2
    rel_types = [rel["type"] for rel in relationships]
    assert "relatedTo" in rel_types
    assert "hasProperty" in rel_types

    # Check relationship structure
    for rel in relationships:
        assert "id" in rel
        assert "startNode" in rel
        assert "endNode" in rel
        assert "properties" in rel
        assert "tenant_id" in rel["properties"]


def test_handle_node_click_for_community(memgraph_lab_adapter, mock_visualizer, mock_response):
    """Test handling node click event for a community node."""
    with patch("requests.post", return_value=mock_response) as mock_post:
        # Setup active visualization
        memgraph_lab_adapter.active_visualizations = {
            "tenant1": {"kg1": "view1"}
        }

        # Simulate node click event
        memgraph_lab_adapter._handle_node_click({
            "id": "community1",
            "type": "community",
            "kg_id": "kg1",
            "tenant_id": "tenant1"
        })

        # Check if community detail was rendered
        mock_visualizer.render_community_detail.assert_called_once_with(
            community_id="community1",
            tenant_id="tenant1"
        )

        # Check if visualization was updated
        mock_post.assert_called()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:3000/api/views/view1/data"
        assert "nodes" in kwargs["json"]
        assert "relationships" in kwargs["json"]
        assert kwargs["json"]["merge"] is True