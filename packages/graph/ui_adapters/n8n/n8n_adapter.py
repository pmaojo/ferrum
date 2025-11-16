"""n8n integration adapter for GraphRAG Ontology Application."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from n8n.client import Client
except Exception:  # pragma: no cover - fallback stub
    from infrastructure.stubs.n8n.client import Client

from application.ports import GraphRetrieverPort, QueryTranslatorPort
from domain.services import WorkflowOrchestrator, QueryService
from domain.exceptions import GraphRAGException

logger = logging.getLogger(__name__)


class N8nGraphRAGAdapter:
    """Adapter integrating GraphRAG workflows with n8n."""

    def __init__(
        self,
        *,
        query_service: QueryService,
        workflow_orchestrator: WorkflowOrchestrator,
        graph_retriever: GraphRetrieverPort,
        query_translator: QueryTranslatorPort,
        n8n_client: Optional[Client] = None,
        default_kg_id: str = "default",
        default_tenant_id: str = "default",
    ) -> None:
        self.query_service = query_service
        self.workflow_orchestrator = workflow_orchestrator
        self.graph_retriever = graph_retriever
        self.query_translator = query_translator
        self.n8n_client = n8n_client or Client()
        self.default_kg_id = default_kg_id
        self.default_tenant_id = default_tenant_id

    # ------------------------------------------------------------------
    # Workflow orchestration helpers
    # ------------------------------------------------------------------
    def create_workflow(
        self,
        *,
        workflow_id: str,
        steps: list[dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> str:
        """Register workflow locally and in n8n."""
        self.workflow_orchestrator.register_workflow(
            workflow_id=workflow_id,
            steps=steps,
            framework="n8n",
            tenant_id=tenant_id or self.default_tenant_id,
        )

        try:
            self.n8n_client.create_workflow(name=workflow_id)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to create workflow in n8n: %s", exc)

        return workflow_id

    def execute_workflow(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute workflow through the orchestrator."""
        return self.workflow_orchestrator.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id=tenant_id or self.default_tenant_id,
        )

    # ------------------------------------------------------------------
    # n8n specific operations
    # ------------------------------------------------------------------
    def trigger_n8n_workflow(self, *, workflow_id: int) -> Dict[str, Any]:
        """Execute a workflow directly on the n8n server."""
        try:
            session = self.n8n_client.login()
            session_id = session.cookies.get("sessionid", "")
            result = self.n8n_client.execute_node(
                workflow_id=workflow_id,
                node_name="Start",
                session_id=session_id,
            )
            return result
        except Exception as exc:
            logger.error("Failed to trigger n8n workflow: %s", exc, exc_info=True)
            return {"status": "failed", "error": str(exc)}

    # ------------------------------------------------------------------
    # Direct query/index operations
    # ------------------------------------------------------------------
    def query_knowledge_graph(
        self,
        *,
        question: str,
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a natural language query against the knowledge graph."""
        try:
            return self.query_service.execute_natural_language_query(
                question=question,
                kg_id=kg_id or self.default_kg_id,
                tenant_id=tenant_id or self.default_tenant_id,
                user_id="n8n_user",
                include_explanation=True,
                query_opts=opts,
            )
        except GraphRAGException as exc:
            logger.error("Query failed: %s", exc, exc_info=True)
            return {
                "results": [],
                "explanation": f"Query execution failed: {exc.message}",
                "metadata": {"error": True, "error_type": exc.error_code},
                "context": exc.context,
            }
        except Exception as exc:
            logger.error("Query failed: %s", exc, exc_info=True)
            return {
                "results": [],
                "explanation": f"Query execution failed: {exc}",
                "metadata": {"error": True, "error_type": type(exc).__name__},
            }

    def run_query(
        self,
        *,
        question: str,
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for :meth:`query_knowledge_graph`."""
        return self.query_knowledge_graph(
            question=question,
            kg_id=kg_id,
            tenant_id=tenant_id,
            opts=opts,
        )

    def index_documents(
        self,
        *,
        docs: list[str],
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Index documents through the graph retriever."""
        try:
            triples = self.graph_retriever.index(
                docs=docs,
                kg_id=kg_id or self.default_kg_id,
                tenant_id=tenant_id or self.default_tenant_id,
            )
            return {
                "status": "success",
                "triple_count": len(triples),
                "kg_id": kg_id or self.default_kg_id,
            }
        except Exception as exc:
            logger.error("Indexing failed: %s", exc, exc_info=True)
            return {
                "status": "failed",
                "error": str(exc),
                "kg_id": kg_id or self.default_kg_id,
            }

    def index(
        self,
        *,
        docs: list[str],
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Alias for :meth:`index_documents` for clearer naming."""
        return self.index_documents(docs=docs, kg_id=kg_id, tenant_id=tenant_id)

    def trigger_workflow(self, *, workflow_id: int) -> Dict[str, Any]:
        """Alias for :meth:`trigger_n8n_workflow`."""
        return self.trigger_n8n_workflow(workflow_id=workflow_id)
