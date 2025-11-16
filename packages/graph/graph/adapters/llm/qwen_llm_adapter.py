"""Qwen LLM adapter for StructRAG and GraphRAG integration."""

import json
import logging
import time
from typing import Any, Dict, Iterator, List, Optional, Union

import requests
from transformers import AutoTokenizer

from application.ports import LLMPort
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class QwenLLMAdapter(LLMPort):
    """Qwen LLM adapter implementing the LLMPort interface.

    This adapter provides integration with Qwen models via API endpoints,
    supporting both local and remote deployments.
    """

    def __init__(
        self,
        url: str,
        model_name: str = "Qwen",
        api_key: str = "EMPTY",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: int = 300,
        max_retries: int = 3,
        tokenizer_path: Optional[str] = None,
    ):
        """Initialize Qwen LLM adapter.

        Args:
            url: API endpoint URL for Qwen service
            model_name: Model name identifier
            api_key: API key (default: "EMPTY" for local deployments)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            tokenizer_path: Path to tokenizer (optional)
        """
        self.url = url
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize tokenizer for token counting
        self.tokenizer = None
        if tokenizer_path:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
                logger.info(f"Loaded tokenizer from {tokenizer_path}")
            except Exception as e:
                logger.warning(f"Failed to load tokenizer: {e}")

        # Fallback tokenizer paths
        if not self.tokenizer:
            fallback_paths = [
                "/data4/user2021/hf_models/llama-2-7b",
                "/mnt/data/user/hf_models/gpt2",
                "gpt2",  # HuggingFace default
            ]

            for path in fallback_paths:
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(path)
                    logger.info(f"Loaded fallback tokenizer from {path}")
                    break
                except Exception:
                    continue

        if not self.tokenizer:
            logger.warning(
                "No tokenizer available - token counting will use approximation"
            )

        logger.info(f"Initialized Qwen LLM adapter with URL: {url}")

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text using Qwen model.

        Args:
            prompt: Input prompt text
            tenant_id: Tenant identifier
            stream: Whether to stream response (not supported)
            tools: Function calling tools (not supported)
            opts: Additional options (max_tokens, temperature, etc.)

        Returns:
            Generated text string

        Raises:
            GraphRAGException: When generation fails
        """
        if stream:
            logger.warning("Streaming not supported by Qwen adapter")

        if tools:
            logger.warning("Function calling not supported by Qwen adapter")

        # Extract options
        opts = opts or {}
        max_tokens = opts.get("max_tokens", self.max_tokens)
        temperature = opts.get("temperature", self.temperature)
        seed = opts.get("seed", 1024)

        # Check and truncate prompt if necessary
        input_text = self._prepare_input(prompt)

        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": input_text}],
            "seed": seed,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key,
        }

        # Make request with retries
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                response = requests.post(
                    self.url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=self.timeout,
                )

                logger.debug(f"Request completed with status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()

                    # Log token usage if available
                    if "usage" in result:
                        usage = result["usage"]
                        logger.debug(
                            f"Token usage - Prompt: {usage.get('prompt_tokens', 0)}, "
                            f"Completion: {usage.get('completion_tokens', 0)}, "
                            f"Total: {usage.get('total_tokens', 0)}"
                        )

                    # Extract generated text
                    if "choices" in result and len(result["choices"]) > 0:
                        generated_text = result["choices"][0]["message"]["content"]

                        elapsed_time = time.time() - start_time
                        logger.debug(
                            f"Generation completed in {elapsed_time:.2f} seconds"
                        )

                        return generated_text
                    else:
                        raise GraphRAGException(
                            message="No choices in response",
                            error_code="INVALID_RESPONSE",
                            context={"response": result},
                        )
                else:
                    # Handle specific error cases
                    try:
                        error_detail = response.json()

                        # Handle token limit exceeded
                        if (
                            "Please reduce the length of the messages"
                            in error_detail.get("message", "")
                        ):
                            token_info = error_detail["message"]
                            if "However, you requested" in token_info:
                                # Extract current token count and adjust
                                current_tokens_str = (
                                    token_info.split("However, you requested")[1]
                                    .split("tokens in the messages")[0]
                                    .strip()
                                )
                                try:
                                    current_tokens = int(current_tokens_str)
                                    reduction_ratio = 128000 / current_tokens
                                    input_text = input_text[
                                        : int(len(input_text) * reduction_ratio)
                                    ]

                                    # Update payload with reduced input
                                    payload["messages"] = [
                                        {"role": "user", "content": input_text}
                                    ]
                                    logger.warning(
                                        f"Reduced input length due to token limit: {current_tokens} tokens"
                                    )
                                    continue  # Retry with reduced input

                                except ValueError:
                                    pass

                        raise GraphRAGException(
                            message=f"API request failed: {error_detail.get('message', 'Unknown error')}",
                            error_code="API_ERROR",
                            context={
                                "status_code": response.status_code,
                                "response": error_detail,
                            },
                        )

                    except json.JSONDecodeError:
                        raise GraphRAGException(
                            message=f"API request failed with status {response.status_code}",
                            error_code="API_ERROR",
                            context={
                                "status_code": response.status_code,
                                "response": response.text[:500],
                            },
                        )

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise GraphRAGException(
                        message="Request timeout after maximum retries",
                        error_code="REQUEST_TIMEOUT",
                        context={"url": self.url, "attempts": self.max_retries},
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise GraphRAGException(
                        message=f"Request failed after maximum retries: {str(e)}",
                        error_code="REQUEST_FAILED",
                        context={"url": self.url, "attempts": self.max_retries},
                    ) from e

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise GraphRAGException(
                        message=f"Generation failed: {str(e)}",
                        error_code="GENERATION_FAILED",
                        context={"tenant_id": tenant_id, "prompt_length": len(prompt)},
                    ) from e

        # This should not be reached due to exception handling above
        raise GraphRAGException(
            message="Generation failed after all retry attempts",
            error_code="GENERATION_FAILED",
            context={"tenant_id": tenant_id, "attempts": self.max_retries},
        )

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings (not supported by basic Qwen adapter).

        Args:
            text: Text or list of texts to embed
            tenant_id: Tenant identifier
            opts: Additional options

        Returns:
            Dummy embeddings (zeros)

        Raises:
            GraphRAGException: Always raises as embeddings not supported
        """
        raise GraphRAGException(
            message="Embeddings not supported by Qwen LLM adapter",
            error_code="EMBEDDINGS_NOT_SUPPORTED",
            context={"tenant_id": tenant_id},
        )

    def get_token_count(self, *, text: str) -> int:
        """Get token count for text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self.tokenizer:
            try:
                tokens = self.tokenizer(text)["input_ids"]
                return len(tokens)
            except Exception as e:
                logger.warning(f"Tokenizer failed: {e}, using approximation")

        # Fallback approximation (roughly 4 characters per token)
        return len(text) // 4

    def _prepare_input(self, prompt: str) -> str:
        """Prepare input text with length checking.

        Args:
            prompt: Original prompt text

        Returns:
            Processed prompt text (potentially truncated)
        """
        if not self.tokenizer:
            # Without tokenizer, use character-based approximation
            max_chars = 128000 * 4  # Rough approximation
            if len(prompt) > max_chars:
                logger.warning(
                    f"Prompt too long ({len(prompt)} chars), truncating to {max_chars}"
                )
                return prompt[:max_chars]
            return prompt

        # Use tokenizer for accurate token counting
        try:
            input_tokens = self.tokenizer(prompt)["input_ids"]
            token_count = len(input_tokens)

            logger.debug(f"Input token count: {token_count}")

            if token_count > 128000:
                logger.warning(f"Input too long ({token_count} tokens), truncating")
                # Calculate reduction ratio
                reduction_ratio = 128000 / token_count
                reduced_length = int(len(prompt) * reduction_ratio)
                return prompt[:reduced_length]

            return prompt

        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using original prompt")
            return prompt

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dictionary containing model information
        """
        return {
            "adapter_type": "QwenLLMAdapter",
            "model_name": self.model_name,
            "url": self.url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "has_tokenizer": self.tokenizer is not None,
            "supports_streaming": False,
            "supports_function_calling": False,
            "supports_embeddings": False,
        }

    def health_check(self) -> bool:
        """Check if the Qwen service is healthy.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": self.api_key,
            }

            response = requests.post(
                self.url,
                headers=headers,
                data=json.dumps(test_payload),
                timeout=10,  # Short timeout for health check
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
