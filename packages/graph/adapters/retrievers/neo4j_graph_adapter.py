"""Neo4j adapter implementing GraphRetrieverPort."""

import logging
from typing import Any, Dict, List, Optional, Union

from neo4j import Driver, GraphDatabase, Session

from application.ports import GraphRetrieverPort, MessageBusPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class Neo4jGraphAdapter(GraphRetrieverPort):
    """GraphRetrieverPort implementation using Neo4j.

    Queries are executed using Cypher and triples are stored as nodes and
    relationships. Documents are expected to contain comma separated triples in
    the form `subject,predicate,object` per line.
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        driver: Optional[Driver] = None,
        message_bus: Optional[MessageBusPort] = None,
        database: str = "neo4j",
    ) -> None:
        self._driver: Driver = driver or GraphDatabase.driver(
            uri, auth=(user, password)
        )
        self._database = database
        self._message_bus = message_bus

    def close(self) -> None:
        """Close the underlying Neo4j driver."""
        self._driver.close()

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        triples: List[Triple] = []
        with self._driver.session(database=self._database) as session:
            for triple in self._parse_documents(docs, tenant_id):
                triples.append(triple)
                self._store_triple(session, triple, kg_id)
        return triples

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple]]:
        with self._driver.session(database=self._database) as session:
            try:
                result = session.run(question, kg_id=kg_id, tenant_id=tenant_id)
                records = [r.data() for r in result]
            except Exception as e:
                raise GraphRAGException(
                    message=f"Neo4j query failed: {e}",
                    error_code="NEO4J_QUERY_ERROR",
                    context={"kg_id": kg_id, "tenant_id": tenant_id},
                ) from e

        if opts and opts.get("return_triples"):
            return self._records_to_triples(records, tenant_id)
        return str(records)

    def _store_triple(self, session: Session, triple: Triple, kg_id: str) -> None:
        cypher = (
            "MERGE (s:Entity {name: $s, tenant_id: $t}) "
            "MERGE (o:Entity {name: $o, tenant_id: $t}) "
            "MERGE (s)-[r:`"
            + triple.predicate.replace("`", "")
            + "` {kg_id: $kg}]->(o)"
        )
        session.run(
            cypher,
            s=triple.subject,
            o=triple.object,
            t=triple.tenant_id,
            kg=kg_id,
        )

    def _parse_documents(self, docs: List[str], tenant_id: str) -> List[Triple]:
        triples: List[Triple] = []
        for doc in docs:
            for line in doc.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 3:
                    triples.append(Triple(parts[0], parts[1], parts[2], tenant_id))
        return triples

    def _records_to_triples(
        self, records: List[Dict[str, Any]], tenant_id: str
    ) -> List[Triple]:
        triples: List[Triple] = []
        for record in records:
            if {"subject", "predicate", "object"} <= record.keys():
                triples.append(
                    Triple(
                        record["subject"],
                        record["predicate"],
                        record["object"],
                        tenant_id,
                    )
                )
        return triples
