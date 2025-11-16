"""Gemini LLM adapter implementing LLMPort for text generation and embeddings.

This adapter integrates with Google's Gemini 2.5 flash API to provide text generation
with streaming and function calling capabilities, as well as embedding generation
using Gemini Text-Embedding-4 with semantic caching.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    from google.generativeai.types import HarmBlockThreshold, HarmCategory
except Exception:  # pragma: no cover - optional dependency
    from infrastructure.stubs.google import generativeai as genai

    HarmCategory = genai.types.HarmCategory
    HarmBlockThreshold = genai.types.HarmBlockThreshold
    from infrastructure.stubs.google.api_core import exceptions as google_exceptions

from adapters.llm.embedding_cache_adapter import EmbeddingCacheAdapter
from application.ports import LLMPort
from domain.services import GraphRAGException
from domain.token_budget_service import TokenBudgetService

logger = logging.getLogger(__name__)


class LLMException(GraphRAGException):
    """Exception for LLM-related errors."""


class QuotaExceededException(LLMException):
    """Exception for API quota exceeded errors."""


class GeminiLLMAdapter(LLMPort):
    """Adapter for Google's Gemini 2.5 flash API implementing LLMPort.

    Provides text generation with streaming and function calling capabilities,
    as well as embedding generation using Gemini Text-Embedding-4.
    """

    def __init__(
        self,
        api_key: str,
        generation_model: str = "gemini-2.5-flash",
        embedding_model: str = "text-embedding-004",
        default_temperature: float = 0.7,
        default_top_p: float = 0.95,
        default_max_tokens: int = 1024,
        default_safety_settings: Optional[Dict[str, str]] = None,
        embedding_cache: Optional[EmbeddingCacheAdapter] = None,
        token_budget_service: Optional[TokenBudgetService] = None,
        tracer=None,
    ):
        """Initialize GeminiLLMAdapter with API key and configuration."""
        try:
            genai.configure(api_key=api_key)
            # Validate API key by listing models
            genai.list_models()

            self.generation_model = generation_model
            self.embedding_model = embedding_model
            self.default_temperature = default_temperature
            self.default_top_p = default_top_p
            self.default_max_tokens = default_max_tokens
            self.default_safety_settings = default_safety_settings or {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            self.embedding_cache = embedding_cache
            self.token_budget_service = token_budget_service
            self.tracer = tracer

        except Exception as e:
            raise LLMException(
                message=f"Failed to initialize Gemini API: {str(e)}",
                error_code="GEMINI_API_KEY_INVALID",
                context={"api_key_prefix": api_key[:10] if api_key else "None"},
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
        """Generate text using Gemini."""
        options = {
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "max_output_tokens": self.default_max_tokens,
        }
        if opts:
            options.update(opts)

        try:
            model = genai.GenerativeModel(self.generation_model)

            generation_config = genai.types.GenerationConfig(
                temperature=options.get("temperature", self.default_temperature),
                top_p=options.get("top_p", self.default_top_p),
                max_output_tokens=options.get(
                    "max_output_tokens", self.default_max_tokens
                ),
            )

            if stream:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=self.default_safety_settings,
                    stream=True,
                )
                return (chunk.text for chunk in response if chunk.text)
            else:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=self.default_safety_settings,
                )
                return response.text

        except google_exceptions.ResourceExhausted as e:
            raise QuotaExceededException(
                message="Gemini API quota exceeded",
                error_code="GEMINI_QUOTA_EXCEEDED",
                context={"tenant_id": tenant_id},
            ) from e
        except Exception as e:
            raise LLMException(
                message=f"Gemini generation failed: {str(e)}",
                error_code="GEMINI_GENERATION_ERROR",
                context={"tenant_id": tenant_id},
            ) from e

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text using Gemini Text-Embedding-4 with semantic caching.

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

            # Configure embedding model
            embedding_model = genai.get_embedding_model(self.embedding_model)

            # Generate embeddings
            if isinstance(text, list):
                result = embedding_model.batch_embed_content(text)
                embeddings = [r.embedding for r in result]
            else:
                result = embedding_model.embed_content(text)
                embeddings = result.embedding

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_embedding_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                    cache_hit=cache_hit,
                )

                if isinstance(text, list):
                    self.tracer.record_metric(
                        name="gemini_embedding_batch_size",
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

        except google_exceptions.ResourceExhausted as e:
            logger.error(
                f"Gemini API quota exceeded for embeddings: {str(e)}", exc_info=True
            )

            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_quota_exceeded",
                    value=1.0,
                    tenant_id=tenant_id,
                    operation="embed",
                )

            raise QuotaExceededException(
                message=f"Gemini API quota exceeded for embeddings: {str(e)}",
                error_code="GEMINI_QUOTA_EXCEEDED",
                context={"tenant_id": tenant_id, "operation": "embed"},
            ) from e

        except Exception as e:
            logger.error(f"Gemini embedding generation failed: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_embedding_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"Gemini embedding generation failed: {str(e)}",
                error_code="GEMINI_EMBEDDING_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.embedding_model,
                    "text_type": "batch" if isinstance(text, list) else "single",
                },
            ) from e

    def moderate(
        self, *, text: str, tenant_id: str, opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Moderate content using Gemini's safety features.

        Analyzes text content for potential policy violations using
        Gemini's built-in safety and moderation capabilities.

        Args:
            text: Text content to moderate
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters for moderation

        Returns:
            Dictionary containing moderation results with safety assessments

        Raises:
            LLMException: When content moderation fails
            QuotaExceededException: When API quota is exceeded
        """
        start_time = datetime.now()

        try:
            # Configure generation model with strict safety settings for moderation
            safety_settings = self._convert_safety_settings(
                {
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_LOW_AND_ABOVE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_LOW_AND_ABOVE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_LOW_AND_ABOVE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_LOW_AND_ABOVE",
                }
            )

            model = genai.GenerativeModel(
                model_name=self.generation_model, safety_settings=safety_settings
            )

            # Use a simple prompt to trigger safety evaluation
            moderation_prompt = f"Analyze this text for safety concerns: {text}"

            response = model.generate_content(moderation_prompt)

            # Initialize moderation result
            moderation_result = {
                "flagged": False,
                "categories": {},
                "category_scores": {},
                "text_safe": True,
            }

            # Check if content was blocked
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                if response.prompt_feedback.block_reason:
                    moderation_result["flagged"] = True
                    moderation_result["text_safe"] = False
                    moderation_result["block_reason"] = str(
                        response.prompt_feedback.block_reason
                    )

                    # Extract safety ratings if available
                    if hasattr(response.prompt_feedback, "safety_ratings"):
                        for rating in response.prompt_feedback.safety_ratings:
                            category = str(rating.category).replace("HarmCategory.", "")
                            probability = str(rating.probability)

                            moderation_result["categories"][category] = (
                                probability not in ["NEGLIGIBLE", "LOW"]
                            )
                            moderation_result["category_scores"][category] = probability

            # Record metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_moderation_latency_ms",
                    value=execution_time_ms,
                    tenant_id=tenant_id,
                )

                self.tracer.record_metric(
                    name="gemini_moderation_flagged",
                    value=1.0 if moderation_result["flagged"] else 0.0,
                    tenant_id=tenant_id,
                )

            return moderation_result

        except google_exceptions.ResourceExhausted as e:
            logger.error(
                f"Gemini API quota exceeded for moderation: {str(e)}", exc_info=True
            )

            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_quota_exceeded",
                    value=1.0,
                    tenant_id=tenant_id,
                    operation="moderate",
                )

            raise QuotaExceededException(
                message=f"Gemini API quota exceeded for moderation: {str(e)}",
                error_code="GEMINI_QUOTA_EXCEEDED",
                context={"tenant_id": tenant_id, "operation": "moderate"},
            ) from e

        except Exception as e:
            logger.error(f"Gemini content moderation failed: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="gemini_moderation_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise LLMException(
                message=f"Gemini content moderation failed: {str(e)}",
                error_code="GEMINI_MODERATION_ERROR",
                context={
                    "tenant_id": tenant_id,
                    "model": self.generation_model,
                    "text_length": len(text),
                },
            ) from e

    def get_token_count(self, *, text: str) -> int:
        """Calculate the number of tokens in the provided text.

        Estimates the token count for the given text according to the
        Gemini model's tokenization scheme.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count as integer

        Raises:
            ValidationError: When text input is invalid
        """
        try:
            # Use Gemini's token counting functionality
            token_count = genai.count_tokens(self.generation_model, text)
            return token_count.total_tokens

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
            models_response = genai.list_models()

            # Handle case where list_models returns None (stub implementation)
            if models_response is None:
                logger.warning(
                    "Using stub implementation - skipping API key validation"
                )
                return

            models = list(models_response)
            logger.debug(f"API key validation successful - found {len(models)} models")

        except google_exceptions.PermissionDenied as e:
            logger.error(f"API key permission denied: {str(e)}")
            raise LLMException(
                message="Invalid API key - permission denied",
                error_code="GEMINI_API_KEY_INVALID",
                context={"details": str(e)},
            ) from e
        except google_exceptions.Unauthenticated as e:
            logger.error(f"API key authentication failed: {str(e)}")
            raise LLMException(
                message="Invalid API key - authentication failed",
                error_code="GEMINI_API_KEY_INVALID",
                context={"details": str(e)},
            ) from e
        except TypeError as e:
            # Handle the specific case where genai.list_models() returns None
            if "'NoneType' object is not iterable" in str(e):
                logger.warning(
                    "Using stub implementation - skipping API key validation"
                )
                return
            raise LLMException(
                message=f"API key validation failed: {str(e)}",
                error_code="GEMINI_API_KEY_INVALID",
                context={"details": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}", exc_info=True)
            # Don't fail on validation if it's just a network issue
            if "network" in str(e).lower() or "connection" in str(e).lower():
                logger.warning(
                    "Network issue during API key validation - proceeding anyway"
                )
                return
            raise LLMException(
                message=f"API key validation failed: {str(e)}",
                error_code="GEMINI_API_KEY_INVALID",
                context={"details": str(e)},
            ) from e

    def _convert_safety_settings(
        self, safety_settings: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Convert safety settings to Gemini format.

        Args:
            safety_settings: Dictionary of safety settings

        Returns:
            List of safety settings in Gemini format
        """
        gemini_safety_settings = []

        # Map string settings to Gemini enum values
        harm_category_map = {
            "HARM_CATEGORY_HARASSMENT": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "HARM_CATEGORY_HATE_SPEECH": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "HARM_CATEGORY_DANGEROUS_CONTENT": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        }

        threshold_map = {
            "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
            "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_HIGH_AND_ABOVE": HarmBlockThreshold.BLOCK_HIGH_AND_ABOVE,
            "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        # Apply default safety settings if not provided
        if not safety_settings:
            safety_settings = self.default_safety_settings

        # Convert to Gemini format
        for category, threshold in safety_settings.items():
            if category in harm_category_map and threshold in threshold_map:
                gemini_safety_settings.append(
                    {
                        "category": harm_category_map[category],
                        "threshold": threshold_map[threshold],
                    }
                )
            else:
                logger.warning(f"Invalid safety setting: {category}={threshold}")

        return gemini_safety_settings

    def _convert_tools_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tools to Gemini format.

        Args:
            tools: List of tool definitions

        Returns:
            List of tools in Gemini format
        """
        gemini_tools = []

        for tool in tools:
            # Convert to Gemini's function calling format
            function_tool = {"function_declarations": []}

            if "name" in tool and "description" in tool and "parameters" in tool:
                function_tool["function_declarations"].append(
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"],
                    }
                )
                gemini_tools.append(function_tool)
            else:
                logger.warning(f"Invalid tool definition: {tool}")

        return gemini_tools

    def _configure_model(
        self,
        options: Dict[str, Any],
        safety_settings: List[Dict[str, Any]],
    ) -> Any:
        """Instantiate and configure the Gemini GenerativeModel."""
        return genai.GenerativeModel(
            model_name=self.generation_model,
            generation_config={
                "temperature": options.get("temperature", self.default_temperature),
                "top_p": options.get("top_p", self.default_top_p),
                "max_output_tokens": options.get("max_tokens", self.default_max_tokens),
            },
            safety_settings=safety_settings,
        )

    def _handle_streaming(
        self,
        *,
        model: Any,
        prompt: str,
        tenant_id: str,
        start_time: datetime,
        model_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """Generate streaming content and delegate to _stream_response."""
        response = model.generate_content(
            prompt,
            stream=True,
            tools=model_tools,
        )
        return self._stream_response(response, tenant_id, start_time)

    def _record_generation_metrics(
        self,
        *,
        tenant_id: str,
        start_time: datetime,
        prompt: str,
        safety_blocks: int,
    ) -> None:
        """Record metrics specific to text generation."""
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        self._record_metrics(
            tenant_id=tenant_id,
            execution_time_ms=execution_time_ms,
            token_count=self.get_token_count(text=prompt),
            safety_blocks=safety_blocks,
        )

    def _stream_response(
        self, response, tenant_id: str, start_time: datetime
    ) -> Iterator[str]:
        """Process streaming response and record metrics.

        Args:
            response: Streaming response from Gemini
            tenant_id: Tenant identifier for metrics
            start_time: Start time for latency calculation

        Returns:
            Iterator of response tokens
        """
        safety_blocks = 0
        tokens_generated = 0

        try:
            for chunk in response:
                # Check for safety blocks
                if hasattr(chunk, "prompt_feedback") and chunk.prompt_feedback:
                    if chunk.prompt_feedback.block_reason:
                        safety_blocks += 1
                        logger.warning(
                            f"Gemini safety block triggered: {chunk.prompt_feedback.block_reason}"
                        )

                # Count tokens
                tokens_generated += 1

                # Yield text chunk
                if chunk.text:
                    yield chunk.text

            # Record metrics after streaming completes
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            if self.tracer:
                self._record_metrics(
                    tenant_id=tenant_id,
                    execution_time_ms=execution_time_ms,
                    token_count=tokens_generated,
                    safety_blocks=safety_blocks,
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
        safety_blocks: int = 0,
        operation: str = "generate",
    ) -> None:
        """Record metrics for Gemini operations.

        Args:
            tenant_id: Tenant identifier for metrics
            execution_time_ms: Execution time in milliseconds
            token_count: Number of tokens processed (prompt tokens)
            completion_tokens: Number of completion tokens generated
            safety_blocks: Number of safety blocks triggered
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
                llm_provider="gemini",
            )

        if not self.tracer:
            return

        # Record latency metric
        self.tracer.record_metric(
            name="gemini_latency_ms", value=execution_time_ms, tenant_id=tenant_id
        )

        # Record token count metrics
        self.tracer.record_metric(
            name="gemini_prompt_token_count",
            value=token_count,
            tenant_id=tenant_id,
            operation=operation,
        )

        if operation == "generate":
            self.tracer.record_metric(
                name="gemini_completion_token_count",
                value=completion_tokens,
                tenant_id=tenant_id,
            )

            # Record total token count
            total_tokens = token_count + completion_tokens
            self.tracer.record_metric(
                name="gemini_total_token_count", value=total_tokens, tenant_id=tenant_id
            )

        # Calculate cost based on model and operation
        if operation == "generate":
            # Gemini 2.5 flash pricing (as of July 2025)
            if self.generation_model == "gemini-2.5-flash":
                input_cost = (
                    token_count / 1000
                ) * 0.0005  # $0.0005 per 1K input tokens
                output_cost = (
                    completion_tokens / 1000
                ) * 0.0015  # $0.0015 per 1K output tokens
            elif self.generation_model == "gemini-2.5-pro":
                input_cost = (
                    token_count / 1000
                ) * 0.0035  # $0.0035 per 1K input tokens
                output_cost = (
                    completion_tokens / 1000
                ) * 0.0105  # $0.0105 per 1K output tokens
            else:
                # Default pricing
                input_cost = (token_count / 1000) * 0.001  # $0.001 per 1K input tokens
                output_cost = (
                    completion_tokens / 1000
                ) * 0.002  # $0.002 per 1K output tokens

            cost_usd = input_cost + output_cost
        else:
            # Embedding pricing
            if self.embedding_model == "text-embedding-004":
                cost_usd = (token_count / 1000) * 0.00025  # $0.00025 per 1K tokens
            else:
                cost_usd = (token_count / 1000) * 0.0001  # Default rate

        # Record cost metric
        self.tracer.record_metric(
            name="gemini_cost_usd",
            value=cost_usd,
            tenant_id=tenant_id,
            operation=operation,
        )

        # Record safety block ratio
        if safety_blocks > 0:
            self.tracer.record_metric(
                name="gemini_safety_block_ratio",
                value=1.0,  # 100% blocked
                tenant_id=tenant_id,
            )
        else:
            self.tracer.record_metric(
                name="gemini_safety_block_ratio",
                value=0.0,  # 0% blocked
                tenant_id=tenant_id,
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

    def generate_with_context(
        self, messages: List[Dict[str, str]], context: Optional[str] = None
    ) -> str:
        """Enhanced generation with conversation context and system instructions."""
        try:
            # Build conversation history
            chat_session = self.model.start_chat(history=[])

            if context:
                # Set system context
                response = chat_session.send_message(
                    f"System context: {context}\n\nUser: {messages[-1]['content']}"
                )
            else:
                # Process conversation
                for msg in messages[:-1]:
                    chat_session.send_message(msg["content"])
                response = chat_session.send_message(messages[-1]["content"])

            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini generation failed: {e}")

    def count_tokens_accurate(self, text: str) -> int:
        """Accurate token counting using Gemini's count_tokens API."""
        try:
            response = genai.count_tokens(self.generation_model, text)
            return response.total_tokens
        except Exception:
            # Fallback to estimation
            return len(text.split()) * 1.3  # Rough estimation
