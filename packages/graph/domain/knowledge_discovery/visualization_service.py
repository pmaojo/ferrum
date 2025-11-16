"""Service for visualizing discovered knowledge."""

from typing import Any, Dict, List

from application.ports import GraphVisualizationPort
from .entities import Pattern, Hypothesis


class DiscoveryVisualizationService:
    """Generate layouts for patterns and hypotheses."""

    def __init__(self, visualizer: GraphVisualizationPort) -> None:
        self._visualizer = visualizer

    def visualize_patterns(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        patterns: List[Pattern],
        algorithm: str = "force_directed",
    ) -> Dict[str, Any]:
        return self._visualizer.generate_layout(
            kg_id=kg_id,
            tenant_id=tenant_id,
            algorithm=algorithm,
            include_communities=False,
        )

    def visualize_hypotheses(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        hypotheses: List[Hypothesis],
        algorithm: str = "force_directed",
    ) -> Dict[str, Any]:
        return self._visualizer.generate_layout(
            kg_id=kg_id,
            tenant_id=tenant_id,
            algorithm=algorithm,
            include_communities=False,
        )
