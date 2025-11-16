from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, Set


@dataclass(frozen=True)
class Viewport:
    """Viewport bounds for culling calculations."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def contains(self, x: float, y: float) -> bool:
        """Return True if the point (x, y) lies within the viewport."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


def filter_positions_by_viewport(
    positions: Dict[str, Dict[str, float]], viewport: Viewport
) -> Set[str]:
    """Return IDs of elements within the viewport."""
    return {
        element_id
        for element_id, coords in positions.items()
        if coords is not None and viewport.contains(coords.get("x", 0), coords.get("y", 0))
    }


def visible_counts(
    node_positions: Dict[str, Dict[str, float]],
    edges: Iterable[Tuple[str, str]],
    community_positions: Dict[str, Dict[str, float]],
    viewport: Viewport,
) -> Dict[str, int]:
    """Calculate counts of visible elements in the viewport."""
    nodes_in_view = filter_positions_by_viewport(node_positions, viewport)
    edges_in_view = {
        edge for edge in edges if edge[0] in nodes_in_view and edge[1] in nodes_in_view
    }
    communities_in_view = filter_positions_by_viewport(community_positions, viewport)

    return {
        "node_count": len(nodes_in_view),
        "edge_count": len(edges_in_view),
        "community_count": len(communities_in_view),
    }

