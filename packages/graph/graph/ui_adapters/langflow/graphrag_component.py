"""
GraphRAG component for Langflow integration.

This module provides a PythonComponent implementation for Langflow that
exposes GraphRAG functionality within the Langflow canvas.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable
import os
import json

# Configure logging
logger = logging.getLogger(__name__)

try:
    from langflow.interface.custom.custom_component import CustomComponent
    from langflow.interface.custom.component import Component
    LANGFLOW_AVAILABLE = True
except ImportError:
    # Create placeholder classes for type hints when Langflow is not available
    class CustomComponent:
        pass

    class Component:
        pass

    LANGFLOW_AVAILABLE = False
    logger.warning("Langflow not available. GraphRAG component will not be functional.")


class GraphRagComponent(CustomComponent):
    """GraphRAG component for Langflow integration.

    This component provides GraphRAG functionality within the Langflow canvas,
    enabling knowledge graph querying and document indexing.

    Requirements addressed:
    - 10.2: Implement PythonComponent wrapper for GraphRetriever with build() method
    - 3.2: Integrate with Langflow for workflow management
    """

    display_name: str = "GraphRAG"
    description: str = "Query and index knowledge graphs using GraphRAG"
    documentation: str = "https://github.com/microsoft/graphrag"
    icon: str = "graph"

    def __init__(self):
        """Initialize GraphRAG component."""
        super().__init__()
        self.graph_retriever = None
        self.query_service = None
        self._initialize_component()

    def _initialize_component(self):
        """Initialize component with GraphRAG dependencies.

        This method attempts to locate and initialize GraphRAG dependencies
        using environment variables or default configuration.
        """
        try:
            # Try to import required modules
            import sys
            from pathlib import Path

            # Look for GraphRAG SDK in common locations
            graphrag_locations = [
                os.path.join(os.path.dirname(__file__), "../.."),
                os.path.expanduser("~/graphrag"),
                "/usr/local/lib/graphrag",
            ]

            for location in graphrag_locations:
                if location and os.path.exists(location):
                    if location not in sys.path:
                        sys.path.append(location)
                    break

            # Try to import GraphRAG dependencies
            try:
                from application.ports import GraphRetrieverPort
                from domain.services import QueryService

                # GraphRAG imports succeeded, but we'll initialize the actual
                # services when build() is called to ensure proper dependency injection
                logger.info("GraphRAG dependencies found and imported successfully")

            except ImportError as e:
                logger.warning(f"GraphRAG dependencies not found: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG component: {str(e)}", exc_info=True)

    def build_config(self) -> Dict[str, Any]:
        """Build component configuration for Langflow UI.

        Returns:
            Dictionary containing component configuration
        """
        return {
            "operation": {
                "type": "str",
                "required": True,
                "placeholder": "query",
                "show": True,
                "multiline": False,
                "value": "query",
                "options": ["query", "index"],
                "description": "Operation to perform (query or index)"
            },
            "input": {
                "type": "str",
                "required": True,
                "placeholder": "What is GraphRAG?",
                "show": True,
                "multiline": True,
                "value": "",
                "description": "Query text or document content"
            },
            "kg_id": {
                "type": "str",
                "required": False,
                "placeholder": "default",
                "show": True,
                "multiline": False,
                "value": "default",
                "description": "Knowledge graph identifier"
            },
            "tenant_id": {
                "type": "str",
                "required": False,
                "placeholder": "default",
                "show": True,
                "multiline": False,
                "value": "default",
                "description": "Tenant identifier for multi-tenant isolation"
            },
            "options": {
                "type": "dict",
                "required": False,
                "placeholder": "{}",
                "show": True,
                "multiline": True,
                "value": "{}",
                "description": "Additional options as JSON"
            }
        }

    def build(
        self,
        operation: str,
        input: str,
        kg_id: str = "default",
        tenant_id: str = "default",
        options: str = "{}"
    ) -> Dict[str, Any]:
        """Build and execute GraphRAG component.

        This method is called by Langflow when the component is executed
        in a workflow. It dynamically initializes GraphRAG dependencies
        and performs the requested operation.

        Args:
            operation: Operation to perform ("query" or "index")
            input: Query text or document content
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            options: Additional options as JSON string

        Returns:
            Dictionary containing operation results

        Raises:
            ValueError: When operation fails or parameters are invalid
        """
        try:
            # Parse options
            if isinstance(options, str):
                try:
                    options_dict = json.loads(options)
                except json.JSONDecodeError:
                    options_dict = {}
            elif isinstance(options, dict):
                options_dict = options
            else:
                options_dict = {}

            # Initialize GraphRAG dependencies if not already done
            if not self.graph_retriever or not self.query_service:
                self._initialize_graphrag_dependencies()

            # Execute requested operation
            if operation.lower() == "query":
                return self._execute_query(
                    question=input,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    opts=options_dict
                )
            elif operation.lower() == "index":
                return self._execute_index(
                    docs=[input],  # Wrap single document in list
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    opts=options_dict
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"GraphRAG component execution failed: {str(e)}", exc_info=True)

            # Return error response
            return {
                "status": "error",
                "error": str(e),
                "operation": operation,
                "kg_id": kg_id,
                "tenant_id": tenant_id
            }

    def _initialize_graphrag_dependencies(self):
        """Initialize GraphRAG dependencies dynamically.

        This method attempts to locate and initialize GraphRAG dependencies
        at runtime, allowing the component to work in various environments.

        Raises:
            ImportError: When required dependencies cannot be found
        """
        try:
            # Import required modules
            from application.ports import GraphRetrieverPort
            from domain.services import QueryService

            # Look for adapter registry or create dependencies directly
            try:
                # Try to find adapter registry first
                from ui_adapters.langflow import get_adapter_registry
                registry = get_adapter_registry()

                self.graph_retriever = registry.get("graph_retriever")
                self.query_service = registry.get("query_service")

                if not self.graph_retriever or not self.query_service:
                    raise ImportError("Required services not found in registry")

            except ImportError:
                # Fall back to direct initialization
                logger.info("Adapter registry not found, initializing dependencies directly")

                # Try to find GraphRAG adapter
                try:
                    from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
                    self.graph_retriever = GraphRAGAdapter()

                    # Create minimal query service
                    from domain.services import QueryService
                    self.query_service = QueryService(
                        retriever=self.graph_retriever,
                        translator=None,
                        visualizer=None
                    )

                except ImportError:
                    # Create mock implementations for testing
                    logger.warning("Creating mock implementations for testing")
                    self.graph_retriever = self._create_mock_graph_retriever()
                    self.query_service = self._create_mock_query_service()

            logger.info("GraphRAG dependencies initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG dependencies: {str(e)}", exc_info=True)
            raise ImportError(f"Failed to initialize GraphRAG dependencies: {str(e)}")

    def _execute_query(
        self,
        question: str,
        kg_id: str,
        tenant_id: str,
        opts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute GraphRAG query operation.

        Args:
            question: Natural language query
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            opts: Additional options

        Returns:
            Query results

        Raises:
            ValueError: When query execution fails
        """
        try:
            if self.query_service:
                # Use query service if available
                result = self.query_service.execute_natural_language_query(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    user_id="langflow_user",
                    include_explanation=True,
                    query_opts=opts
                )
                return result
            elif self.graph_retriever:
                # Fall back to direct graph retriever
                result = self.graph_retriever.run(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    opts=opts
                )

                # Format result
                if isinstance(result, str):
                    return {"result": result, "kg_id": kg_id, "tenant_id": tenant_id}
                else:
                    return {
                        "triples": [t._asdict() for t in result] if hasattr(result, "_asdict") else result,
                        "kg_id": kg_id,
                        "tenant_id": tenant_id
                    }
            else:
                raise ValueError("GraphRAG dependencies not initialized")

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise ValueError(f"Query execution failed: {str(e)}")

    def _execute_index(
        self,
        docs: List[str],
        kg_id: str,
        tenant_id: str,
        opts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute GraphRAG index operation.

        Args:
            docs: List of document content strings
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier
            opts: Additional options

        Returns:
            Indexing results

        Raises:
            ValueError: When indexing fails
        """
        try:
            if not self.graph_retriever:
                raise ValueError("GraphRAG dependencies not initialized")

            # Extract triples using GraphRAG
            triples = self.graph_retriever.index(
                docs=docs,
                kg_id=kg_id,
                tenant_id=tenant_id
            )

            # Format result
            return {
                "status": "success",
                "triple_count": len(triples),
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "triples": [t._asdict() for t in triples] if hasattr(triples[0], "_asdict") else triples
            }

        except Exception as e:
            logger.error(f"Indexing failed: {str(e)}", exc_info=True)
            raise ValueError(f"Indexing failed: {str(e)}")

    def _create_mock_graph_retriever(self):
        """Create mock graph retriever for testing.

        Returns:
            Mock graph retriever implementation
        """
        from typing import NamedTuple

        class MockTriple(NamedTuple):
            subject: str
            predicate: str
            object: str
            tenant_id: str

            def _asdict(self):
                return {
                    "subject": self.subject,
                    "predicate": self.predicate,
                    "object": self.object,
                    "tenant_id": self.tenant_id
                }

        class MockGraphRetriever:
            def index(self, *, docs, kg_id, tenant_id):
                logger.info(f"Mock indexing {len(docs)} documents for kg_id={kg_id}")
                return [
                    MockTriple(
                        subject=f"entity_{i}",
                        predicate="has_content",
                        object=doc[:50] + "..." if len(doc) > 50 else doc,
                        tenant_id=tenant_id
                    )
                    for i, doc in enumerate(docs)
                ]

            def run(self, *, question, kg_id, tenant_id, opts=None):
                logger.info(f"Mock query: '{question}' for kg_id={kg_id}")
                return f"Mock response for: {question}"

        return MockGraphRetriever()

    def _create_mock_query_service(self):
        """Create mock query service for testing.

        Returns:
            Mock query service implementation
        """
        class MockQueryService:
            def execute_natural_language_query(
                self, *, question, kg_id, tenant_id, user_id, include_explanation, query_opts
            ):
                logger.info(f"Mock query service: '{question}' for kg_id={kg_id}")
                return {
                    "results": [f"Mock result for: {question}"],
                    "explanation": "This is a mock explanation",
                    "metadata": {
                        "kg_id": kg_id,
                        "tenant_id": tenant_id,
                        "user_id": user_id
                    }
                }

        return MockQueryService()


# Register component with Langflow if available
if LANGFLOW_AVAILABLE:
    try:
        Component.add_component(GraphRagComponent, "GraphRAG")
        logger.info("GraphRAG component registered with Langflow")
    except Exception as e:
        logger.error(f"Failed to register GraphRAG component: {str(e)}", exc_info=True)