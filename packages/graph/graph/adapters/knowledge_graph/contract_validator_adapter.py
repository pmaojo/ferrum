from __future__ import annotations

"""Adapter for validating knowledge graph contracts using graph checks."""

from typing import Any, Dict, List, Tuple

from application.use_cases.knowledge_graph.validate_knowledge_graph_use_case import (
    KnowledgeGraphValidatorPort,
    ValidationRule,
)


class ContractValidatorAdapter(KnowledgeGraphValidatorPort):
    """Validate knowledge graph invariants via simple graph queries."""

    def __init__(self, *, triples: List[tuple[str, str, str]] | None = None) -> None:
        self.triples = triples or []

    def load_triples(self, triples: List[tuple[str, str, str]]) -> None:
        """Replace current graph triples."""

        self.triples = triples

    def validate(
        self,
        *,
        kg_id: str,
        tenant_id: str,
        rules: List[ValidationRule],
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Validate the knowledge graph against provided rules."""

        details: List[Dict[str, Any]] = []
        is_valid = True

        # Build adjacency and type maps
        adjacency: Dict[str, set[str]] = {}
        class_nodes: set[str] = set()
        instance_nodes: set[str] = set()
        for subj, pred, obj in self.triples:
            adjacency.setdefault(subj, set()).add(obj)
            adjacency.setdefault(obj, set()).add(subj)
            if pred == "rdf:type":
                if obj == "owl:Class":
                    class_nodes.add(subj)
                else:
                    instance_nodes.add(subj)

        nodes = set(adjacency)

        for rule in rules:
            if rule.name == "connectivity":
                if not nodes:
                    connected = True
                else:
                    visited: set[str] = set()
                    stack = [next(iter(nodes))]
                    while stack:
                        node = stack.pop()
                        if node not in visited:
                            visited.add(node)
                            stack.extend(adjacency.get(node, set()) - visited)
                    connected = len(visited) == len(nodes)
                details.append({"rule": rule.name, "status": connected})
                is_valid &= connected
            elif rule.name == "class_instance_separation":
                violations = list(class_nodes & instance_nodes)
                ok = len(violations) == 0
                details.append(
                    {"rule": rule.name, "status": ok, "violations": violations}
                )
                is_valid &= ok
            else:
                details.append({"rule": rule.name, "status": True})

        return is_valid, details
