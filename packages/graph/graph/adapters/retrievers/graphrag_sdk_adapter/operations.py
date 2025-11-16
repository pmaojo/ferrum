from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from domain.entities import Triple
from domain.services import GraphRAGException

from .management import KnowledgeGraphManager

logger = logging.getLogger(__name__)


class QueryIndexOperations:
    def __init__(self, sdk: Dict[str, Any], kg_manager: KnowledgeGraphManager) -> None:
        self._sdk = sdk
        self._kg_manager = kg_manager

    def index_documents(
        self,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        ontology_file: Optional[str] = None,
    ) -> List[Triple]:
        logger.info(
            "Indexing %s documents for kg_id=%s, tenant_id=%s",
            len(docs),
            kg_id,
            tenant_id,
        )
        try:
            kg = self._kg_manager.get_or_create(kg_id, tenant_id, ontology_file)
            sources = [{"type": "text", "data": doc} for doc in docs]
            result = kg.process_sources(sources)
            triples: List[Triple] = []
            if hasattr(result, "entities"):
                for entity in result.entities:
                    triples.append(
                        Triple(
                            subject=entity.name,
                            predicate="is_a",
                            object=entity.type,
                            tenant_id=tenant_id,
                        )
                    )
            if hasattr(result, "relationships"):
                for rel in result.relationships:
                    triples.append(
                        Triple(
                            subject=rel.source,
                            predicate=rel.type,
                            object=rel.target,
                            tenant_id=tenant_id,
                        )
                    )
            return triples
        except Exception as e:
            logger.error("Document indexing failed: %s", e, exc_info=True)
            raise GraphRAGException(
                message=f"Document indexing failed: {str(e)}",
                error_code="INDEXING_ERROR",
                context={
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "doc_count": len(docs),
                },
            ) from e

    def run_query(
        self,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple], Dict[str, Any]]:
        logger.info(
            "Processing GraphRAG query for kg_id=%s, tenant_id=%s", kg_id, tenant_id
        )
        if not question or not question.strip():
            raise GraphRAGException(
                message="Question cannot be empty",
                error_code="INVALID_INPUT",
                context={"question": question, "kg_id": kg_id, "tenant_id": tenant_id},
            )
        options = {
            "return_formatted": True,
            "include_reasoning": True,
            "include_metadata": True,
        }
        if opts:
            options.update(opts)
        try:
            start_time = datetime.now()
            kg = self._kg_manager.get_or_create(kg_id, tenant_id)
            result = kg.ask(question)
            exec_ms = (datetime.now() - start_time).total_seconds() * 1000
            if options.get("return_triples", False):
                return self._extract_triples_from_result(result, tenant_id)
            if options.get("return_formatted", True):
                return self._format_sdk_response(
                    result, question, kg_id, tenant_id, exec_ms, options
                )
            return result.response if hasattr(result, "response") else str(result)
        except Exception as e:
            logger.error("GraphRAG query failed: %s", e, exc_info=True)
            raise GraphRAGException(
                message=f"GraphRAG query failed: {str(e)}",
                error_code="QUERY_ERROR",
                context={
                    "question": question[:100],
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                },
            ) from e

    def translate_query(
        self,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
        target_format: str = "cypher",
    ) -> tuple[str, str]:
        logger.info(
            "Translating natural language to %s for kg_id=%s", target_format, kg_id
        )
        try:
            query_lower = natural_language.lower()
            if target_format.lower() == "cypher":
                if "find" in query_lower or "search" in query_lower:
                    return "MATCH (n) RETURN n LIMIT 10", "Basic entity search query"
                if "count" in query_lower:
                    return "MATCH (n) RETURN count(n)", "Count all entities"
                return "MATCH (n) RETURN n LIMIT 10", "Default entity listing query"
            return "g.V().limit(10)", f"Basic {target_format} traversal"
        except Exception as e:
            logger.error("Query translation failed: %s", e, exc_info=True)
            raise GraphRAGException(
                message=f"Query translation failed: {str(e)}",
                error_code="TRANSLATION_ERROR",
                context={
                    "natural_language": natural_language[:100],
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "target_format": target_format,
                },
            ) from e

    def _extract_triples_from_result(self, result: Any, tenant_id: str) -> List[Triple]:
        triples: List[Triple] = []
        try:
            if hasattr(result, "context"):
                for entity in getattr(result.context, "entities", []):
                    triples.append(
                        Triple(
                            subject=entity.name,
                            predicate="is_a",
                            object=entity.type,
                            tenant_id=tenant_id,
                        )
                    )
                for rel in getattr(result.context, "relationships", []):
                    triples.append(
                        Triple(
                            subject=rel.source,
                            predicate=rel.type,
                            object=rel.target,
                            tenant_id=tenant_id,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to extract triples from result: %s", e)
        return triples

    def _format_sdk_response(
        self,
        result: Any,
        question: str,
        kg_id: str,
        tenant_id: str,
        execution_time_ms: float,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        answer = result.response if hasattr(result, "response") else str(result)
        context = getattr(result, "context", None)
        formatted = {
            "question": question,
            "kg_id": kg_id,
            "tenant_id": tenant_id,
            "answer": answer,
            "results": [],
        }
        if context:
            for entity in getattr(context, "entities", []):
                formatted["results"].append(
                    {
                        "type": "entity",
                        "name": entity.name,
                        "entity_type": entity.type,
                        "description": getattr(entity, "description", ""),
                        "tenant_id": tenant_id,
                    }
                )
            for rel in getattr(context, "relationships", []):
                formatted["results"].append(
                    {
                        "type": "relationship",
                        "source": rel.source,
                        "predicate": rel.type,
                        "target": rel.target,
                        "tenant_id": tenant_id,
                    }
                )
        if hasattr(result, "reasoning"):
            formatted["explanation"] = result.reasoning
        if options.get("include_metadata", True):
            formatted["metadata"] = {
                "execution_time_ms": execution_time_ms,
                "result_count": len(formatted["results"]),
                "timestamp": datetime.now().isoformat(),
                "source": "graphrag_sdk",
            }
        return formatted
