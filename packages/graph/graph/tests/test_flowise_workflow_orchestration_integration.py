"""
Integration tests for Flowise workflow orchestration.

This module contains integration tests for the Flowise workflow orchestration capabilities,
focusing on error handling, fallback mechanisms, and complex pipeline execution.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import asyncio
import time
from datetime import datetime
import threading

from domain.services import WorkflowOrchestrator
from ui_adapters.flowise.workflow_orchestration import FlowiseWorkflowOrchestrator


class TestFlowiseWorkflowOrchestrationIntegration(unittest.TestCase):
    """Integration test suite for Flowise workflow orchestration."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_workflow_orchestrator = MagicMock(spec=WorkflowOrchestrator)

        # Create orchestrator instance
        self.orchestrator = FlowiseWorkflowOrchestrator(
            workflow_orchestrator=self.mock_workflow_orchestrator,
            default_tenant_id="test_tenant"
        )

        # Define test workflow template
        self.template_id = "test_template"
        self.template_name = "Test Template"
        self.template_description = "Test workflow template"
        self.template_steps = [
            {
                "type": "graphrag_query",
                "name": "Query Step",
                "question": "What is ${entity}?"
            }
        ]
        self.template_input_schema = {
            "type": "object",
            "properties": {
                "entity": {"type": "string"}
            },
            "required": ["entity"]
        }
        self.template_output_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"}
            }
        }

        # Register template
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        # Create test workflows
        self.primary_workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            workflow_id="primary_workflow",
            parameters={"entity": "GraphRAG"}
        )

        self.fallback_workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            workflow_id="fallback_workflow",
            parameters={"entity": "Knowledge Graph"}
        )

    def test_execute_with_fallback_success_on_first_attempt(self):
        """Test fallback execution with success on first attempt."""
        # Configure primary workflow to succeed
        expected_result = {
            "workflow_id": self.primary_workflow_id,
            "status": "completed",
            "results": {"step_0": {"result": "GraphRAG is a knowledge graph system."}}
        }
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Execute with fallback
        result = self.orchestrator.execute_with_fallback(
            workflow_id=self.primary_workflow_id,
            input_data={"context": "ontology"},
            fallback_workflow_id=self.fallback_workflow_id
        )

        # Verify primary workflow was executed
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once()

        # Verify result
        self.assertEqual(result, expected_result)

    def test_execute_with_fallback_success_after_retry(self):
        """Test fallback execution with success after retry."""
        # Configure primary workflow to fail on first attempt, then succeed
        def side_effect(*args, **kwargs):
            if self.mock_workflow_orchestrator.execute_workflow.call_count == 1:
                return {"workflow_id": self.primary_workflow_id, "status": "failed"}
            else:
                return {
                    "workflow_id": self.primary_workflow_id,
                    "status": "completed",
                    "results": {"step_0": {"result": "GraphRAG is a knowledge graph system."}}
                }

        self.mock_workflow_orchestrator.execute_workflow.side_effect = side_effect

        # Execute with fallback
        result = self.orchestrator.execute_with_fallback(
            workflow_id=self.primary_workflow_id,
            input_data={"context": "ontology"},
            fallback_workflow_id=self.fallback_workflow_id,
            max_retries=2,
            retry_delay_seconds=0.1  # Short delay for testing
        )

        # Verify primary workflow was executed twice
        self.assertEqual(self.mock_workflow_orchestrator.execute_workflow.call_count, 2)

        # Verify result
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["workflow_id"], self.primary_workflow_id)

    def test_execute_with_fallback_using_fallback_workflow(self):
        """Test fallback execution using fallback workflow after primary fails."""
        # Configure primary workflow to always fail
        primary_result = {"workflow_id": self.primary_workflow_id, "status": "failed"}
        fallback_result = {
            "workflow_id": self.fallback_workflow_id,
            "status": "completed",
            "results": {"step_0": {"result": "Knowledge Graph is a data structure."}}
        }

        def side_effect(*args, **kwargs):
            if kwargs.get("workflow_id") == self.primary_workflow_id:
                return primary_result
            else:
                return fallback_result

        self.mock_workflow_orchestrator.execute_workflow.side_effect = side_effect

        # Execute with fallback
        result = self.orchestrator.execute_with_fallback(
            workflow_id=self.primary_workflow_id,
            input_data={"context": "ontology"},
            fallback_workflow_id=self.fallback_workflow_id,
            max_retries=2,
            retry_delay_seconds=0.1  # Short delay for testing
        )

        # Verify both workflows were executed
        self.assertEqual(self.mock_workflow_orchestrator.execute_workflow.call_count, 3)  # 2 primary + 1 fallback

        # Verify result
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["workflow_id"], self.fallback_workflow_id)
        self.assertEqual(result["fallback_from"], self.primary_workflow_id)
        self.assertEqual(result["primary_failed_attempts"], 2)

    def test_execute_parallel_workflows(self):
        """Test parallel workflow execution."""
        # Configure workflow results
        workflow_results = {
            "workflow_1": {
                "workflow_id": "workflow_1",
                "status": "completed",
                "results": {"step_0": {"result": "Result 1"}}
            },
            "workflow_2": {
                "workflow_id": "workflow_2",
                "status": "completed",
                "results": {"step_0": {"result": "Result 2"}}
            },
            "workflow_3": {
                "workflow_id": "workflow_3",
                "status": "failed",
                "error": "Test error"
            }
        }

        def side_effect(*args, **kwargs):
            workflow_id = kwargs.get("workflow_id")
            return workflow_results.get(workflow_id, {"status": "unknown"})

        self.mock_workflow_orchestrator.execute_workflow.side_effect = side_effect

        # Define workflow configurations
        workflow_configs = [
            {"workflow_id": "workflow_1", "input_data": {"param": "value1"}},
            {"workflow_id": "workflow_2", "input_data": {"param": "value2"}},
            {"workflow_id": "workflow_3", "input_data": {"param": "value3"}}
        ]

        # Execute parallel workflows
        result = self.orchestrator.execute_parallel_workflows(
            workflow_configs=workflow_configs,
            timeout_seconds=5
        )

        # Verify results
        self.assertEqual(result["workflow_count"], 3)
        self.assertEqual(result["completed_count"], 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["status"], "partial")

        # Verify individual results
        self.assertEqual(result["results"]["workflow_1"]["status"], "completed")
        self.assertEqual(result["results"]["workflow_2"]["status"], "completed")
        self.assertEqual(result["results"]["workflow_3"]["status"], "failed")

    def test_workflow_monitoring(self):
        """Test workflow monitoring."""
        # Configure workflow to start as running, then complete after delay
        self.orchestrator.active_workflows[self.primary_workflow_id]["status"] = "running"

        def update_workflow_status():
            # Wait a short time, then update status
            time.sleep(0.5)
            self.orchestrator.active_workflows[self.primary_workflow_id]["status"] = "completed"
            self.orchestrator.active_workflows[self.primary_workflow_id]["completed_at"] = datetime.now().isoformat()

        # Start thread to update workflow status
        update_thread = threading.Thread(target=update_workflow_status)
        update_thread.daemon = True
        update_thread.start()

        # Create workflow monitor
        monitor_config = self.orchestrator.create_workflow_monitor(
            workflow_id=self.primary_workflow_id,
            check_interval_seconds=0.1,
            timeout_seconds=2
        )

        # Verify monitor configuration
        self.assertIn("monitor_id", monitor_config)
        self.assertEqual(monitor_config["workflow_id"], self.primary_workflow_id)

        # Wait for monitoring to complete
        time.sleep(1)

        # Verify workflow status was updated
        workflow_status = self.orchestrator.get_workflow_status(
            workflow_id=self.primary_workflow_id
        )
        self.assertEqual(workflow_status["status"], "completed")

    def test_complex_workflow_with_nested_steps(self):
        """Test complex workflow with nested steps."""
        # Define complex template with nested steps
        complex_template_id = "complex_template"
        complex_template_steps = [
            {
                "type": "sequence",
                "name": "Sequence Step",
                "steps": [
                    {
                        "type": "graphrag_query",
                        "name": "Query Step 1",
                        "question": "What is ${entity}?"
                    },
                    {
                        "type": "graphrag_query",
                        "name": "Query Step 2",
                        "question": "Tell me more about ${entity} in ${context}."
                    }
                ]
            },
            {
                "type": "parallel",
                "name": "Parallel Step",
                "branches": [
                    [
                        {
                            "type": "graphrag_query",
                            "name": "Branch 1 Step",
                            "question": "${entity} applications in ${domain}?"
                        }
                    ],
                    [
                        {
                            "type": "graphrag_query",
                            "name": "Branch 2 Step",
                            "question": "${entity} limitations in ${domain}?"
                        }
                    ]
                ]
            }
        ]

        # Register complex template
        self.orchestrator.register_workflow_template(
            template_id=complex_template_id,
            name="Complex Template",
            description="Complex workflow template with nested steps",
            steps=complex_template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        # Define parameters
        parameters = {
            "entity": "GraphRAG",
            "context": "ontology validation",
            "domain": "knowledge graphs"
        }

        # Instantiate workflow
        complex_workflow_id = self.orchestrator.instantiate_workflow(
            template_id=complex_template_id,
            parameters=parameters
        )

        # Configure mock to return success
        self.mock_workflow_orchestrator.execute_workflow.return_value = {
            "workflow_id": complex_workflow_id,
            "status": "completed",
            "steps_completed": 4,
            "steps_total": 4,
            "results": {
                "sequence": {"status": "completed"},
                "parallel": {"status": "completed"}
            }
        }

        # Execute workflow
        result = self.orchestrator.execute_workflow(
            workflow_id=complex_workflow_id,
            input_data={"additional_context": "testing"}
        )

        # Verify workflow was executed
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once()

        # Verify result
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps_completed"], 4)

        # Verify workflow status
        workflow_status = self.orchestrator.get_workflow_status(
            workflow_id=complex_workflow_id,
            include_history=True
        )
        self.assertEqual(workflow_status["status"], "completed")
        self.assertIn("history", workflow_status)


if __name__ == "__main__":
    unittest.main()