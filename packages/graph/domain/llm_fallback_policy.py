"""LLM fallback policy for resilient AI operations.

This module implements a circuit breaker pattern for LLM operations,
providing automatic fallback between different LLM providers based on
error conditions, latency thresholds, and quota limits.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union, Iterator, Callable, TypeVar
from datetime import datetime, timedelta
import threading
from enum import Enum, auto

from application.ports import LLMPort, TracingPort
from domain.utils.tracing import tracing_span
from domain.exceptions import (
    LLMException,
    QuotaExceededException,
    RateLimitedException,
    ServiceUnavailableException,
    BudgetExceededException,
)

logger = logging.getLogger(__name__)

# Generic type for function return values
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = auto()  # Normal operation
    OPEN = auto()  # Failing, bypass and use fallback
    HALF_OPEN = auto()  # Testing if service has recovered


class LLMFallbackPolicy:
    """Policy for managing LLM fallbacks with circuit breaker pattern.

    Implements resilient LLM operations by automatically switching between
    primary and fallback LLM providers based on error conditions, latency
    thresholds, and quota limits.
    """

    def __init__(
        self,
        primary_llm: LLMPort,
        fallback_llm: Optional[LLMPort] = None,
        tracer: Optional[TracingPort] = None,
        error_threshold: int = 5,  # Number of errors before opening circuit
        latency_threshold_ms: int = 800,  # p95 latency threshold
        reset_timeout_seconds: int = 60,  # Time before testing circuit again
        track_window_seconds: int = 300,  # Time window for tracking errors/latency
    ):
        """Initialize LLMFallbackPolicy.

        Args:
            primary_llm: Primary LLM provider
            fallback_llm: Optional fallback LLM provider
            tracer: Optional tracing port for observability
            error_threshold: Number of errors before opening circuit
            latency_threshold_ms: p95 latency threshold in milliseconds
            reset_timeout_seconds: Time before testing circuit again
            track_window_seconds: Time window for tracking errors/latency
        """
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm
        self.tracer = tracer
        self.error_threshold = error_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.reset_timeout_seconds = reset_timeout_seconds
        self.track_window_seconds = track_window_seconds

        # Circuit state
        self.circuit_state = CircuitState.CLOSED
        self.last_error_time = None
        self.next_retry_time = None

        # Error and latency tracking
        self.error_count = 0
        self.request_latencies = []
        self.request_timestamps = []

        # Thread safety
        self.lock = threading.RLock()

        # Track whether we just transitioned to HALF_OPEN
        self._half_open_probe = False

        logger.info(
            f"Initialized LLMFallbackPolicy with "
            f"error_threshold={error_threshold}, "
            f"latency_threshold_ms={latency_threshold_ms}, "
            f"reset_timeout_seconds={reset_timeout_seconds}"
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
        """Generate text with automatic fallback handling.

        Args:
            prompt: Text prompt to send to the language model
            tenant_id: Tenant identifier for multi-tenant isolation
            stream: Whether to stream the response tokens
            tools: Optional list of tool definitions for function calling
            opts: Optional parameters for generation

        Returns:
            Generated text as string or token iterator if streaming

        Raises:
            LLMException: When both primary and fallback LLMs fail
        """
        return self._execute_with_fallback(
            operation="generate",
            func=lambda llm: llm.generate(
                prompt=prompt,
                tenant_id=tenant_id,
                stream=stream,
                tools=tools,
                opts=opts,
            ),
            tenant_id=tenant_id,
            context={
                "operation": "generate",
                "prompt_length": len(prompt),
                "stream": stream,
                "has_tools": tools is not None,
            },
        )

    def embed(
        self,
        *,
        text: Union[str, List[str]],
        tenant_id: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings with automatic fallback handling.

        Args:
            text: Text string or list of strings to embed
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters for embedding generation

        Returns:
            Vector embedding(s) as list of floats or list of list of floats

        Raises:
            LLMException: When both primary and fallback LLMs fail
        """
        return self._execute_with_fallback(
            operation="embed",
            func=lambda llm: llm.embed(text=text, tenant_id=tenant_id, opts=opts),
            tenant_id=tenant_id,
            context={
                "operation": "embed",
                "text_count": 1 if isinstance(text, str) else len(text),
            },
        )

    def moderate(
        self, *, text: str, tenant_id: str, opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Moderate content with automatic fallback handling.

        Args:
            text: Text content to moderate
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional parameters for moderation

        Returns:
            Dictionary containing moderation results

        Raises:
            LLMException: When both primary and fallback LLMs fail
        """
        return self._execute_with_fallback(
            operation="moderate",
            func=lambda llm: llm.moderate(text=text, tenant_id=tenant_id, opts=opts),
            tenant_id=tenant_id,
            context={"operation": "moderate", "text_length": len(text)},
        )

    def get_token_count(self, *, text: str) -> int:
        """Calculate token count with automatic fallback handling.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count as integer

        Raises:
            LLMException: When both primary and fallback LLMs fail
        """
        return self._execute_with_fallback(
            operation="get_token_count",
            func=lambda llm: llm.get_token_count(text=text),
            tenant_id=None,
            context={"operation": "get_token_count", "text_length": len(text)},
        )

    def _execute_with_fallback(
        self,
        *,
        operation: str,
        func: Callable[[LLMPort], T],
        tenant_id: Optional[str],
        context: Dict[str, Any],
    ) -> T:
        """Execute an LLM operation with circuit breaker and fallback logic."""

        with tracing_span(
            self.tracer if tenant_id else None,
            name=f"llm_fallback.{operation}",
            tenant_id=tenant_id or "unknown",
            circuit_state=self.circuit_state.name,
            **context,
        ):
            try:
                use_fallback = self._should_use_fallback()

                if use_fallback and self.fallback_llm is None:
                    logger.warning(
                        "Circuit is %s but no fallback LLM available",
                        self.circuit_state.name,
                    )
                    raise ServiceUnavailableException(
                        model="primary",
                        tenant_id=tenant_id or "unknown",
                        retry_after=self._get_retry_after_seconds(),
                        context={
                            "circuit_state": self.circuit_state.name,
                            "operation": operation,
                            **context,
                        },
                    )

                selected_llm = self.fallback_llm if use_fallback else self.primary_llm

                if use_fallback and self.tracer and tenant_id:
                    self.tracer.record_metric(
                        name="llm_fallback_total",
                        value=1.0,
                        tenant_id=tenant_id,
                        operation=operation,
                        circuit_state=self.circuit_state.name,
                    )

                start_time = time.time()
                try:
                    result = func(selected_llm)
                    self._record_success(time.time() - start_time)
                    return result
                except (
                    QuotaExceededException,
                    RateLimitedException,
                    ServiceUnavailableException,
                ) as e:
                    self._record_failure(e)
                    if not use_fallback and self.fallback_llm is not None:
                        logger.warning(
                            "Primary LLM failed with %s, falling back to secondary LLM",
                            type(e).__name__,
                        )
                        if self.tracer and tenant_id:
                            self.tracer.record_metric(
                                name="llm_fallback_total",
                                value=1.0,
                                tenant_id=tenant_id,
                                operation=operation,
                                error_type=type(e).__name__,
                            )
                        return func(self.fallback_llm)
                    raise
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "LLM operation %s failed: %s", operation, str(e), exc_info=True
                )
                if self.tracer and tenant_id:
                    self.tracer.record_metric(
                        name="llm_error_total",
                        value=1.0,
                        tenant_id=tenant_id,
                        operation=operation,
                        error_type=type(e).__name__,
                    )
                raise

    def _should_use_fallback(self) -> bool:
        """Determine if fallback should be used based on circuit state.

        Returns:
            True if fallback should be used, False otherwise
        """
        with self.lock:
            now = datetime.now()

            # Clean up old latency and error data
            self._clean_old_data(now)

            # Check circuit state
            if self.circuit_state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if self._should_open_circuit():
                    self.circuit_state = CircuitState.OPEN
                    self.last_error_time = now
                    self.next_retry_time = now + timedelta(
                        seconds=self.reset_timeout_seconds
                    )

                    logger.warning(
                        f"Opening circuit due to errors/latency, "
                        f"will retry at {self.next_retry_time}"
                    )

                    return True

                return False

            elif self.circuit_state == CircuitState.OPEN:
                # Check if we should try half-open
                if now >= self.next_retry_time:
                    self.circuit_state = CircuitState.HALF_OPEN
                    self._half_open_probe = True
                    logger.info("Circuit half-open, testing primary LLM")
                    return False

                return True

            elif self.circuit_state == CircuitState.HALF_OPEN:
                # We're testing the primary LLM in half-open state
                return False

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened based on errors and latency.

        Returns:
            True if circuit should be opened, False otherwise
        """
        # Check error count
        if self.error_count >= self.error_threshold:
            return True

        # Check p95 latency if we have enough data
        if len(self.request_latencies) >= 20:
            # Calculate p95 latency
            sorted_latencies = sorted(self.request_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency_ms = sorted_latencies[p95_index] * 1000  # Convert to ms

            if p95_latency_ms > self.latency_threshold_ms:
                logger.warning(
                    f"p95 latency ({p95_latency_ms:.1f}ms) exceeds threshold "
                    f"({self.latency_threshold_ms}ms)"
                )
                return True

        return False

    def _record_success(self, latency_seconds: float) -> None:
        """Record successful operation.

        Args:
            latency_seconds: Operation latency in seconds
        """
        with self.lock:
            now = datetime.now()

            # Add latency data
            self.request_latencies.append(latency_seconds)
            self.request_timestamps.append(now)

            # If we were probing the primary LLM, keep half-open state and clear the flag
            if self._half_open_probe:
                self._half_open_probe = False
            elif self.circuit_state == CircuitState.HALF_OPEN:
                self.circuit_state = CircuitState.CLOSED
                self.error_count = 0
                logger.info("Circuit closed, primary LLM is healthy")

    def _record_failure(self, exception: Exception) -> None:
        """Record failed operation.

        Args:
            exception: Exception that occurred
        """
        with self.lock:
            now = datetime.now()

            # Increment error count
            self.error_count += 1

            # Update last error time
            self.last_error_time = now

            if (
                self.circuit_state == CircuitState.CLOSED
                and self.error_count >= self.error_threshold
            ):
                self.circuit_state = CircuitState.OPEN
                self.next_retry_time = now + timedelta(seconds=self.reset_timeout_seconds)
                logger.warning(
                    f"Opening circuit due to errors, will retry at {self.next_retry_time}"
                )

            # If we're in half-open state, go back to open on failure
            if self.circuit_state == CircuitState.HALF_OPEN:
                self.circuit_state = CircuitState.OPEN
                self.next_retry_time = now + timedelta(
                    seconds=self.reset_timeout_seconds
                )

                logger.warning(
                    f"Circuit re-opened due to failure in half-open state, "
                    f"will retry at {self.next_retry_time}"
                )

    def _clean_old_data(self, now: datetime) -> None:
        """Clean up old latency and timestamp data.

        Args:
            now: Current datetime
        """
        # Calculate cutoff time
        cutoff_time = now - timedelta(seconds=self.track_window_seconds)

        # Filter out old data
        if self.request_timestamps:
            valid_indices = [
                i for i, ts in enumerate(self.request_timestamps) if ts >= cutoff_time
            ]

            self.request_latencies = [self.request_latencies[i] for i in valid_indices]
            self.request_timestamps = [
                self.request_timestamps[i] for i in valid_indices
            ]

    def _get_retry_after_seconds(self) -> int:
        """Get seconds until next retry attempt.

        Returns:
            Seconds until next retry
        """
        if self.next_retry_time is None:
            return self.reset_timeout_seconds

        now = datetime.now()
        if now >= self.next_retry_time:
            return 0

        return int((self.next_retry_time - now).total_seconds())

    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Dictionary with circuit status information
        """
        with self.lock:
            now = datetime.now()

            # Clean up old data
            self._clean_old_data(now)

            # Calculate p95 latency if we have enough data
            p95_latency_ms = None
            if len(self.request_latencies) >= 20:
                sorted_latencies = sorted(self.request_latencies)
                p95_index = int(len(sorted_latencies) * 0.95)
                p95_latency_ms = sorted_latencies[p95_index] * 1000  # Convert to ms

            return {
                "circuit_state": self.circuit_state.name,
                "error_count": self.error_count,
                "error_threshold": self.error_threshold,
                "request_count": len(self.request_latencies),
                "p95_latency_ms": p95_latency_ms,
                "latency_threshold_ms": self.latency_threshold_ms,
                "last_error_time": (
                    self.last_error_time.isoformat() if self.last_error_time else None
                ),
                "next_retry_time": (
                    self.next_retry_time.isoformat() if self.next_retry_time else None
                ),
                "retry_after_seconds": (
                    self._get_retry_after_seconds() if self.next_retry_time else None
                ),
            }
