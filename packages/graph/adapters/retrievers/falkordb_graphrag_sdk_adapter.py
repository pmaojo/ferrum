"""Clean FalkorDB GraphRAG adapter without SDK dependencies."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis

from application.ports import GraphRetrieverPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class FalkorDBGraphRAGAdapter(GraphRetrieverPort):
    """Clean GraphRAG adapter using FalkorDB directly via Redis protocol."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tracer=None,
    ):
        """Initialize FalkorDB GraphRAG adapter.

        Args:
            host: FalkorDB host
            port: FalkorDB port
            username: Optional FalkorDB username
            password: Optional FalkorDB password
            tracer: Optional tracing port
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.tracer = tracer

        # Direct Redis connection to FalkorDB
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                username=username,
                password=password,
                decode_responses=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to FalkorDB at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            raise GraphRAGException(
                message=f"FalkorDB connection failed: {str(e)}",
                error_code="CONNECTION_FAILED",
                context={"host": host, "port": port},
            )

    def index(self, *, docs: List[str], kg_id: str, tenant_id: str) -> List[Triple]:
        """Index documents into the knowledge graph."""
        try:
            if self.tracer:
                self.tracer.start_span(
                    name="falkordb.index",
                    tenant_id=tenant_id,
                    kg_id=kg_id,
                    doc_count=len(docs),
                )

            logger.info(
                f"Indexing {len(docs)} documents for kg_id={kg_id}, tenant_id={tenant_id}"
            )

            graph_name = f"{tenant_id}_{kg_id}"

            # Create graph if it doesn't exist
            self.redis_client.execute_command("GRAPH.QUERY", graph_name, "RETURN 1")

            triples = []
            for i, doc_content in enumerate(docs):
                # Simple entity extraction (you can enhance this with LLM calls)
                doc_node = f"Document_{i}"

                # Create document node
                query = f"""
                MERGE (d:Document {{id: '{doc_node}', content: $content, tenant_id: '{tenant_id}'}})
                RETURN d
                """
                self.redis_client.execute_command(
                    "GRAPH.QUERY",
                    graph_name,
                    query,
                    "--params",
                    json.dumps({"content": doc_content[:500]}),
                )

                # Create triple
                triples.append(
                    Triple(
                        subject=doc_node,
                        predicate="contains_content",
                        object=f"content_{i}",
                        tenant_id=tenant_id,
                    )
                )

            logger.info(
                f"Successfully indexed documents, created {len(triples)} triples"
            )
            return triples

        except Exception as e:
            logger.error(f"Failed to index documents: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"Document indexing failed: {str(e)}",
                error_code="INDEXING_FAILED",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "doc_count": len(docs),
                },
            ) from e

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple], Dict[str, Any]]:
        """Execute natural language query against knowledge graph."""
        try:
            if self.tracer:
                self.tracer.start_span(
                    name="falkordb.query",
                    tenant_id=tenant_id,
                    kg_id=kg_id,
                    question=question[:100],
                )

            logger.info(f"Executing query for kg_id={kg_id}, tenant_id={tenant_id}")

            options = {"return_formatted": True, "max_results": 10, **(opts or {})}

            graph_name = f"{tenant_id}_{kg_id}"

            # Simple graph query based on question keywords
            query = f"""
            MATCH (n)
            WHERE n.tenant_id = '{tenant_id}'
            RETURN n.id, labels(n), n
            LIMIT {options.get('max_results', 10)}
            """

            result = self.redis_client.execute_command("GRAPH.QUERY", graph_name, query)

            # Parse FalkorDB result format
            entities = []
            if result and len(result) > 1:
                for row in result[1]:  # Skip header row
                    entities.append(
                        {
                            "id": row[0] if len(row) > 0 else "unknown",
                            "labels": row[1] if len(row) > 1 else [],
                            "properties": row[2] if len(row) > 2 else {},
                        }
                    )

            if options.get("return_formatted", True):
                return {
                    "answer": f"Found {len(entities)} entities in the knowledge graph related to your query.",
                    "question": question,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "entities": entities,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return f"Found {len(entities)} entities"

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise GraphRAGException(
                message=f"Query execution failed: {str(e)}",
                error_code="QUERY_FAILED",
                context={
                    "question": question[:100],
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                },
            ) from e

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
        target_format: str = "cypher",
    ) -> tuple[str, str]:
        """Translate natural language to graph query language."""
        query_lower = natural_language.lower()

        if "find" in query_lower or "search" in query_lower:
            query = f"MATCH (n) WHERE n.tenant_id = '{tenant_id}' RETURN n LIMIT 10"
            explanation = "Search for entities in the knowledge graph"
        elif "count" in query_lower:
            query = f"MATCH (n) WHERE n.tenant_id = '{tenant_id}' RETURN count(n)"
            explanation = "Count entities in the knowledge graph"
        else:
            query = f"MATCH (n) WHERE n.tenant_id = '{tenant_id}' RETURN n LIMIT 10"
            explanation = "List entities in the knowledge graph"

        return query, explanation
