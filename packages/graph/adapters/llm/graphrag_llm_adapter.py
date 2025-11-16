"""GraphRAG SDK-based LLM adapter implementing LLMPort.

This adapter relies on the GraphRAG SDK `GenerativeModel` for text generation
and optionally embeddings. It avoids direct calls to LLM providers by
deferring all model interaction to the SDK.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, List, Optional, Union

from application.ports import LLMPort
from domain.services import GraphRAGException

try:
    from graphrag_sdk.models import openai as graphrag_openai
except Exception:  # pragma: no cover - SDK optional
    graphrag_openai = None

logger = logging.getLogger(__name__)


class LLMException(GraphRAGException):
    """Exception for LLM-related errors."""


class GraphRAGLLMAdapter(LLMPort):
    """LLM adapter using GraphRAG SDK generative models."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        default_temperature: float = 0.7,
        default_top_p: float = 0.95,
        default_max_tokens: int = 1024,
    ) -> None:
        if graphrag_openai is None:
            raise LLMException(
                message="GraphRAG SDK not installed",
                error_code="GRAPHRAG_SDK_MISSING",
                context={},
            )

        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        try:
            self.model = graphrag_openai.OpenAiGenerativeModel(model_name)
            logger.info("Initialized GraphRAGLLMAdapter with model %s", model_name)
        except Exception as e:
            raise LLMException(
                message=f"Failed to initialize GraphRAG model: {e}",
                error_code="GRAPHRAG_MODEL_INIT_ERROR",
                context={"model_name": model_name},
            ) from e

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text using the GraphRAG SDK model."""
        opts = opts or {}
        temperature = opts.get("temperature", self.default_temperature)
        top_p = opts.get("top_p", self.default_top_p)
        max_tokens = opts.get("max_tokens", self.default_max_tokens)

        session = self.model.start_chat()
        try:
            if stream:
                response_iter = session.send_message_stream(
                    prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    tools=tools,
                )
                return (chunk for chunk in response_iter)
            response = session.send_message(
                prompt,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                tools=tools,
            )
            return response.text
        except Exception as e:  # pragma: no cover - runtime errors
            logger.error("GraphRAG generation failed: %s", e)
            raise LLMException(
                message=f"GraphRAG generation failed: {e}",
                error_code="GRAPHRAG_GENERATION_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Embeddings are delegated to the model if available."""
        if not hasattr(self.model, "embed"):
            raise LLMException(
                message="Embedding not supported by GraphRAG model",
                error_code="GRAPHRAG_EMBED_NOT_SUPPORTED",
                context={},
            )
        try:
            return self.model.embed(text)
        except Exception as e:  # pragma: no cover - runtime errors
            logger.error("GraphRAG embedding failed: %s", e)
            raise LLMException(
                message=f"GraphRAG embedding failed: {e}",
                error_code="GRAPHRAG_EMBED_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

    def moderate(
        self,
        *,
        text: str,
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Basic moderation using the model's capabilities if exposed."""
        if hasattr(self.model, "moderate"):
            try:
                return self.model.moderate(text)
            except Exception as e:  # pragma: no cover - runtime errors
                logger.error("GraphRAG moderation failed: %s", e)
                raise LLMException(
                    message=f"GraphRAG moderation failed: {e}",
                    error_code="GRAPHRAG_MODERATION_ERROR",
                    context={"tenant_id": tenant_id},
                ) from e
        return {
            "flagged": False,
            "categories": {},
            "category_scores": {},
            "text_safe": True,
        }

    def get_token_count(self, *, text: str) -> int:
        """Estimate token count using the model tokenizer if available."""
        if hasattr(self.model, "count_tokens"):
            try:
                return self.model.count_tokens(text)
            except Exception:
                pass
        return max(1, len(text) // 4)
