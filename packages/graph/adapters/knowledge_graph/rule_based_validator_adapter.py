from __future__ import annotations

from typing import Any, Dict, List

from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
    KnowledgeGraphValidatorPort,
    ValidationRule,
)


class RuleBasedValidatorAdapter(KnowledgeGraphValidatorPort):
    """Simple in-memory validation based on provided rules."""

    def validate(
        self, *, kg_id: str, tenant_id: str, rules: List[ValidationRule]
    ) -> tuple[bool, List[Dict[str, Any]]]:
        # This mock simply returns success if any rule is provided
        details = [{"rule": r.name, "status": "checked"} for r in rules]
        is_valid = True
        return is_valid, details
