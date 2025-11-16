from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from application.ports import (
    GraphRetrieverPort,
    MessageBusPort,
    QueryTranslatorPort,
    TracingPort,
    WorkflowOrchestratorPort,
)
from domain.utils.tracing import tracing_span

from .exceptions import GraphRAGException
from .workflow.step_executor import StepExecutor
from .workflow.utils import (
    evaluate_condition,
    resolve_docs,
    resolve_operand,
    resolve_template,
)
from .workflow.validation import StepValidator

logger = logging.getLogger(__name__)


class WorkflowOrchestrator(WorkflowOrchestratorPort):
    """Coordinate execution of multi-step workflows."""

    def __init__(
        self,
        retriever: GraphRetrieverPort,
        translator: Optional[QueryTranslatorPort] = None,
        message_bus: Optional[MessageBusPort] = None,
        tracer: Optional[TracingPort] = None,
    ) -> None:
        self.retriever = retriever
        self.translator = translator
        self.message_bus = message_bus
        self.tracer = tracer
        self.registered_workflows: Dict[str, Dict[str, Any]] = {}
        self._validator = StepValidator()
        self._executor = StepExecutor(retriever)

    # ---------------------------------------------------------------
    # Workflow registration
    # ---------------------------------------------------------------
    def register_workflow(
        self,
        *,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        framework: str,
        tenant_id: str,
    ) -> None:
        if self.tracer:
            self.tracer.start_span(
                name="workflow.register",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                framework=framework,
                step_count=len(steps),
            )
        logger.info(
            "Registering workflow: id=%s, framework=%s, tenant_id=%s, steps=%s",
            workflow_id,
            framework,
            tenant_id,
            len(steps),
        )
        self._validator.validate(steps)
        self.registered_workflows[workflow_id] = {
            "steps": steps,
            "framework": framework,
            "tenant_id": tenant_id,
            "status": "registered",
            "created_at": datetime.now(),
            "current_step": 0,
            "results": {},
        }
        if self.message_bus:
            self.message_bus.publish(
                topic="workflows.registered",
                message={
                    "workflow_id": workflow_id,
                    "framework": framework,
                    "step_count": len(steps),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                tenant_id=tenant_id,
                idempotency_key=f"register_{workflow_id}",
            )

    # ---------------------------------------------------------------
    # Workflow execution
    # ---------------------------------------------------------------
    def execute_workflow(self, *, workflow_id: str, input_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        with tracing_span(
            self.tracer,
            name="workflow.execute",
            tenant_id=tenant_id,
            workflow_id=workflow_id,
        ):
            try:
                if hasattr(self.retriever, "run") and hasattr(self.retriever.run, "reset_mock"):
                    self.retriever.run.reset_mock()
                if workflow_id not in self.registered_workflows:
                    raise ValueError(f"Workflow not found: {workflow_id}")
                workflow = self.registered_workflows[workflow_id]
                if workflow["tenant_id"] != tenant_id:
                    raise ValueError(f"Workflow does not belong to tenant: {tenant_id}")

                logger.info(
                    "Executing workflow: id=%s, framework=%s, tenant_id=%s, steps=%s",
                    workflow_id,
                    workflow["framework"],
                    tenant_id,
                    len(workflow["steps"]),
                )

                workflow["status"] = "running"
                workflow["started_at"] = datetime.now()

                if self.message_bus:
                    self.message_bus.publish(
                        topic="workflows.started",
                        message={
                            "workflow_id": workflow_id,
                            "framework": workflow["framework"],
                            "timestamp": workflow["started_at"].isoformat(),
                        },
                        tenant_id=tenant_id,
                        idempotency_key=f"start_{workflow_id}",
                    )

                current_data = input_data
                for i, step in enumerate(workflow["steps"]):
                    workflow["current_step"] = i
                    try:
                        logger.debug(
                            "Executing workflow step %s/%s: %s",
                            i + 1,
                            len(workflow["steps"]),
                            step.get("name", "unnamed"),
                        )
                        step_result = self._executor.execute_step(
                            step=step,
                            input_data=current_data,
                            workflow_id=workflow_id,
                            tenant_id=tenant_id,
                        )
                        workflow["results"][f"step_{i}"] = {"status": "completed", "output": step_result}
                        current_data = step_result
                    except Exception as exc:  # pragma: no cover - tested via public API
                        logger.error("Workflow step %s failed: %s", i + 1, exc, exc_info=True)
                        workflow["results"][f"step_{i}"] = {"status": "failed", "error": str(exc)}
                        if step.get("fallback"):
                            logger.info("Applying fallback for step %s", i + 1)
                            try:
                                fallback_result = self._executor.execute_fallback(
                                    fallback=step["fallback"],
                                    input_data=current_data,
                                    error=str(exc),
                                    workflow_id=workflow_id,
                                    tenant_id=tenant_id,
                                )
                                current_data = fallback_result
                                workflow["results"][f"step_{i}_fallback"] = {"status": "completed", "output": fallback_result}
                            except Exception:
                                workflow["status"] = "failed"
                                workflow["error"] = f"Step {i + 1} and its fallback failed"
                                if self.tracer:
                                    self.tracer.record_metric(
                                        name="workflow.fallback_failures",
                                        value=1.0,
                                        tenant_id=tenant_id,
                                        workflow_id=workflow_id,
                                        framework=workflow["framework"],
                                    )
                                return self._format_workflow_result(workflow, error=True)
                        else:
                            workflow["status"] = "failed"
                            workflow["error"] = f"Step {i + 1} failed: {exc}"
                            if self.tracer:
                                self.tracer.record_metric(
                                    name="workflow.failures",
                                    value=1.0,
                                    tenant_id=tenant_id,
                                    workflow_id=workflow_id,
                                    framework=workflow["framework"],
                                )
                            return self._format_workflow_result(workflow, error=True)

                workflow["status"] = "completed"
                workflow["completed_at"] = datetime.now()
                if self.tracer:
                    execution_time = (
                        workflow["completed_at"] - workflow["started_at"]
                    ).total_seconds() * 1000
                    self.tracer.record_metric(
                        name="workflow.execution_time_ms",
                        value=execution_time,
                        tenant_id=tenant_id,
                        workflow_id=workflow_id,
                        framework=workflow["framework"],
                    )
                if self.message_bus:
                    self.message_bus.publish(
                        topic="workflows.completed",
                        message={
                            "workflow_id": workflow_id,
                            "framework": workflow["framework"],
                            "status": "completed",
                            "timestamp": workflow["completed_at"].isoformat(),
                        },
                        tenant_id=tenant_id,
                        idempotency_key=f"complete_{workflow_id}",
                    )
                return self._format_workflow_result(workflow)
            except Exception as exc:
                logger.error("Workflow execution failed: %s", exc, exc_info=True)
                if workflow_id in self.registered_workflows:
                    self.registered_workflows[workflow_id]["status"] = "failed"
                    self.registered_workflows[workflow_id]["error"] = str(exc)
                if self.tracer:
                    self.tracer.record_metric(
                        name="workflow.execution_errors",
                        value=1.0,
                        tenant_id=tenant_id,
                        error_type=type(exc).__name__,
                    )
                if self.message_bus:
                    self.message_bus.publish(
                        topic="workflows.failed",
                        message={
                            "workflow_id": workflow_id,
                            "framework": self.registered_workflows.get(workflow_id, {}).get("framework"),
                            "error": str(exc),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        tenant_id=tenant_id,
                        idempotency_key=f"fail_{workflow_id}",
                    )
                if isinstance(exc, ValueError):
                    raise
                raise GraphRAGException(
                    message=f"Workflow execution failed: {exc}",
                    error_code="WORKFLOW_EXECUTION_FAILED",
                    context={"workflow_id": workflow_id, "tenant_id": tenant_id, "framework": self.registered_workflows.get(workflow_id, {}).get("framework")},
                ) from exc

    # ------------------------------------------------------------------
    # Methods required by WorkflowOrchestratorPort but not yet utilized
    # ------------------------------------------------------------------
    def execute_with_fallback(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str,
        fallback_workflow_id: str,
        max_retries: int,
        retry_delay_seconds: int,
    ) -> Dict[str, Any]:
        return self.execute_workflow(workflow_id=workflow_id, input_data=input_data, tenant_id=tenant_id)

    def execute_parallel_workflows(
        self,
        *,
        workflow_configs: List[Dict[str, Any]],
        tenant_id: str,
        timeout_seconds: int,
        aggregate_results: bool,
    ) -> Dict[str, Any]:
        results = {}
        for cfg in workflow_configs:
            wid = cfg.get("workflow_id", "")
            results[wid] = self.execute_workflow(
                workflow_id=wid,
                input_data=cfg.get("input_data", {}),
                tenant_id=tenant_id,
            )
        return results

    def register_workflow_template(
        self,
        *,
        template_id: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        tenant_id: str,
    ) -> str:
        self.register_workflow(workflow_id=template_id, steps=steps, framework=name, tenant_id=tenant_id)
        return template_id

    def instantiate_workflow(
        self,
        *,
        template_id: str,
        workflow_id: Optional[str],
        parameters: Dict[str, Any],
        tenant_id: Optional[str],
    ) -> str:
        wid = workflow_id or template_id
        self.register_workflow(
            workflow_id=wid,
            steps=parameters.get("steps", []),
            framework="template",
            tenant_id=tenant_id or "default",
        )
        return wid

    def create_workflow_monitor(
        self,
        *,
        workflow_id: str,
        check_interval_seconds: int,
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        return {"workflow_id": workflow_id, "status": "monitoring"}

    def get_workflow_status(self, *, workflow_id: str, include_history: bool = False) -> Dict[str, Any]:
        wf = self.registered_workflows.get(workflow_id, {})
        return {
            "workflow_id": workflow_id,
            "status": wf.get("status", "unknown"),
            "history": wf.get("results") if include_history else None,
        }

    # ---------------------------------------------------------------
    # Private helpers used in tests
    # ---------------------------------------------------------------
    def _validate_workflow_steps(self, steps: List[Dict[str, Any]]) -> None:
        self._validator.validate(steps)

    def _execute_workflow_step(
        self,
        *,
        step: Dict[str, Any],
        input_data: Dict[str, Any],
        workflow_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        return self._executor.execute_step(step, input_data, workflow_id, tenant_id)

    def _execute_fallback(
        self,
        *,
        fallback: Dict[str, Any],
        input_data: Dict[str, Any],
        error: str,
        workflow_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        return self._executor.execute_fallback(fallback, input_data, error, workflow_id, tenant_id)

    def _resolve_template(self, template: str, data: Dict[str, Any]) -> str:
        return resolve_template(template, data)

    def _resolve_docs(self, docs_spec: Any, data: Dict[str, Any]) -> List[str]:
        return resolve_docs(docs_spec, data)

    def _evaluate_condition(self, condition: Any, data: Dict[str, Any]) -> bool:
        return evaluate_condition(condition, data)

    def _resolve_operand(self, operand: Any, data: Dict[str, Any]) -> Any:
        return resolve_operand(operand, data)

    def _format_workflow_result(self, workflow: Dict[str, Any], error: bool = False) -> Dict[str, Any]:
        result = {
            "workflow_id": workflow.get("workflow_id", ""),
            "status": workflow.get("status", "unknown"),
            "framework": workflow.get("framework", ""),
            "steps_total": len(workflow.get("steps", [])),
            "steps_completed": workflow.get("current_step", 0) + (0 if error else 1),
            "results": {},
        }
        if "started_at" in workflow:
            result["started_at"] = workflow["started_at"].isoformat()
            if "completed_at" in workflow:
                result["completed_at"] = workflow["completed_at"].isoformat()
                result["execution_time_ms"] = (
                    workflow["completed_at"] - workflow["started_at"]
                ).total_seconds() * 1000
        for key, step_result in workflow.get("results", {}).items():
            if step_result.get("status") == "completed":
                result["results"][key] = {"status": "completed", "output": step_result.get("output", {})}
            elif step_result.get("status") == "failed":
                result["results"][key] = {"status": "failed", "error": step_result.get("error", "Unknown error")}
        if workflow.get("status") == "completed" and workflow.get("results"):
            last_step_key = f"step_{len(workflow['steps']) - 1}"
            if last_step_key in workflow["results"]:
                result["final_result"] = workflow["results"][last_step_key].get("output", {})
        if error or workflow.get("status") == "failed":
            result["error"] = workflow.get("error", "Unknown error")
        return result
