"""
Langflow adapter for GraphRAG Ontology Application.

This module provides integration between the GraphRAG Ontology Application
and the Langflow framework, enabling knowledge graph querying and workflow
orchestration through the Langflow canvas.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..registration_utils import copy_items, ensure_directory

from application.ports import GraphRetrieverPort, QueryTranslatorPort
from domain.entities import Triple
from domain.services import IngestionService, QueryService, WorkflowOrchestrator
from domain.exceptions import GraphRAGException

# Configure logging
logger = logging.getLogger(__name__)


class LangflowGraphRAGAdapter:
    """Langflow adapter for GraphRAG Ontology Application.

    This adapter provides integration with the Langflow framework,
    exposing GraphRAG functionality as a Python component in the Langflow canvas.
    """

    def __init__(
        self,
        query_service: QueryService,
        workflow_orchestrator: WorkflowOrchestrator,
        graph_retriever: GraphRetrieverPort,
        query_translator: QueryTranslatorPort,
        default_kg_id: str = "default",
        default_tenant_id: str = "default",
        component_directory: Optional[str] = None,
        ingestion_service: Optional[IngestionService] = None,
    ):
        """Initialize Langflow GraphRAG adapter.

        Args:
            query_service: Domain service for query processing
            workflow_orchestrator: Domain service for workflow orchestration
            graph_retriever: Port for GraphRAG operations
            query_translator: Port for query translation
            default_kg_id: Default knowledge graph ID
            default_tenant_id: Default tenant ID
            component_directory: Directory for Langflow component registration
        """
        self.query_service = query_service
        self.workflow_orchestrator = workflow_orchestrator
        self.graph_retriever = graph_retriever
        self.query_translator = query_translator
        self.default_kg_id = default_kg_id
        self.default_tenant_id = default_tenant_id
        self.component_directory = (
            component_directory or self._get_default_component_directory()
        )
        self.ingestion_service = ingestion_service

        # Register Langflow component
        self._register_component()

    def _get_default_component_directory(self) -> str:
        """Get default Langflow component directory.

        Returns:
            Path to default component directory
        """
        # Check common Langflow installation locations
        possible_paths = [
            os.path.expanduser("~/.langflow/components"),
            "/usr/local/lib/python3.*/site-packages/langflow/components/custom",
            "./langflow/components/custom",
        ]

        for path_pattern in possible_paths:
            # Handle wildcard paths
            if "*" in path_pattern:
                import glob

                matching_paths = glob.glob(path_pattern)
                if matching_paths:
                    return matching_paths[0]
            elif os.path.exists(path_pattern):
                return path_pattern

        # Default to current directory if no Langflow installation found
        return "./langflow-components"

    def _register_component(self) -> None:
        """Register GraphRAG components with Langflow.

        Copies the GraphRagComponent and GeminiGraphRagComponent implementations
        to the Langflow components directory for automatic discovery and registration.
        """
        try:
            ensure_directory(self.component_directory)

            current_dir = Path(__file__).parent
            file_map = {
                current_dir
                / "graphrag_component.py": Path(self.component_directory)
                / "graphrag_component.py",
                current_dir
                / "gemini_graphrag_component.py": Path(self.component_directory)
                / "gemini_graphrag_component.py",
                current_dir
                / "gemini_icon.svg": Path(self.component_directory)
                / "gemini_icon.svg",
            }

            copy_items(
                {str(src): str(dst) for src, dst in file_map.items()}, logger=logger
            )

            logger.info(
                "GraphRAG components registered with Langflow at %s",
                self.component_directory,
            )

        except Exception as e:
            logger.error(
                f"Failed to register GraphRAG components with Langflow: {str(e)}",
                exc_info=True,
            )

    def create_workflow(
        self,
        *,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> str:
        """Create a new workflow for Langflow integration.

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
                framework="langflow",
                tenant_id=tenant_id or self.default_tenant_id,
            )

            logger.info(
                f"Created Langflow workflow: id={workflow_id}, steps={len(steps)}"
            )
            return workflow_id

        except Exception as e:
            logger.error(f"Failed to create Langflow workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow creation failed: {str(e)}")

    def execute_workflow(
        self,
        *,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a registered workflow with provided input data.

        Args:
            workflow_id: Identifier for the registered workflow
            input_data: Input data for workflow execution
            tenant_id: Tenant identifier for multi-tenant isolation

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
            )

            logger.info(
                f"Executed Langflow workflow: id={workflow_id}, status={result.get('status')}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to execute Langflow workflow: {str(e)}", exc_info=True
            )

            # Return error response instead of raising exception
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "framework": "langflow",
            }

    def export_workflow_as_code(
        self,
        *,
        workflow_id: str,
        format: str = "python",
        include_imports: bool = True,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a workflow as executable code.

        Args:
            workflow_id: Workflow identifier to export
            format: Code format ("python", "notebook", or "yaml")
            include_imports: Whether to include import statements
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            Dictionary containing exported code and metadata

        Raises:
            ValueError: When workflow export fails
        """
        try:
            # Verify workflow exists
            if workflow_id not in self.workflow_orchestrator.registered_workflows:
                raise ValueError(f"Workflow not found: {workflow_id}")

            workflow = self.workflow_orchestrator.registered_workflows[workflow_id]
            tenant_id = tenant_id or workflow["tenant_id"]

            # Generate code based on format
            if format == "python":
                code = self._generate_python_code(workflow, include_imports)
                file_extension = "py"
            elif format == "notebook":
                code = self._generate_notebook_code(workflow, include_imports)
                file_extension = "ipynb"
            elif format == "yaml":
                code = self._generate_yaml_code(workflow)
                file_extension = "yaml"
            else:
                raise ValueError(f"Unsupported export format: {format}")

            logger.info(
                f"Exported Langflow workflow: id={workflow_id}, format={format}"
            )

            return {
                "workflow_id": workflow_id,
                "format": format,
                "code": code,
                "file_extension": file_extension,
                "metadata": {
                    "framework": "langflow",
                    "tenant_id": tenant_id,
                    "step_count": len(workflow["steps"]),
                    "exported_at": str(datetime.now()),
                },
            }

        except Exception as e:
            logger.error(f"Failed to export Langflow workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow export failed: {str(e)}")

    def _generate_python_code(
        self, workflow: Dict[str, Any], include_imports: bool
    ) -> str:
        """Generate Python code from workflow configuration.

        Args:
            workflow: Workflow configuration
            include_imports: Whether to include import statements

        Returns:
            Generated Python code as string
        """
        code_lines = []

        # Add imports if requested
        if include_imports:
            code_lines.extend(
                [
                    "# Generated by GraphRAG Ontology Application",
                    "# Langflow workflow export",
                    "",
                    "from langflow import load_flow_from_json",
                    "from langflow.graph import Graph",
                    "import json",
                    "",
                ]
            )

        # Add workflow definition
        code_lines.extend(
            [
                f"# Workflow: {workflow.get('id', 'unnamed')}",
                "workflow_definition = {",
                f"    \"id\": \"{workflow.get('id', 'unnamed')}\",",
                f"    \"framework\": \"{workflow.get('framework', 'langflow')}\",",
                '    "steps": [',
            ]
        )

        # Add steps
        for i, step in enumerate(workflow["steps"]):
            step_json = json.dumps(step, indent=4).replace("\n", "\n        ")
            code_lines.append(
                f"        {step_json}{'' if i == len(workflow['steps']) - 1 else ','}"
            )

        code_lines.extend(
            [
                "    ]",
                "}",
                "",
                "# Load and execute workflow",
                "def execute_workflow(input_data):",
                "    # Convert workflow definition to Langflow format",
                "    langflow_json = {",
                '        "nodes": [],',
                '        "edges": []',
                "    }",
                "    for idx, step in enumerate(workflow_definition['steps']):",
                "        node_id = f'node_{idx}'",
                "        langflow_json['nodes'].append({'id': node_id, 'data': step})",
                "        if idx > 0:",
                "            langflow_json['edges'].append({'source': f'node_{idx-1}', 'target': node_id})",
                "    # Load and execute flow",
                "    graph = Graph.from_payload(langflow_json)",
                "    result = graph.build()",
                "    return result",
                "",
                "# Example usage",
                'if __name__ == "__main__":',
                '    input_data = {"query": "What is GraphRAG?"}',
                "    result = execute_workflow(input_data)",
                "    import logging",
                "    logging.getLogger(__name__).info(result)",
            ]
        )

        return "\n".join(code_lines)

    def _generate_notebook_code(
        self, workflow: Dict[str, Any], include_imports: bool
    ) -> str:
        """Generate Jupyter notebook from workflow configuration.

        Args:
            workflow: Workflow configuration
            include_imports: Whether to include import statements

        Returns:
            Generated notebook JSON as string
        """
        cells = []

        # Add imports cell if requested
        if include_imports:
            cells.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "source": [
                        "# Generated by GraphRAG Ontology Application\n",
                        "# Langflow workflow export\n",
                        "\n",
                        "from langflow import load_flow_from_json\n",
                        "from langflow.graph import Graph\n",
                        "import json",
                    ],
                    "outputs": [],
                }
            )

        # Add workflow definition cell
        workflow_cell_source = [
            f"# Workflow: {workflow.get('id', 'unnamed')}\n",
            "workflow_definition = {\n",
            f"    \"id\": \"{workflow.get('id', 'unnamed')}\",\n",
            f"    \"framework\": \"{workflow.get('framework', 'langflow')}\",\n",
            '    "steps": [\n',
        ]

        # Add steps
        for i, step in enumerate(workflow["steps"]):
            step_json = json.dumps(step, indent=4).replace("\n", "\n        ")
            workflow_cell_source.append(
                f"        {step_json}{'' if i == len(workflow['steps']) - 1 else ','}\n"
            )

        workflow_cell_source.extend(["    ]\n", "}"])

        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": workflow_cell_source,
                "outputs": [],
            }
        )

        # Add execution cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Load and execute workflow\n",
                    "def execute_workflow(input_data):\n",
                    "    # Convert workflow definition to Langflow format\n",
                    "    langflow_json = {\n",
                    '        "nodes": [],\n',
                    '        "edges": []\n',
                    "    }\n",
                    "    for idx, step in enumerate(workflow_definition['steps']):\n",
                    "        node_id = f'node_{idx}'\n",
                    "        langflow_json['nodes'].append({'id': node_id, 'data': step})\n",
                    "        if idx > 0:\n",
                    "            langflow_json['edges'].append({'source': f'node_{idx-1}', 'target': node_id})\n",
                    "    # Load and execute flow\n",
                    "    graph = Graph.from_payload(langflow_json)\n",
                    "    result = graph.build()\n",
                    "    return result",
                ],
                "outputs": [],
            }
        )

        # Add example usage cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Example usage\n",
                    'input_data = {"query": "What is GraphRAG?"}\n',
                    "result = execute_workflow(input_data)\n",
                    "import logging\n",
                    "logging.getLogger(__name__).info(result)",
                ],
                "outputs": [],
            }
        )

        # Create notebook JSON
        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.8.0",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        return json.dumps(notebook, indent=2)

    def _convert_steps_to_langflow(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert workflow steps to Langflow node/edge representation."""
        nodes = []
        edges = []
        for index, step in enumerate(steps):
            node_id = f"node_{index}"
            nodes.append({"id": node_id, "data": step})
            if index > 0:
                edges.append({"source": f"node_{index-1}", "target": node_id})
        return {"nodes": nodes, "edges": edges}

    def _generate_yaml_code(self, workflow: Dict[str, Any]) -> str:
        """Generate YAML from workflow configuration.

        Args:
            workflow: Workflow configuration

        Returns:
            Generated YAML as string
        """
        try:
            import yaml

            # Create YAML-friendly structure
            yaml_dict = {
                "id": workflow.get("id", "unnamed"),
                "framework": workflow.get("framework", "langflow"),
                "steps": workflow["steps"],
                "metadata": {
                    "exported_at": str(datetime.now()),
                    "tenant_id": workflow.get("tenant_id", "default"),
                },
            }

            return yaml.dump(yaml_dict, sort_keys=False, default_flow_style=False)

        except ImportError:
            # Fallback if PyYAML is not available
            yaml_lines = [
                "# Generated by GraphRAG Ontology Application",
                "# Langflow workflow export",
                "",
                f"id: {workflow.get('id', 'unnamed')}",
                f"framework: {workflow.get('framework', 'langflow')}",
                "steps:",
            ]

            # Add steps
            for step in workflow["steps"]:
                yaml_lines.append("  - type: " + step.get("type", "unknown"))

                for key, value in step.items():
                    if key != "type":
                        if isinstance(value, str):
                            yaml_lines.append(f"    {key}: {value}")
                        else:
                            yaml_lines.append(f"    {key}: {json.dumps(value)}")

            return "\n".join(yaml_lines)

    def query_knowledge_graph(
        self,
        *,
        question: str,
        kg_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the knowledge graph using natural language.

        This method is exposed to the Langflow GraphRAG component for direct querying
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
                user_id="langflow_user",  # Could be enhanced with actual user ID
                include_explanation=True,
                query_opts=opts,
            )

            logger.info(
                f"Executed Langflow query: '{question[:50]}...' (kg_id={kg_id or self.default_kg_id})"
            )
            return result

        except GraphRAGException as e:
            logger.error("Failed to execute Langflow query: %s", e, exc_info=True)

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
            logger.error("Failed to execute Langflow query: %s", e, exc_info=True)

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

        This method is exposed to the Langflow GraphRAG component for document indexing
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
                f"Indexed documents through Langflow: count={len(docs)}, "
                f"triples={len(triples)}, kg_id={kg_id or self.default_kg_id}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to index documents through Langflow: {str(e)}", exc_info=True
            )

            # Return error response instead of raising exception
            return {
                "status": "failed",
                "error": str(e),
                "kg_id": kg_id or self.default_kg_id,
                "tenant_id": tenant_id or self.default_tenant_id,
            }
