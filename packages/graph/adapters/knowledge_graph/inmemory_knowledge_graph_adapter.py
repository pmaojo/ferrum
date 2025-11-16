"""In-memory implementation of KnowledgeGraphPort."""

from collections import defaultdict
import re
from typing import List, Optional, Dict, Any

from application.ports.knowledge_graph_port import KnowledgeGraphPort
from domain.entities.triple import Triple


class InMemoryKnowledgeGraphAdapter(KnowledgeGraphPort):
    """Store triples in memory for each tenant."""

    def __init__(self) -> None:
        self._graphs: Dict[str, List[Triple]] = defaultdict(list)

    def add_triple(self, tenant_id: str, triple: Triple) -> bool:
        self._graphs[tenant_id].append(triple)
        return True

    def remove_triple(self, tenant_id: str, triple: Triple) -> bool:
        triples = self._graphs.get(tenant_id, [])
        self._graphs[tenant_id] = [t for t in triples if t != triple]
        return True

    def query_triples(
        self,
        tenant_id: str,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> List[Triple]:
        results = []
        for t in self._graphs.get(tenant_id, []):
            if subject and t.subject != subject:
                continue
            if predicate and t.predicate != predicate:
                continue
            if object and t.object != object:
                continue
            results.append(t)
        return results

    def execute_sparql(self, tenant_id: str, query: str) -> List[Dict[str, Any]]:
        query = " ".join(query.strip().split())
        match = re.match(
            r"select\s+(?P<select>\*|(?:\?[spo](?:\s+\?[spo]){0,2}))\s+where\s*{\s*(?P<s>[^\s]+)\s+(?P<p>[^\s]+)\s+(?P<o>[^\s]+)\s*}",
            query,
            re.IGNORECASE,
        )
        if not match:
            return []

        select = match.group("select").split()
        s, p, o = match.group("s"), match.group("p"), match.group("o")

        def _value(val: str, triple: Triple, attr: str) -> Optional[str]:
            if val.startswith("?"):
                return getattr(triple, attr)
            if getattr(triple, attr) == val:
                return getattr(triple, attr)
            return None

        results: List[Dict[str, Any]] = []
        for t in self._graphs.get(tenant_id, []):
            sv = _value(s, t, "subject")
            if sv is None:
                continue
            pv = _value(p, t, "predicate")
            if pv is None:
                continue
            ov = _value(o, t, "object")
            if ov is None:
                continue

            if select == ["*"]:
                results.append(t.to_dict())
            else:
                row: Dict[str, Any] = {}
                for var in select:
                    if var == "?s":
                        row[var[1:]] = sv
                    elif var == "?p":
                        row[var[1:]] = pv
                    elif var == "?o":
                        row[var[1:]] = ov
                results.append(row)
        return results

    def clear_graph(self, tenant_id: str) -> bool:
        self._graphs[tenant_id] = []
        return True

