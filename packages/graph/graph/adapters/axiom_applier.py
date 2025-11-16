from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Protocol


class AxiomApplier(Protocol):
    """Protocol for applying OWL axioms to an ontology."""

    def apply(self, ontology: Any, axioms: List[str]) -> None:
        """Apply axioms to the given ontology."""
        ...


@dataclass
class BasicAxiomApplier:
    """Apply only basic entity declarations."""

    def apply(self, ontology: Any, axioms: List[str]) -> None:
        for ax in axioms:
            line = ax.strip()
            if not line:
                continue
            if line.startswith("Class:"):
                name = line.split(":", 1)[1].strip()
                setattr(ontology, name, type(name, (), {}))
            elif line.startswith("ObjectProperty:"):
                name = line.split(":", 1)[1].strip()
                setattr(ontology, name, type(name, (), {}))
            elif line.startswith("DataProperty:"):
                name = line.split(":", 1)[1].strip()
                setattr(ontology, name, type(name, (), {}))
            elif line.startswith("Individual:"):
                name = line.split(":", 1)[1].strip()
                setattr(ontology, name, type(name, (), {}))


@dataclass
class FullAxiomApplier:
    """Apply full axiom sets including relationships."""

    base: AxiomApplier = field(default_factory=BasicAxiomApplier)

    def apply(self, ontology: Any, axioms: List[str]) -> None:
        # Apply basic declarations first
        self.base.apply(ontology, axioms)

        for ax in axioms:
            line = ax.strip()
            if not line:
                continue
            if line.startswith("SubClassOf:"):
                _, rest = line.split(":", 1)
                parts = rest.strip().split()
                if (
                    len(parts) == 2
                    and hasattr(ontology, parts[0])
                    and hasattr(ontology, parts[1])
                ):
                    getattr(ontology, parts[0]).is_a = getattr(
                        ontology, parts[0]
                    ).__dict__.get("is_a", []) + [getattr(ontology, parts[1])]
            elif line.startswith("ClassAssertion:"):
                _, rest = line.split(":", 1)
                parts = rest.strip().split()
                if (
                    len(parts) == 2
                    and hasattr(ontology, parts[1])
                    and hasattr(ontology, parts[0])
                ):
                    getattr(ontology, parts[1]).is_a = getattr(
                        ontology, parts[1]
                    ).__dict__.get("is_a", []) + [getattr(ontology, parts[0])]
            elif line.startswith("ObjectPropertyAssertion:"):
                _, rest = line.split(":", 1)
                parts = rest.strip().split()
                if len(parts) == 3 and all(hasattr(ontology, p) for p in parts):
                    prop = getattr(ontology, parts[0])
                    prop.assertions = getattr(prop, "assertions", []) + [
                        (getattr(ontology, parts[1]), getattr(ontology, parts[2]))
                    ]
            elif line.startswith("DataPropertyAssertion:"):
                _, rest = line.split(":", 1)
                parts = rest.strip().split()
                if (
                    len(parts) == 3
                    and hasattr(ontology, parts[0])
                    and hasattr(ontology, parts[1])
                ):
                    prop = getattr(ontology, parts[0])
                    prop.data_assertions = getattr(prop, "data_assertions", []) + [
                        (getattr(ontology, parts[1]), parts[2])
                    ]
