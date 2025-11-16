"""
Tests for Flowise workflow orchestration.

This module contains tests for the Flowise workflow orchestration capabilities,
including complex pipelines, error handling, and fallback mechanisms.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import asyncio
from datetime import datetime

from domain.services import WorkflowOrchestrator
from ui_adapters.flowise.workflow_orchestration import FlowiseWorkflowOrchestrator


class TestFlowiseWorkflowOrchestration(unittest.TestCase):
    """Test suite for Flowise workflow orchestration."""

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

    def test_register_workflow_template(self):
        """Test workflow template registration."""
        # Call method under test
        result = self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        # Verify results
        self.assertEqual(result, self.template_id)
        self.assertIn(self.template_id, self.orchestrator.workflow_templates)
        self.assertEqual(
            self.orchestrator.workflow_templates[self.template_id]["name"],
            self.template_name
        )

    def test_instantiate_workflow(self):
        """Test workflow instantiation from template."""
        # Register template
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        # Define parameters
        parameters = {"entity": "GraphRAG"}
        workflow_id = "test_workflow"

        # Call method under test
        result = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            workflow_id=workflow_id,
            parameters=parameters
        )

        # Verify results
        self.assertEqual(result, workflow_id)
        self.assertIn(workflow_id, self.orchestrator.active_workflows)

        # Verify interactions
        self.mock_workflow_orchestrator.register_workflow.assert_called_once()
        call_args = self.mock_workflow_orchestrator.register_workflow.call_args[1]
        self.assertEqual(call_args["workflow_id"], workflow_id)
        self.assertEqual(call_args["framework"], "flowise")

        # Verify parameter application
        steps = call_args["steps"]
        self.assertEqual(steps[0]["question"], "What is GraphRAG?")

    def test_execute_workflow_sync(self):
        """Test synchronous workflow execution."""
        # Register and instantiate workflow
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            parameters={"entity": "GraphRAG"}
        )

        # Define input data and expected result
        input_data = {"additional_context": "ontology"}
        expected_result = {
            "workflow_id": workflow_id,
            "status": "completed",
            "steps_completed": 1,
            "steps_total": 1,
            "results": {
                "step_0": {"result": "GraphRAG is a knowledge graph system."}
            }
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Call method under test
        result = self.orchestrator.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id="test_tenant"
        )

        # Verify workflow status update
        self.assertEqual(self.orchestrator.active_workflows[workflow_id]["status"], "completed")
        self.assertIn("completed_at", self.orchestrator.active_workflows[workflow_id])

    def test_execute_workflow_async(self):
        """Test asynchronous workflow execution."""
        # Register and instantiate workflow
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            parameters={"entity": "GraphRAG"}
        )

        # Define input data and expected result
        input_data = {"additional_context": "ontology"}
        expected_result = {
            "workflow_id": workflow_id,
            "status": "completed",
            "steps_completed": 1,
            "steps_total": 1,
            "results": {
                "step_0": {"result": "GraphRAG is a knowledge graph system."}
            }
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Call method under test
        result = self.orchestrator.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
            async_execution=True
        )

        # Verify initial response
        self.assertEqual(result["workflow_id"], workflow_id)
        self.assertEqual(result["status"], "running")
        self.assertIn("started_at", result)

        # Verify workflow status
        self.assertEqual(self.orchestrator.active_workflows[workflow_id]["status"], "running")
        self.assertIn("started_at", self.orchestrator.active_workflows[workflow_id])

    def test_get_workflow_status(self):
        """Test workflow status retrieval."""
        # Register and instantiate workflow
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            parameters={"entity": "GraphRAG"}
        )

        # Call method under test
        status = self.orchestrator.get_workflow_status(
            workflow_id=workflow_id
        )

        # Verify results
        self.assertEqual(status["workflow_id"], workflow_id)
        self.assertEqual(status["status"], "instantiated")
        self.assertEqual(status["template_id"], self.template_id)
        self.assertEqual(status["tenant_id"], "test_tenant")
        self.assertIn("created_at", status)

    def test_error_handling(self):
        """Test error handling in workflow execution."""
        # Register and instantiate workflow
        self.orchestrator.register_workflow_template(
            template_id=self.template_id,
            name=self.template_name,
            description=self.template_description,
            steps=self.template_steps,
            input_schema=self.template_input_schema,
            output_schema=self.template_output_schema
        )

        workflow_id = self.orchestrator.instantiate_workflow(
            template_id=self.template_id,
            parameters={"entity": "GraphRAG"}
        )

        # Configure mock to raise exception
        self.mock_workflow_orchestrator.execute_workflow.side_effect = ValueError("Test error")

        # Call method under test and expect exception
        with self.assertRaises(ValueError) as context:
            self.orchestrator.execute_workflow(
                workflow_id=workflow_id,
                input_data={}
            )

        # Verify error message
        self.assertIn("Test error", str(context.exception))

        # Verify workflow status update
        self.assertEqual(self.orchestrator.active_workflows[workflow_id]["status"], "failed")
        self.assertIn("error", self.orchestrator.active_workflows[workflow_id])
        self.assertEqual(
            self.orchestrator.active_workflows[workflow_id]["error"],
            "Test error"
        )

    def test_parameter_application(self):
        """Test parameter application to workflow steps."""
        # Define complex template with nested steps
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

        # Register template
        self.orchestrator.register_workflow_template(
            template_id="complex_template",
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
        workflow_id = self.orchestrator.instantiate_workflow(
            template_id="complex_template",
            parameters=parameters
        )

        # Verify parameter application
        call_args = self.mock_workflow_orchestrator.register_workflow.call_args[1]
        steps = call_args["steps"]

        # Check sequence step
        sequence_steps = steps[0]["steps"]
        self.assertEqual(sequence_steps[0]["question"], "What is GraphRAG?")
        self.assertEqual(
            sequence_steps[1]["question"],
            "Tell me more about GraphRAG in ontology validation."
        )

        # Check parallel step
        parallel_branches = steps[1]["branches"]
        self.assertEqual(
            parallel_branches[0][0]["question"],
            "GraphRAG applications in knowledge graphs?"
        )
        self.assertEqual(
            parallel_branches[1][0]["question"],
            "GraphRAG limitations in knowledge graphs?"
        )


if __name__ == "__main__":
    unittest.main()