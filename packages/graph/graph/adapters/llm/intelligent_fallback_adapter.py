"""Intelligent LLM fallback adapter with transformers server priority.

This adapter implements a smart fallback strategy that prioritizes local
transformers server, then falls back to cloud providers based on
availability, performance, and cost considerations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional, Union

from adapters.llm.transformers_server_adapter import (
    TransformersServerAdapter,
    TransformersServerUnavailableException,
)
from application.ports import LLMPort
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)


class IntelligentFallbackAdapter(LLMPort):
    """Intelligent LLM adapter with transformers server priority.

    This adapter implements a smart fallback strategy:
    1. Try local transformers server first (cost-effective, private)
    2. Fall back to Gemini (good performance/cost ratio)
    3. Fall back to OpenAI (reliable fallback)
    4. Fall back to Perplexica (search-augmented if needed)
    """

    def __init__(
        self,
        transformers_adapter: Optional[TransformersServerAdapter] = None,
        gemini_adapter: Optional[LLMPort] = None,
        openai_adapter: Optional[LLMPort] = None,
        perplexica_adapter: Optional[LLMPort] = None,
        tracer=None,
        prefer_local: bool = True,
        max_retries_per_adapter: int = 2,
    ):
        """Initialize intelligent fallback adapter.

        Args:
            transformers_adapter: Local transformers server adapter
            gemini_adapter: Gemini LLM adapter
            openai_adapter: OpenAI LLM adapter
            perplexica_adapter: Perplexica LLM adapter
            tracer: Optional tracing port
            prefer_local: Whether to prefer local models when available
            max_retries_per_adapter: Maximum retries per adapter before fallback
        """
        self.transformers_adapter = transformers_adapter
        self.gemini_adapter = gemini_adapter
        self.openai_adapter = openai_adapter
        self.perplexica_adapter = perplexica_adapter
        self.tracer = tracer
        self.prefer_local = prefer_local
        self.max_retries_per_adapter = max_retries_per_adapter

        # Track adapter health and performance
        self.adapter_health = {}
        self.adapter_performance = {}
        self.last_health_check = {}

        # Build fallback chain
        self._build_fallback_chain()

        logger.info(
            f"Initialized IntelligentFallbackAdapter with "
            f"{len(self.fallback_chain)} adapters in chain"
        )

    def _build_fallback_chain(self):
        """Build the fallback chain based on available adapters."""
        self.fallback_chain = []

        if self.prefer_local and self.transformers_adapter:
            self.fallback_chain.append(("transformers", self.transformers_adapter))

        if self.gemini_adapter:
            self.fallback_chain.append(("gemini", self.gemini_adapter))

        if self.openai_adapter:
            self.fallback_chain.append(("openai", self.openai_adapter))

        if self.perplexica_adapter:
            self.fallback_chain.append(("perplexica", self.perplexica_adapter))

        if not self.prefer_local and self.transformers_adapter:
            self.fallback_chain.append(("transformers", self.transformers_adapter))

        if not self.fallback_chain:
            raise GraphRAGException(
                message="No LLM adapters configured for fallback",
                error_code="NO_ADAPTERS_CONFIGURED",
                context={},
            )

    async def _check_adapter_health(self, adapter_name: str, adapter: LLMPort) -> bool:
        """Check if an adapter is healthy."""
        try:
            # For transformers adapter, use specific health check
            if adapter_name == "transformers" and hasattr(adapter, "_health_check"):
                return await adapter._health_check()

            # For other adapters, try a simple generation test
            test_result = adapter.generate(
                prompt="test", tenant_id="health_check", opts={"max_tokens": 1}
            )
            return test_result is not None
        except Exception as e:
            logger.warning(f"Health check failed for {adapter_name}: {e}")
            return False

    def _record_adapter_performance(
        self, adapter_name: str, latency_ms: float, success: bool
    ):
        """Record performance metrics for an adapter."""
        if adapter_name not in self.adapter_performance:
            self.adapter_performance[adapter_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_latency_ms": 0,
                "last_success": None,
                "last_failure": None,
            }

        perf = self.adapter_performance[adapter_name]
        perf["total_requests"] += 1
        perf["total_latency_ms"] += latency_ms

        if success:
            perf["successful_requests"] += 1
            perf["last_success"] = datetime.now()
        else:
            perf["last_failure"] = datetime.now()

    def _get_best_adapter(self) -> tuple[str, LLMPort]:
        """Get the best available adapter based on health and performance."""
        now = datetime.now()

        for adapter_name, adapter in self.fallback_chain:
            # Check if we need to update health status
            last_check = self.last_health_check.get(adapter_name, datetime.min)
            if now - last_check > timedelta(minutes=5):  # Check every 5 minutes
                try:
                    health = asyncio.run(
                        self._check_adapter_health(adapter_name, adapter)
                    )
                    self.adapter_health[adapter_name] = health
                    self.last_health_check[adapter_name] = now
                except Exception:
                    self.adapter_health[adapter_name] = False

            # Return first healthy adapter
            if self.adapter_health.get(
                adapter_name, True
            ):  # Default to healthy if not checked
                return adapter_name, adapter

        # If no healthy adapters, return the first one anyway
        logger.warning("No healthy adapters found, using first available")
        return self.fallback_chain[0]

    def generate(
        self,
        *,
        prompt: str,
        tenant_id: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Iterator[str]]:
        """Generate text with intelligent fallback."""
        start_time = datetime.now()
        last_exception = None

        for attempt in range(self.max_retries_per_adapter):
            adapter_name, adapter = self._get_best_adapter()

            try:
                if self.tracer:
                    self.tracer.record_metric(
                        name="intelligent_fallback_attempt",
                        value=1.0,
                        tenant_id=tenant_id,
                        adapter=adapter_name,
                        attempt=attempt + 1,
                    )

                result = adapter.generate(
                    prompt=prompt,
                    tenant_id=tenant_id,
                    stream=stream,
                    tools=tools,
                    opts=opts,
                )

                # Record success
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._record_adapter_performance(adapter_name, latency_ms, True)

                if self.tracer:
                    self.tracer.record_metric(
                        name="intelligent_fallback_success",
                        value=1.0,
                        tenant_id=tenant_id,
                        adapter=adapter_name,
                        latency_ms=latency_ms,
                    )

                return result

            except TransformersServerUnavailableException as e:
                # Mark transformers as unhealthy and try next adapter
                self.adapter_health["transformers"] = False
                last_exception = e
                logger.warning(
                    f"Transformers server unavailable, trying next adapter: {e}"
                )
                continue

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Adapter {adapter_name} failed on attempt {attempt + 1}: {e}"
                )

                # Record failure
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._record_adapter_performance(adapter_name, latency_ms, False)

                # Mark adapter as unhealthy if it failed multiple times
                if attempt >= self.max_retries_per_adapter - 1:
                    self.adapter_health[adapter_name] = False

                if self.tracer:
                    self.tracer.record_metric(
                        name="intelligent_fallback_failure",
                        value=1.0,
                        tenant_id=tenant_id,
                        adapter=adapter_name,
                        error_type=type(e).__name__,
                    )

                # Try next adapter in chain
                if len(self.fallback_chain) > 1:
                    # Move failed adapter to end of chain
                    self.fallback_chain = [
                        (n, a) for n, a in self.fallback_chain if n != adapter_name
                    ]
                    self.fallback_chain.append((adapter_name, adapter))
                    continue

        # All adapters failed
        raise GraphRAGException(
            message=f"All LLM adapters failed. Last error: {str(last_exception)}",
            error_code="ALL_ADAPTERS_FAILED",
            context={
                "tenant_id": tenant_id,
                "prompt_length": len(prompt),
                "last_error": str(last_exception),
                "adapter_chain": [name for name, _ in self.fallback_chain],
            },
        ) from last_exception

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings with intelligent fallback."""
        start_time = datetime.now()
        last_exception = None

        for attempt in range(self.max_retries_per_adapter):
            adapter_name, adapter = self._get_best_adapter()

            try:
                result = adapter.embed(text=text, tenant_id=tenant_id, opts=opts)

                # Record success
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._record_adapter_performance(adapter_name, latency_ms, True)

                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"Embedding failed with {adapter_name}: {e}")

                # Record failure
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._record_adapter_performance(adapter_name, latency_ms, False)

                # Try next adapter
                continue

        # All adapters failed
        raise GraphRAGException(
            message=f"All embedding adapters failed. Last error: {str(last_exception)}",
            error_code="ALL_EMBEDDING_ADAPTERS_FAILED",
            context={
                "tenant_id": tenant_id,
                "text_type": "batch" if isinstance(text, list) else "single",
                "last_error": str(last_exception),
            },
        ) from last_exception

    def get_token_count(self, *, text: str) -> int:
        """Get token count using the best available adapter."""
        _, adapter = self._get_best_adapter()
        return adapter.get_token_count(text=text)

    def get_adapter_status(self) -> Dict[str, Any]:
        """Get status of all adapters."""
        status = {
            "fallback_chain": [name for name, _ in self.fallback_chain],
            "adapter_health": self.adapter_health.copy(),
            "adapter_performance": {},
        }

        # Calculate performance metrics
        for adapter_name, perf in self.adapter_performance.items():
            if perf["total_requests"] > 0:
                status["adapter_performance"][adapter_name] = {
                    "success_rate": perf["successful_requests"]
                    / perf["total_requests"],
                    "avg_latency_ms": perf["total_latency_ms"] / perf["total_requests"],
                    "total_requests": perf["total_requests"],
                    "last_success": (
                        perf["last_success"].isoformat()
                        if perf["last_success"]
                        else None
                    ),
                    "last_failure": (
                        perf["last_failure"].isoformat()
                        if perf["last_failure"]
                        else None
                    ),
                }

        return status
