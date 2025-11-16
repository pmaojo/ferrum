"""In-memory implementation of :class:`OntologyAdapter`."""

from collections import defaultdict
from typing import Dict, List, Any

from application.ports.ontology_adapter import OntologyAdapter
from domain.entities.triple import Triple
from domain.entities.validation_report import ValidationReport


class InMemoryOntologyAdapter(OntologyAdapter):
    """Maintain ontology data structures in memory."""

    def __init__(self) -> None:
        self._ontologies: Dict[str, List[Triple]] = defaultdict(list)

    def load_base_ontology(self, tenant_id: str) -> bool:
        self._ontologies[tenant_id] = []
        return True

    def import_architecture_graph(self, tenant_id: str, graph_json: Dict) -> List[Triple]:
        triples = [Triple(**t) for t in graph_json.get("triples", [])]
        self._ontologies[tenant_id].extend(triples)
        return triples

    def validate_architecture(self, tenant_id: str) -> ValidationReport:
        return ValidationReport(
            tenant_id=tenant_id,
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation=None,
        )

    def sync_incremental_changes(self, tenant_id: str, delta: Dict) -> ValidationReport:
        adds = [Triple(**t) for t in delta.get("add", [])]
        removes = [Triple(**t) for t in delta.get("remove", [])]
        current = self._ontologies[tenant_id]
        current[:] = [t for t in current if t.to_dict() not in [r.to_dict() for r in removes]]
        current.extend(adds)
        return self.validate_architecture(tenant_id)

    def export_react_flow_format(self, tenant_id: str) -> Dict[str, Any]:
        triples = self._ontologies.get(tenant_id, [])
        nodes = {}
        edges = []
        for t in triples:
            nodes.setdefault(t.subject, {"id": t.subject})
            nodes.setdefault(t.object, {"id": t.object})
            edges.append({"source": t.subject, "target": t.object, "label": t.predicate})
        return {"nodes": list(nodes.values()), "edges": edges}

    def export_rdf_turtle(self, tenant_id: str) -> str:
        return "\n".join(t.to_turtle() for t in self._ontologies.get(tenant_id, []))

    def get_module_triples(self, module: str) -> List[Dict[str, Any]]:
        triples = self._ontologies.get(module, [])
        return [t.to_dict() for t in triples]
