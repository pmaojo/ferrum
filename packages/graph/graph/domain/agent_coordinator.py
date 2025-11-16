from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from application.ports.messaging import MessageBusPort
from .entities import JobStatus
from .exceptions import ValidationError
from application.ports import TracingPort

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Domain service for coordinating multi-agent workflows with message passing.

    Orchestrates communication and coordination between different agents in the
    system using a message bus, with support for idempotent operations and
    distributed tracing.
    """

    def __init__(
        self, message_bus: MessageBusPort, tracer: Optional[TracingPort] = None
    ):
        """Initialize AgentCoordinator with port dependencies.

        Args:
            message_bus: Message bus port for agent communication
            tracer: Optional tracing port for observability
        """
        self.message_bus = message_bus
        self.tracer = tracer
        self.registered_handlers = {}

    def coordinate_ingestion_workflow(
        self,
        *,
        document_ids: List[str],
        kg_id: str,
        tenant_id: str,
        workflow_id: str,
        ontology_version_id: str,
        callback_topic: Optional[str] = None,
    ) -> str:
        """Coordinate document ingestion workflow across multiple agents.

        Initiates and coordinates the document ingestion workflow by publishing
        messages to appropriate topics and handling responses.

        Args:
            document_ids: List of document IDs to process
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            workflow_id: Unique workflow identifier for tracking
            ontology_version_id: Ontology version for validation
            callback_topic: Optional topic for workflow completion notification

        Returns:
            Workflow tracking ID for status monitoring

        Raises:
            CoordinationException: When workflow coordination fails

        Requirements addressed:
            - 3.1: Multi-agent coordination
            - 3.2: Asynchronous workflow management
            - 8.1: Idempotent operations
        """
        span_context = {}
        if self.tracer:
            span = self.tracer.start_span(
                name="coordinator.ingestion_workflow",
                tenant_id=tenant_id,
                kg_id=kg_id,
                workflow_id=workflow_id,
                document_count=len(document_ids),
            )
            span_context["span"] = span

        try:
            logger.info(
                f"Starting ingestion workflow: workflow_id={workflow_id}, "
                f"kg_id={kg_id}, tenant_id={tenant_id}, document_count={len(document_ids)}"
            )

            # Create workflow context with all necessary information
            workflow_context = {
                "workflow_id": workflow_id,
                "workflow_type": "document_ingestion",
                "document_ids": document_ids,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "ontology_version_id": ontology_version_id,
                "status": JobStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "steps": [
                    {"name": "document_retrieval", "status": JobStatus.PENDING},
                    {"name": "entity_extraction", "status": JobStatus.PENDING},
                    {"name": "ontology_validation", "status": JobStatus.PENDING},
                    {"name": "knowledge_graph_update", "status": JobStatus.PENDING},
                ],
            }

            if callback_topic:
                workflow_context["callback_topic"] = callback_topic

            # Publish initial message to start the workflow
            self.message_bus.publish(
                topic="workflows.ingestion.start",
                message=workflow_context,
                idempotency_key=workflow_id,  # Prevent duplicate workflows
                tenant_id=tenant_id,
            )

            logger.info(f"Ingestion workflow initiated: workflow_id={workflow_id}")

            # Record workflow initiation metric
            if self.tracer:
                self.tracer.record_metric(
                    name="coordinator.workflows_initiated",
                    value=1.0,
                    tenant_id=tenant_id,
                    workflow_type="document_ingestion",
                )

            return workflow_id

        except Exception as e:
            logger.error(
                f"Failed to coordinate ingestion workflow: {str(e)}", exc_info=True
            )

            if self.tracer:
                self.tracer.record_metric(
                    name="coordinator.workflow_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise CoordinationException(
                message=f"Failed to coordinate ingestion workflow: {str(e)}",
                error_code="COORDINATION_FAILED",
                context={
                    "workflow_id": workflow_id,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "document_count": len(document_ids),
                },
            ) from e

        finally:
            if span_context.get("span") and hasattr(span_context["span"], "end"):
                span_context["span"].end()

    def coordinate_query_workflow(
        self,
        *,
        question: str,
        kg_id: str,
        tenant_id: str,
        user_id: str,
        workflow_id: str,
        callback_topic: Optional[str] = None,
        query_opts: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Coordinate natural language query workflow across multiple agents.

        Initiates and coordinates the query processing workflow by publishing
        messages to appropriate topics and handling responses.

        Args:
            question: Natural language query
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            user_id: User identifier for query tracking
            workflow_id: Unique workflow identifier for tracking
            callback_topic: Optional topic for workflow completion notification
            query_opts: Optional query execution parameters

        Returns:
            Workflow tracking ID for status monitoring

        Raises:
            CoordinationException: When workflow coordination fails

        Requirements addressed:
            - 3.1: Multi-agent coordination
            - 3.2: Asynchronous workflow management
            - 8.1: Idempotent operations
        """
        span_context = {}
        if self.tracer:
            span = self.tracer.start_span(
                name="coordinator.query_workflow",
                tenant_id=tenant_id,
                kg_id=kg_id,
                workflow_id=workflow_id,
                user_id=user_id,
            )
            span_context["span"] = span

        try:
            logger.info(
                f"Starting query workflow: workflow_id={workflow_id}, "
                f"kg_id={kg_id}, tenant_id={tenant_id}, user_id={user_id}"
            )

            # Create workflow context with all necessary information
            workflow_context = {
                "workflow_id": workflow_id,
                "workflow_type": "natural_language_query",
                "question": question,
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "status": JobStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "steps": [
                    {"name": "query_translation", "status": JobStatus.PENDING},
                    {"name": "query_execution", "status": JobStatus.PENDING},
                    {"name": "result_formatting", "status": JobStatus.PENDING},
                ],
                "query_opts": query_opts or {},
            }

            if callback_topic:
                workflow_context["callback_topic"] = callback_topic

            # Publish initial message to start the workflow
            self.message_bus.publish(
                topic="workflows.query.start",
                message=workflow_context,
                idempotency_key=workflow_id,  # Prevent duplicate workflows
                tenant_id=tenant_id,
            )

            logger.info(f"Query workflow initiated: workflow_id={workflow_id}")

            # Record workflow initiation metric
            if self.tracer:
                self.tracer.record_metric(
                    name="coordinator.workflows_initiated",
                    value=1.0,
                    tenant_id=tenant_id,
                    workflow_type="natural_language_query",
                )

            return workflow_id

        except Exception as e:
            logger.error(
                f"Failed to coordinate query workflow: {str(e)}", exc_info=True
            )

            if self.tracer:
                self.tracer.record_metric(
                    name="coordinator.workflow_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise CoordinationException(
                message=f"Failed to coordinate query workflow: {str(e)}",
                error_code="COORDINATION_FAILED",
                context={
                    "workflow_id": workflow_id,
                    "kg_id": kg_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            ) from e

        finally:
            if span_context.get("span") and hasattr(span_context["span"], "end"):
                span_context["span"].end()

    def register_workflow_handler(
        self, *, topic: str, handler: Callable[[Dict[str, Any]], None], tenant_id: str
    ) -> None:
        """Register handler for workflow messages with tenant isolation.

        Registers a callback function to handle messages on a specific topic
        with tenant-based filtering for multi-tenant isolation.

        Args:
            topic: Message topic to subscribe to
            handler: Callback function for message processing
            tenant_id: Tenant identifier for filtering messages

        Raises:
            ValidationError: When handler is invalid

        Requirements addressed:
            - 3.3: Event-driven architecture
            - 8.2: Multi-tenant isolation
        """
        try:
            logger.info(
                f"Registering workflow handler for topic={topic}, tenant_id={tenant_id}"
            )

            # Register with message bus first to ensure it works
            self.message_bus.subscribe(
                topic=topic, handler=handler, tenant_id=tenant_id
            )

            # Only store handler reference after successful registration
            handler_key = f"{topic}:{tenant_id}"
            self.registered_handlers[handler_key] = handler

            logger.info(f"Handler registered successfully for topic={topic}")

        except Exception as e:
            logger.error(
                f"Failed to register workflow handler: {str(e)}", exc_info=True
            )
            raise ValueError(f"Failed to register workflow handler: {str(e)}") from e

    def update_workflow_status(
        self,
        *,
        workflow_id: str,
        step_name: str,
        status: JobStatus,
        tenant_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update workflow step status with progress tracking.

        Updates the status of a specific workflow step and publishes
        a status update message for workflow monitoring.

        Args:
            workflow_id: Workflow identifier
            step_name: Name of the workflow step to update
            status: New status value as ``JobStatus``
            tenant_id: Tenant identifier for multi-tenant isolation
            result: Optional result data for completed steps

        Raises:
            ValidationError: When parameters are invalid

        Requirements addressed:
            - 3.2: Workflow status tracking
            - 3.3: Event-driven architecture
        """
        try:
            logger.info(
                f"Updating workflow status: workflow_id={workflow_id}, "
                f"step={step_name}, status={status}"
            )

            # Validate status value
            valid_statuses = set(JobStatus)
            if status not in valid_statuses:
                raise ValueError(
                    f"Invalid status: {status}. Must be one of {list(valid_statuses)}"
                )

            # Create status update message
            status_update = {
                "workflow_id": workflow_id,
                "step_name": step_name,
                "status": status,
                "updated_at": datetime.now().isoformat(),
                "tenant_id": tenant_id,
            }

            if result:
                status_update["result"] = result

            # Publish status update message
            self.message_bus.publish(
                topic=f"workflows.status.{workflow_id}",
                message=status_update,
                tenant_id=tenant_id,
            )

            # Also publish to general status topic for monitoring
            self.message_bus.publish(
                topic="workflows.status.updates",
                message=status_update,
                tenant_id=tenant_id,
            )

            logger.info(
                f"Workflow status updated: workflow_id={workflow_id}, step={step_name}"
            )

            # Record metric for workflow step completion
            if self.tracer and status == JobStatus.COMPLETED:
                self.tracer.record_metric(
                    name="coordinator.workflow_steps_completed",
                    value=1.0,
                    tenant_id=tenant_id,
                    step_name=step_name,
                )

        except Exception as e:
            logger.error(f"Failed to update workflow status: {str(e)}", exc_info=True)

            if self.tracer:
                self.tracer.record_metric(
                    name="coordinator.status_update_errors",
                    value=1.0,
                    tenant_id=tenant_id,
                    error_type=type(e).__name__,
                )

            raise ValueError(f"Failed to update workflow status: {str(e)}") from e


class CoordinationException(Exception):
    """Exception for agent coordination failures."""

    def __init__(self, message: str, error_code: str, context: Dict[str, Any]):
        self.message = message
        self.error_code = error_code
        self.context = context
