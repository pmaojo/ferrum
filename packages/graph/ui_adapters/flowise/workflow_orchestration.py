"""
Workflow orchestration for Flowise AI framework integration.

This module provides workflow orchestration capabilities for the Flowise AI
framework, enabling complex pipelines with error handling and fallback mechanisms.
It also supports workflow export and versioning through Git integration.

Requirements:
- 3.1: Integrate with WorkflowOrchestrator for complex pipelines
- 3.4: Serialize to YAML compatible with both frameworks
- 3.6: Add error handling and fallback mechanisms
- 4.4: Integrate version in Git tags and activate rollback
"""

import logging
import json
import os
import time
import traceback
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
import asyncio
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

from domain.services import WorkflowOrchestrator
from domain.entities import Triple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlowiseWorkflowOrchestrator:
    """Workflow orchestration for Flowise AI framework integration.

    This class provides enhanced workflow orchestration capabilities for
    Flowise AI, including complex pipeline management, error handling,
    and fallback mechanisms.

    Features:
    - Template-based workflow management
    - Parameter substitution for workflow customization
    - Synchronous and asynchronous execution
    - Comprehensive error handling with fallback mechanisms
    - Execution history tracking and monitoring
    - Multi-tenant isolation
    """

    def __init__(
        self,
        workflow_orchestrator: WorkflowOrchestrator,
        default_tenant_id: str = "default"
    ):
        """Initialize Flowise workflow orchestrator.

        Args:
            workflow_orchestrator: Domain service for workflow orchestration
            default_tenant_id: Default tenant ID
        """
        self.workflow_orchestrator = workflow_orchestrator
        self.default_tenant_id = default_tenant_id
        self.workflow_templates = {}
        self.active_workflows = {}
        self.workflow_history = {}

    def register_workflow_template(
        self,
        *,
        template_id: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> str:
        """Register a workflow template for reuse.

        Args:
            template_id: Unique identifier for the template
            name: Human-readable name for the template
            description: Description of the template's purpose
            steps: List of workflow steps with their configurations
            input_schema: JSON schema for template inputs
            output_schema: JSON schema for template outputs
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Template ID for future reference

        Raises:
            ValueError: When template registration fails
        """
        try:
            # Validate steps
            self._validate_workflow_steps(steps)

            # Store template
            self.workflow_templates[template_id] = {
                "id": template_id,
                "name": name,
                "description": description,
                "steps": steps,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "tenant_id": tenant_id or self.default_tenant_id,
                "created_at": datetime.now().isoformat()
            }

            logger.info(f"Registered workflow template: id={template_id}, name={name}")
            return template_id

        except Exception as e:
            logger.error(f"Failed to register workflow template: {str(e)}", exc_info=True)
            raise ValueError(f"Template registration failed: {str(e)}")

    def instantiate_workflow(
        self,
        *,
        template_id: str,
        workflow_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """Instantiate a workflow from a template.

        Args:
            template_id: Template identifier
            workflow_id: Optional workflow identifier (generated if not provided)
            parameters: Optional parameters for template customization
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Workflow ID for the instantiated workflow

        Raises:
            ValueError: When workflow instantiation fails
        """
        try:
            # Verify template exists
            if template_id not in self.workflow_templates:
                raise ValueError(f"Template not found: {template_id}")

            template = self.workflow_templates[template_id]

            # Generate workflow ID if not provided
            workflow_id = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"

            # Apply parameters to template steps
            steps = self._apply_parameters_to_steps(template["steps"], parameters or {})

            # Register workflow with orchestrator
            self.workflow_orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=steps,
                framework="flowise",
                tenant_id=tenant_id or template["tenant_id"]
            )

            # Store workflow metadata
            self.active_workflows[workflow_id] = {
                "id": workflow_id,
                "template_id": template_id,
                "parameters": parameters or {},
                "tenant_id": tenant_id or template["tenant_id"],
                "status": "instantiated",
                "created_at": datetime.now().isoformat()
            }

            logger.info(
                f"Instantiated workflow: id={workflow_id}, template={template_id}, "
                f"tenant_id={tenant_id or template['tenant_id']}"
            )

            return workflow_id

        except Exception as e:
            logger.error(f"Failed to instantiate workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow instantiation failed: {str(e)}")

    def execute_workflow(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        async_execution: bool = False,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a workflow with input data.

        Args:
            workflow_id: Workflow identifier
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation
            async_execution: Whether to execute asynchronously
            callback_url: Optional URL for execution completion callback

        Returns:
            Workflow execution results or status information

        Raises:
            ValueError: When workflow execution fails
        """
        try:
            # Verify workflow exists
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.active_workflows[workflow_id]
            tenant_id = tenant_id or workflow["tenant_id"]

            # Update workflow status
            workflow["status"] = "running"
            workflow["started_at"] = datetime.now().isoformat()

            if async_execution:
                # Start asynchronous execution
                asyncio.create_task(
                    self._execute_workflow_async(
                        workflow_id=workflow_id,
                        input_data=input_data,
                        tenant_id=tenant_id,
                        callback_url=callback_url
                    )
                )

                return {
                    "workflow_id": workflow_id,
                    "status": "running",
                    "message": "Workflow execution started asynchronously",
                    "started_at": workflow["started_at"]
                }
            else:
                # Execute synchronously
                result = self.workflow_orchestrator.execute_workflow(
                    workflow_id=workflow_id,
                    input_data=input_data,
                    tenant_id=tenant_id
                )

                # Update workflow status
                workflow["status"] = result.get("status", "unknown")
                workflow["completed_at"] = datetime.now().isoformat()

                # Store execution history
                self._store_execution_history(workflow_id, result)

                return result

        except Exception as e:
            logger.error(f"Failed to execute workflow: {str(e)}", exc_info=True)

            # Update workflow status if possible
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)

            raise ValueError(f"Workflow execution failed: {str(e)}")

    async def _execute_workflow_async(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str,
        callback_url: Optional[str] = None
    ) -> None:
        """Execute workflow asynchronously.

        Args:
            workflow_id: Workflow identifier
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation
            callback_url: Optional URL for execution completion callback
        """
        try:
            # Execute workflow
            result = self.workflow_orchestrator.execute_workflow(
                workflow_id=workflow_id,
                input_data=input_data,
                tenant_id=tenant_id
            )

            # Update workflow status
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = result.get("status", "unknown")
                self.active_workflows[workflow_id]["completed_at"] = datetime.now().isoformat()

            # Store execution history
            self._store_execution_history(workflow_id, result)

            # Send callback if provided
            if callback_url:
                await self._send_callback(callback_url, result)

        except Exception as e:
            logger.error(f"Async workflow execution failed: {str(e)}", exc_info=True)

            # Update workflow status
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)

            # Send error callback if provided
            if callback_url:
                error_result = {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": str(e)
                }
                await self._send_callback(callback_url, error_result)

    async def _send_callback(self, callback_url: str, data: Dict[str, Any]) -> None:
        """Send callback with workflow execution results.

        Args:
            callback_url: URL for callback
            data: Callback data
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    callback_url,
                    json=data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status >= 400:
                        logger.warning(
                            f"Callback failed with status {response.status}: "
                            f"{await response.text()}"
                        )
                    else:
                        logger.info(f"Callback sent successfully to {callback_url}")

        except Exception as e:
            logger.error(f"Failed to send callback: {str(e)}", exc_info=True)

    def get_workflow_status(
        self,
        *,
        workflow_id: str,
        include_history: bool = False
    ) -> Dict[str, Any]:
        """Get workflow status and execution information.

        Args:
            workflow_id: Workflow identifier
            include_history: Whether to include execution history

        Returns:
            Workflow status information

        Raises:
            ValueError: When workflow is not found
        """
        # Verify workflow exists
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self.active_workflows[workflow_id]

        # Prepare response
        response = {
            "workflow_id": workflow_id,
            "status": workflow.get("status", "unknown"),
            "template_id": workflow.get("template_id"),
            "tenant_id": workflow.get("tenant_id"),
            "created_at": workflow.get("created_at")
        }

        # Add timing information if available
        if "started_at" in workflow:
            response["started_at"] = workflow["started_at"]

            if "completed_at" in workflow:
                response["completed_at"] = workflow["completed_at"]

                # Calculate duration if both timestamps are available
                try:
                    started = datetime.fromisoformat(workflow["started_at"])
                    completed = datetime.fromisoformat(workflow["completed_at"])
                    duration_ms = (completed - started).total_seconds() * 1000
                    response["duration_ms"] = duration_ms
                except Exception:
                    pass

        # Add error information if available
        if "error" in workflow:
            response["error"] = workflow["error"]

        # Add execution history if requested
        if include_history and workflow_id in self.workflow_history:
            response["history"] = self.workflow_history[workflow_id]

        return response

    def _validate_workflow_steps(self, steps: List[Dict[str, Any]]) -> None:
        """Validate workflow steps for correctness.

        Args:
            steps: List of workflow step configurations

        Raises:
            ValueError: When steps are invalid
        """
        if not steps:
            raise ValueError("Workflow must have at least one step")

        for i, step in enumerate(steps):
            if "type" not in step:
                raise ValueError(f"Step {i+1} missing required 'type' field")

            # Validate step type
            valid_types = [
                "graphrag_query", "graphrag_index", "custom_function",
                "condition", "parallel", "sequence", "retry"
            ]

            if step["type"] not in valid_types:
                raise ValueError(f"Step {i+1} has invalid type: {step['type']}")

            # Validate step-specific requirements
            if step["type"] == "graphrag_query" and "question" not in step:
                raise ValueError(f"Step {i+1} (graphrag_query) missing required 'question' field")

            if step["type"] == "graphrag_index" and "docs" not in step:
                raise ValueError(f"Step {i+1} (graphrag_index) missing required 'docs' field")

            if step["type"] == "custom_function" and "function" not in step:
                raise ValueError(f"Step {i+1} (custom_function) missing required 'function' field")

            if step["type"] == "parallel" and "branches" not in step:
                raise ValueError(f"Step {i+1} (parallel) missing required 'branches' field")

            if step["type"] == "sequence" and "steps" not in step:
                raise ValueError(f"Step {i+1} (sequence) missing required 'steps' field")

            if step["type"] == "retry" and "step" not in step:
                raise ValueError(f"Step {i+1} (retry) missing required 'step' field")

            # Recursively validate nested steps
            if step["type"] == "sequence" and "steps" in step:
                self._validate_workflow_steps(step["steps"])

            if step["type"] == "parallel" and "branches" in step:
                for j, branch in enumerate(step["branches"]):
                    if not isinstance(branch, list):
                        raise ValueError(f"Branch {j+1} in step {i+1} must be a list of steps")
                    self._validate_workflow_steps(branch)

            if step["type"] == "retry" and "step" in step:
                self._validate_workflow_steps([step["step"]])

    def _apply_parameters_to_steps(
        self,
        steps: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply parameters to workflow steps.

        Args:
            steps: List of workflow step configurations
            parameters: Parameters for template customization

        Returns:
            Updated workflow steps with parameters applied
        """
        import copy

        # Deep copy steps to avoid modifying the template
        updated_steps = copy.deepcopy(steps)

        # Helper function to replace parameter placeholders
        def replace_placeholders(obj: Any) -> Any:
            if isinstance(obj, str):
                # Replace ${param} placeholders
                for param_name, param_value in parameters.items():
                    placeholder = f"${{{param_name}}}"
                    if placeholder in obj:
                        obj = obj.replace(placeholder, str(param_value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            else:
                return obj

        # Apply parameters to steps
        return replace_placeholders(updated_steps)

    def _store_execution_history(self, workflow_id: str, result: Dict[str, Any]) -> None:
        """Store workflow execution history.

        Args:
            workflow_id: Workflow identifier
            result: Workflow execution result
        """
        if workflow_id not in self.workflow_history:
            self.workflow_history[workflow_id] = []

        # Add execution record
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "status": result.get("status", "unknown"),
            "steps_completed": result.get("steps_completed", 0),
            "steps_total": result.get("steps_total", 0)
        }

        # Add error information if available
        if "error" in result:
            execution_record["error"] = result["error"]

        # Add execution record to history
        self.workflow_history[workflow_id].append(execution_record)

        # Limit history size
        if len(self.workflow_history[workflow_id]) > 10:
            self.workflow_history[workflow_id] = self.workflow_history[workflow_id][-10:]

    def execute_with_fallback(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        fallback_workflow_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 2
    ) -> Dict[str, Any]:
        """Execute a workflow with automatic fallback to another workflow if execution fails.

        Args:
            workflow_id: Primary workflow identifier
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation
            fallback_workflow_id: Optional fallback workflow to execute on failure
            max_retries: Maximum number of retry attempts before using fallback
            retry_delay_seconds: Delay between retry attempts in seconds

        Returns:
            Workflow execution results or fallback results

        Raises:
            ValueError: When both primary and fallback workflow executions fail
        """
        # Track retry attempts
        for attempt in range(max_retries):
            try:
                logger.info(f"Executing workflow {workflow_id}, attempt {attempt + 1}/{max_retries}")

                # Execute primary workflow
                result = self.execute_workflow(
                    workflow_id=workflow_id,
                    input_data=input_data,
                    tenant_id=tenant_id
                )

                # Check for success
                if result.get("status") == "completed":
                    logger.info(f"Workflow {workflow_id} executed successfully on attempt {attempt + 1}")
                    return result

                # If workflow failed but we have more retries, continue
                logger.warning(
                    f"Workflow {workflow_id} execution attempt {attempt + 1} failed "
                    f"with status {result.get('status')}"
                )

                # Add retry information to result
                if "retries" not in result:
                    result["retries"] = []

                result["retries"].append({
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                    "status": result.get("status")
                })

                # Wait before retrying
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_seconds)

            except Exception as e:
                logger.error(
                    f"Workflow {workflow_id} execution attempt {attempt + 1} "
                    f"failed with error: {str(e)}",
                    exc_info=True
                )

                # Wait before retrying
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_seconds)

        # All retries failed, try fallback workflow if provided
        if fallback_workflow_id:
            try:
                logger.info(
                    f"All {max_retries} attempts to execute workflow {workflow_id} failed. "
                    f"Trying fallback workflow {fallback_workflow_id}"
                )

                # Execute fallback workflow
                fallback_result = self.execute_workflow(
                    workflow_id=fallback_workflow_id,
                    input_data=input_data,
                    tenant_id=tenant_id
                )

                # Add fallback information to result
                fallback_result["fallback_from"] = workflow_id
                fallback_result["primary_failed_attempts"] = max_retries

                logger.info(
                    f"Fallback workflow {fallback_workflow_id} executed with "
                    f"status {fallback_result.get('status')}"
                )

                return fallback_result

            except Exception as fallback_error:
                logger.error(
                    f"Fallback workflow {fallback_workflow_id} execution failed: {str(fallback_error)}",
                    exc_info=True
                )

                # Both primary and fallback workflows failed
                raise ValueError(
                    f"Both primary workflow {workflow_id} and fallback workflow "
                    f"{fallback_workflow_id} failed. Primary error: {str(e)}, "
                    f"Fallback error: {str(fallback_error)}"
                )

        # No fallback workflow provided, raise error for primary workflow failure
        raise ValueError(
            f"Workflow {workflow_id} execution failed after {max_retries} attempts"
        )

    def execute_parallel_workflows(
        self,
        *,
        workflow_configs: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        timeout_seconds: int = 60,
        aggregate_results: bool = True
    ) -> Dict[str, Any]:
        """Execute multiple workflows in parallel and optionally aggregate results.

        Args:
            workflow_configs: List of workflow configurations with workflow_id and input_data
            tenant_id: Tenant identifier for multi-tenant isolation
            timeout_seconds: Maximum execution time in seconds
            aggregate_results: Whether to aggregate results into a single response

        Returns:
            Dictionary containing execution results for all workflows

        Raises:
            ValueError: When parallel execution fails
        """
        if not workflow_configs:
            raise ValueError("No workflow configurations provided")

        # Create thread pool for parallel execution
        with ThreadPoolExecutor(max_workers=min(len(workflow_configs), 10)) as executor:
            # Submit all workflow executions to thread pool
            future_to_workflow = {
                executor.submit(
                    self._execute_workflow_in_thread,
                    workflow_id=config["workflow_id"],
                    input_data=config["input_data"],
                    tenant_id=tenant_id or config.get("tenant_id") or self.default_tenant_id
                ): config["workflow_id"]
                for config in workflow_configs
            }

            # Collect results with timeout
            results = {}
            for future in future_to_workflow:
                workflow_id = future_to_workflow[future]
                try:
                    # Wait for workflow execution with timeout
                    result = future.result(timeout=timeout_seconds)
                    results[workflow_id] = result
                except Exception as e:
                    logger.error(
                        f"Parallel workflow {workflow_id} execution failed: {str(e)}",
                        exc_info=True
                    )
                    results[workflow_id] = {
                        "status": "failed",
                        "error": str(e),
                        "workflow_id": workflow_id
                    }

        # Return results based on aggregation preference
        if aggregate_results:
            # Combine all results into a single response
            aggregated_result = {
                "status": "completed" if all(r.get("status") == "completed" for r in results.values()) else "partial",
                "workflow_count": len(workflow_configs),
                "completed_count": sum(1 for r in results.values() if r.get("status") == "completed"),
                "failed_count": sum(1 for r in results.values() if r.get("status") != "completed"),
                "results": results
            }
            return aggregated_result
        else:
            # Return individual results
            return results

    def _execute_workflow_in_thread(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, Any]:
        """Execute workflow in a separate thread for parallel execution.

        Args:
            workflow_id: Workflow identifier
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Workflow execution results

        Raises:
            Exception: When workflow execution fails
        """
        try:
            return self.execute_workflow(
                workflow_id=workflow_id,
                input_data=input_data,
                tenant_id=tenant_id
            )
        except Exception as e:
            # Capture full stack trace for debugging
            stack_trace = traceback.format_exc()
            logger.error(
                f"Thread execution of workflow {workflow_id} failed: {str(e)}\n{stack_trace}"
            )
            raise

    def create_workflow_monitor(
        self,
        *,
        workflow_id: str,
        check_interval_seconds: int = 5,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Create a monitoring task for a workflow execution.

        Args:
            workflow_id: Workflow identifier to monitor
            check_interval_seconds: Interval between status checks in seconds
            timeout_seconds: Maximum monitoring time in seconds

        Returns:
            Dictionary with monitoring configuration

        Raises:
            ValueError: When workflow is not found
        """
        # Verify workflow exists
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Create monitor ID
        monitor_id = f"monitor_{uuid.uuid4().hex[:8]}"

        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_workflow,
            args=(workflow_id, monitor_id, check_interval_seconds, timeout_seconds),
            daemon=True
        )
        monitor_thread.start()

        return {
            "monitor_id": monitor_id,
            "workflow_id": workflow_id,
            "check_interval_seconds": check_interval_seconds,
            "timeout_seconds": timeout_seconds,
            "started_at": datetime.now().isoformat()
        }

    def _monitor_workflow(
        self,
        workflow_id: str,
        monitor_id: str,
        check_interval_seconds: int,
        timeout_seconds: int
    ) -> None:
        """Monitor workflow execution in a separate thread.

        Args:
            workflow_id: Workflow identifier to monitor
            monitor_id: Monitor identifier
            check_interval_seconds: Interval between status checks in seconds
            timeout_seconds: Maximum monitoring time in seconds
        """
        start_time = datetime.now()
        timeout = timedelta(seconds=timeout_seconds)

        logger.info(
            f"Started monitoring workflow {workflow_id} with monitor {monitor_id}, "
            f"timeout: {timeout_seconds}s"
        )

        while datetime.now() - start_time < timeout:
            try:
                # Check workflow status
                if workflow_id not in self.active_workflows:
                    logger.warning(f"Monitored workflow {workflow_id} not found, stopping monitor {monitor_id}")
                    break

                workflow = self.active_workflows[workflow_id]
                status = workflow.get("status", "unknown")

                logger.debug(f"Monitor {monitor_id}: workflow {workflow_id} status is {status}")

                # If workflow completed or failed, stop monitoring
                if status in ["completed", "failed"]:
                    logger.info(
                        f"Workflow {workflow_id} reached terminal status {status}, "
                        f"stopping monitor {monitor_id}"
                    )
                    break

                # Wait before next check
                time.sleep(check_interval_seconds)

            except Exception as e:
                logger.error(
                    f"Error in workflow monitor {monitor_id} for workflow {workflow_id}: {str(e)}",
                    exc_info=True
                )
                break

        # Check if monitoring timed out
        if datetime.now() - start_time >= timeout:
            logger.warning(
                f"Monitoring of workflow {workflow_id} timed out after {timeout_seconds}s, "
                f"stopping monitor {monitor_id}"
            )

            # Update workflow status if still running
            if (workflow_id in self.active_workflows and
                self.active_workflows[workflow_id].get("status") == "running"):
                self.active_workflows[workflow_id]["status"] = "timeout"
                self.active_workflows[workflow_id]["error"] = f"Execution timed out after {timeout_seconds}s"
    def export_workflow(
        self,
        *,
        workflow_id: str,
        format: str = "yaml",
        include_history: bool = False,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export a workflow to a serialized format.

        Args:
            workflow_id: Workflow identifier to export
            format: Export format ("yaml", "json")
            include_history: Whether to include execution history
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Dictionary containing exported workflow data

        Raises:
            ValueError: When workflow export fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Verify workflow exists
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.active_workflows[workflow_id]
            tenant_id = tenant_id or workflow.get("tenant_id", self.default_tenant_id)

            # Get workflow data from orchestrator
            workflow_data = self.workflow_orchestrator.get_workflow(workflow_id)
            if not workflow_data:
                raise ValueError(f"Workflow data not found: {workflow_id}")

            # Add metadata
            if "metadata" not in workflow_data:
                workflow_data["metadata"] = {}

            workflow_data["metadata"].update({
                "exported_at": datetime.now().isoformat(),
                "tenant_id": tenant_id,
                "framework": "flowise"
            })

            # Add execution history if requested
            if include_history and workflow_id in self.workflow_history:
                workflow_data["metadata"]["execution_history"] = self.workflow_history[workflow_id]

            # Generate version ID if not present
            if "version_id" not in workflow_data["metadata"]:
                workflow_data["metadata"]["version_id"] = WorkflowSerializer.generate_version_id(workflow_data)

            # Export based on format
            if format.lower() == "yaml":
                exported_content = WorkflowSerializer.to_yaml(workflow_data, "flowise")
                file_extension = "yaml"
            elif format.lower() == "json":
                exported_content = json.dumps(workflow_data, indent=2)
                file_extension = "json"
            else:
                raise ValueError(f"Unsupported export format: {format}")

            logger.info(f"Exported workflow {workflow_id} to {format} format")

            return {
                "workflow_id": workflow_id,
                "format": format,
                "content": exported_content,
                "file_extension": file_extension,
                "version_id": workflow_data["metadata"]["version_id"]
            }

        except Exception as e:
            logger.error(f"Failed to export workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow export failed: {str(e)}")

    def import_workflow(
        self,
        *,
        content: str,
        format: str = "yaml",
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        override_existing: bool = False
    ) -> str:
        """Import a workflow from serialized format.

        Args:
            content: Serialized workflow content
            format: Import format ("yaml", "json")
            workflow_id: Optional workflow identifier (generated if not provided)
            tenant_id: Tenant identifier for multi-tenant isolation
            override_existing: Whether to override existing workflow with same ID

        Returns:
            Workflow ID of the imported workflow

        Raises:
            ValueError: When workflow import fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Parse content based on format
            if format.lower() == "yaml":
                workflow_data = WorkflowSerializer.from_yaml(content)
            elif format.lower() == "json":
                workflow_data = json.loads(content)
            else:
                raise ValueError(f"Unsupported import format: {format}")

            # Validate workflow data
            if "steps" not in workflow_data:
                raise ValueError("Invalid workflow format: 'steps' field is required")

            # Use provided workflow ID or generate one
            imported_id = workflow_id or workflow_data.get("id") or f"wf_{uuid.uuid4().hex[:8]}"

            # Check if workflow already exists
            if imported_id in self.active_workflows and not override_existing:
                raise ValueError(f"Workflow already exists: {imported_id}. Use override_existing=True to replace it.")

            # Set tenant ID
            tenant_id = tenant_id or workflow_data.get("metadata", {}).get("tenant_id", self.default_tenant_id)

            # Register workflow with orchestrator
            self.workflow_orchestrator.register_workflow(
                workflow_id=imported_id,
                steps=workflow_data["steps"],
                framework="flowise",
                tenant_id=tenant_id
            )

            # Store workflow metadata
            self.active_workflows[imported_id] = {
                "id": imported_id,
                "tenant_id": tenant_id,
                "status": "imported",
                "created_at": datetime.now().isoformat(),
                "imported_at": datetime.now().isoformat(),
                "original_id": workflow_data.get("id"),
                "version_id": workflow_data.get("metadata", {}).get("version_id")
            }

            logger.info(f"Imported workflow: id={imported_id}, format={format}")
            return imported_id

        except Exception as e:
            logger.error(f"Failed to import workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow import failed: {str(e)}")

    def create_workflow_version(
        self,
        *,
        workflow_id: str,
        commit_message: str,
        tenant_id: Optional[str] = None,
        create_git_tag: bool = True,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a versioned snapshot of a workflow.

        Args:
            workflow_id: Workflow identifier
            commit_message: Message describing the version
            tenant_id: Tenant identifier for multi-tenant isolation
            create_git_tag: Whether to create a Git tag for the version
            repo_path: Path to Git repository (current directory if not provided)

        Returns:
            Dictionary with version information

        Raises:
            ValueError: When version creation fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Export workflow to get version ID
            export_result = self.export_workflow(
                workflow_id=workflow_id,
                format="yaml",
                tenant_id=tenant_id
            )

            version_id = export_result["version_id"]
            content = export_result["content"]

            # Create Git tag if requested
            if create_git_tag:
                repo_path = repo_path or os.getcwd()

                # Create tag
                tag_name = f"flowise-{workflow_id}-{version_id}"
                tag_created = WorkflowSerializer.create_git_tag(
                    repo_path=repo_path,
                    tag_name=tag_name,
                    message=f"{commit_message} [workflow: {workflow_id}]",
                    annotated=True
                )

                if not tag_created:
                    logger.warning(f"Failed to create Git tag for workflow {workflow_id}")

            # Store version information in workflow metadata
            if workflow_id in self.active_workflows:
                if "versions" not in self.active_workflows[workflow_id]:
                    self.active_workflows[workflow_id]["versions"] = []

                self.active_workflows[workflow_id]["versions"].append({
                    "version_id": version_id,
                    "created_at": datetime.now().isoformat(),
                    "commit_message": commit_message,
                    "git_tag": tag_name if create_git_tag else None
                })

                # Limit version history size
                if len(self.active_workflows[workflow_id]["versions"]) > 10:
                    self.active_workflows[workflow_id]["versions"] = self.active_workflows[workflow_id]["versions"][-10:]

            logger.info(f"Created workflow version: workflow={workflow_id}, version={version_id}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "created_at": datetime.now().isoformat(),
                "commit_message": commit_message,
                "git_tag": tag_name if create_git_tag else None
            }

        except Exception as e:
            logger.error(f"Failed to create workflow version: {str(e)}", exc_info=True)
            raise ValueError(f"Version creation failed: {str(e)}")

    def rollback_workflow(
        self,
        *,
        workflow_id: str,
        version_id: str,
        tenant_id: Optional[str] = None,
        repo_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Roll back a workflow to a previous version.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier to roll back to
            tenant_id: Tenant identifier for multi-tenant isolation
            repo_path: Path to Git repository (current directory if not provided)

        Returns:
            Dictionary with rollback information

        Raises:
            ValueError: When rollback fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Verify workflow exists
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.active_workflows[workflow_id]
            tenant_id = tenant_id or workflow.get("tenant_id", self.default_tenant_id)

            # Check if version exists in workflow metadata
            version_found = False
            if "versions" in workflow:
                for version in workflow["versions"]:
                    if version["version_id"] == version_id:
                        version_found = True
                        break

            # If version not found in metadata, try Git tag
            if not version_found:
                repo_path = repo_path or os.getcwd()
                tag_name = f"flowise-{workflow_id}-{version_id}"

                # Check if tag exists
                tags = WorkflowSerializer.list_tags(
                    repo_path=repo_path,
                    pattern=tag_name
                )

                if not tags:
                    raise ValueError(f"Version not found: {version_id}")

                # Roll back using Git tag
                workflow_path = f"workflows/{workflow_id}"
                rollback_success = WorkflowSerializer.rollback_to_tag(
                    repo_path=repo_path,
                    tag_name=tag_name,
                    workflow_path=workflow_path
                )

                if not rollback_success:
                    raise ValueError(f"Failed to roll back to version: {version_id}")

                # Load workflow from file
                workflow_file = os.path.join(repo_path, workflow_path, "workflow.yaml")
                if not os.path.exists(workflow_file):
                    workflow_file = os.path.join(repo_path, workflow_path, "workflow.json")

                if not os.path.exists(workflow_file):
                    raise ValueError(f"Workflow file not found after rollback")

                # Read workflow file
                with open(workflow_file, "r") as f:
                    content = f.read()

                # Import rolled back workflow
                format = "yaml" if workflow_file.endswith(".yaml") else "json"
                self.import_workflow(
                    content=content,
                    format=format,
                    workflow_id=workflow_id,
                    tenant_id=tenant_id,
                    override_existing=True
                )

            logger.info(f"Rolled back workflow {workflow_id} to version {version_id}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "rollback_time": datetime.now().isoformat(),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Failed to roll back workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow rollback failed: {str(e)}")

    def list_workflow_versions(
        self,
        *,
        workflow_id: str,
        include_git_tags: bool = True,
        repo_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List versions of a workflow.

        Args:
            workflow_id: Workflow identifier
            include_git_tags: Whether to include Git tags in the results
            repo_path: Path to Git repository (current directory if not provided)

        Returns:
            List of version information dictionaries

        Raises:
            ValueError: When listing versions fails
        """
        try:
            # Verify workflow exists
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.active_workflows[workflow_id]
            versions = []

            # Add versions from workflow metadata
            if "versions" in workflow:
                versions.extend(workflow["versions"])

            # Add versions from Git tags if requested
            if include_git_tags:
                from ui_adapters.workflow_serialization import WorkflowSerializer

                repo_path = repo_path or os.getcwd()
                tag_pattern = f"flowise-{workflow_id}-*"

                # Get tags matching pattern
                tags = WorkflowSerializer.list_tags(
                    repo_path=repo_path,
                    pattern=tag_pattern
                )

                # Add tags to versions if not already included
                for tag in tags:
                    tag_name = tag["name"]

                    # Extract version ID from tag name
                    if tag_name.startswith(f"flowise-{workflow_id}-"):
                        version_id = tag_name[len(f"flowise-{workflow_id}-"):]

                        # Check if version already in list
                        if not any(v.get("version_id") == version_id for v in versions):
                            versions.append({
                                "version_id": version_id,
                                "created_at": tag["date"],
                                "commit_message": tag["message"],
                                "git_tag": tag_name,
                                "source": "git"
                            })

            # Sort versions by creation date (newest first)
            versions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return versions

        except Exception as e:
            logger.error(f"Failed to list workflow versions: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to list workflow versions: {str(e)}")