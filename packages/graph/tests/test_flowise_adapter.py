"""
Tests for Flowise AI framework adapter.

This module contains tests for the Flowise AI framework adapter,
including GraphRagNode integration and workflow orchestration.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import os
import tempfile
from pathlib import Path

from domain.entities import Triple
from domain.services import WorkflowOrchestrator, QueryService
from ui_adapters.flowise.flowise_adapter import FlowiseGraphRAGAdapter


class TestFlowiseAdapter(unittest.TestCase):
    """Test suite for Flowise AI framework adapter."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_query_service = MagicMock(spec=QueryService)
        self.mock_workflow_orchestrator = MagicMock(spec=WorkflowOrchestrator)
        self.mock_graph_retriever = MagicMock()
        self.mock_query_translator = MagicMock()

        # Create temporary directory for node registration
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create adapter instance
        self.adapter = FlowiseGraphRAGAdapter(
            query_service=self.mock_query_service,
            workflow_orchestrator=self.mock_workflow_orchestrator,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            default_kg_id="test_kg",
            default_tenant_id="test_tenant",
            node_directory=self.temp_dir.name
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_node_registration(self):
        """Test that the GraphRagNode is registered with Flowise."""
        # Check that node directory was created
        node_path = os.path.join(self.temp_dir.name, "graphrag")
        self.assertTrue(os.path.exists(node_path))

        # Check that node files were created
        self.assertTrue(os.path.exists(os.path.join(node_path, "graphrag_node.js")))
        self.assertTrue(os.path.exists(os.path.join(node_path, "package.json")))
        self.assertTrue(os.path.exists(os.path.join(node_path, "graphrag.svg")))

        # Check package.json content
        with open(os.path.join(node_path, "package.json"), "r") as f:
            package_json = json.load(f)
            self.assertEqual(package_json["name"], "flowise-graphrag-node")
            self.assertEqual(package_json["main"], "graphrag_node.js")

    def test_create_workflow(self):
        """Test workflow creation."""
        # Define test data
        workflow_id = "test_workflow"
        steps = [
            {
                "type": "graphrag_query",
                "name": "Query Step",
                "question": "What is GraphRAG?"
            }
        ]

        # Call method under test
        result = self.adapter.create_workflow(
            workflow_id=workflow_id,
            steps=steps
        )

        # Verify results
        self.assertEqual(result, workflow_id)

        # Verify interactions
        self.mock_workflow_orchestrator.register_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            steps=steps,
            framework="flowise",
            tenant_id="test_tenant"
        )

    def test_execute_workflow(self):
        """Test workflow execution."""
        # Define test data
        workflow_id = "test_workflow"
        input_data = {"question": "What is GraphRAG?"}
        expected_result = {
            "workflow_id": workflow_id,
            "status": "completed",
            "results": {"step_0": {"result": "GraphRAG is a knowledge graph system."}}
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Call method under test
        result = self.adapter.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id="test_tenant",
            async_execution=False,
            callback_url=None
        )

    def test_execute_workflow_async(self):
        """Test asynchronous workflow execution."""
        # Define test data
        workflow_id = "test_workflow"
        input_data = {"question": "What is GraphRAG?"}
        callback_url = "http://example.com/callback"
        expected_result = {
            "workflow_id": workflow_id,
            "status": "running",
            "message": "Workflow execution started asynchronously"
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Call method under test
        result = self.adapter.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
            async_execution=True,
            callback_url=callback_url
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id="test_tenant",
            async_execution=True,
            callback_url=callback_url
        )

    def test_execute_workflow_with_fallback(self):
        """Test workflow execution with fallback."""
        # Define test data
        workflow_id = "primary_workflow"
        fallback_workflow_id = "fallback_workflow"
        input_data = {"question": "What is GraphRAG?"}
        expected_result = {
            "workflow_id": fallback_workflow_id,
            "status": "completed",
            "fallback_from": workflow_id,
            "primary_failed_attempts": 3,
            "results": {"step_0": {"result": "GraphRAG is a knowledge graph system."}}
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_with_fallback.return_value = expected_result

        # Call method under test
        result = self.adapter.execute_workflow_with_fallback(
            workflow_id=workflow_id,
            input_data=input_data,
            fallback_workflow_id=fallback_workflow_id,
            max_retries=3,
            retry_delay_seconds=1
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_workflow_orchestrator.execute_with_fallback.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id="test_tenant",
            fallback_workflow_id=fallback_workflow_id,
            max_retries=3,
            retry_delay_seconds=1
        )

    def test_execute_parallel_workflows(self):
        """Test parallel workflow execution."""
        # Define test data
        workflow_configs = [
            {"workflow_id": "workflow_1", "input_data": {"param": "value1"}},
            {"workflow_id": "workflow_2", "input_data": {"param": "value2"}}
        ]
        expected_result = {
            "status": "completed",
            "workflow_count": 2,
            "completed_count": 2,
            "failed_count": 0,
            "results": {
                "workflow_1": {"status": "completed", "results": {"step_0": {"result": "Result 1"}}},
                "workflow_2": {"status": "completed", "results": {"step_0": {"result": "Result 2"}}}
            }
        }

        # Configure mock
        self.mock_workflow_orchestrator.execute_parallel_workflows.return_value = expected_result

        # Call method under test
        result = self.adapter.execute_parallel_workflows(
            workflow_configs=workflow_configs,
            timeout_seconds=30,
            aggregate_results=True
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_workflow_orchestrator.execute_parallel_workflows.assert_called_once_with(
            workflow_configs=workflow_configs,
            tenant_id="test_tenant",
            timeout_seconds=30,
            aggregate_results=True
        )

    def test_query_knowledge_graph(self):
        """Test knowledge graph querying."""
        # Define test data
        question = "What is GraphRAG?"
        expected_result = {
            "results": ["GraphRAG is a knowledge graph system."],
            "explanation": "Query executed successfully."
        }

        # Configure mock
        self.mock_query_service.execute_natural_language_query.return_value = expected_result

        # Call method under test
        result = self.adapter.query_knowledge_graph(
            question=question
        )

        # Verify results
        self.assertEqual(result, expected_result)

        # Verify interactions
        self.mock_query_service.execute_natural_language_query.assert_called_once_with(
            question=question,
            kg_id="test_kg",
            tenant_id="test_tenant",
            user_id="flowise_user",
            include_explanation=True,
            query_opts=None
        )

    def test_index_documents(self):
        """Test document indexing."""
        # Define test data
        docs = ["Document 1", "Document 2"]
        triples = [
            Triple(subject="entity1", predicate="relates_to", object="entity2", tenant_id="test_tenant"),
            Triple(subject="entity2", predicate="has_property", object="value", tenant_id="test_tenant")
        ]

        # Configure mock
        self.mock_graph_retriever.index.return_value = triples

        # Call method under test
        result = self.adapter.index_documents(
            docs=docs
        )

        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["triple_count"], 2)
        self.assertEqual(result["kg_id"], "test_kg")

        # Verify interactions
        self.mock_graph_retriever.index.assert_called_once_with(
            docs=docs,
            kg_id="test_kg",
            tenant_id="test_tenant"
        )

    def test_index_documents_with_validation(self):
        """Test indexing with validation service."""
        docs = ["Doc"]
        from domain.entities import Triple, ValidationReport
        validation_report = ValidationReport(
            is_consistent=True,
            unsat_classes=[],
            repair_suggestions=[],
            tenant_id="test_tenant",
            ontology_version_id="latest",
        )
        ingestion_service = MagicMock()
        ingestion_service.process_documents.return_value = validation_report
        self.adapter.ingestion_service = ingestion_service
        self.mock_graph_retriever.index.return_value = [
            Triple(subject="s", predicate="p", object="o", tenant_id="test_tenant")
        ]

        result = self.adapter.index_documents(docs=docs)

        ingestion_service.process_documents.assert_called_once()
        self.assertTrue(result["validation"]["performed"])
        self.assertTrue(result["validation"]["report"]["is_consistent"])

    def test_error_handling(self):
        """Test error handling in adapter methods."""
        # Configure mock to raise exception
        self.mock_query_service.execute_natural_language_query.side_effect = ValueError("Test error")

        # Call method under test
        result = self.adapter.query_knowledge_graph(
            question="What is GraphRAG?"
        )

        # Verify error response
        self.assertIn("results", result)
        self.assertEqual(len(result["results"]), 0)
        self.assertIn("error", result["metadata"])
        self.assertTrue(result["metadata"]["error"])
        self.assertIn("Test error", result["explanation"])


if __name__ == "__main__":
    unittest.main()