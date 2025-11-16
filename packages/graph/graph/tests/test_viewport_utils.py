import pytest

from domain.utils.viewport import Viewport, filter_positions_by_viewport, visible_counts


def test_filter_positions_all_visible():
    viewport = Viewport(x_min=0, y_min=0, x_max=100, y_max=100)
    positions = {
        "a": {"x": 10, "y": 10},
        "b": {"x": 50, "y": 50},
    }
    assert filter_positions_by_viewport(positions, viewport) == {"a", "b"}


def test_filter_positions_partial():
    viewport = Viewport(x_min=0, y_min=0, x_max=100, y_max=100)
    positions = {
        "a": {"x": -10, "y": -10},
        "b": {"x": 50, "y": 50},
    }
    assert filter_positions_by_viewport(positions, viewport) == {"b"}


def test_visible_counts_edges_and_boundaries():
    viewport = Viewport(x_min=0, y_min=0, x_max=100, y_max=100)
    node_positions = {
        "n1": {"x": 0, "y": 0},
        "n2": {"x": 100, "y": 100},
        "n3": {"x": 200, "y": 200},
    }
    edges = {("n1", "n2"), ("n2", "n3")}
    community_positions = {"c1": {"x": 50, "y": 50}}
    counts = visible_counts(node_positions, edges, community_positions, viewport)
    assert counts == {"node_count": 2, "edge_count": 1, "community_count": 1}

