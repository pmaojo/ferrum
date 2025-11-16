"""
Tests for Langflow adapter integration.

This module contains tests for the Langflow adapter implementation,
verifying proper integration with the GraphRAG Ontology Application.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import os
import tempfile
import shutil

from ui_adapters.langflow.langflow_adapter import LangflowGraphRAGAdapter
from ui_adapters.langflow.graphrag_component import GraphRagComponent


class TestLangflowAdapter(unittest.TestCase):
    """Test suite for Langflow adapter integration."""

    def setUp(self):
        """Set up test environment."""
        # Create mock dependencies
        self.mock_query_service = MagicMock()
        self.mock_workflow_orchestrator = MagicMock()
        self.mock_graph_retriever = MagicMock()
        self.mock_query_translator = MagicMock()

        # Create temporary directory for component registration
        self.temp_dir = tempfile.mkdtemp()

        # Create adapter instance
        self.adapter = LangflowGraphRAGAdapter(
            query_service=self.mock_query_service,
            workflow_orchestrator=self.mock_workflow_orchestrator,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            component_directory=self.temp_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)

    def test_adapter_initialization(self):
        """Test adapter initialization and component registration."""
        # Verify component was registered
        component_path = os.path.join(self.temp_dir, "graphrag_component.py")
        self.assertTrue(os.path.exists(component_path), "Component file was not created")

    def test_create_workflow(self):
        """Test workflow creation."""
        # Define test data
        workflow_id = "test_workflow"
        steps = [{"type": "graphrag_query", "question": "What is GraphRAG?"}]
        tenant_id = "test_tenant"

        # Call method under test
        result = self.adapter.create_workflow(
            workflow_id=workflow_id,
            steps=steps,
            tenant_id=tenant_id
        )

        # Verify results
        self.assertEqual(result, workflow_id)
        self.mock_workflow_orchestrator.register_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            steps=steps,
            framework="langflow",
            tenant_id=tenant_id
        )

    def test_execute_workflow(self):
        """Test workflow execution."""
        # Define test data
        workflow_id = "test_workflow"
        input_data = {"query": "What is GraphRAG?"}
        tenant_id = "test_tenant"
        expected_result = {"status": "completed", "result": "Test result"}

        # Configure mock
        self.mock_workflow_orchestrator.execute_workflow.return_value = expected_result

        # Call method under test
        result = self.adapter.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id=tenant_id
        )

        # Verify results
        self.assertEqual(result, expected_result)
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id=tenant_id
        )

    def test_execute_workflow_error_handling(self):
        """Test workflow execution error handling."""
        # Define test data
        workflow_id = "test_workflow"
        input_data = {"query": "What is GraphRAG?"}

        # Configure mock to raise exception
        self.mock_workflow_orchestrator.execute_workflow.side_effect = ValueError("Test error")

        # Call method under test
        result = self.adapter.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data
        )

        # Verify error handling
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["workflow_id"], workflow_id)
        self.assertEqual(result["error"], "Test error")
        self.assertEqual(result["framework"], "langflow")

    def test_export_workflow_as_python(self):
        """Test workflow export as Python code."""
        # Define test data
        workflow_id = "test_workflow"
        workflow = {
            "id": workflow_id,
            "framework": "langflow",
            "tenant_id": "test_tenant",
            "steps": [{"type": "graphrag_query", "question": "What is GraphRAG?"}]
        }

        # Configure mock
        self.mock_workflow_orchestrator.registered_workflows = {workflow_id: workflow}

        # Call method under test
        result = self.adapter.export_workflow_as_code(
            workflow_id=workflow_id,
            format="python"
        )

        # Verify results
        self.assertEqual(result["workflow_id"], workflow_id)
        self.assertEqual(result["format"], "python")
        self.assertIn("# Generated by GraphRAG Ontology Application", result["code"])
        self.assertEqual(result["file_extension"], "py")

    def test_export_workflow_as_notebook(self):
        """Test workflow export as Jupyter notebook."""
        # Define test data
        workflow_id = "test_workflow"
        workflow = {
            "id": workflow_id,
            "framework": "langflow",
            "tenant_id": "test_tenant",
            "steps": [{"type": "graphrag_query", "question": "What is GraphRAG?"}]
        }

        # Configure mock
        self.mock_workflow_orchestrator.registered_workflows = {workflow_id: workflow}

        # Call method under test
        result = self.adapter.export_workflow_as_code(
            workflow_id=workflow_id,
            format="notebook"
        )

        # Verify results
        self.assertEqual(result["workflow_id"], workflow_id)
        self.assertEqual(result["format"], "notebook")

        # Parse notebook JSON
        notebook = json.loads(result["code"])
        self.assertIn("cells", notebook)
        self.assertIn("metadata", notebook)
        self.assertEqual(result["file_extension"], "ipynb")

    def test_query_knowledge_graph(self):
        """Test knowledge graph querying."""
        # Define test data
        question = "What is GraphRAG?"
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        expected_result = {"results": ["Test result"], "explanation": "Test explanation"}

        # Configure mock
        self.mock_query_service.execute_natural_language_query.return_value = expected_result

        # Call method under test
        result = self.adapter.query_knowledge_graph(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id
        )

        # Verify results
        self.assertEqual(result, expected_result)
        self.mock_query_service.execute_natural_language_query.assert_called_once_with(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            user_id="langflow_user",
            include_explanation=True,
            query_opts=None
        )

    def test_query_knowledge_graph_error_handling(self):
        """Test knowledge graph querying error handling."""
        # Define test data
        question = "What is GraphRAG?"

        # Configure mock to raise exception
        self.mock_query_service.execute_natural_language_query.side_effect = ValueError("Test error")

        # Call method under test
        result = self.adapter.query_knowledge_graph(
            question=question
        )

        # Verify error handling
        self.assertEqual(result["results"], [])
        self.assertIn("Query execution failed", result["explanation"])
        self.assertTrue(result["metadata"]["error"])

    def test_index_documents(self):
        """Test document indexing."""
        # Define test data
        docs = ["Test document"]
        kg_id = "test_kg"
        tenant_id = "test_tenant"

        # Configure mock
        from domain.entities import Triple
        mock_triples = [Triple(subject="entity1", predicate="has_content", object="Test document", tenant_id=tenant_id)]
        self.mock_graph_retriever.index.return_value = mock_triples

        # Call method under test
        result = self.adapter.index_documents(
            docs=docs,
            kg_id=kg_id,
            tenant_id=tenant_id
        )

        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["triple_count"], 1)
        self.assertEqual(result["kg_id"], kg_id)
        self.assertEqual(result["tenant_id"], tenant_id)
        self.mock_graph_retriever.index.assert_called_once_with(
            docs=docs,
            kg_id=kg_id,
            tenant_id=tenant_id
        )

    def test_index_documents_error_handling(self):
        """Test document indexing error handling."""
        # Define test data
        docs = ["Test document"]

        # Configure mock to raise exception
        self.mock_graph_retriever.index.side_effect = ValueError("Test error")

        # Call method under test
        result = self.adapter.index_documents(
            docs=docs
        )

        # Verify error handling
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Test error")

    def test_index_documents_with_validation(self):
        """Test document indexing with validation service."""
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
            Triple(subject="a", predicate="b", object="c", tenant_id="test_tenant")
        ]

        result = self.adapter.index_documents(docs=docs, tenant_id="test_tenant")

        ingestion_service.process_documents.assert_called_once()
        self.assertTrue(result["validation"]["performed"])
        self.assertTrue(result["validation"]["report"]["is_consistent"])

    def test_convert_steps_to_langflow(self):
        """Test conversion of steps to Langflow JSON."""
        steps = [{"type": "a"}, {"type": "b"}]
        result = self.adapter._convert_steps_to_langflow(steps)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(len(result["edges"]), 1)
        self.assertEqual(result["edges"][0]["source"], "node_0")
        self.assertEqual(result["edges"][0]["target"], "node_1")


class TestGraphRagComponent(unittest.TestCase):
    """Test suite for GraphRAG Langflow component."""

    def setUp(self):
        """Set up test environment."""
        # Create component instance
        self.component = GraphRagComponent()

        # Create mock dependencies
        self.mock_graph_retriever = MagicMock()
        self.mock_query_service = MagicMock()

        # Inject mock dependencies
        self.component.graph_retriever = self.mock_graph_retriever
        self.component.query_service = self.mock_query_service

    def test_build_config(self):
        """Test component configuration building."""
        # Call method under test
        config = self.component.build_config()

        # Verify configuration
        self.assertIn("operation", config)
        self.assertIn("input", config)
        self.assertIn("kg_id", config)
        self.assertIn("tenant_id", config)
        self.assertIn("options", config)

    def test_build_query_operation(self):
        """Test component build with query operation."""
        # Define test data
        operation = "query"
        input_text = "What is GraphRAG?"
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        options = "{}"
        expected_result = {"results": ["Test result"], "explanation": "Test explanation"}

        # Configure mock
        self.mock_query_service.execute_natural_language_query.return_value = expected_result

        # Call method under test
        result = self.component.build(
            operation=operation,
            input=input_text,
            kg_id=kg_id,
            tenant_id=tenant_id,
            options=options
        )

        # Verify results
        self.assertEqual(result, expected_result)
        self.mock_query_service.execute_natural_language_query.assert_called_once()

    def test_build_index_operation(self):
        """Test component build with index operation."""
        # Define test data
        operation = "index"
        input_text = "Test document"
        kg_id = "test_kg"
        tenant_id = "test_tenant"
        options = "{}"

        # Configure mock
        from domain.entities import Triple
        mock_triples = [Triple(subject="entity1", predicate="has_content", object="Test document", tenant_id=tenant_id)]
        self.mock_graph_retriever.index.return_value = mock_triples

        # Call method under test
        result = self.component.build(
            operation=operation,
            input=input_text,
            kg_id=kg_id,
            tenant_id=tenant_id,
            options=options
        )

        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["triple_count"], 1)
        self.assertEqual(result["kg_id"], kg_id)
        self.assertEqual(result["tenant_id"], tenant_id)
        self.mock_graph_retriever.index.assert_called_once()

    def test_build_invalid_operation(self):
        """Test component build with invalid operation."""
        # Define test data
        operation = "invalid"
        input_text = "Test input"

        # Call method under test
        result = self.component.build(
            operation=operation,
            input=input_text
        )

        # Verify error handling
        self.assertEqual(result["status"], "error")
        self.assertIn("Unsupported operation", result["error"])

    def test_build_error_handling(self):
        """Test component build error handling."""
        # Define test data
        operation = "query"
        input_text = "What is GraphRAG?"

        # Configure mock to raise exception
        self.mock_query_service.execute_natural_language_query.side_effect = ValueError("Test error")

        # Call method under test
        result = self.component.build(
            operation=operation,
            input=input_text
        )

        # Verify error handling
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Test error")
        self.assertEqual(result["operation"], "query")


if __name__ == "__main__":
    unittest.main()