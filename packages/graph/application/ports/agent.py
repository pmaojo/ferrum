"""Port interfaces for multi-agent coordination."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from domain.entities import (
    Agent,
    AgentType,
    CoordinationSession,
    CoordinationStrategy,
    ScientificDomain,
)


class AgentCoordinationPort(ABC):
    """Port for coordinating multiple agents."""

    @abstractmethod
    async def create_coordination_session(
        self,
        tenant_id: str,
        kg_id: str,
        strategy: CoordinationStrategy,
        participating_agents: List[str],
        session_goal: str,
        created_by: str,
    ) -> CoordinationSession:
        """Create a new coordination session."""

    @abstractmethod
    async def assign_task_to_agent(
        self,
        agent_id: str,
        task_description: str,
        task_parameters: Dict[str, Any],
        session_id: str,
    ) -> str:
        """Assign a task to a specific agent."""

    @abstractmethod
    async def coordinate_agent_responses(
        self,
        session_id: str,
        agent_responses: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Coordinate and synthesize responses from multiple agents."""

    @abstractmethod
    async def monitor_session_progress(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """Monitor the progress of a coordination session."""


class AgentRepositoryPort(ABC):
    """Port for agent persistence operations."""

    @abstractmethod
    async def create_agent(
        self,
        agent: Agent,
    ) -> Agent:
        """Create a new agent."""

    @abstractmethod
    async def get_agent_by_id(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> Optional[Agent]:
        """Get agent by ID."""

    @abstractmethod
    async def list_agents_by_type(
        self,
        agent_type: AgentType,
        tenant_id: str,
        is_active: bool = True,
    ) -> List[Agent]:
        """List agents by type."""

    @abstractmethod
    async def list_agents_by_domain(
        self,
        domain: ScientificDomain,
        tenant_id: str,
        is_active: bool = True,
    ) -> List[Agent]:
        """List agents specialized in a domain."""

    @abstractmethod
    async def update_agent(
        self,
        agent: Agent,
    ) -> Agent:
        """Update an existing agent."""

    @abstractmethod
    async def deactivate_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> None:
        """Deactivate an agent."""


class TaskSchedulingPort(ABC):
    """Port for task scheduling and management."""

    @abstractmethod
    async def schedule_task(
        self,
        task_description: str,
        agent_requirements: Dict[str, Any],
        priority: int,
        tenant_id: str,
    ) -> str:
        """Schedule a task for execution."""

    @abstractmethod
    async def get_available_agents(
        self,
        requirements: Dict[str, Any],
        tenant_id: str,
    ) -> List[Agent]:
        """Get agents available for task execution."""

    @abstractmethod
    async def distribute_workload(
        self,
        tasks: List[Dict[str, Any]],
        agents: List[Agent],
    ) -> Dict[str, List[str]]:
        """Distribute tasks among available agents."""

    @abstractmethod
    async def monitor_task_execution(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """Monitor the execution of a task."""


class PerformanceMonitoringPort(ABC):
    """Port for monitoring agent performance."""

    @abstractmethod
    async def record_agent_performance(
        self,
        agent_id: str,
        task_id: str,
        metrics: Dict[str, float],
        tenant_id: str,
    ) -> None:
        """Record performance metrics for an agent."""

    @abstractmethod
    async def get_agent_performance_summary(
        self,
        agent_id: str,
        tenant_id: str,
        time_period_days: int = 30,
    ) -> Dict[str, float]:
        """Get performance summary for an agent."""

    @abstractmethod
    async def compare_agent_performance(
        self,
        agent_ids: List[str],
        tenant_id: str,
        metric: str,
    ) -> Dict[str, float]:
        """Compare performance across multiple agents."""

    @abstractmethod
    async def identify_performance_bottlenecks(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks in coordination sessions."""


class AgentManagementPort(ABC):
    """Port for basic agent lifecycle management and event streaming."""

    @abstractmethod
    async def list_agents(self) -> List[str]:
        """Return names of available agents."""

    @abstractmethod
    async def start_agent(self, name: str) -> None:
        """Start an agent by name."""

    @abstractmethod
    async def stop_agent(self, name: str) -> None:
        """Stop an agent by name."""

    @abstractmethod
    def log(self, name: str, message: str) -> None:
        """Emit a log message for the agent."""

    @abstractmethod
    def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to agent events as an async iterator."""
