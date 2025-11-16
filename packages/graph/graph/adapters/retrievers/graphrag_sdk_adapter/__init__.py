from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from application.ports import GraphRetrieverPort
from domain.entities import Triple

from .configuration import DEFAULT_PROMPTS, SDKConfig, initialize_sdk
from .management import KnowledgeGraphManager
from .operations import QueryIndexOperations


class GraphRAGSDKAdapter(GraphRetrieverPort):
    """Adapter integrating the GraphRAG SDK."""

    DEFAULT_PROMPTS = DEFAULT_PROMPTS

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        username: Optional[str] = None,
        password: Optional[str] = None,
        llm_model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        tracer=None,
        use_litellm: bool = False,
        litellm_fallbacks: Optional[List[str]] = None,
        custom_prompts: Optional[Dict[str, str]] = None,
    ) -> None:
        config = SDKConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            llm_model=llm_model,
            api_key=api_key,
            tracer=tracer,
            use_litellm=use_litellm,
            litellm_fallbacks=litellm_fallbacks,
        )
        self._sdk = initialize_sdk(config)
        self.prompts = {**DEFAULT_PROMPTS, **(custom_prompts or {})}
        self._kg_manager = KnowledgeGraphManager(
            self._sdk, host, port, username, password
        )
        self._ops = QueryIndexOperations(self._sdk, self._kg_manager)

    def index(
        self,
        *,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        ontology_file: Optional[str] = None,
    ) -> List[Triple]:
        return self._ops.index_documents(docs, kg_id, tenant_id, ontology_file)

    def run(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, List[Triple], Dict[str, Any]]:
        return self._ops.run_query(question, kg_id, tenant_id, opts)

    def translate(
        self,
        *,
        natural_language: str,
        kg_id: str,
        tenant_id: str,
        target_format: str = "cypher",
    ) -> tuple[str, str]:
        return self._ops.translate_query(
            natural_language, kg_id, tenant_id, target_format
        )

    def create_ontology_file(
        self,
        entities: List[str],
        relationships: List[str],
        output_file: str = "ontology.json",
    ) -> str:
        return KnowledgeGraphManager.create_ontology_file(
            entities, relationships, output_file
        )
