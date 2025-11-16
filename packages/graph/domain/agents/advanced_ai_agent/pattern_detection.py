import logging
from datetime import datetime
from typing import Any, Dict, List

from application.ports.base import MessageBusPort
from domain.services.architectural_pattern_service import (
    ArchitecturalPatternService,
    PatternType,
)

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detect architectural anti-patterns."""

    def __init__(
        self,
        message_bus: MessageBusPort,
        pattern_service: ArchitecturalPatternService,
        tenant_id: str,
        error_handler,
    ) -> None:
        self.message_bus = message_bus
        self.pattern_service = pattern_service
        self.tenant_id = tenant_id
        self.error_handler = error_handler

    def handle_anti_pattern_detection(self, message: Dict[str, Any]) -> None:
        try:
            pattern_analysis = self.pattern_service.analyze_patterns(self.tenant_id)
            anti_patterns = pattern_analysis.anti_patterns
            report = self._generate_anti_pattern_report(anti_patterns)
            self.message_bus.publish(
                topic="ai.anti_pattern_report",
                message={
                    "anti_patterns": [
                        {
                            "type": ap.pattern_type.value,
                            "confidence": ap.confidence.value,
                            "description": ap.description,
                            "components": [c.name for c in ap.components],
                            "evidence": ap.evidence,
                            "recommendations": ap.recommendations,
                            "severity": self._calculate_severity(ap),
                        }
                        for ap in anti_patterns
                    ],
                    "overall_assessment": report,
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now().isoformat(),
                },
                tenant_id=self.tenant_id,
            )
            logger.info("Detected %d anti-patterns", len(anti_patterns))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Error handling anti-pattern detection: %s", exc)
            self.error_handler("anti_pattern_detection", str(exc))

    def _generate_anti_pattern_report(self, anti_patterns: List) -> Dict[str, Any]:
        if not anti_patterns:
            return {
                "status": "healthy",
                "message": "No significant anti-patterns detected",
                "priority_actions": [],
            }
        high = [ap for ap in anti_patterns if self._calculate_severity(ap) == "high"]
        medium = [ap for ap in anti_patterns if self._calculate_severity(ap) == "medium"]
        low = [ap for ap in anti_patterns if self._calculate_severity(ap) == "low"]
        priority_actions = []
        if high:
            priority_actions.extend(
                [
                    f"Fix {ap.pattern_type.value} in {ap.components[0].name if ap.components else 'unknown'}"
                    for ap in high[:3]
                ]
            )
        status = "critical" if high else "warning" if medium else "minor"
        return {
            "status": status,
            "message": f"Found {len(anti_patterns)} anti-patterns: {len(high)} high, {len(medium)} medium, {len(low)} low severity",
            "priority_actions": priority_actions,
            "severity_breakdown": {
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
        }

    def _calculate_severity(self, anti_pattern) -> str:
        high = [PatternType.CIRCULAR_DEPENDENCY, PatternType.GOD_OBJECT]
        medium = [PatternType.ANEMIC_DOMAIN_MODEL, PatternType.FEATURE_ENVY]
        if anti_pattern.pattern_type in high:
            return "high"
        if anti_pattern.pattern_type in medium:
            return "medium"
        return "low"
