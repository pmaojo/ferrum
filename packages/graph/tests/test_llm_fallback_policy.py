"""Tests for LLMFallbackPolicy."""

import unittest
from unittest.mock import Mock, MagicMock, patch
import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Union, Iterator

from domain.llm_fallback_policy import LLMFallbackPolicy, CircuitState
from domain.exceptions import (
    QuotaExceededException, RateLimitedException, ServiceUnavailableException
)


class TestLLMFallbackPolicy:
    """Test suite for LLMFallbackPolicy."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLMs
        self.primary_llm = Mock()
        self.fallback_llm = Mock()
        self.tracer_mock = Mock()
        self.tracer_mock.start_span.return_value = MagicMock()

        # Configure primary LLM mock
        self.primary_llm.generate.return_value = "Primary LLM response"
        self.primary_llm.embed.return_value = [0.1, 0.2, 0.3, 0.4]
        self.primary_llm.moderate.return_value = {"flagged": False}
        self.primary_llm.get_token_count.return_value = 10

        # Configure fallback LLM mock
        self.fallback_llm.generate.return_value = "Fallback LLM response"
        self.fallback_llm.embed.return_value = [0.5, 0.6, 0.7, 0.8]
        self.fallback_llm.moderate.return_value = {"flagged": True}
        self.fallback_llm.get_token_count.return_value = 12

        # Initialize policy with test configuration
        self.policy = LLMFallbackPolicy(
            primary_llm=self.primary_llm,
            fallback_llm=self.fallback_llm,
            tracer=self.tracer_mock,
            error_threshold=3,
            latency_threshold_ms=500,
            reset_timeout_seconds=30,
            track_window_seconds=60
        )

    def test_generate_primary(self):
        """Test generate using primary LLM."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Act
        result = self.policy.generate(
            prompt=prompt,
            tenant_id=tenant_id
        )

        # Assert
        assert result == "Primary LLM response"
        self.primary_llm.generate.assert_called_once_with(
            prompt=prompt,
            tenant_id=tenant_id,
            stream=False,
            tools=None,
            opts=None
        )
        self.fallback_llm.generate.assert_not_called()

    def test_span_closed_on_generate(self):
        """Verify span is closed after generation."""
        span = MagicMock()
        self.tracer_mock.start_span.return_value = span

        self.policy.generate(prompt="q", tenant_id="t")

        span.end.assert_called_once()

    def test_embed_primary(self):
        """Test embed using primary LLM."""
        # Arrange
        text = "Test text"
        tenant_id = "test-tenant"

        # Act
        result = self.policy.embed(
            text=text,
            tenant_id=tenant_id
        )

        # Assert
        assert result == [0.1, 0.2, 0.3, 0.4]
        self.primary_llm.embed.assert_called_once_with(
            text=text,
            tenant_id=tenant_id,
            opts=None
        )
        self.fallback_llm.embed.assert_not_called()

    def test_moderate_primary(self):
        """Test moderate using primary LLM."""
        # Arrange
        text = "Test text"
        tenant_id = "test-tenant"

        # Act
        result = self.policy.moderate(
            text=text,
            tenant_id=tenant_id
        )

        # Assert
        assert result == {"flagged": False}
        self.primary_llm.moderate.assert_called_once_with(
            text=text,
            tenant_id=tenant_id,
            opts=None
        )
        self.fallback_llm.moderate.assert_not_called()

    def test_get_token_count_primary(self):
        """Test get_token_count using primary LLM."""
        # Arrange
        text = "Test text"

        # Act
        result = self.policy.get_token_count(
            text=text
        )

        # Assert
        assert result == 10
        self.primary_llm.get_token_count.assert_called_once_with(
            text=text
        )
        self.fallback_llm.get_token_count.assert_not_called()

    def test_fallback_on_quota_exceeded(self):
        """Test fallback when primary LLM exceeds quota."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Configure primary LLM to raise exception
        self.primary_llm.generate.side_effect = QuotaExceededException(
            model="gemini-1.5-flash",
            tenant_id=tenant_id
        )

        # Act
        result = self.policy.generate(
            prompt=prompt,
            tenant_id=tenant_id
        )

        # Assert
        assert result == "Fallback LLM response"
        self.primary_llm.generate.assert_called_once()
        self.fallback_llm.generate.assert_called_once()

        # Check that metric was recorded
        self.tracer_mock.record_metric.assert_any_call(
            name="llm_fallback_total",
            value=1.0,
            tenant_id=tenant_id,
            operation="generate",
            error_type="QuotaExceededException"
        )

    def test_fallback_on_rate_limited(self):
        """Test fallback when primary LLM is rate limited."""
        # Arrange
        text = "Test text"
        tenant_id = "test-tenant"

        # Configure primary LLM to raise exception
        self.primary_llm.embed.side_effect = RateLimitedException(
            model="gemini-1.5-flash",
            tenant_id=tenant_id,
            retry_after=30
        )

        # Act
        result = self.policy.embed(
            text=text,
            tenant_id=tenant_id
        )

        # Assert
        assert result == [0.5, 0.6, 0.7, 0.8]
        self.primary_llm.embed.assert_called_once()
        self.fallback_llm.embed.assert_called_once()

    def test_circuit_opens_after_errors(self):
        """Test circuit opens after multiple errors."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Configure primary LLM to raise exception
        self.primary_llm.generate.side_effect = ServiceUnavailableException(
            model="gemini-1.5-flash",
            tenant_id=tenant_id
        )

        # Act - Trigger errors to reach threshold
        for _ in range(self.policy.error_threshold):
            try:
                self.policy.generate(
                    prompt=prompt,
                    tenant_id=tenant_id
                )
            except ServiceUnavailableException:
                pass

        # Assert circuit is open
        assert self.policy.circuit_state == CircuitState.OPEN

        # Act again - Should use fallback directly
        self.primary_llm.generate.reset_mock()
        self.fallback_llm.generate.reset_mock()

        result = self.policy.generate(
            prompt=prompt,
            tenant_id=tenant_id
        )

        # Assert
        assert result == "Fallback LLM response"
        self.primary_llm.generate.assert_not_called()  # Should not call primary
        self.fallback_llm.generate.assert_called_once()

        # Check that metric was recorded
        self.tracer_mock.record_metric.assert_any_call(
            name="llm_fallback_total",
            value=1.0,
            tenant_id=tenant_id,
            operation="generate",
            circuit_state="OPEN"
        )

    def test_circuit_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Open the circuit
        self.policy.circuit_state = CircuitState.OPEN
        self.policy.next_retry_time = datetime.now() - timedelta(seconds=1)  # In the past

        # Act
        self.policy.generate(
            prompt=prompt,
            tenant_id=tenant_id
        )

        # Assert
        assert self.policy.circuit_state == CircuitState.HALF_OPEN
        self.primary_llm.generate.assert_called_once()  # Should try primary again
        self.fallback_llm.generate.assert_not_called()

    def test_circuit_closes_after_success(self):
        """Test circuit closes after successful operation in half-open state."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Set circuit to half-open
        self.policy.circuit_state = CircuitState.HALF_OPEN

        # Act
        result = self.policy.generate(
            prompt=prompt,
            tenant_id=tenant_id
        )

        # Assert
        assert result == "Primary LLM response"
        assert self.policy.circuit_state == CircuitState.CLOSED
        self.primary_llm.generate.assert_called_once()

    def test_circuit_reopens_after_failure_in_half_open(self):
        """Test circuit reopens after failure in half-open state."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Set circuit to half-open
        self.policy.circuit_state = CircuitState.HALF_OPEN

        # Configure primary LLM to raise exception
        self.primary_llm.generate.side_effect = ServiceUnavailableException(
            model="gemini-1.5-flash",
            tenant_id=tenant_id
        )

        # Act
        try:
            self.policy.generate(
                prompt=prompt,
                tenant_id=tenant_id
            )
        except ServiceUnavailableException:
            pass

        # Assert
        assert self.policy.circuit_state == CircuitState.OPEN
        assert self.policy.next_retry_time is not None

    def test_circuit_opens_on_high_latency(self):
        """Test circuit opens when p95 latency exceeds threshold."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Configure primary LLM to be slow
        def slow_generate(*args, **kwargs):
            time.sleep(0.01)  # Small delay for testing
            return "Slow response"

        self.primary_llm.generate.side_effect = slow_generate

        # Act - Generate enough requests to calculate p95
        for _ in range(25):
            self.policy.generate(
                prompt=prompt,
                tenant_id=tenant_id
            )

        # Manually set latencies to exceed threshold
        self.policy.request_latencies = [0.6] * 25  # 600ms, above threshold

        # Trigger circuit check
        self.policy._should_use_fallback()

        # Assert
        assert self.policy.circuit_state == CircuitState.OPEN

    def test_get_circuit_status(self):
        """Test getting circuit status."""
        # Arrange
        self.policy.circuit_state = CircuitState.OPEN
        self.policy.error_count = 5
        self.policy.last_error_time = datetime.now()
        self.policy.next_retry_time = datetime.now() + timedelta(seconds=30)
        self.policy.request_latencies = [0.1, 0.2, 0.3, 0.4, 0.5] * 5  # 25 values
        self.policy.request_timestamps = [datetime.now()] * 25

        # Act
        status = self.policy.get_circuit_status()

        # Assert
        assert status["circuit_state"] == "OPEN"
        assert status["error_count"] == 5
        assert status["error_threshold"] == 3
        assert status["request_count"] == 25
        assert status["p95_latency_ms"] is not None
        assert status["latency_threshold_ms"] == 500
        assert status["last_error_time"] is not None
        assert status["next_retry_time"] is not None
        assert status["retry_after_seconds"] is not None

    def test_no_fallback_available(self):
        """Test behavior when no fallback is available."""
        # Arrange
        prompt = "Test prompt"
        tenant_id = "test-tenant"

        # Create policy without fallback
        policy = LLMFallbackPolicy(
            primary_llm=self.primary_llm,
            fallback_llm=None,
            tracer=self.tracer_mock
        )

        # Configure primary LLM to raise exception
        self.primary_llm.generate.side_effect = QuotaExceededException(
            model="gemini-1.5-flash",
            tenant_id=tenant_id
        )

        # Act/Assert
        with pytest.raises(QuotaExceededException):
            policy.generate(
                prompt=prompt,
                tenant_id=tenant_id
            )

    def test_clean_old_data(self):
        """Test cleaning of old data."""
        # Arrange
        now = datetime.now()
        old_time = now - timedelta(seconds=self.policy.track_window_seconds + 10)
        recent_time = now - timedelta(seconds=10)

        self.policy.request_latencies = [0.1, 0.2, 0.3]
        self.policy.request_timestamps = [old_time, recent_time, now]

        # Act
        self.policy._clean_old_data(now)

        # Assert
        assert len(self.policy.request_latencies) == 2
        assert len(self.policy.request_timestamps) == 2
        assert self.policy.request_latencies == [0.2, 0.3]
        assert self.policy.request_timestamps == [recent_time, now]