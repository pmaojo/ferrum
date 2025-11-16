from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from domain.services import GraphRAGException

logger = logging.getLogger(__name__)

DEFAULT_PROMPTS: Dict[str, str] = {
    "cypher_system_instruction": """
You are an expert in generating Cypher queries for Neo4j/FalkorDB graph databases.
Use the provided ontology to understand the graph structure and relationships.

Ontology:
{ontology}

Generate accurate Cypher queries based on the user's natural language questions.
Always consider the ontology when creating queries.
""",
    "qa_system_instruction": """
You are a helpful assistant that answers questions based on graph database query results.
Provide clear, accurate, and contextual answers based on the retrieved information.
""",
    "cypher_gen_prompt": """
Based on the following question, generate a Cypher query:

Question: {question}

Generate only the Cypher query without explanations.
""",
    "cypher_gen_prompt_history": """
Based on the following question and previous context, generate a Cypher query:

Question: {question}
Previous Answer: {last_answer}

Generate only the Cypher query without explanations.
""",
    "qa_prompt": """
Based on the following question, Cypher query, and results, provide a comprehensive answer:

Question: {question}
Cypher Query: {cypher}
Results: {context}

Provide a clear and informative answer based on the query results.
""",
}

DEFAULT_LITELLM_FALLBACKS = [
    "gemini/gemini-2.0-flash",
    "openai/gpt-4o-mini",
    "anthropic/claude-3-haiku-20240307",
    "groq/llama-3.1-8b-instant",
]


@dataclass
class SDKConfig:
    host: str = "127.0.0.1"
    port: int = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    llm_model: str = "gemini-2.5-flash"
    api_key: Optional[str] = None
    tracer: Any = None
    use_litellm: bool = False
    litellm_fallbacks: Optional[List[str]] = None


def initialize_sdk(config: SDKConfig) -> Dict[str, Any]:
    """Load GraphRAG SDK components and create the base GraphRAG instance."""
    try:
        from graphrag_sdk import (
            GenerativeModel,
            GraphRAG,
            KnowledgeGraph,
            KnowledgeGraphModelConfig,
            Ontology,
        )
    except ImportError as e:
        logger.error("GraphRAG SDK not available: %s", e)
        raise GraphRAGException(
            message="GraphRAG SDK not installed or configured properly",
            error_code="GRAPHRAG_SDK_NOT_AVAILABLE",
            context={"error": str(e)},
        ) from e

    supported_prefixes = ("gemini", "openai", "groq", "anthropic", "deepseek")
    if config.llm_model.startswith(supported_prefixes):
        model = GenerativeModel(model_name=config.llm_model, api_key=config.api_key)
    else:
        model = GenerativeModel(model_name="gemini-2.5-flash", api_key=config.api_key)

    sdk_conf: Dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "username": config.username,
        "password": config.password,
    }

    if config.use_litellm:
        sdk_conf["llm_config"] = {
            "provider": "litellm",
            "model": config.llm_model,
            "api_key": config.api_key,
            "fallbacks": config.litellm_fallbacks or DEFAULT_LITELLM_FALLBACKS,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "cost_tracking": True,
            "error_handling": {
                "rate_limit_retry": True,
                "context_length_fallback": True,
                "model_unavailable_fallback": True,
            },
        }
    else:
        sdk_conf["api_key"] = config.api_key

    graphrag = GraphRAG(**sdk_conf)
    logger.info("GraphRAG SDK initialized successfully")

    return {
        "KnowledgeGraph": KnowledgeGraph,
        "KnowledgeGraphModelConfig": KnowledgeGraphModelConfig,
        "Ontology": Ontology,
        "GenerativeModel": GenerativeModel,
        "GraphRAG": GraphRAG,
        "model": model,
        "graphrag": graphrag,
    }
