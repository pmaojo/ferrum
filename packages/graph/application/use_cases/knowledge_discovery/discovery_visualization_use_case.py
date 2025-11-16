"""Use case for visualizing discoveries."""

from dataclasses import dataclass
from typing import Any, Dict, List

from application.ports.knowledge_discovery import DiscoveryVisualizationPort
from application.use_cases.base_use_case import BaseUseCase
from domain.knowledge_discovery import Hypothesis, Pattern


@dataclass
class DiscoveryVisualizationRequest:
    kg_id: str
    tenant_id: str
    patterns: List[Pattern]
    hypotheses: List[Hypothesis]


@dataclass
class DiscoveryVisualizationResponse:
    layout: Dict[str, Any]


class DiscoveryVisualizationUseCase(
    BaseUseCase[DiscoveryVisualizationRequest, DiscoveryVisualizationResponse]
):
    """Generate a visualization layout for patterns and hypotheses."""

    def __init__(self, visualizer: DiscoveryVisualizationPort) -> None:
        super().__init__()
        self._visualizer = visualizer

    async def _execute_internal(
        self, request: DiscoveryVisualizationRequest
    ) -> DiscoveryVisualizationResponse:
        if request.patterns:
            layout = self._visualizer.visualize_patterns(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                patterns=request.patterns,
            )
        else:
            layout = self._visualizer.visualize_hypotheses(
                kg_id=request.kg_id,
                tenant_id=request.tenant_id,
                hypotheses=request.hypotheses,
            )
        return DiscoveryVisualizationResponse(layout=layout)
