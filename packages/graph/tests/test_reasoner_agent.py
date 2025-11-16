"""Tests for ReasonerAgent."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from domain.agents.reasoner_agent import (
    ReasonerAgent,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    create_reasoner_agent
)
from domain.entities import Triple, ValidationReport, JobStatus
from domain.entities.validation_report import RuleViolation, RepairSuggestion
from domain.agent_coordinator import AgentCoordinator


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker(config)
        
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.can_execute() is True
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        
        # Record failures
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3
        assert breaker.can_execute() is False


class TestReasonerAgent:
    """Test ReasonerAgent functionality."""
    
    @pytest.fixture
    def mock_message_bus(self):
        """Mock message bus."""
        return Mock()
    
    @pytest.fixture
    def mock_ontology_validator(self):
        """Mock ontology validator."""
        return Mock()
    
    @pytest.fixture
    def sample_validation_report(self):
        """Sample validation report."""
        return ValidationReport(
            tenant_id="test_tenant",
            is_consistent=True,
            violated_rules=[],
            unsat_classes=[],
            repair_suggestions=[],
            explanation=None,
            ontology_version_id="test_version"
        )
    
    def test_reasoner_agent_initialization(self, mock_message_bus, mock_ontology_validator):
        """Test reasoner agent initialization."""
        agent = ReasonerAgent(
            message_bus=mock_message_bus,
            ontology_validator=mock_ontology_validator,
            tenant_id="test_tenant"
        )
        
        assert agent.message_bus == mock_message_bus
        assert agent.ontology_validator == mock_ontology_validator
        assert agent.tenant_id == "test_tenant"
        assert agent.is_running is False
        assert agent.validation_count == 0
        assert agent.circuit_breaker.state == CircuitBreakerState.CLOSED
    
    def test_start_stop_agent(self, mock_message_bus, mock_ontology_validator):
        """Test starting and stopping the agent."""
        agent = ReasonerAgent(
            message_bus=mock_message_bus,
            ontology_validator=mock_ontology_validator,
            tenant_id="test_tenant"
        )
        
        # Start agent
        agent.start()
        assert agent.is_running is True
        
        # Stop agent
        agent.stop()
        assert agent.is_running is False


def test_create_reasoner_agent_default():
    """Test creating reasoner agent with default configuration."""
    mock_message_bus = Mock()
    mock_ontology_validator = Mock()
    
    agent = create_reasoner_agent(
        message_bus=mock_message_bus,
        ontology_validator=mock_ontology_validator,
        tenant_id="test_tenant"
    )
    
    assert isinstance(agent, ReasonerAgent)
    assert agent.tenant_id == "test_tenant"
    assert agent.circuit_breaker.config.failure_threshold == 5
    assert agent.circuit_breaker.config.recovery_timeout == 60