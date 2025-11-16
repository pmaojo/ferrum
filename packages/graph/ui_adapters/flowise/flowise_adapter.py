"""
Flowise AI adapter for GraphRAG Ontology Application.

This module provides integration between the GraphRAG Ontology Application
and the Flowise AI framework, enabling knowledge graph querying and workflow
orchestration through the Flowise canvas.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from ..registration_utils import copy_items, ensure_directory

from domain.entities import Triple
from application.ports import (
    GraphRetrieverPort,
    QueryTranslatorPort,
    WorkflowOrchestratorPort,
    FlowiseAdapterPort,
)
from domain.services import WorkflowOrchestrator, QueryService, IngestionService
from domain.exceptions import GraphRAGException

# Configure logging
logger = logging.getLogger(__name__)


class FlowiseGraphRAGAdapter(FlowiseAdapterPort):
    """Flowise adapter for GraphRAG Ontology Application.

    This adapter provides integration with the Flowise AI framework,
    exposing GraphRAG functionality as a custom node in the Flowise canvas.
    """

    def __init__(
        self,
        query_service: QueryService,
        workflow_orchestrator: WorkflowOrchestratorPort,
        graph_retriever: GraphRetrieverPort,
        query_translator: QueryTranslatorPort,
        default_kg_id: str = "default",
        default_tenant_id: str = "default",
        node_directory: Optional[str] = None,
        ingestion_service: Optional[IngestionService] = None,
    ):
        """Initialize Flowise GraphRAG adapter.

        Args:
            query_service: Domain service for query processing
            workflow_orchestrator: Domain service for workflow orchestration
            graph_retriever: Port for GraphRAG operations
            query_translator: Port for query translation
            default_kg_id: Default knowledge graph ID
            default_tenant_id: Default tenant ID
            node_directory: Directory for Flowise node registration
        """
        self.query_service = query_service
        self.workflow_orchestrator = workflow_orchestrator
        self.graph_retriever = graph_retriever
        self.query_translator = query_translator
        self.default_kg_id = default_kg_id
        self.default_tenant_id = default_tenant_id
        self.node_directory = node_directory or self._get_default_node_directory()
        self.ingestion_service = ingestion_service

        # Register Flowise node
        self._register_node()

    def _get_default_node_directory(self) -> str:
        """Get default Flowise node directory.

        Returns:
            Path to default node directory
        """
        # Check common Flowise installation locations
        possible_paths = [
            os.path.expanduser("~/.flowise/custom-nodes"),
            "/usr/local/lib/node_modules/flowise/custom-nodes",
            "./flowise/custom-nodes",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Default to current directory if no Flowise installation found
        return "./flowise-nodes"

    def _register_node(self) -> None:
        """Register GraphRAG nodes with Flowise.

        Copies the GraphRagNode and GeminiGraphRAGNode implementations to the Flowise
        custom nodes directory for automatic discovery and registration.
        """
        try:
            node_path = ensure_directory(Path(self.node_directory) / "graphrag")

            current_dir = Path(__file__).parent
            node_file_map = {
                current_dir / "graphrag_node.js": node_path / "graphrag_node.js",
            }
            copy_items(
                {str(src): str(dst) for src, dst in node_file_map.items()},
                logger=logger,
            )

            package_json = {
                "name": "flowise-graphrag-node",
                "version": "1.0.0",
                "description": "GraphRAG node for Flowise AI",
                "main": "graphrag_node.js",
                "author": "GraphRAG Ontology Application",
                "license": "MIT",
                "dependencies": {},
            }
            with open(node_path / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)

            self._create_icon_file(node_path)
            logger.info(f"GraphRAG node registered with Flowise at {node_path}")

            gemini_js = current_dir / "gemini_graphrag_node.js"
            if gemini_js.exists():
                gemini_node_path = ensure_directory(
                    Path(self.node_directory) / "gemini-graphrag"
                )
                gemini_file_map = {
                    gemini_js: gemini_node_path / "gemini_graphrag_node.js",
                }
                copy_items(
                    {str(src): str(dst) for src, dst in gemini_file_map.items()},
                    logger=logger,
                )

                package_json = {
                    "name": "flowise-gemini-graphrag-node",
                    "version": "1.0.0",
                    "description": "Gemini GraphRAG node for Flowise AI",
                    "main": "gemini_graphrag_node.js",
                    "author": "GraphRAG Ontology Application",
                    "license": "MIT",
                    "dependencies": {},
                }
                with open(gemini_node_path / "package.json", "w") as f:
                    json.dump(package_json, f, indent=2)

                gemini_svg = current_dir / "gemini.svg"
                if gemini_svg.exists():
                    copy_items(
                        {str(gemini_svg): str(gemini_node_path / "gemini.svg")},
                        logger=logger,
                    )
                else:
                    self._create_icon_file(gemini_node_path)
                logger.info(
                    f"Gemini GraphRAG node registered with Flowise at {gemini_node_path}"
                )
            else:
                logger.error(
                    f"Gemini GraphRAG node implementation not found at {gemini_js}"
                )
        except Exception as e:
            logger.error(
                f"Failed to register GraphRAG nodes with Flowise: {str(e)}",
                exc_info=True,
            )

    def _create_icon_file(self, node_path: str) -> None:
        """Create SVG icon file for the GraphRAG node.

        Args:
            node_path: Path to node directory
        """
        # Simple graph icon SVG
        icon_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="5" cy="6" r="3"></circle>
            <circle cx="12" cy="18" r="3"></circle>
            <circle cx="19" cy="6" r="3"></circle>
            <line x1="5" y1="9" x2="12" y2="15"></line>
            <line x1="12" y1="15" x2="19" y2="9"></line>
            <line x1="5" y1="6" x2="19" y2="6"></line>
        </svg>"""

        with open(os.path.join(node_path, "graphrag.svg"), "w") as f:
            f.write(icon_svg)

    def create_workflow(
        self,
        *,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> str:
        """Create a new workflow for Flowise integration.

        Args:
            workflow_id: Unique identifier for the workflow
            steps: List of workflow steps with their configurations
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Workflow ID for future reference

        Raises:
            ValueError: When workflow creation fails
        """
        try:
            # Register workflow with orchestrator
            self.workflow_orchestrator.register_workflow(
                workflow_id=workflow_id,
                steps=steps,
                framework="flowise",
                tenant_id=tenant_id or self.default_tenant_id,
            )

            logger.info(
                f"Created Flowise workflow: id={workflow_id}, steps={len(steps)}"
            )
            return workflow_id

        except Exception as e:
            logger.error(f"Failed to create Flowise workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow creation failed: {str(e)}")

    def execute_workflow(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        async_execution: bool = False,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a registered workflow with provided input data.

        Args:
            workflow_id: Identifier for the registered workflow
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation
            async_execution: Whether to execute asynchronously
            callback_url: Optional URL for execution completion callback

        Returns:
            Dictionary containing workflow execution results

        Raises:
            ValueError: When workflow execution fails
        """
        try:
            # Execute workflow through orchestrator
            result = self.workflow_orchestrator.execute_workflow(
                workflow_id=workflow_id,
                input_data=input_data,
                tenant_id=tenant_id or self.default_tenant_id,
                async_execution=async_execution,
                callback_url=callback_url,
            )

            logger.info(
                f"Executed Flowise workflow: id={workflow_id}, status={result.get('status')}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to execute Flowise workflow: {str(e)}", exc_info=True)

            # Return error response instead of raising exception
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "framework": "flowise",
            }

    def execute_workflow_with_fallback(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        fallback_workflow_id: str,
        tenant_id: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 2,
    ) -> Dict[str, Any]:
        """Execute a workflow with automatic fallback to another workflow if execution fails.

        Args:
            workflow_id: Primary workflow identifier
            input_data: Input data for workflow execution
            fallback_workflow_id: Fallback workflow to execute on failure
            tenant_id: Tenant identifier for multi-tenant isolation
            max_retries: Maximum number of retry attempts before using fallback
            retry_delay_seconds: Delay between retry attempts in seconds

        Returns:
            Workflow execution results or fallback results
        """
        try:
            # Execute with fallback through orchestrator
            result = self.workflow_orchestrator.execute_with_fallback(
                workflow_id=workflow_id,
                input_data=input_data,
                tenant_id=tenant_id or self.default_tenant_id,
                fallback_workflow_id=fallback_workflow_id,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
            )

            logger.info(
                f"Executed Flowise workflow with fallback: id={workflow_id}, "
                f"fallback={fallback_workflow_id}, status={result.get('status')}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to execute Flowise workflow with fallback: {str(e)}",
                exc_info=True,
            )

            # Return error response instead of raising exception
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "framework": "flowise",
                "fallback_attempted": True,
            }

    def execute_parallel_workflows(
        self,
        *,
        workflow_configs: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        timeout_seconds: int = 60,
        aggregate_results: bool = True,
    ) -> Dict[str, Any]:
        """Execute multiple workflows in parallel and optionally aggregate results.

        Args:
            workflow_configs: List of workflow configurations with workflow_id and input_data
            tenant_id: Tenant identifier for multi-tenant isolation
            timeout_seconds: Maximum execution time in seconds
            aggregate_results: Whether to aggregate results into a single response

        Returns:
            Dictionary containing execution results for all workflows
        """
        try:
            # Execute parallel workflows through orchestrator
            result = self.workflow_orchestrator.execute_parallel_workflows(
                workflow_configs=workflow_configs,
                tenant_id=tenant_id or self.default_tenant_id,
                timeout_seconds=timeout_seconds,
                aggregate_results=aggregate_results,
            )

            logger.info(
                f"Executed {len(workflow_configs)} Flowise workflows in parallel, "
                f"completed: {result.get('completed_count', 0)}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to execute parallel Flowise workflows: {str(e)}", exc_info=True
            )

            # Return error response instead of raising exception
            return {
                "status": "failed",
                "error": str(e),
                "framework": "flowise",
                "workflow_count": len(workflow_configs),
            }

    def query_knowledge_graph(
        self,
        *,
        question: str,
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the knowledge graph using natural language.

        This method is exposed to the Flowise GraphRAG node for direct querying
        without going through a workflow.

        Args:
            question: Natural language query
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            opts: Optional query parameters

        Returns:
            Query results as formatted dictionary

        Raises:
            ValueError: When query execution fails
        """
        try:
            # Execute query through query service
            result = self.query_service.execute_natural_language_query(
                question=question,
                kg_id=kg_id or self.default_kg_id,
                tenant_id=tenant_id or self.default_tenant_id,
                user_id="flowise_user",  # Could be enhanced with actual user ID
                include_explanation=True,
                query_opts=opts,
            )

            logger.info(
                f"Executed Flowise query: '{question[:50]}...' (kg_id={kg_id or self.default_kg_id})"
            )
            return result

        except GraphRAGException as e:
            logger.error("Failed to execute Flowise query: %s", e, exc_info=True)

            return {
                "results": [],
                "explanation": f"Query execution failed: {e.message}",
                "metadata": {"error": True, "error_type": e.error_code},
                "context": e.context,
                "suggestions": [
                    "Try rephrasing your question",
                    "Check if the knowledge graph contains relevant information",
                ],
            }
        except Exception as e:
            logger.error("Failed to execute Flowise query: %s", e, exc_info=True)

            return {
                "results": [],
                "explanation": f"Query execution failed: {str(e)}",
                "metadata": {"error": True, "error_type": type(e).__name__},
                "suggestions": [
                    "Try rephrasing your question",
                    "Check if the knowledge graph contains relevant information",
                ],
            }

    def index_documents(
        self,
        *,
        docs: List[str],
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        validate: bool = True,
        ontology_version_id: str = "latest",
    ) -> Dict[str, Any]:
        """Index documents into the knowledge graph.

        This method is exposed to the Flowise GraphRAG node for document indexing
        without going through a workflow.

        Args:
            docs: List of document content strings
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            validate: Whether to validate extracted triples
            ontology_version_id: Ontology version for validation

        Returns:
            Indexing results as formatted dictionary

        Raises:
            ValueError: When document indexing fails
        """
        try:
            # Extract triples using GraphRAG
            triples = self.graph_retriever.index(
                docs=docs,
                kg_id=kg_id or self.default_kg_id,
                tenant_id=tenant_id or self.default_tenant_id,
            )

            result = {
                "status": "success",
                "triple_count": len(triples),
                "kg_id": kg_id or self.default_kg_id,
                "tenant_id": tenant_id or self.default_tenant_id,
            }

            # Add validation information if requested
            if validate and triples:
                from domain.entities import Document

                documents = [
                    Document(
                        id=f"doc_{i}",
                        content=doc,
                        metadata={},
                        processed_at=None,
                        extraction_status="extracted",
                        tenant_id=tenant_id or self.default_tenant_id,
                    )
                    for i, doc in enumerate(docs)
                ]

                if self.ingestion_service:
                    report = self.ingestion_service.process_documents(
                        documents=documents,
                        kg_id=kg_id or self.default_kg_id,
                        tenant_id=tenant_id or self.default_tenant_id,
                        ontology_version_id=ontology_version_id,
                    )
                    result["validation"] = {
                        "performed": True,
                        "report": report._asdict(),
                    }
                else:
                    result["validation"] = {
                        "performed": False,
                        "message": "IngestionService not configured",
                    }

            logger.info(
                f"Indexed documents through Flowise: count={len(docs)}, "
                f"triples={len(triples)}, kg_id={kg_id or self.default_kg_id}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to index documents through Flowise: {str(e)}", exc_info=True
            )

            # Return error response instead of raising exception
            return {
                "status": "failed",
                "error": str(e),
                "kg_id": kg_id or self.default_kg_id,
                "tenant_id": tenant_id or self.default_tenant_id,
            }

    def orchestrator(self) -> WorkflowOrchestratorPort:
        """Return the underlying workflow orchestrator."""
        return self.workflow_orchestrator
