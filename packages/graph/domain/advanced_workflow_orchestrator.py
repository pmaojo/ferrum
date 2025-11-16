"""Advanced workflow orchestration patterns for complex multi-agent scenarios."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass

from application.ports.messaging import MessageBusPort
from application.ports import TracingPort
from domain.entities import JobStatus
from domain.agent_coordinator import AgentCoordinator, CoordinationException

logger = logging.getLogger(__name__)


class WorkflowPattern(Enum):
    """Workflow execution patterns."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    MAP_REDUCE = "map_reduce"
    SAGA = "saga"  # For distributed transactions


@dataclass
class WorkflowStep:
    """Individual workflow step definition."""
    name: str
    agent_type: str
    action: str
    inputs: Dict[str, Any]
    outputs: List[str]
    timeout: Optional[timedelta] = None
    retry_count: int = 3
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    version: str
    pattern: WorkflowPattern
    steps: List[WorkflowStep]
    global_timeout: Optional[timedelta] = None
    rollback_strategy: Optional[str] = None


class AdvancedWorkflowOrchestrator:
    """Advanced workflow orchestration with complex patterns."""

    def __init__(
        self,
        agent_coordinator: AgentCoordinator,
        message_bus: MessageBusPort,
        tracer: Optional[TracingPort] = None
    ):
        self.agent_coordinator = agent_coordinator
        self.message_bus = message_bus
        self.tracer = tracer
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}

    def register_workflow_definition(self, workflow_def: WorkflowDefinition) -> None:
        """Register a reusable workflow definition."""
        self.workflow_definitions[workflow_def.name] = workflow_def
        logger.info(f"Registered workflow definition: {workflow_def.name} v{workflow_def.version}")

    async def execute_graphrag_research_workflow(
        self,
        *,
        research_query: str,
        knowledge_graphs: List[str],
        tenant_id: str,
        workflow_id: str,
        user_id: str
    ) -> str:
        """Execute a sophisticated GraphRAG research workflow."""

        # Define research workflow
        research_workflow = WorkflowDefinition(
            name="graphrag_research",
            version="1.0",
            pattern=WorkflowPattern.MAP_REDUCE,
            steps=[
                # Map phase: Query each KG in parallel
                WorkflowStep(
                    name="query_knowledge_graphs",
                    agent_type="graphrag_query_agent",
                    action="parallel_query",
                    inputs={
                        "query": research_query,
                        "knowledge_graphs": knowledge_graphs,
                        "tenant_id": tenant_id
                    },
                    outputs=["kg_results"],
                    timeout=timedelta(minutes=5)
                ),
                # Reduce phase: Synthesize results
                WorkflowStep(
                    name="synthesize_results",
                    agent_type="synthesis_agent",
                    action="synthesize",
                    inputs={"kg_results": "{{query_knowledge_graphs.kg_results}}"},
                    outputs=["synthesized_answer"],
                    timeout=timedelta(minutes=3)
                ),
                # Validation phase
                WorkflowStep(
                    name="validate_synthesis",
                    agent_type="validation_agent",
                    action="validate",
                    inputs={
                        "original_query": research_query,
                        "synthesis": "{{synthesize_results.synthesized_answer}}"
                    },
                    outputs=["validated_answer"],
                    conditions={"confidence_threshold": 0.8}
                )
            ],
            global_timeout=timedelta(minutes=10)
        )

        return await self._execute_workflow(research_workflow, workflow_id, tenant_id, user_id)

    async def execute_ontology_evolution_workflow(
        self,
        *,
        kg_id: str,
        new_documents: List[str],
        tenant_id: str,
        workflow_id: str
    ) -> str:
        """Execute ontology evolution workflow when new documents suggest schema changes."""

        evolution_workflow = WorkflowDefinition(
            name="ontology_evolution",
            version="1.0",
            pattern=WorkflowPattern.SAGA,  # Ensures rollback capability
            steps=[
                WorkflowStep(
                    name="analyze_new_entities",
                    agent_type="entity_extraction_agent",
                    action="extract_and_analyze",
                    inputs={
                        "documents": new_documents,
                        "kg_id": kg_id,
                        "tenant_id": tenant_id
                    },
                    outputs=["new_entities", "new_relationships"]
                ),
                WorkflowStep(
                    name="propose_schema_changes",
                    agent_type="ontology_agent",
                    action="propose_changes",
                    inputs={
                        "current_ontology": "{{kg_metadata.ontology}}",
                        "new_entities": "{{analyze_new_entities.new_entities}}",
                        "new_relationships": "{{analyze_new_entities.new_relationships}}"
                    },
                    outputs=["schema_proposal"]
                ),
                WorkflowStep(
                    name="validate_schema_compatibility",
                    agent_type="validation_agent",
                    action="validate_compatibility",
                    inputs={"schema_proposal": "{{propose_schema_changes.schema_proposal}}"},
                    outputs=["validation_result"],
                    conditions={"breaking_changes": False}
                ),
                WorkflowStep(
                    name="apply_schema_changes",
                    agent_type="schema_migration_agent",
                    action="migrate_schema",
                    inputs={
                        "kg_id": kg_id,
                        "schema_proposal": "{{propose_schema_changes.schema_proposal}}"
                    },
                    outputs=["migration_result"]
                )
            ],
            rollback_strategy="compensation"
        )

        return await self._execute_workflow(evolution_workflow, workflow_id, tenant_id)

    async def _execute_workflow(
        self,
        workflow_def: WorkflowDefinition,
        workflow_id: str,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """Execute a workflow according to its pattern."""

        workflow_context = {
            "workflow_id": workflow_id,
            "definition": workflow_def,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "status": JobStatus.RUNNING,
            "started_at": datetime.now(),
            "step_results": {},
            "current_step": 0
        }

        self.active_workflows[workflow_id] = workflow_context

        try:
            if workflow_def.pattern == WorkflowPattern.SEQUENTIAL:
                return await self._execute_sequential(workflow_context)
            elif workflow_def.pattern == WorkflowPattern.PARALLEL:
                return await self._execute_parallel(workflow_context)
            elif workflow_def.pattern == WorkflowPattern.MAP_REDUCE:
                return await self._execute_map_reduce(workflow_context)
            elif workflow_def.pattern == WorkflowPattern.SAGA:
                return await self._execute_saga(workflow_context)
            else:
                raise CoordinationException(
                    message=f"Unsupported workflow pattern: {workflow_def.pattern}",
                    error_code="UNSUPPORTED_PATTERN",
                    context={"pattern": workflow_def.pattern}
                )

        except Exception as e:
            workflow_context["status"] = JobStatus.FAILED
            workflow_context["error"] = str(e)
            raise
        finally:
            workflow_context["completed_at"] = datetime.now()

    async def _execute_sequential(self, context: Dict[str, Any]) -> str:
        """Execute steps sequentially."""
        workflow_def = context["definition"]

        for i, step in enumerate(workflow_def.steps):
            context["current_step"] = i

            # Resolve input variables from previous steps
            resolved_inputs = self._resolve_step_inputs(step.inputs, context["step_results"])

            # Execute step
            step_result = await self._execute_step(step, resolved_inputs, context)
            context["step_results"][step.name] = step_result

            # Check conditions if any
            if step.conditions and not self._evaluate_conditions(step.conditions, step_result):
                raise CoordinationException(
                    message=f"Step condition failed: {step.name}",
                    error_code="CONDITION_FAILED",
                    context={"step": step.name, "conditions": step.conditions}
                )

        return context["workflow_id"]

    async def _execute_map_reduce(self, context: Dict[str, Any]) -> str:
        """Execute map-reduce pattern for parallel processing."""
        workflow_def = context["definition"]

        # Find map and reduce steps
        map_steps = [s for s in workflow_def.steps if "map" in s.name.lower() or "parallel" in s.name.lower()]
        reduce_steps = [s for s in workflow_def.steps if "reduce" in s.name.lower() or "synthesize" in s.name.lower()]

        # Execute map phase in parallel
        map_results = []
        for step in map_steps:
            resolved_inputs = self._resolve_step_inputs(step.inputs, context["step_results"])
            result = await self._execute_step(step, resolved_inputs, context)
            map_results.append(result)
            context["step_results"][step.name] = result

        # Execute reduce phase
        for step in reduce_steps:
            resolved_inputs = self._resolve_step_inputs(step.inputs, context["step_results"])
            resolved_inputs["map_results"] = map_results
            result = await self._execute_step(step, resolved_inputs, context)
            context["step_results"][step.name] = result

        return context["workflow_id"]

    async def _execute_saga(self, context: Dict[str, Any]) -> str:
        """Execute SAGA pattern with compensation for rollback."""
        workflow_def = context["definition"]
        executed_steps = []

        try:
            for step in workflow_def.steps:
                resolved_inputs = self._resolve_step_inputs(step.inputs, context["step_results"])
                result = await self._execute_step(step, resolved_inputs, context)
                context["step_results"][step.name] = result
                executed_steps.append((step, result))

        except Exception as e:
            # Rollback executed steps in reverse order
            logger.warning(f"Workflow {context['workflow_id']} failed, initiating rollback")
            await self._rollback_saga_steps(executed_steps, context)
            raise

        return context["workflow_id"]

    async def _execute_step(
        self,
        step: WorkflowStep,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""

        # Create step execution message
        step_message = {
            "workflow_id": context["workflow_id"],
            "step_name": step.name,
            "agent_type": step.agent_type,
            "action": step.action,
            "inputs": inputs,
            "tenant_id": context["tenant_id"],
            "timeout": step.timeout.total_seconds() if step.timeout else 300
        }

        # Publish to agent-specific topic
        topic = f"agents.{step.agent_type}.{step.action}"
        self.message_bus.publish(
            topic=topic,
            message=step_message,
            tenant_id=context["tenant_id"]
        )

        # Wait for response (simplified - would use proper async messaging in production)
        # This would typically involve setting up a response handler and waiting
        return {"status": "completed", "result": f"Step {step.name} executed"}

    def _resolve_step_inputs(self, inputs: Dict[str, Any], step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve input variables from previous step results."""
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # Variable reference: {{step_name.output_key}}
                var_path = value[2:-2]
                parts = var_path.split(".")

                if len(parts) >= 2:
                    step_name = parts[0]
                    output_key = ".".join(parts[1:])

                    if step_name in step_results:
                        resolved[key] = step_results[step_name].get(output_key, value)
                    else:
                        resolved[key] = value
                else:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    def _evaluate_conditions(self, conditions: Dict[str, Any], step_result: Dict[str, Any]) -> bool:
        """Evaluate step conditions."""
        for condition_key, expected_value in conditions.items():
            actual_value = step_result.get(condition_key)

            if condition_key == "confidence_threshold":
                confidence = step_result.get("confidence", 0.0)
                if confidence < expected_value:
                    return False
            elif condition_key == "breaking_changes":
                has_breaking_changes = step_result.get("breaking_changes", True)
                if has_breaking_changes != expected_value:
                    return False
            elif actual_value != expected_value:
                return False

        return True

    async def _rollback_saga_steps(
        self,
        executed_steps: List[tuple],
        context: Dict[str, Any]
    ) -> None:
        """Rollback SAGA steps using compensation actions."""

        for step, result in reversed(executed_steps):
            try:
                # Execute compensation action
                compensation_message = {
                    "workflow_id": context["workflow_id"],
                    "step_name": f"rollback_{step.name}",
                    "agent_type": step.agent_type,
                    "action": f"rollback_{step.action}",
                    "inputs": {"original_result": result},
                    "tenant_id": context["tenant_id"]
                }

                topic = f"agents.{step.agent_type}.rollback"
                self.message_bus.publish(
                    topic=topic,
                    message=compensation_message,
                    tenant_id=context["tenant_id"]
                )

                logger.info(f"Rollback initiated for step: {step.name}")

            except Exception as rollback_error:
                logger.error(f"Rollback failed for step {step.name}: {rollback_error}")
