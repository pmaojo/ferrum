from __future__ import annotations

"""Knowledge graph contract definitions."""

from dataclasses import dataclass
from application.contracts.contract import Contract, Invariant


@dataclass
class ValidationRule:
    """Rule used for validating a knowledge graph."""

    name: str
    expression: str

# Validation rules for knowledge graph integrity
CONNECTIVITY_RULE = ValidationRule(
    name="connectivity",
    expression="Graph must remain fully connected",
)

CLASS_INSTANCE_SEPARATION_RULE = ValidationRule(
    name="class_instance_separation",
    expression="Classes cannot simultaneously be instances",
)


class KGContract(Contract):
    """Contract enforcing knowledge graph invariants."""

    def __init__(self) -> None:
        super().__init__(
            invariants=[
                Invariant(rule=CONNECTIVITY_RULE),
                Invariant(rule=CLASS_INSTANCE_SEPARATION_RULE),
            ]
        )

__all__ = ["KGContract", "CONNECTIVITY_RULE", "CLASS_INSTANCE_SEPARATION_RULE"]
