from typing import Any, Dict, List

from application.ports.knowledge_discovery import DiscoveryVisualizationPort
from domain.knowledge_discovery import (
    DiscoveryVisualizationService,
    Hypothesis,
    Pattern,
)


class SimpleDiscoveryVisualizationAdapter(DiscoveryVisualizationPort):
    """Adapter delegating to DiscoveryVisualizationService."""

    def __init__(self, service: DiscoveryVisualizationService) -> None:
        self._service = service

    def visualize_patterns(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        patterns: List[Pattern],
    ) -> Dict[str, Any]:
        return self._service.visualize_patterns(
            kg_id=kg_id, tenant_id=tenant_id, patterns=patterns
        )

    def visualize_hypotheses(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        hypotheses: List[Hypothesis],
    ) -> Dict[str, Any]:
        return self._service.visualize_hypotheses(
            kg_id=kg_id, tenant_id=tenant_id, hypotheses=hypotheses
        )
