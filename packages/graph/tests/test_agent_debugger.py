"""Unit tests for AutoGen Studio agent debugger."""

import pytest
from unittest.mock import Mock, MagicMock, call
import uuid
from datetime import datetime
from typing import Dict, Any, List

from application.ports.messaging import MessageBusPort
from application.ports import TracingPort
from ui_adapters.autogen.agent_debugger import (
    AgentDebugger, AgentState, AgentNode, MessageEdge
)


class TestAgentDebugger:
    """Test suite for AutoGen Studio agent debugger."""

    @pytest.fixture
    def mock_message_bus(self) -> Mock:
        """Mock MessageBusPort for testing."""
        mock = Mock(spec=MessageBusPort)
        return mock

    @pytest.fixture
    def mock_tracer(self) -> Mock:
        """Mock TracingPort for testing."""
        mock = Mock(spec=TracingPort)
        mock.start_span.return_value = MagicMock()
        return mock

    @pytest.fixture
    def agent_debugger(
        self,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ) -> AgentDebugger:
        """AgentDebugger instance with mocked dependencies."""
        return AgentDebugger(
            message_bus=mock_message_bus,
            tracer=mock_tracer
        )

    def test_initialization(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
    ) -> None:
        """Test initialization of AgentDebugger."""
        # Verify message handlers are set up
        assert mock_message_bus.subscribe.call_count == 3

        # Check subscriptions
        topics = [
            call_args[1]["topic"]
            for call_args in mock_message_bus.subscribe.call_args_list
        ]
        assert "agents.state.changes" in topics
        assert "agents.messages" in topics
        assert "agents.debug.commands" in topics

        # Verify initial state
        assert agent_debugger.agents == {}
        assert agent_debugger.messages == {}
        assert agent_debugger.active_sessions == {}
        assert agent_debugger.paused_agents == set()
        assert agent_debugger.breakpoints == {}

    def test_register_agent(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test agent registration functionality."""
        # Arrange
        agent_id = "test_agent"
        name = "Test Agent"
        role = "assistant"
        tools = ["graphrag", "calculator"]
        tenant_id = "tenant1"
        position = {"x": 100, "y": 200}

        # Act
        agent_debugger.register_agent(
            agent_id=agent_id,
            name=name,
            role=role,
            tools=tools,
            tenant_id=tenant_id,
            position=position
        )

        # Assert
        # Verify agent is registered
        assert agent_id in agent_debugger.agents
        assert agent_debugger.agents[agent_id].name == name
        assert agent_debugger.agents[agent_id].role == role
        assert agent_debugger.agents[agent_id].tools == tools
        assert agent_debugger.agents[agent_id].position == position
        assert agent_debugger.agents[agent_id].state == AgentState.IDLE

        # Verify event publication
        mock_message_bus.publish.assert_called_once()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "agents.debug.events"
        assert call_args[1]["tenant_id"] == tenant_id

        # Verify message content
        message = call_args[1]["message"]
        assert message["event_type"] == "agent_registered"
        assert message["agent_id"] == agent_id
        assert message["name"] == name
        assert message["role"] == role
        assert message["tools"] == tools

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="agent_debugger.register_agent",
            tenant_id=tenant_id,
            agent_id=agent_id,
            role=role
        )

    def test_start_debug_session(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test starting a debug session."""
        # Arrange
        session_id = "session1"
        workflow_id = "workflow1"
        tenant_id = "tenant1"
        agent_ids = ["agent1", "agent2"]
        initial_message = "Hello, agents!"

        # Register agents first
        for i, agent_id in enumerate(agent_ids):
            agent_debugger.register_agent(
                agent_id=agent_id,
                name=f"Agent {i+1}",
                role="assistant",
                tools=[],
                tenant_id=tenant_id
            )

        # Reset mock to clear registration calls
        mock_message_bus.reset_mock()
        mock_tracer.reset_mock()

        # Act
        result = agent_debugger.start_debug_session(
            session_id=session_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            agent_ids=agent_ids,
            initial_message=initial_message
        )

        # Assert
        assert result == session_id

        # Verify session is created
        assert session_id in agent_debugger.active_sessions
        assert agent_debugger.active_sessions[session_id]["workflow_id"] == workflow_id
        assert agent_debugger.active_sessions[session_id]["tenant_id"] == tenant_id
        assert agent_debugger.active_sessions[session_id]["agent_ids"] == agent_ids
        assert agent_debugger.active_sessions[session_id]["status"] == "running"
        assert agent_debugger.active_sessions[session_id]["step_mode"] is False

        # Verify agent states are reset
        for agent_id in agent_ids:
            assert agent_debugger.agents[agent_id].state == AgentState.IDLE
            assert agent_debugger.agents[agent_id].messages == []

        # Verify events are published (session start + initial message)
        assert mock_message_bus.publish.call_count == 2

        # Check session start event
        first_call = mock_message_bus.publish.call_args_list[0]
        assert first_call[1]["topic"] == "agents.debug.events"
        assert first_call[1]["tenant_id"] == tenant_id
        assert first_call[1]["message"]["event_type"] == "debug_session_started"
        assert first_call[1]["message"]["session_id"] == session_id

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="agent_debugger.start_debug_session",
            tenant_id=tenant_id,
            session_id=session_id,
            workflow_id=workflow_id,
            agent_count=len(agent_ids)
        )

    def test_enable_step_mode(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test enabling step mode."""
        # Arrange
        session_id = "session1"
        workflow_id = "workflow1"
        tenant_id = "tenant1"
        agent_ids = ["agent1", "agent2"]

        # Register agents and start session
        for agent_id in agent_ids:
            agent_debugger.register_agent(
                agent_id=agent_id,
                name=agent_id,
                role="assistant",
                tools=[],
                tenant_id=tenant_id
            )

        agent_debugger.start_debug_session(
            session_id=session_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            agent_ids=agent_ids
        )

        # Reset mock to clear previous calls
        mock_message_bus.reset_mock()
        mock_tracer.reset_mock()

        # Act
        agent_debugger.enable_step_mode(session_id, tenant_id)

        # Assert
        # Verify step mode is enabled
        assert agent_debugger.active_sessions[session_id]["step_mode"] is True

        # Verify agents are paused
        for agent_id in agent_ids:
            assert agent_debugger.agents[agent_id].state == AgentState.PAUSED
            assert agent_id in agent_debugger.paused_agents

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="agent_debugger.enable_step_mode",
            tenant_id=tenant_id,
            session_id=session_id
        )

    def test_step_over(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test step-over functionality."""
        # Arrange
        session_id = "session1"
        workflow_id = "workflow1"
        tenant_id = "tenant1"
        agent_ids = ["agent1", "agent2"]

        # Register agents and start session
        for agent_id in agent_ids:
            agent_debugger.register_agent(
                agent_id=agent_id,
                name=agent_id,
                role="assistant",
                tools=[],
                tenant_id=tenant_id
            )

        agent_debugger.start_debug_session(
            session_id=session_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            agent_ids=agent_ids
        )

        # Enable step mode first
        agent_debugger.enable_step_mode(session_id, tenant_id)

        # Reset mock to clear previous calls
        mock_message_bus.reset_mock()
        mock_tracer.reset_mock()

        # Act
        agent_debugger.step_over(session_id, tenant_id)

        # Assert
        # Verify step counter is incremented
        assert agent_debugger.active_sessions[session_id]["current_step"] == 1

        # Verify one agent is resumed (the first one)
        assert agent_debugger.agents[agent_ids[0]].state == AgentState.IDLE
        assert agent_ids[0] not in agent_debugger.paused_agents

        # Other agents should still be paused
        assert agent_debugger.agents[agent_ids[1]].state == AgentState.PAUSED
        assert agent_ids[1] in agent_debugger.paused_agents

        # Verify tracing
        mock_tracer.start_span.assert_called_with(
            name="agent_debugger.step_over",
            tenant_id=tenant_id,
            session_id=session_id,
            step=1
        )

    def test_add_breakpoint(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock,
        mock_tracer: Mock
    ):
        """Test adding breakpoints."""
        # Arrange
        agent_id = "test_agent"
        tenant_id = "tenant1"
        condition = {
            "type": "message_pattern",
            "pattern": "error"
        }

        # Register agent
        agent_debugger.register_agent(
            agent_id=agent_id,
            name="Test Agent",
            role="assistant",
            tools=[],
            tenant_id=tenant_id
        )

        # Reset mock to clear registration calls
        mock_message_bus.reset_mock()
        mock_tracer.reset_mock()

        # Act - Add breakpoint
        breakpoint_id = agent_debugger.add_breakpoint(agent_id, condition, tenant_id)

        # Assert - Add
        assert agent_id in agent_debugger.breakpoints
        assert len(agent_debugger.breakpoints[agent_id]) == 1
        assert agent_debugger.breakpoints[agent_id][0]["id"] == breakpoint_id
        assert agent_debugger.breakpoints[agent_id][0]["condition"] == condition

        # Verify add event
        mock_message_bus.publish.assert_called_once()
        call_args = mock_message_bus.publish.call_args
        assert call_args[1]["topic"] == "agents.debug.events"
        assert call_args[1]["message"]["event_type"] == "breakpoint_added"
        assert call_args[1]["message"]["breakpoint_id"] == breakpoint_id

    def test_get_workflow_visualization(
        self,
        agent_debugger: AgentDebugger,
        mock_message_bus: Mock
    ):
        """Test getting workflow visualization data."""
        # Arrange
        session_id = "session1"
        workflow_id = "workflow1"
        tenant_id = "tenant1"
        agent_ids = ["agent1", "agent2"]

        # Register agents and start session
        for i, agent_id in enumerate(agent_ids):
            agent_debugger.register_agent(
                agent_id=agent_id,
                name=f"Agent {i+1}",
                role="assistant",
                tools=["tool1", "tool2"],
                tenant_id=tenant_id,
                position={"x": i * 200, "y": 100}
            )

        agent_debugger.start_debug_session(
            session_id=session_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            agent_ids=agent_ids,
            initial_message="Hello, agents!"
        )

        # Act
        visualization = agent_debugger.get_workflow_visualization(session_id, tenant_id)

        # Assert
        assert visualization["session_id"] == session_id
        assert visualization["workflow_id"] == workflow_id
        assert visualization["tenant_id"] == tenant_id
        assert visualization["status"] == "running"
        assert visualization["step_mode"] is False
        assert visualization["current_step"] == 0

        # Check nodes (agents + user)
        assert len(visualization["nodes"]) == len(agent_ids) + 1

        # Verify agent nodes
        agent_nodes = [node for node in visualization["nodes"] if node["id"] != "user"]
        assert len(agent_nodes) == len(agent_ids)

        # Verify user node
        user_node = next((n for n in visualization["nodes"] if n["id"] == "user"), None)
        assert user_node is not None
        assert user_node["name"] == "User"
        assert user_node["role"] == "user"


if __name__ == "__main__":
    pytest.main([__file__])