"""OpenAI LLM adapter implementing LLMPort for text generation and embeddings.

This adapter integrates with OpenAI's API to provide text generation
with streaming and function calling capabilities, as well as embedding generation
using text-embedding-3-large with semantic caching.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

import openai
from openai import AsyncOpenAI  # Import AsyncOpenAI
from openai import OpenAI

from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter
from application.ports import LLMPort
from domain.services import GraphRAGException
from domain.token_budget_service import TokenBudgetService

logger = logging.getLogger(__name__)


class LLMException(GraphRAGException):
    """Exception for LLM-related errors."""


class QuotaExceededException(LLMException):
    """Exception for API quota exceeded errors."""


class OpenAILLMAdapter(LLMPort):
    """Adapter for OpenAI API implementing LLMPort.

    Provides text generation with streaming and function calling capabilities,
    as well as embedding generation using text-embedding-3-large with semantic caching.
    """

    def __init__(
        self,
        api_key: str,
        generation_model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-large",
        default_temperature: float = 0.7,
        default_top_p: float = 0.95,
        default_max_tokens: int = 1024,
        embedding_cache: Optional[EmbeddingCacheAdapter] = None,
        token_budget_service: Optional[TokenBudgetService] = None,
        tracer=None,
        model: str = "gpt-4o-mini",
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize OpenAILLMAdapter with API key and configuration.

        Args:
            api_key: OpenAI API key
            generation_model: OpenAI model name for text generation (default: "gpt-4o")
            embedding_model: OpenAI model name for embeddings (default: "text-embedding-3-large")
            default_temperature: Default sampling temperature (default: 0.7)
            default_top_p: Default nucleus sampling parameter (default: 0.95)
            default_max_tokens: Default maximum tokens to generate (default: 1024)
            embedding_cache: Optional embedding cache adapter for semantic caching
            tracer: Optional tracing port for observability
            model: Model for structured output generation
            organization: OpenAI organization
            base_url: OpenAI base url

        Raises:
            LLMException: When API initialization fails
        """
        self.generation_model = generation_model
        self.embedding_model = embedding_model
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.embedding_cache = embedding_cache
        self.token_budget_service = token_budget_service
        self.tracer = tracer
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key, organization=organization, base_url=base_url
        )
        self.sync_client = OpenAI(
            api_key=api_key, organization=organization, base_url=base_url
        )

        try:
            # Initialize OpenAI client
            # self.client = OpenAI(api_key=api_key)

            # Validate API key by making a simple request
            # self._validate_api_key()

            logger.info(
                f"Initialized OpenAILLMAdapter with models: {generation_model}, {embedding_model}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI API: {str(e)}", exc_info=True)
            raise LLMException(
                message=f"Failed to initialize OpenAI API: {str(e)}",
                error_code="OPENAI_INIT_ERROR",
                context={
                    "generation_model": generation_model,
                    "embedding_model": embedding_model,
                },
            ) from e

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Generate with structured outputs and function calling."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4096,
            }

            if response_format:
                kwargs["response_format"] = response_format
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)

            result = {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }

            if response.choices[0].message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": call.id,
                        "function": call.function.name,
                        "arguments": json.loads(call.function.arguments),
                    }
                    for call in response.choices[0].message.tool_calls
                ]

            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI generation failed: {e}")

    async def create_embeddings(
        self, texts: List[str], model: str = "text-embedding-3-large"
    ) -> List[List[float]]:
        """Create embeddings with the latest embedding models."""
        try:
            response = await self.client.embeddings.create(
                model=model, input=texts, encoding_format="float"
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise RuntimeError(f"OpenAI embedding failed: {e}")

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text from a prompt using OpenAI.

        Processes a text prompt through OpenAI to generate a response,
        with optional streaming and tool/function calling capabilities.

        Args:
            prompt: Text prompt to send to OpenAI
            tenant_id: Tenant identifier for multi-tenant isolation
            stream: Whether to stream the response tokens (default: False)
            tools: Optional list of tool definitions for function calling
            opts: Optional parameters including:
                - temperature: Sampling temperature (default: 0.7)
                - top_p: Nucleus sampling parameter (default: 0.95)
                - max_tokens: Maximum tokens to generate (default: 1024)

        Returns:
            Generated text as string or token iterator if streaming

        Raises:
            LLMException: When text generation fails
            QuotaExceededException: When API quota is exceeded
            ValidationError: When prompt or parameters are invalid
        """
        # Set default options
        options = {
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "max_tokens": self.default_max_tokens,
        }

        # Update with user-provided options
        if opts:
            options.update(opts)

        start_time = datetime.now()

        try:
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Configure generation parameters
            params = {
                "model": self.generation_model,
                "messages": messages,
                "temperature": options.get("temperature", self.default_temperature),
                "top_p": options.get("top_p", self.default_top_p),
                "max_tokens": options.get("max_tokens", self.default_max_tokens),
                "stream": stream,
            }

            # Add tools if provided
            if tools:
                params["tools"] = tools

            # Generate with streaming
            if stream:
                response = self.sync_client.chat.completions.create(**params)
                return self._stream_response(response, tenant_id, start_time)

            # Generate without streaming
            response = self.sync_client.chat.completions.create(**params)

            # Process non-streaming response
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record metrics
            if self.tracer:
                self._record_metrics(
                    tenant_id=tenant_id,
                    execution_time_ms=execution_time_ms,
                    token_count=self.get_token_count(text=prompt),
                    completion_tokens=response.usage.completion_tokens,
                )

            # Return text response
            return response.choices[0].message.content

        except openai.RateLimitError as e:
            logger.error(f"OpenAI API quota exceeded: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="openai_quota_exceeded", value=1.0, tenant_id=tenant_id
                )

            raise QuotaExceededException(
                message=f"OpenAI API quota exceeded: {str(e)}",
                error_code="OPENAI_QUOTA_EXCEEDED",
                context={"tenant_id": tenant_id},
            ) from e

        except Exception as e:
            logger.error(f"OpenAI text generation failed: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="openai_generation_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"OpenAI text generation failed: {str(e)}",
                error_code="OPENAI_GENERATION_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.generation_model,
                    "prompt_length": len(prompt),
                },
            ) from e

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text using OpenAI with semantic caching.

        Creates vector embeddings for text input that can be used for
        semantic search, clustering, or other vector operations.
        Uses Redis-based semantic caching to avoid recalculating embeddings
        for identical inputs.

        Args:
            text: Text string or list of strings to embed
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters for embedding generation

        Returns:
            Vector embedding(s) as list of floats or list of list of floats

        Raises:
            LLMException: When embedding generation fails
            QuotaExceededException: When API quota is exceeded
            ValidationError: When text input is invalid
        """
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

                    # Record cache hit metrics
                    if self.tracer:
                        self.tracer.record_metric(
                            name="embedding_cache_hit", value=1.0, tenant_id=tenant_id
                        )

                    logger.debug(f"Embedding cache hit for tenant {tenant_id}")
                    return cached_embedding

            # Generate hash for caching and metrics
            self._generate_hash(text, tenant_id, opts)

            # Generate embeddings from API
            if isinstance(text, list):
                # Batch embedding
                response = self.sync_client.embeddings.create(
                    model=self.embedding_model, input=text
                )
                embeddings = [data.embedding for data in response.data]
            else:
                # Single embedding
                response = self.sync_client.embeddings.create(
                    model=self.embedding_model, input=text
                )
                embeddings = response.data[0].embedding

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="openai_embedding_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                    cache_hit=cache_hit,
                )

                if isinstance(text, list):
                    self.tracer.record_metric(
                        name="openai_embedding_batch_size",
                        value=len(text),
                        tenant_id=tenant_id,
                    )

            # Store in cache if available
            if self.embedding_cache:
                self.embedding_cache.store_embedding(
                    text=text, embedding=embeddings, tenant_id=tenant_id, opts=opts
                )

                # Record cache store metrics
                if self.tracer:
                    self.tracer.record_metric(
                        name="embedding_cache_store", value=1.0, tenant_id=tenant_id
                    )

            return embeddings

        except openai.RateLimitError as e:
            logger.error(
                f"OpenAI API quota exceeded for embeddings: {str(e)}", exc_info=True
            )

            if self.tracer:
                self.tracer.record_metric(
                    name="openai_quota_exceeded",
                    value=1.0,
                    tenant_id=tenant_id,
                    operation="embed",
                )

            raise QuotaExceededException(
                message=f"OpenAI API quota exceeded for embeddings: {str(e)}",
                error_code="OPENAI_QUOTA_EXCEEDED",
                context={"tenant_id": tenant_id, "operation": "embed"},
            ) from e

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="openai_embedding_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"OpenAI embedding generation failed: {str(e)}",
                error_code="OPENAI_EMBEDDING_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.embedding_model,
                    "text_type": "batch" if isinstance(text, list) else "single",
                },
            ) from e

    def get_token_count(self, *, text: str) -> int:
        """Calculate the number of tokens in the provided text.

        Estimates the token count for the given text according to the
        OpenAI model's tokenization scheme.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count as integer

        Raises:
            ValidationError: When text input is invalid
        """
        try:
            # Use tiktoken for accurate token counting
            import tiktoken

            # Get the encoding for the model
            encoding = tiktoken.encoding_for_model(self.generation_model)

            # Count tokens
            tokens = encoding.encode(text)
            return len(tokens)

        except ImportError:
            logger.warning("tiktoken not installed, using fallback token estimation")

            # Fallback to rough estimation (4 chars per token)
            estimated_tokens = len(text) // 4
            logger.warning(f"Using fallback token estimation: {estimated_tokens}")
            return estimated_tokens

        except Exception as e:
            logger.error(f"Token counting failed: {str(e)}", exc_info=True)

            # Fallback to rough estimation (4 chars per token)
            estimated_tokens = len(text) // 4
            logger.warning(f"Using fallback token estimation: {estimated_tokens}")
            return estimated_tokens

    def _validate_api_key(self) -> None:
        """Validate API key by making a simple request.

        Raises:
            LLMException: When API key validation fails
        """
        try:
            # Make a simple models list request to validate API key
            # self.client.models.list()
            logger.debug("API key validation successful")

        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}", exc_info=True)
            raise LLMException(
                message=f"API key validation failed: {str(e)}",
                error_code="OPENAI_API_KEY_INVALID",
                context={},
            ) from e

    def _stream_response(
        self, response, tenant_id: str, start_time: datetime
    ) -> Iterator[str]:
        """Process streaming response and record metrics.

        Args:
            response: Streaming response from OpenAI
            tenant_id: Tenant identifier for metrics
            start_time: Start time for latency calculation

        Returns:
            Iterator of response tokens
        """
        tokens_generated = 0

        try:
            for chunk in response:
                # Count tokens
                tokens_generated += 1

                # Get content delta
                content = chunk.choices[0].delta.content

                # Yield text chunk if it exists
                if content:
                    yield content

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
            logger.error(f"Error during response streaming: {str(e)}", exc_info=True)
            # Re-raise to be handled by caller
            raise

    def _record_metrics(
        self,
        *,
        tenant_id: str,
        execution_time_ms: float,
        token_count: int,
        completion_tokens: int = 0,
        operation: str = "generate",
    ) -> None:
        """Record metrics for OpenAI operations.

        Args:
            tenant_id: Tenant identifier for metrics
            execution_time_ms: Execution time in milliseconds
            token_count: Number of prompt tokens processed
            completion_tokens: Number of completion tokens generated
            operation: Operation type ("generate" or "embed")
        """
        # Track token usage with budget service if available
        if self.token_budget_service:
            self.token_budget_service.track_usage(
                tenant_id=tenant_id,
                prompt_tokens=token_count,
                completion_tokens=completion_tokens,
                model=(
                    self.generation_model
                    if operation == "generate"
                    else self.embedding_model
                ),
                operation=operation,
                llm_provider="openai",
            )

        if not self.tracer:
            return

        # Record latency metric
        self.tracer.record_metric(
            name="openai_latency_ms", value=execution_time_ms, tenant_id=tenant_id
        )

        # Record token count metrics
        self.tracer.record_metric(
            name="openai_prompt_token_count",
            value=token_count,
            tenant_id=tenant_id,
            operation=operation,
        )

        self.tracer.record_metric(
            name="openai_completion_token_count",
            value=completion_tokens,
            tenant_id=tenant_id,
        )

        # Record total token count
        total_tokens = token_count + completion_tokens
        self.tracer.record_metric(
            name="openai_total_token_count", value=total_tokens, tenant_id=tenant_id
        )

        # Record cost estimate (approximate based on OpenAI pricing)
        # Note: Pricing may change, this is an estimate
        if self.generation_model == "gpt-4o":
            input_cost = (token_count / 1000) * 0.005  # $0.005 per 1K input tokens
            output_cost = (
                completion_tokens / 1000
            ) * 0.015  # $0.015 per 1K output tokens
        else:
            # Default to GPT-3.5 Turbo pricing
            input_cost = (token_count / 1000) * 0.0005  # $0.0005 per 1K input tokens
            output_cost = (
                completion_tokens / 1000
            ) * 0.0015  # $0.0015 per 1K output tokens

        total_cost = input_cost + output_cost
        self.tracer.record_metric(
            name="openai_cost_usd",
            value=total_cost,
            tenant_id=tenant_id,
            operation=operation,
        )

    def _generate_hash(
        self,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate hash for text and options for caching.

        Args:
            text: Text or list of texts to hash
            tenant_id: Tenant identifier
            opts: Optional parameters

        Returns:
            Hash string for caching
        """
        # Create a dictionary with all inputs that affect the result
        hash_input = {
            "text": text,
            "tenant_id": tenant_id,
            "model": self.embedding_model,
        }

        # Add options if provided
        if opts:
            hash_input["opts"] = opts

        # Convert to JSON and hash
        hash_json = json.dumps(hash_input, sort_keys=True)
        return hashlib.md5(hash_json.encode()).hexdigest()
