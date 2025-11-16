"""Tests for N8nGraphRAGAdapter."""

from unittest.mock import MagicMock
import unittest

from domain.services import WorkflowOrchestrator, QueryService
from ui_adapters.n8n.n8n_adapter import N8nGraphRAGAdapter


class TestN8nAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_query_service = MagicMock(spec=QueryService)
        self.mock_workflow_orchestrator = MagicMock(spec=WorkflowOrchestrator)
        self.mock_graph_retriever = MagicMock()
        self.mock_query_translator = MagicMock()
        self.mock_n8n_client = MagicMock()

        self.adapter = N8nGraphRAGAdapter(
            query_service=self.mock_query_service,
            workflow_orchestrator=self.mock_workflow_orchestrator,
            graph_retriever=self.mock_graph_retriever,
            query_translator=self.mock_query_translator,
            n8n_client=self.mock_n8n_client,
        )

    def test_create_workflow_registers_with_orchestrator(self):
        workflow_id = "wf1"
        steps = [{"type": "graphrag_query", "question": "hi"}]
        result = self.adapter.create_workflow(workflow_id=workflow_id, steps=steps)
        self.assertEqual(result, workflow_id)
        self.mock_workflow_orchestrator.register_workflow.assert_called_once()

    def test_execute_workflow_uses_orchestrator(self):
        workflow_id = "wf1"
        input_data = {"param": 1}
        self.adapter.execute_workflow(workflow_id=workflow_id, input_data=input_data)
        self.mock_workflow_orchestrator.execute_workflow.assert_called_once_with(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id="default",
        )

    def test_query_knowledge_graph_delegates_to_service(self):
        self.mock_query_service.execute_natural_language_query.return_value = {
            "ok": True
        }
        result = self.adapter.query_knowledge_graph(question="q")
        self.assertTrue(result["ok"])
        self.mock_query_service.execute_natural_language_query.assert_called_once()

    def test_run_query_alias(self):
        self.mock_query_service.execute_natural_language_query.return_value = {
            "ok": True
        }
        result = self.adapter.run_query(question="hello")
        self.assertTrue(result["ok"])
        self.mock_query_service.execute_natural_language_query.assert_called_once()

    def test_index_documents(self):
        docs = ["Doc1", "Doc2"]
        self.mock_graph_retriever.index.return_value = ["t1", "t2"]
        result = self.adapter.index_documents(docs=docs)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["triple_count"], 2)
        self.mock_graph_retriever.index.assert_called_once_with(
            docs=docs,
            kg_id="default",
            tenant_id="default",
        )

    def test_trigger_n8n_workflow(self):
        self.mock_n8n_client.login.return_value.cookies.get.return_value = "sid"
        self.mock_n8n_client.execute_node.return_value = {"ok": True}

        result = self.adapter.trigger_n8n_workflow(workflow_id=1)

        self.assertEqual(result, {"ok": True})
        self.mock_n8n_client.login.assert_called_once()
        self.mock_n8n_client.execute_node.assert_called_once_with(
            workflow_id=1,
            node_name="Start",
            session_id="sid",
        )


if __name__ == "__main__":
    unittest.main()
