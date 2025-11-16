"""FalkorDB GraphRAG SDK Agent Coordinator integration."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from application.ports import MessageBusPort, TracingPort
from domain.entities import JobStatus
from domain.exceptions import ValidationError
from adapters.retrievers.falkordb_graphrag_sdk_adapter import FalkorDBGraphRAGAdapter

logger = logging.getLogger(__name__)


class FalkorDBAgentCoordinator:
    """Agent coordinator using FalkorDB GraphRAG SDK for multi-agent workflows."""

    def __init__(
        self,
        falkordb_adapter: FalkorDBGraphRAGAdapter,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        """Initialize FalkorDB agent coordinator.

        Args:
            falkordb_adapter: FalkorDB GraphRAG SDK adapter
            message_bus: Message bus for agent communication
            tracer: Optional tracing port for observability
        """
        self.falkordb_adapter = falkordb_adapter
        self.message_bus = message_bus
        self.tracer = tracer
        self.active_workflows: Dict[str, Dict[str, Any]] = {}

        # Subscribe to workflow messages
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers for agent coordination."""
        try:
            # Subscribe to agent workflow requests
            self.message_bus.subscribe(
                topic="falkordb.agents.workflow.start",
                handler=self._handle_workflow_start,
                tenant_id="*"
            )

            # Subscribe to agent query requests
            self.message_bus.subscribe(
                topic="falkordb.agents.query",
                handler=self._handle_agent_query,
                tenant_id="*"
            )

            # Subscribe to orchestrator requests
            self.message_bus.subscribe(
                topic="falkordb.orchestrator.query",
                handler=self._handle_orchestrator_query,
                tenant_id="*"
            )

            logger.info("FalkorDB agent coordinator message handlers registered")

        except Exception as e:
            logger.error(f"Failed to set up message handlers: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to set up message handlers: {str(e)}")

    def create_specialized_agents_workflow(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        agent_configs: List[Dict[str, Any]],
        initial_docs: Optional[List[str]] = None,
        orchestrator_backstory: Optional[str] = None
    ) -> str:
        """Create a workflow with specialized agents for different domains.

        Args:
            tenant_id: Tenant identifier
            workflow_id: Unique workflow identifier
            agent_configs: List of agent configurations with kg_id and specialization
            initial_docs: Optional documents to index for each agent
            orchestrator_backstory: Custom backstory for the orchestrator

        Returns:
            Workflow ID for tracking
        """
        try:
            if self.tracer:
                self.tracer.start_span(
                    name="falkordb_coordinator.create_workflow",
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    agent_count=len(agent_configs)
                )

            logger.info(
                f"Creating specialized agents workflow: workflow_id={workflow_id}, "
                f"tenant_id={tenant_id}, agents={len(agent_configs)}"
            )

            # Create workflow tracking
            self.active_workflows[workflow_id] = {
                "tenant_id": tenant_id,
                "status": JobStatus.PENDING,
                "created_at": datetime.now(),
                "agent_configs": agent_configs,
                "steps": []
            }

            # Step 1: Index documents for each agent (if provided)
            if initial_docs:
                for i, config in enumerate(agent_configs):
                    kg_id = config.get("kg_id", f"agent_kg_{i}")

                    try:
                        self.falkordb_adapter.index(
                            docs=initial_docs,
                            kg_id=kg_id,
                            tenant_id=tenant_id
                        )

                        self.active_workflows[workflow_id]["steps"].append({
                            "name": f"index_documents_agent_{i}",
                            "status": JobStatus.COMPLETED,
                            "agent_kg_id": kg_id
                        })

                    except Exception as e:
                        logger.error(f"Failed to index documents for agent {kg_id}: {e}")
                        self.active_workflows[workflow_id]["steps"].append({
                            "name": f"index_documents_agent_{i}",
                            "status": JobStatus.FAILED,
                            "error": str(e)
                        })

            # Step 2: Create multi-agent orchestrator
            backstory = orchestrator_backstory or (
                f"You are a smart orchestrator managing {len(agent_configs)} specialized "
                "knowledge graph agents. Each agent has expertise in different domains. "
                "Coordinate between agents to provide comprehensive and accurate answers."
            )

            orchestrator_id = self.falkordb_adapter.create_multi_agent_orchestrator(
                tenant_id=tenant_id,
                agent_configs=agent_configs,
                backstory=backstory
            )

            self.active_workflows[workflow_id]["orchestrator_id"] = orchestrator_id
            self.active_workflows[workflow_id]["status"] = JobStatus.COMPLETED
            self.active_workflows[workflow_id]["steps"].append({
                "name": "create_orchestrator",
                "status": JobStatus.COMPLETED,
                "orchestrator_id": orchestrator_id
            })

            # Publish workflow completion event
            self.message_bus.publish(
                topic="falkordb.agents.workflow.completed",
                message={
                    "workflow_id": workflow_id,
                    "tenant_id": tenant_id,
                    "orchestrator_id": orchestrator_id,
                    "agent_count": len(agent_configs),
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"workflow_complete_{workflow_id}"
            )

            logger.info(f"Specialized agents workflow created successfully: {workflow_id}")
            return workflow_id

        except Exception as e:
            logger.error(f"Failed to create workflow: {str(e)}", exc_info=True)

            # Update workflow status
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = JobStatus.FAILED
                self.active_workflows[workflow_id]["error"] = str(e)

            # Publish error event
            self.message_bus.publish(
                topic="falkordb.agents.workflow.failed",
                message={
                    "workflow_id": workflow_id,
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"workflow_error_{workflow_id}"
            )

            raise

    def query_orchestrated_agents(
        self,
        *,
        tenant_id: str,
        question: str,
        workflow_id: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the orchestrated multi-agent system.

        Args:
            tenant_id: Tenant identifier
            question: Natural language query
            workflow_id: Optional workflow ID to use specific orchestrator
            opts: Optional query parameters

        Returns:
            Orchestrated response from multiple agents
        """
        try:
            if self.tracer:
                self.tracer.start_span(
                    name="falkordb_coordinator.query_orchestrated",
                    tenant_id=tenant_id,
                    question=question[:100],
                    workflow_id=workflow_id
                )

            logger.info(f"Querying orchestrated agents for tenant: {tenant_id}")

            # Use FalkorDB SDK orchestrator
            response = self.falkordb_adapter.query_orchestrator(
                tenant_id=tenant_id,
                question=question,
                opts=opts
            )

            # Add workflow context if available
            if workflow_id and workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                response["workflow_context"] = {
                    "workflow_id": workflow_id,
                    "agent_count": len(workflow.get("agent_configs", [])),
                    "created_at": workflow.get("created_at", "").isoformat() if workflow.get("created_at") else None
                }

            # Publish query event
            self.message_bus.publish(
                topic="falkordb.agents.query.completed",
                message={
                    "tenant_id": tenant_id,
                    "question": question,
                    "workflow_id": workflow_id,
                    "response_length": len(str(response.get("answer", ""))),
                    "agents_used": response.get("agents_used", []),
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"query_{tenant_id}_{hash(question)}"
            )

            return response

        except Exception as e:
            logger.error(f"Orchestrated query failed: {str(e)}", exc_info=True)

            # Publish error event
            self.message_bus.publish(
                topic="falkordb.agents.query.failed",
                message={
                    "tenant_id": tenant_id,
                    "question": question,
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"query_error_{tenant_id}_{hash(question)}"
            )

            raise

    def _handle_workflow_start(self, message: Dict[str, Any]) -> None:
        """Handle workflow start messages."""
        try:
            workflow_id = message.get("workflow_id")
            tenant_id = message.get("tenant_id")
            agent_configs = message.get("agent_configs", [])
            initial_docs = message.get("initial_docs")
            orchestrator_backstory = message.get("orchestrator_backstory")

            if not workflow_id or not tenant_id:
                logger.warning("Invalid workflow start message")
                return

            self.create_specialized_agents_workflow(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                agent_configs=agent_configs,
                initial_docs=initial_docs,
                orchestrator_backstory=orchestrator_backstory
            )

        except Exception as e:
            logger.error(f"Error handling workflow start: {str(e)}", exc_info=True)

    def _handle_agent_query(self, message: Dict[str, Any]) -> None:
        """Handle individual agent query messages."""
        try:
            tenant_id = message.get("tenant_id")
            kg_id = message.get("kg_id", "default")
            question = message.get("question")
            response_topic = message.get("response_topic")
            query_id = message.get("query_id")

            if not all([tenant_id, question, response_topic]):
                logger.warning("Invalid agent query message")
                return

            # Query individual agent
            result = self.falkordb_adapter.run(
                question=question,
                kg_id=kg_id,
                tenant_id=tenant_id,
                opts=message.get("opts", {})
            )

            # Send response
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "query_id": query_id,
                    "tenant_id": tenant_id,
                    "kg_id": kg_id,
                    "question": question,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"response_{query_id}"
            )

        except Exception as e:
            logger.error(f"Error handling agent query: {str(e)}", exc_info=True)

    def _handle_orchestrator_query(self, message: Dict[str, Any]) -> None:
        """Handle orchestrator query messages."""
        try:
            tenant_id = message.get("tenant_id")
            question = message.get("question")
            response_topic = message.get("response_topic")
            query_id = message.get("query_id")
            workflow_id = message.get("workflow_id")

            if not all([tenant_id, question, response_topic]):
                logger.warning("Invalid orchestrator query message")
                return

            # Query orchestrator
            result = self.query_orchestrated_agents(
                tenant_id=tenant_id,
                question=question,
                workflow_id=workflow_id,
                opts=message.get("opts", {})
            )

            # Send response
            self.message_bus.publish(
                topic=response_topic,
                message={
                    "query_id": query_id,
                    "tenant_id": tenant_id,
                    "question": question,
                    "result": result,
                    "workflow_id": workflow_id,
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=tenant_id,
                idempotency_key=f"orchestrator_response_{query_id}"
            )

        except Exception as e:
            logger.error(f"Error handling orchestrator query: {str(e)}", exc_info=True)

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a workflow."""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self.active_workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "status": workflow.get("status"),
            "tenant_id": workflow.get("tenant_id"),
            "created_at": workflow.get("created_at", "").isoformat() if workflow.get("created_at") else None,
            "orchestrator_id": workflow.get("orchestrator_id"),
            "agent_count": len(workflow.get("agent_configs", [])),
            "steps": workflow.get("steps", []),
            "error": workflow.get("error")
        }
