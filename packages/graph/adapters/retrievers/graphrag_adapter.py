"""Main GraphRAG adapter that delegates to the GraphRAG SDK adapter."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from application.ports import GraphRetrieverPort
from domain.entities import Triple
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class GraphRAGAdapter(GraphRetrieverPort):
    """Main GraphRAG adapter that uses the GraphRAG SDK."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        username: Optional[str] = None,
        password: Optional[str] = None,
        llm_model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        tracer=None,
    ) -> None:
        """Initialize GraphRAG adapter."""
        try:
            from adapters.retrievers.graphrag_sdk_adapter import GraphRAGSDKAdapter

            self._sdk_adapter = GraphRAGSDKAdapter(
                host=host,
                port=port,
                username=username,
                password=password,
                llm_model=llm_model,
                api_key=api_key,
                tracer=tracer,
            )
            logger.info("GraphRAG adapter initialized with GraphRAG SDK")

        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG SDK adapter: {str(e)}")
            raise GraphRAGException(
                message="GraphRAG adapter initialization failed",
                error_code="ADAPTER_INIT_ERROR",
                context={"error": str(e)},
            ) from e

    def index(
        self,
        *,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        ontology_file: Optional[str] = None,
    ) -> List[Triple]:
        """Index documents using GraphRAG SDK."""
        return self._sdk_adapter.index(
            docs=docs, kg_id=kg_id, tenant_id=tenant_id, ontology_file=ontology_file
        )

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple], Dict[str, Any]]:
        """Query using GraphRAG SDK."""
        return self._sdk_adapter.run(
            question=question, kg_id=kg_id, tenant_id=tenant_id, opts=opts
        )

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
        target_format: str = "cypher",
    ) -> tuple[str, str]:
        """Translate natural language to graph query using GraphRAG SDK."""
        return self._sdk_adapter.translate(
            natural_language=natural_language,
            kg_id=kg_id,
            tenant_id=tenant_id,
            target_format=target_format,
        )

    def create_ontology_file(
        self,
        entities: List[str],
        relationships: List[str],
        output_file: str = "ontology.json",
    ) -> str:
        """Create ontology file for GraphRAG SDK."""
        return self._sdk_adapter.create_ontology_file(
            entities=entities, relationships=relationships, output_file=output_file
        )
