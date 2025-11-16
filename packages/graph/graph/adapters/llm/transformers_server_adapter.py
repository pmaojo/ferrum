"""Transformers HTTP Server adapter implementing LLMPort with OpenAI-compatible API.

This adapter integrates with Hugging Face transformers HTTP server to provide
local model inference with OpenAI-compatible API endpoints for text generation,
embeddings, and function calling capabilities.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

import aiohttp

from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter
from application.ports import LLMPort
from domain.services import GraphRAGException
from domain.token_budget_service import TokenBudgetService

logger = logging.getLogger(__name__)


class LLMException(GraphRAGException):
    """Exception for LLM-related errors."""


class TransformersServerUnavailableException(LLMException):
    """Exception for transformers server unavailability."""


@dataclass
class TransformersServerConfig:
    """Configuration for transformers server connection."""

    base_url: str
    model_name: str
    max_retries: int = 3
    timeout_seconds: int = 120
    health_check_interval: int = 30


class TransformersServerAdapter(LLMPort):
    """Adapter for Hugging Face transformers HTTP server with OpenAI compatibility.

    This adapter provides local model inference using the transformers serve
    command with OpenAI-compatible API endpoints, offering:
    - Text generation with streaming support
    - Function calling capabilities
    - Embedding generation
    - Semantic caching integration
    - Fallback compatibility with existing LLM adapters
    """

    def __init__(
        self,
        server_config: TransformersServerConfig,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        default_temperature: float = 0.7,
        default_top_p: float = 0.95,
        default_max_tokens: int = 1024,
        embedding_cache: Optional[EmbeddingCacheAdapter] = None,
        token_budget_service: Optional[TokenBudgetService] = None,
        tracer=None,
    ):
        """Initialize TransformersServerAdapter.

        Args:
            server_config: Configuration for transformers server connection
            embedding_model: Model name for embeddings (can be different from generation)
            default_temperature: Default sampling temperature
            default_top_p: Default nucleus sampling parameter
            default_max_tokens: Default maximum tokens to generate
            embedding_cache: Optional embedding cache adapter
            token_budget_service: Optional token budget tracking service
            tracer: Optional tracing port for observability
        """
        self.server_config = server_config
        self.embedding_model = embedding_model
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.embedding_cache = embedding_cache
        self.token_budget_service = token_budget_service
        self.tracer = tracer

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._server_healthy = False
        self._last_health_check = None

        logger.info(
            f"Initialized TransformersServerAdapter with server: {server_config.base_url}, "
            f"model: {server_config.model_name}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.server_config.timeout_seconds)
            self.session = aiohttp.ClientSession(
                timeout=timeout, headers={"Content-Type": "application/json"}
            )
        return self.session

    async def _health_check(self) -> bool:
        """Check if transformers server is healthy."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.server_config.base_url}/v1/models"
            ) as response:
                if response.status == 200:
                    models_data = await response.json()
                    # Check if our configured model is available
                    available_models = [
                        m.get("id", "") for m in models_data.get("data", [])
                    ]
                    self._server_healthy = (
                        self.server_config.model_name in available_models
                    )
                    self._last_health_check = datetime.now()
                    return self._server_healthy
                return False
        except Exception as e:
            logger.warning(f"Transformers server health check failed: {e}")
            self._server_healthy = False
            return False

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Generate with structured outputs and function calling."""
        if not await self._health_check():
            raise TransformersServerUnavailableException(
                message="Transformers server is not available",
                error_code="TRANSFORMERS_SERVER_UNAVAILABLE",
                context={"server_url": self.server_config.base_url},
            )

        try:
            session = await self._get_session()

            payload = {
                "model": self.server_config.model_name,
                "messages": messages,
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
            }

            if response_format:
                payload["response_format"] = response_format
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            url = f"{self.server_config.base_url}/v1/chat/completions"

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()

                    result = {
                        "content": data["choices"][0]["message"]["content"],
                        "usage": data.get(
                            "usage",
                            {
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_tokens": 0,
                            },
                        ),
                    }

                    # Handle tool calls if present
                    if "tool_calls" in data["choices"][0]["message"]:
                        result["tool_calls"] = [
                            {
                                "id": call["id"],
                                "function": call["function"]["name"],
                                "arguments": json.loads(call["function"]["arguments"]),
                            }
                            for call in data["choices"][0]["message"]["tool_calls"]
                        ]

                    return result
                else:
                    error_text = await response.text()
                    raise LLMException(
                        message=f"Transformers server error: {error_text}",
                        error_code="TRANSFORMERS_GENERATION_ERROR",
                        context={"status_code": response.status},
                    )

        except Exception as e:
            logger.error(f"Transformers server structured generation failed: {e}")
            raise LLMException(
                message=f"Transformers server generation failed: {str(e)}",
                error_code="TRANSFORMERS_GENERATION_ERROR",
                context={"model": self.server_config.model_name},
            ) from e

    async def create_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """Create embeddings using transformers server."""
        if not await self._health_check():
            raise TransformersServerUnavailableException(
                message="Transformers server is not available for embeddings",
                error_code="TRANSFORMERS_SERVER_UNAVAILABLE",
                context={"server_url": self.server_config.base_url},
            )

        try:
            session = await self._get_session()

            embedding_model = model or self.embedding_model
            payload = {
                "model": embedding_model,
                "input": texts,
                "encoding_format": "float",
            }

            url = f"{self.server_config.base_url}/v1/embeddings"

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return [item["embedding"] for item in data["data"]]
                else:
                    error_text = await response.text()
                    raise LLMException(
                        message=f"Transformers server embedding error: {error_text}",
                        error_code="TRANSFORMERS_EMBEDDING_ERROR",
                        context={"status_code": response.status},
                    )

        except Exception as e:
            logger.error(f"Transformers server embedding generation failed: {e}")
            raise LLMException(
                message=f"Transformers server embedding failed: {str(e)}",
                error_code="TRANSFORMERS_EMBEDDING_ERROR",
                context={"model": embedding_model},
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
        """Generate text from a prompt using transformers server.

        Args:
            prompt: Text prompt to send to the model
            tenant_id: Tenant identifier for multi-tenant isolation
            stream: Whether to stream the response tokens
            tools: Optional list of tool definitions for function calling
            opts: Optional parameters for generation

        Returns:
            Generated text as string or token iterator if streaming
        """
        # Run async method in sync context
        return asyncio.run(
            self._generate_async(
                prompt=prompt,
                tenant_id=tenant_id,
                stream=stream,
                tools=tools,
                opts=opts,
            )
        )

    async def _generate_async(
        self,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Async implementation of text generation."""
        if not await self._health_check():
            raise TransformersServerUnavailableException(
                message="Transformers server is not available",
                error_code="TRANSFORMERS_SERVER_UNAVAILABLE",
                context={
                    "server_url": self.server_config.base_url,
                    "tenant_id": tenant_id,
                },
            )

        # Set default options
        options = {
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "max_tokens": self.default_max_tokens,
        }

        if opts:
            options.update(opts)

        start_time = datetime.now()

        try:
            session = await self._get_session()

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Configure generation parameters
            payload = {
                "model": self.server_config.model_name,
                "messages": messages,
                "temperature": options.get("temperature", self.default_temperature),
                "top_p": options.get("top_p", self.default_top_p),
                "max_tokens": options.get("max_tokens", self.default_max_tokens),
                "stream": stream,
            }

            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            url = f"{self.server_config.base_url}/v1/chat/completions"

            if stream:
                return await self._stream_response(
                    session, url, payload, tenant_id, start_time
                )
            else:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Record metrics
                        execution_time_ms = (
                            datetime.now() - start_time
                        ).total_seconds() * 1000
                        if self.tracer:
                            self._record_metrics(
                                tenant_id=tenant_id,
                                execution_time_ms=execution_time_ms,
                                token_count=data.get("usage", {}).get(
                                    "prompt_tokens", 0
                                ),
                                completion_tokens=data.get("usage", {}).get(
                                    "completion_tokens", 0
                                ),
                            )

                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        raise LLMException(
                            message=f"Transformers server error: {error_text}",
                            error_code="TRANSFORMERS_GENERATION_ERROR",
                            context={
                                "status_code": response.status,
                                "tenant_id": tenant_id,
                            },
                        )

        except Exception as e:
            logger.error(f"Transformers server generation failed: {str(e)}")

            if self.tracer:
                self.tracer.record_metric(
                    name="transformers_generation_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"Transformers server generation failed: {str(e)}",
                error_code="TRANSFORMERS_GENERATION_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.server_config.model_name,
                    "prompt_length": len(prompt),
                },
            ) from e

    async def _stream_response(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: Dict,
        tenant_id: str,
        start_time: datetime,
    ) -> Iterator[str]:
        """Handle streaming response from transformers server."""
        tokens_generated = 0

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMException(
                        message=f"Transformers server streaming error: {error_text}",
                        error_code="TRANSFORMERS_STREAMING_ERROR",
                        context={"status_code": response.status},
                    )

                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        chunk_data = line[6:]  # Remove 'data: ' prefix
                        if chunk_data == "[DONE]":
                            break

                        try:
                            chunk_json = json.loads(chunk_data)
                            if "choices" in chunk_json and chunk_json["choices"]:
                                delta = chunk_json["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    tokens_generated += 1
                                    yield content
                        except json.JSONDecodeError:
                            continue

            # Record metrics after streaming completes
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self._record_metrics(
                    tenant_id=tenant_id,
                    execution_time_ms=execution_time_ms,
                    token_count=0,  # We don't know prompt tokens in streaming mode
                    completion_tokens=tokens_generated,
                )

        except Exception as e:
            logger.error(f"Error during transformers server streaming: {str(e)}")
            raise

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text using transformers server."""
        return asyncio.run(self._embed_async(text=text, tenant_id=tenant_id, opts=opts))

    async def _embed_async(
        self,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Async implementation of embedding generation."""
        start_time = datetime.now()
        cache_hit = False

        try:
            # Check cache if available
            if self.embedding_cache:
                cached_embedding = self.embedding_cache.get_embedding(
                    text=text, tenant_id=tenant_id, opts=opts
                )

                if cached_embedding is not None:
                    cache_hit = True
                    if self.tracer:
                        self.tracer.record_metric(
                            name="embedding_cache_hit", value=1.0, tenant_id=tenant_id
                        )
                    return cached_embedding

            # Generate embeddings from transformers server
            if isinstance(text, list):
                embeddings = await self.create_embeddings(text)
            else:
                embeddings_list = await self.create_embeddings([text])
                embeddings = embeddings_list[0]

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="transformers_embedding_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                    cache_hit=cache_hit,
                )

            # Store in cache if available
            if self.embedding_cache:
                self.embedding_cache.store_embedding(
                    text=text, embedding=embeddings, tenant_id=tenant_id, opts=opts
                )

            return embeddings

        except Exception as e:
            logger.error(f"Transformers server embedding generation failed: {str(e)}")

            if self.tracer:
                self.tracer.record_metric(
                    name="transformers_embedding_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"Transformers server embedding generation failed: {str(e)}",
                error_code="TRANSFORMERS_EMBEDDING_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.embedding_model,
                    "text_type": "batch" if isinstance(text, list) else "single",
                },
            ) from e

    def get_token_count(self, *, text: str) -> int:
        """Calculate the number of tokens in the provided text."""
        try:
            # Use a simple heuristic: ~4 characters per token for most models
            estimated_tokens = len(text) // 4
            return max(1, estimated_tokens)  # Ensure at least 1 token
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}")
            return len(text) // 4

    def _record_metrics(
        self,
        *,
        tenant_id: str,
        execution_time_ms: float,
        token_count: int,
        completion_tokens: int = 0,
        operation: str = "generate",
    ) -> None:
        """Record metrics for transformers server operations."""
        # Track token usage with budget service if available
        if self.token_budget_service:
            self.token_budget_service.track_usage(
                tenant_id=tenant_id,
                prompt_tokens=token_count,
                completion_tokens=completion_tokens,
                model=self.server_config.model_name,
                operation=operation,
                llm_provider="transformers_server",
            )

        if not self.tracer:
            return

        # Record latency metric
        self.tracer.record_metric(
            name="transformers_latency_ms", value=execution_time_ms, tenant_id=tenant_id
        )

        # Record token count metrics
        self.tracer.record_metric(
            name="transformers_prompt_token_count",
            value=token_count,
            tenant_id=tenant_id,
            operation=operation,
        )

        self.tracer.record_metric(
            name="transformers_completion_token_count",
            value=completion_tokens,
            tenant_id=tenant_id,
        )

        # Record total token count
        total_tokens = token_count + completion_tokens
        self.tracer.record_metric(
            name="transformers_total_token_count",
            value=total_tokens,
            tenant_id=tenant_id,
        )

    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
