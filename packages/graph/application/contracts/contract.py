from __future__ import annotations

"""Contract-based validation models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
        KnowledgeGraphValidatorPort,
        ValidationRule,
    )
else:  # pragma: no cover - runtime
    KnowledgeGraphValidatorPort = Any  # type: ignore
    ValidationRule = Any  # type: ignore


@dataclass
class Precondition:
    """Condition that must hold true before execution."""

    rule: ValidationRule


@dataclass
class Postcondition:
    """Condition that must hold true after execution."""

    rule: ValidationRule


@dataclass
class Invariant:
    """Condition that must always hold true."""

    rule: ValidationRule


@dataclass
class Contract:
    """Contract grouping preconditions, postconditions and invariants."""

    preconditions: List[Precondition] = field(default_factory=list)
    postconditions: List[Postcondition] = field(default_factory=list)
    invariants: List[Invariant] = field(default_factory=list)

    def verify(
        self,
        validator: KnowledgeGraphValidatorPort,
        *,
        kg_id: str,
        tenant_id: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify all contract conditions using the provided validator.

        Conditions are checked sequentially; the first failing condition
        aborts verification and returns its validation details.
        """

        details: List[Dict[str, Any]] = []
        for condition in (
            [*self.preconditions, *self.invariants, *self.postconditions]
        ):
            is_valid, cond_details = validator.validate(
                kg_id=kg_id,
                tenant_id=tenant_id,
                rules=[condition.rule],
            )
            details.extend(cond_details)
            if not is_valid:
                return False, details
        return True, details
