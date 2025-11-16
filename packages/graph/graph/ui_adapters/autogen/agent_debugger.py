"""AutoGen Studio multi-agent debugging and step-over capabilities.

This module provides debugging and step-over functionality for multi-agent
interactions in AutoGen Studio, enabling visualization and control of agent
workflows.

Requirements addressed:
- 6.2: Step-over and debugging capabilities for agent interactions
- 6.4: Visual representation of agent interactions
"""

from typing import Dict, Any, Optional, List, Callable, Set, Tuple
import logging
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from application.ports import MessageBusPort, TracingPort


# Setup logging
logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Enum representing possible agent states in a workflow."""
    IDLE = "idle"
    THINKING = "thinking"
    WAITING = "waiting"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentNode:
    """Represents an agent in the workflow visualization."""
    id: str
    name: str
    role: str
    state: AgentState = AgentState.IDLE
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    position: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class MessageEdge:
    """Represents a message between agents in the workflow visualization."""
    id: str
    source_id: str
    target_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: str = "text"
    status: str = "delivered"


class AgentDebugger:
    """Debugger for multi-agent workflows with step-over capabilities.

    Provides visualization and control of multi-agent interactions,
    enabling step-by-step execution and debugging of agent workflows.
    """

    def __init__(
        self,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        """Initialize the agent debugger.

        Args:
            message_bus: Message bus for agent coordination
            tracer: Optional tracing port for observability
        """
        self.message_bus = message_bus
        self.tracer = tracer
        self.agents: Dict[str, AgentNode] = {}
        self.messages: Dict[str, MessageEdge] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.paused_agents: Set[str] = set()
        self.breakpoints: Dict[str, List[Dict[str, Any]]] = {}

        # Subscribe to agent messages for debugging
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers for agent coordination."""
        try:
            # Subscribe to agent state changes
            self.message_bus.subscribe(
                topic="agents.state.changes",
                handler=self._handle_agent_state_change,
                tenant_id="*"  # Subscribe to all tenants
            )

            # Subscribe to agent messages
            self.message_bus.subscribe(
                topic="agents.messages",
                handler=self._handle_agent_message,
                tenant_id="*"  # Subscribe to all tenants
            )

            # Subscribe to debugging commands
            self.message_bus.subscribe(
                topic="agents.debug.commands",
                handler=self._handle_debug_command,
                tenant_id="*"  # Subscribe to all tenants
            )

            logger.info("Agent debugger message handlers registered successfully")

        except Exception as e:
            logger.error(f"Failed to set up message handlers: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to set up message handlers: {str(e)}")

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        tools: List[str],
        tenant_id: str,
        position: Optional[Dict[str, float]] = None
    ) -> None:
        """Register an agent for debugging.

        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            role: Role of the agent in the workflow
            tools: List of tools available to the agent
            tenant_id: Tenant identifier for multi-tenant isolation
            position: Optional position for visualization
        """
        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.register_agent",
                tenant_id=tenant_id,
                agent_id=agent_id,
                role=role
            )

        logger.info(f"Registering agent for debugging: id={agent_id}, name={name}, role={role}")

        # Create agent node
        self.agents[agent_id] = AgentNode(
            id=agent_id,
            name=name,
            role=role,
            state=AgentState.IDLE,
            tools=tools,
            position=position or {"x": len(self.agents) * 200, "y": 100}
        )

        # Publish agent registration event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "agent_registered",
                "agent_id": agent_id,
                "name": name,
                "role": role,
                "tools": tools,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"register_{agent_id}"
        )

    def start_debug_session(
        self,
        session_id: str,
        workflow_id: str,
        tenant_id: str,
        agent_ids: List[str],
        initial_message: Optional[str] = None
    ) -> str:
        """Start a new debugging session for a multi-agent workflow.

        Args:
            session_id: Unique identifier for the debug session
            workflow_id: Identifier for the workflow being debugged
            tenant_id: Tenant identifier for multi-tenant isolation
            agent_ids: List of agent IDs participating in the workflow
            initial_message: Optional initial message to start the workflow

        Returns:
            Debug session ID for tracking
        """
        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.start_debug_session",
                tenant_id=tenant_id,
                session_id=session_id,
                workflow_id=workflow_id,
                agent_count=len(agent_ids)
            )

        logger.info(
            f"Starting debug session: id={session_id}, workflow_id={workflow_id}, "
            f"tenant_id={tenant_id}, agent_count={len(agent_ids)}"
        )

        # Create debug session
        self.active_sessions[session_id] = {
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "agent_ids": agent_ids,
            "start_time": datetime.now(),
            "status": "running",
            "step_mode": False,  # Start in continuous mode
            "current_step": 0,
            "messages": []
        }

        # Reset agent states for this session
        for agent_id in agent_ids:
            if agent_id in self.agents:
                self.agents[agent_id].state = AgentState.IDLE
                self.agents[agent_id].messages = []

        # Publish debug session start event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "debug_session_started",
                "session_id": session_id,
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "agent_ids": agent_ids,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"session_start_{session_id}"
        )

        # Send initial message if provided
        if initial_message and agent_ids:
            initial_agent_id = agent_ids[0]
            message_id = f"msg_{uuid.uuid4().hex}"

            # Create message edge
            self.messages[message_id] = MessageEdge(
                id=message_id,
                source_id="user",
                target_id=initial_agent_id,
                content=initial_message,
                timestamp=datetime.now(),
                message_type="text",
                status="delivered"
            )

            # Add message to session
            self.active_sessions[session_id]["messages"].append(message_id)

            # Publish message event
            self.message_bus.publish(
                topic="agents.messages",
                message={
                    "message_id": message_id,
                    "session_id": session_id,
                    "source_id": "user",
                    "target_id": initial_agent_id,
                    "content": initial_message,
                    "timestamp": datetime.now().isoformat(),
                    "tenant_id": tenant_id
                },
                tenant_id=tenant_id,
                idempotency_key=message_id
            )

        return session_id

    def enable_step_mode(
        self,
        session_id: str,
        tenant_id: str
    ) -> None:
        """Enable step-by-step execution mode for a debug session.

        Args:
            session_id: Debug session identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When session is not found
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Debug session not found: {session_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.enable_step_mode",
                tenant_id=tenant_id,
                session_id=session_id
            )

        logger.info(f"Enabling step mode for session: {session_id}")

        # Update session state
        self.active_sessions[session_id]["step_mode"] = True

        # Pause all agents in the session
        for agent_id in self.active_sessions[session_id]["agent_ids"]:
            self.pause_agent(agent_id, tenant_id)

        # Publish step mode event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "step_mode_enabled",
                "session_id": session_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"step_mode_{session_id}"
        )

    def disable_step_mode(
        self,
        session_id: str,
        tenant_id: str
    ) -> None:
        """Disable step-by-step execution mode for a debug session.

        Args:
            session_id: Debug session identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When session is not found
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Debug session not found: {session_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.disable_step_mode",
                tenant_id=tenant_id,
                session_id=session_id
            )

        logger.info(f"Disabling step mode for session: {session_id}")

        # Update session state
        self.active_sessions[session_id]["step_mode"] = False

        # Resume all agents in the session
        for agent_id in self.active_sessions[session_id]["agent_ids"]:
            self.resume_agent(agent_id, tenant_id)

        # Publish step mode event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "step_mode_disabled",
                "session_id": session_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"step_mode_{session_id}"
        )

    def step_over(
        self,
        session_id: str,
        tenant_id: str
    ) -> None:
        """Execute a single step in step-by-step mode.

        Args:
            session_id: Debug session identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When session is not found or not in step mode
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Debug session not found: {session_id}")

        if not self.active_sessions[session_id]["step_mode"]:
            raise ValueError(f"Session is not in step mode: {session_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.step_over",
                tenant_id=tenant_id,
                session_id=session_id,
                step=self.active_sessions[session_id]["current_step"] + 1
            )

        logger.info(f"Stepping over in session: {session_id}")

        # Increment step counter
        self.active_sessions[session_id]["current_step"] += 1
        current_step = self.active_sessions[session_id]["current_step"]

        # Find next agent to resume
        next_agent_id = self._get_next_agent_to_resume(session_id)

        if next_agent_id:
            # Resume only the next agent
            self.resume_agent(next_agent_id, tenant_id)

            # Publish step event
            self.message_bus.publish(
                topic="agents.debug.events",
                message={
                    "event_type": "step_executed",
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "step": current_step,
                    "agent_id": next_agent_id,
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"step_{session_id}_{current_step}"
            )
        else:
            logger.warning(f"No agent available to resume in session: {session_id}")

    def _get_next_agent_to_resume(self, session_id: str) -> Optional[str]:
        """Get the next agent to resume in step mode.

        Args:
            session_id: Debug session identifier

        Returns:
            Agent ID to resume or None if no agent is available
        """
        # Simple strategy: find the first paused agent
        for agent_id in self.active_sessions[session_id]["agent_ids"]:
            if agent_id in self.paused_agents:
                return agent_id

        return None

    def pause_agent(
        self,
        agent_id: str,
        tenant_id: str
    ) -> None:
        """Pause an agent's execution.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When agent is not found
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.pause_agent",
                tenant_id=tenant_id,
                agent_id=agent_id
            )

        logger.info(f"Pausing agent: {agent_id}")

        # Update agent state
        self.agents[agent_id].state = AgentState.PAUSED
        self.paused_agents.add(agent_id)

        # Publish agent pause event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "agent_paused",
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"pause_{agent_id}_{int(time.time())}"
        )

        # Publish agent state change
        self.message_bus.publish(
            topic="agents.state.changes",
            message={
                "agent_id": agent_id,
                "state": AgentState.PAUSED.value,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"state_{agent_id}_{int(time.time())}"
        )

    def resume_agent(
        self,
        agent_id: str,
        tenant_id: str
    ) -> None:
        """Resume a paused agent's execution.

        Args:
            agent_id: Agent identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When agent is not found
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.resume_agent",
                tenant_id=tenant_id,
                agent_id=agent_id
            )

        logger.info(f"Resuming agent: {agent_id}")

        # Update agent state
        self.agents[agent_id].state = AgentState.IDLE
        if agent_id in self.paused_agents:
            self.paused_agents.remove(agent_id)

        # Publish agent resume event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "agent_resumed",
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"resume_{agent_id}_{int(time.time())}"
        )

        # Publish agent state change
        self.message_bus.publish(
            topic="agents.state.changes",
            message={
                "agent_id": agent_id,
                "state": AgentState.IDLE.value,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"state_{agent_id}_{int(time.time())}"
        )

    def add_breakpoint(
        self,
        agent_id: str,
        condition: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """Add a breakpoint for an agent.

        Args:
            agent_id: Agent identifier
            condition: Breakpoint condition (e.g., message pattern, tool usage)
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Breakpoint ID for reference

        Raises:
            ValueError: When agent is not found
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.add_breakpoint",
                tenant_id=tenant_id,
                agent_id=agent_id,
                condition_type=condition.get("type")
            )

        logger.info(f"Adding breakpoint for agent: {agent_id}")

        # Generate breakpoint ID
        breakpoint_id = f"bp_{uuid.uuid4().hex}"

        # Initialize breakpoints list for agent if needed
        if agent_id not in self.breakpoints:
            self.breakpoints[agent_id] = []

        # Add breakpoint
        self.breakpoints[agent_id].append({
            "id": breakpoint_id,
            "condition": condition,
            "created_at": datetime.now()
        })

        # Publish breakpoint event
        self.message_bus.publish(
            topic="agents.debug.events",
            message={
                "event_type": "breakpoint_added",
                "breakpoint_id": breakpoint_id,
                "agent_id": agent_id,
                "condition": condition,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            },
            tenant_id=tenant_id,
            idempotency_key=f"breakpoint_{breakpoint_id}"
        )

        return breakpoint_id

    def remove_breakpoint(
        self,
        breakpoint_id: str,
        tenant_id: str
    ) -> None:
        """Remove a breakpoint.

        Args:
            breakpoint_id: Breakpoint identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Raises:
            ValueError: When breakpoint is not found
        """
        # Find the breakpoint
        found = False
        for agent_id, breakpoints in self.breakpoints.items():
            for i, bp in enumerate(breakpoints):
                if bp["id"] == breakpoint_id:
                    if self.tracer:
                        self.tracer.start_span(
                            name="agent_debugger.remove_breakpoint",
                            tenant_id=tenant_id,
                            agent_id=agent_id,
                            breakpoint_id=breakpoint_id
                        )

                    logger.info(f"Removing breakpoint: {breakpoint_id} for agent: {agent_id}")

                    # Remove breakpoint
                    self.breakpoints[agent_id].pop(i)
                    found = True

                    # Publish breakpoint event
                    self.message_bus.publish(
                        topic="agents.debug.events",
                        message={
                            "event_type": "breakpoint_removed",
                            "breakpoint_id": breakpoint_id,
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "timestamp": datetime.now().isoformat()
                        },
                        tenant_id=tenant_id,
                        idempotency_key=f"remove_bp_{breakpoint_id}"
                    )

                    break

            if found:
                break

        if not found:
            raise ValueError(f"Breakpoint not found: {breakpoint_id}")

    def get_workflow_visualization(
        self,
        session_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get visualization data for a workflow.

        Args:
            session_id: Debug session identifier
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Visualization data including nodes (agents) and edges (messages)

        Raises:
            ValueError: When session is not found
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Debug session not found: {session_id}")

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.get_workflow_visualization",
                tenant_id=tenant_id,
                session_id=session_id
            )

        logger.debug(f"Getting workflow visualization for session: {session_id}")

        session = self.active_sessions[session_id]

        # Collect agent nodes
        nodes = []
        for agent_id in session["agent_ids"]:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                nodes.append({
                    "id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "state": agent.state.value,
                    "tools": agent.tools,
                    "position": agent.position,
                    "last_updated": agent.last_updated.isoformat()
                })

        # Add user node
        nodes.append({
            "id": "user",
            "name": "User",
            "role": "user",
            "state": "idle",
            "tools": [],
            "position": {"x": 0, "y": 100},
            "last_updated": datetime.now().isoformat()
        })

        # Collect message edges
        edges = []
        for message_id in session["messages"]:
            if message_id in self.messages:
                message = self.messages[message_id]
                edges.append({
                    "id": message.id,
                    "source": message.source_id,
                    "target": message.target_id,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "type": message.message_type,
                    "status": message.status
                })

        # Return visualization data
        return {
            "session_id": session_id,
            "workflow_id": session["workflow_id"],
            "tenant_id": tenant_id,
            "status": session["status"],
            "step_mode": session["step_mode"],
            "current_step": session["current_step"],
            "start_time": session["start_time"].isoformat(),
            "nodes": nodes,
            "edges": edges
        }

    def _handle_agent_state_change(self, message: Dict[str, Any]) -> None:
        """Handle agent state change messages.

        Args:
            message: State change message
        """
        agent_id = message.get("agent_id")
        state_str = message.get("state")
        tenant_id = message.get("tenant_id")

        if not agent_id or not state_str:
            logger.warning("Received invalid state change message")
            return

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.handle_state_change",
                tenant_id=tenant_id,
                agent_id=agent_id,
                state=state_str
            )

        logger.debug(f"Handling state change for agent: {agent_id}, state: {state_str}")

        # Update agent state if registered
        if agent_id in self.agents:
            try:
                state = AgentState(state_str)
                self.agents[agent_id].state = state
                self.agents[agent_id].last_updated = datetime.now()

                # Check if we need to pause due to breakpoints
                if state == AgentState.EXECUTING and agent_id in self.breakpoints:
                    self._check_breakpoints(agent_id, message)

            except ValueError:
                logger.warning(f"Invalid agent state: {state_str}")

    def _handle_agent_message(self, message: Dict[str, Any]) -> None:
        """Handle agent message events.

        Args:
            message: Message event
        """
        message_id = message.get("message_id")
        session_id = message.get("session_id")
        source_id = message.get("source_id")
        target_id = message.get("target_id")
        content = message.get("content")
        tenant_id = message.get("tenant_id")

        if not message_id or not source_id or not target_id or not content:
            logger.warning("Received invalid message event")
            return

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.handle_message",
                tenant_id=tenant_id,
                message_id=message_id,
                source_id=source_id,
                target_id=target_id
            )

        logger.debug(f"Handling message: {message_id}, from: {source_id}, to: {target_id}")

        # Create message edge
        timestamp = datetime.now()
        if "timestamp" in message:
            try:
                timestamp = datetime.fromisoformat(message["timestamp"])
            except ValueError:
                pass

        self.messages[message_id] = MessageEdge(
            id=message_id,
            source_id=source_id,
            target_id=target_id,
            content=content,
            timestamp=timestamp,
            message_type=message.get("message_type", "text"),
            status=message.get("status", "delivered")
        )

        # Add message to session if applicable
        if session_id and session_id in self.active_sessions:
            self.active_sessions[session_id]["messages"].append(message_id)

        # Add message to source agent if registered
        if source_id in self.agents:
            self.agents[source_id].messages.append({
                "id": message_id,
                "direction": "outgoing",
                "target_id": target_id,
                "content": content,
                "timestamp": timestamp
            })

        # Add message to target agent if registered
        if target_id in self.agents:
            self.agents[target_id].messages.append({
                "id": message_id,
                "direction": "incoming",
                "source_id": source_id,
                "content": content,
                "timestamp": timestamp
            })

            # Check if we need to pause due to message breakpoints
            if target_id in self.breakpoints:
                self._check_message_breakpoints(target_id, message)

    def _handle_debug_command(self, message: Dict[str, Any]) -> None:
        """Handle debugging commands.

        Args:
            message: Debug command message
        """
        command = message.get("command")
        session_id = message.get("session_id")
        tenant_id = message.get("tenant_id")

        if not command or not session_id:
            logger.warning("Received invalid debug command")
            return

        if self.tracer:
            self.tracer.start_span(
                name="agent_debugger.handle_debug_command",
                tenant_id=tenant_id,
                command=command,
                session_id=session_id
            )

        logger.debug(f"Handling debug command: {command}, session: {session_id}")

        try:
            if command == "enable_step_mode":
                self.enable_step_mode(session_id, tenant_id)

            elif command == "disable_step_mode":
                self.disable_step_mode(session_id, tenant_id)

            elif command == "step_over":
                self.step_over(session_id, tenant_id)

            elif command == "pause_agent":
                agent_id = message.get("agent_id")
                if agent_id:
                    self.pause_agent(agent_id, tenant_id)

            elif command == "resume_agent":
                agent_id = message.get("agent_id")
                if agent_id:
                    self.resume_agent(agent_id, tenant_id)

            elif command == "add_breakpoint":
                agent_id = message.get("agent_id")
                condition = message.get("condition")
                if agent_id and condition:
                    self.add_breakpoint(agent_id, condition, tenant_id)

            elif command == "remove_breakpoint":
                breakpoint_id = message.get("breakpoint_id")
                if breakpoint_id:
                    self.remove_breakpoint(breakpoint_id, tenant_id)

            else:
                logger.warning(f"Unknown debug command: {command}")

        except Exception as e:
            logger.error(f"Error handling debug command: {str(e)}", exc_info=True)

            # Publish error event
            self.message_bus.publish(
                topic="agents.debug.events",
                message={
                    "event_type": "command_error",
                    "command": command,
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"cmd_error_{uuid.uuid4().hex}"
            )

    def _check_breakpoints(
        self,
        agent_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Check if any breakpoints should be triggered.

        Args:
            agent_id: Agent identifier
            context: Current execution context
        """
        if agent_id not in self.breakpoints:
            return

        tenant_id = context.get("tenant_id", "default")

        for bp in self.breakpoints[agent_id]:
            condition = bp["condition"]

            # Check condition type
            if condition.get("type") == "tool_usage" and context.get("tool") == condition.get("tool_name"):
                logger.info(f"Breakpoint triggered for agent {agent_id}: tool usage - {condition.get('tool_name')}")
                self.pause_agent(agent_id, tenant_id)

                # Publish breakpoint hit event
                self.message_bus.publish(
                    topic="agents.debug.events",
                    message={
                        "event_type": "breakpoint_hit",
                        "breakpoint_id": bp["id"],
                        "agent_id": agent_id,
                        "condition": condition,
                        "context": context,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.now().isoformat()
                    },
                    tenant_id=tenant_id,
                    idempotency_key=f"bp_hit_{bp['id']}"
                )

                break

    def _check_message_breakpoints(
        self,
        agent_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Check if any message-related breakpoints should be triggered.

        Args:
            agent_id: Agent identifier
            message: Message context
        """
        if agent_id not in self.breakpoints:
            return

        tenant_id = message.get("tenant_id", "default")
        content = message.get("content", "")

        for bp in self.breakpoints[agent_id]:
            condition = bp["condition"]

            # Check condition type
            if condition.get("type") == "message_pattern" and condition.get("pattern") in content:
                logger.info(f"Breakpoint triggered for agent {agent_id}: message pattern - {condition.get('pattern')}")
                self.pause_agent(agent_id, tenant_id)

                # Publish breakpoint hit event
                self.message_bus.publish(
                    topic="agents.debug.events",
                    message={
                        "event_type": "breakpoint_hit",
                        "breakpoint_id": bp["id"],
                        "agent_id": agent_id,
                        "condition": condition,
                        "message": message,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.now().isoformat()
                    },
                    tenant_id=tenant_id,
                    idempotency_key=f"bp_hit_{bp['id']}"
                )

                break