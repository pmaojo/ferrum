"""Micro LLM adapter implementing LLMPort using small local models."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union

from application.ports import LLMPort
from domain.services import GraphRAGException
from domain.token_budget_service import TokenBudgetService

if TYPE_CHECKING:  # pragma: no cover - used only for type hints
    from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter
else:
    EmbeddingCacheAdapter = Any  # type: ignore

logger = logging.getLogger(__name__)


class LLMException(GraphRAGException):
    """Exception for LLM-related errors."""


@dataclass
class MicroLLMConfig:
    """Configuration for micro LLM models."""

    generation_model: str = "phi-2"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"


class MicroLLMAdapter(LLMPort):
    """LLM adapter using small local transformers models."""

    def __init__(
        self,
        *,
        config: MicroLLMConfig = MicroLLMConfig(),
        default_temperature: float = 0.7,
        default_top_p: float = 0.95,
        default_max_tokens: int = 1024,
        embedding_cache: Optional[EmbeddingCacheAdapter] = None,
        token_budget_service: Optional[TokenBudgetService] = None,
        tracer: Any = None,
    ) -> None:
        self.config = config
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.embedding_cache = embedding_cache
        self.token_budget_service = token_budget_service
        self.tracer = tracer

        # Lazy imports to avoid mandatory heavy dependencies in all environments
        try:  # pragma: no cover - optional dependency
            from sentence_transformers import SentenceTransformer
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        except Exception:  # pragma: no cover - not installed
            AutoModelForCausalLM = None
            AutoTokenizer = None
            pipeline = None
            SentenceTransformer = None

        if AutoModelForCausalLM is None or AutoTokenizer is None or pipeline is None:
            raise LLMException(
                message="transformers library is required for MicroLLMAdapter",
                error_code="TRANSFORMERS_MISSING",
                context={},
            )

        self.tokenizer = AutoTokenizer.from_pretrained(config.generation_model)
        model = AutoModelForCausalLM.from_pretrained(config.generation_model)
        self.generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=self.tokenizer,
            device=0 if config.device == "cuda" else -1,
        )

        if SentenceTransformer is None:
            raise LLMException(
                message="sentence-transformers library is required",
                error_code="SENTENCE_TRANSFORMERS_MISSING",
                context={},
            )

        self.embedder = SentenceTransformer(
            config.embedding_model, device=config.device
        )

        logger.info(
            "Initialized MicroLLMAdapter with generation model %s and embedding model %s",
            config.generation_model,
            config.embedding_model,
        )

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text using the local model."""
        options = {
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "max_tokens": self.default_max_tokens,
        }
        if opts:
            options.update(opts)

        try:
            outputs = self.generator(
                prompt,
                max_new_tokens=options["max_tokens"],
                temperature=options["temperature"],
                top_p=options["top_p"],
                return_full_text=False,
            )
            text = outputs[0]["generated_text"]
        except Exception as e:  # pragma: no cover - runtime errors
            logger.error("Local generation failed: %s", e)
            raise LLMException(
                message=f"Local generation failed: {e}",
                error_code="LOCAL_GENERATION_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

        if not stream:
            return text

        return iter(text.split())

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using the local embedder."""
        try:
            if isinstance(text, list):
                embeddings = self.embedder.encode(text, convert_to_numpy=True).tolist()
            else:
                embeddings = self.embedder.encode([text], convert_to_numpy=True)[
                    0
                ].tolist()
            return embeddings
        except Exception as e:  # pragma: no cover - runtime errors
            logger.error("Local embedding failed: %s", e)
            raise LLMException(
                message=f"Local embedding failed: {e}",
                error_code="LOCAL_EMBEDDING_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

    def moderate(
        self, *, text: str, tenant_id: str, opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simple moderation placeholder always returning safe."""
        return {
            "flagged": False,
            "categories": {},
            "category_scores": {},
            "text_safe": True,
        }

    def get_token_count(self, *, text: str) -> int:
        """Count tokens using the tokenizer."""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4
