"""Workflow and Agent Integration Service following SOLID principles."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from application.ports import (
    JobRepositoryPort,
    MessageBusPort,
    WorkflowExecutionPort,
    WorkflowRepositoryPort,
)
from domain.entities import Job, Workflow, WorkflowType
from domain.exceptions import ValidationError


class AgentWorkflowIntegrationPort(ABC):
    """Port for agent-workflow integration following Interface Segregation Principle."""

    @abstractmethod
    def execute_workflow_with_agents(
        self, workflow_id: str, tenant_id: str, agent_configs: List[Dict[str, Any]]
    ) -> str:
        """Execute workflow with agent coordination."""

    @abstractmethod
    def get_agent_workflow_status(self, job_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get status of agent-coordinated workflow execution."""


class LangGraphWorkflowExecutor(ABC):
    """Abstract base for LangGraph workflow execution following Open/Closed Principle."""

    @abstractmethod
    def create_langgraph_workflow(self, workflow_definition: Dict[str, Any]) -> Any:
        """Create a LangGraph workflow from definition."""

    @abstractmethod
    def execute_langgraph_workflow(
        self, langgraph_workflow: Any, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a LangGraph workflow."""


class WorkflowAgentCoordinator:
    """
    Coordinates workflow execution with agents following Single Responsibility Principle.

    This class is responsible only for coordinating between workflows and agents,
    delegating specific tasks to appropriate services.
    """

    def __init__(
        self,
        workflow_repository: WorkflowRepositoryPort,
        job_repository: JobRepositoryPort,
        workflow_execution_service: WorkflowExecutionPort,
        message_bus: MessageBusPort,
        langgraph_executor: Optional[LangGraphWorkflowExecutor] = None,
    ):
        """Initialize with dependencies following Dependency Inversion Principle."""
        self.workflow_repository = workflow_repository
        self.job_repository = job_repository
        self.workflow_execution_service = workflow_execution_service
        self.message_bus = message_bus
        self.langgraph_executor = langgraph_executor

    def execute_agent_coordinated_workflow(
        self,
        workflow_id: str,
        tenant_id: str,
        input_parameters: Dict[str, Any],
        agent_configs: List[Dict[str, Any]],
        created_by: str,
    ) -> str:
        """
        Execute a workflow with agent coordination.

        Args:
            workflow_id: ID of the workflow to execute
            tenant_id: Tenant identifier
            input_parameters: Input parameters for the workflow
            agent_configs: Configuration for agents to coordinate
            created_by: User who initiated the execution

        Returns:
            Job ID for tracking execution

        Raises:
            ValidationError: If workflow or agents are invalid
        """
        # Get and validate workflow
        workflow = self._get_and_validate_workflow(workflow_id, tenant_id)

        # Validate agent configurations
        self._validate_agent_configs(agent_configs)

        # Create job for tracking
        job = self._create_coordination_job(workflow, input_parameters, created_by)

        # Determine execution strategy based on workflow type
        if self._should_use_langgraph(workflow):
            return self._execute_with_langgraph(workflow, job, agent_configs)
        else:
            return self._execute_with_message_coordination(workflow, job, agent_configs)

    def _get_and_validate_workflow(self, workflow_id: str, tenant_id: str) -> Workflow:
        """Get and validate workflow exists and is active."""
        workflow = self.workflow_repository.get_by_id(workflow_id, tenant_id)

        if not workflow:
            raise ValidationError(
                message=f"Workflow with ID {workflow_id} not found", param="workflow_id"
            )

        if not workflow.is_active:
            raise ValidationError(
                message=f"Workflow with ID {workflow_id} is not active",
                param="workflow_id",
            )

        return workflow

    def _validate_agent_configs(self, agent_configs: List[Dict[str, Any]]) -> None:
        """Validate agent configurations."""
        if not agent_configs:
            raise ValidationError(
                message="At least one agent configuration is required",
                param="agent_configs",
            )

        for i, config in enumerate(agent_configs):
            if "agent_type" not in config:
                raise ValidationError(
                    message=f"Agent configuration {i} missing required 'agent_type'",
                    param=f"agent_configs[{i}].agent_type",
                )

            if "capabilities" not in config:
                raise ValidationError(
                    message=f"Agent configuration {i} missing required 'capabilities'",
                    param=f"agent_configs[{i}].capabilities",
                )

    def _create_coordination_job(
        self, workflow: Workflow, input_parameters: Dict[str, Any], created_by: str
    ) -> Job:
        """Create a job for tracking agent-coordinated execution."""
        job = Job.create(
            workflow_id=workflow.id,
            tenant_id=workflow.tenant_id,
            input_parameters=input_parameters,
            created_by=created_by,
            max_retries=3,
        )

        # Add agent coordination metadata
        if job.output_data is None:
            job.output_data = {}
        job.output_data["coordination_type"] = "agent_coordinated"
        job.output_data["coordination_started_at"] = datetime.now().isoformat()

        return self.job_repository.create(job)

    def _should_use_langgraph(self, workflow: Workflow) -> bool:
        """Determine if workflow should use LangGraph for execution."""
        # Use LangGraph for complex workflows with multiple decision points
        if not self.langgraph_executor:
            return False

        # Check workflow definition for LangGraph indicators
        definition = workflow.definition

        # Use LangGraph if workflow has conditional logic or multiple agents
        has_conditions = "conditions" in definition or "branches" in definition
        has_multiple_agents = (
            "agents" in definition and len(definition.get("agents", [])) > 1
        )
        is_complex_type = workflow.workflow_type in [
            WorkflowType.ANALYTICS,
            WorkflowType.VALIDATION,
        ]

        return has_conditions or has_multiple_agents or is_complex_type

    def _execute_with_langgraph(
        self, workflow: Workflow, job: Job, agent_configs: List[Dict[str, Any]]
    ) -> str:
        """Execute workflow using LangGraph for complex agent coordination."""
        if not self.langgraph_executor:
            raise ValidationError(
                message="LangGraph executor not available", param="langgraph_executor"
            )

        try:
            # Start job
            job.start()
            self.job_repository.update(job)

            # Create LangGraph workflow
            langgraph_definition = self._create_langgraph_definition(
                workflow, agent_configs
            )
            langgraph_workflow = self.langgraph_executor.create_langgraph_workflow(
                langgraph_definition
            )

            # Execute asynchronously (in a real implementation, this would be async)
            self._publish_langgraph_execution_message(
                job, langgraph_workflow, agent_configs
            )

            return job.id

        except Exception as e:
            job.fail(f"LangGraph execution failed: {str(e)}")
            self.job_repository.update(job)
            raise

    def _execute_with_message_coordination(
        self, workflow: Workflow, job: Job, agent_configs: List[Dict[str, Any]]
    ) -> str:
        """Execute workflow using message bus for simple agent coordination."""
        try:
            # Start job
            job.start()
            self.job_repository.update(job)

            # Publish coordination messages for each agent
            for agent_config in agent_configs:
                self._publish_agent_coordination_message(job, workflow, agent_config)

            return job.id

        except Exception as e:
            job.fail(f"Message coordination failed: {str(e)}")
            self.job_repository.update(job)
            raise

    def _create_langgraph_definition(
        self, workflow: Workflow, agent_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create LangGraph workflow definition from workflow and agent configs."""
        return {
            "workflow_id": workflow.id,
            "workflow_type": workflow.workflow_type.value,
            "workflow_definition": workflow.definition,
            "agents": agent_configs,
            "coordination_strategy": "langgraph",
            "created_at": datetime.now().isoformat(),
        }

    def _publish_langgraph_execution_message(
        self, job: Job, langgraph_workflow: Any, agent_configs: List[Dict[str, Any]]
    ) -> None:
        """Publish message to execute LangGraph workflow."""
        message = {
            "job_id": job.id,
            "workflow_id": job.workflow_id,
            "tenant_id": job.tenant_id,
            "execution_type": "langgraph",
            "langgraph_workflow": str(langgraph_workflow),  # Serialized workflow
            "agent_configs": agent_configs,
            "input_parameters": job.input_parameters,
            "timestamp": datetime.now().isoformat(),
        }

        self.message_bus.publish(
            topic="workflow.langgraph.execute",
            message=message,
            tenant_id=job.tenant_id,
            idempotency_key=f"langgraph_execute_{job.id}",
        )

    def _publish_agent_coordination_message(
        self, job: Job, workflow: Workflow, agent_config: Dict[str, Any]
    ) -> None:
        """Publish message for individual agent coordination."""
        message = {
            "job_id": job.id,
            "workflow_id": workflow.id,
            "tenant_id": job.tenant_id,
            "agent_config": agent_config,
            "workflow_definition": workflow.definition,
            "input_parameters": job.input_parameters,
            "coordination_type": "message_bus",
            "timestamp": datetime.now().isoformat(),
        }

        agent_type = agent_config.get("agent_type", "default")

        self.message_bus.publish(
            topic=f"agent.{agent_type}.coordinate",
            message=message,
            tenant_id=job.tenant_id,
            idempotency_key=f"agent_coordinate_{job.id}_{agent_type}",
        )


class DefaultLangGraphExecutor(LangGraphWorkflowExecutor):
    """Default implementation of LangGraph executor."""

    def create_langgraph_workflow(self, workflow_definition: Dict[str, Any]) -> Any:
        """Create a mock LangGraph workflow (in real implementation, use actual LangGraph)."""
        # This would create an actual LangGraph workflow in a real implementation
        return {
            "type": "langgraph_workflow",
            "definition": workflow_definition,
            "created_at": datetime.now().isoformat(),
        }

    def execute_langgraph_workflow(
        self, langgraph_workflow: Any, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a mock LangGraph workflow."""
        # This would execute an actual LangGraph workflow in a real implementation
        return {
            "status": "completed",
            "result": "Mock LangGraph execution completed",
            "workflow": langgraph_workflow,
            "input": input_data,
            "executed_at": datetime.now().isoformat(),
        }


class WorkflowAgentIntegrationService(AgentWorkflowIntegrationPort):
    """
    Service implementing agent-workflow integration following SOLID principles.

    This service acts as a facade, providing a simple interface for complex
    agent-workflow coordination operations.
    """

    def __init__(self, coordinator: WorkflowAgentCoordinator):
        """Initialize with coordinator following Dependency Inversion Principle."""
        self.coordinator = coordinator

    def execute_workflow_with_agents(
        self,
        workflow_id: str,
        tenant_id: str,
        agent_configs: List[Dict[str, Any]],
        input_parameters: Dict[str, Any] = None,
        created_by: str = "system",
    ) -> str:
        """Execute workflow with agent coordination."""
        return self.coordinator.execute_agent_coordinated_workflow(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            input_parameters=input_parameters or {},
            agent_configs=agent_configs,
            created_by=created_by,
        )

    def get_agent_workflow_status(self, job_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get status of agent-coordinated workflow execution."""
        # This would be implemented to get detailed status from job repository
        # and coordination services
        return {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "running",
            "coordination_type": "agent_coordinated",
            "last_updated": datetime.now().isoformat(),
        }
