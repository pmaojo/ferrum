"""
Gemini GraphRAG component for Langflow integration.

This component integrates Google's Gemini LLM with GraphRAG for knowledge graph
querying and document indexing with configurable parameters.

Requirements:
- 10.2: Create PythonComponent for Langflow integration
- 11.1: Add visual configuration for temperature, top_p, context_tokens

Features:
- Seamless integration with Google's Gemini 2.5 flash LLM
- Configurable parameters for fine-tuning generation quality
- Support for both querying and indexing operations
- Multi-tenant isolation with tenant_id parameter
- Safety settings configuration for content filtering
- Ontology validation for knowledge graph consistency

Example Usage:
```python
# Query mode example
result = gemini_graphrag(
    mode="query",
    question="What is the relationship between Alice and Bob?",
    kg_id="my_knowledge_graph",
    temperature=0.5,
    context_tokens=2048
)

# Index mode example
result = gemini_graphrag(
    mode="index",
    documents=["Alice is Bob's sister.", "Bob works at Acme Corp."],
    kg_id="my_knowledge_graph",
    validate_ontology=True
)

# Advanced configuration example
result = gemini_graphrag(
    mode="query",
    question="What projects is Bob working on at Acme Corp?",
    kg_id="my_knowledge_graph",
    tenant_id="customer-123",
    temperature=0.3,
    top_p=0.92,
    context_tokens=6144,
    max_hops=3,
    safety_settings="high"
)
```

Return Value Format:
```python
# Query mode return value
{
    "results": [
        {"subject": "Bob", "predicate": "works_on", "object": "Project X"},
        {"subject": "Project X", "predicate": "part_of", "object": "Acme Corp"}
    ],
    "explanation": "Bob is working on Project X at Acme Corp...",
    "metadata": {
        "query_time_ms": 245,
        "node_count": 15,
        "edge_count": 23
    }
}

# Index mode return value
{
    "status": "success",
    "triple_count": 5,
    "kg_id": "my_knowledge_graph",
    "tenant_id": "customer-123",
    "validation": {
        "performed": True,
        "is_consistent": True
    }
}
```
"""

import os
import json
from typing import Dict, Any, List, Optional, Union

from langflow.interface.custom.custom_component import CustomComponent
from langflow.interface.custom.component import Component
from langflow.interface.custom.constants import ComponentCategory


class GeminiGraphRagComponent(Component):
    """Gemini GraphRAG component for Langflow integration.

    This component provides integration between Google's Gemini LLM and GraphRAG
    for knowledge graph querying and document indexing with configurable parameters.
    """

    display_name: str = "Gemini GraphRAG"
    description: str = "Query knowledge graphs using Google Gemini LLM with GraphRAG"
    documentation: str = """
    # Gemini GraphRAG Component

    This component integrates Google's Gemini LLM with GraphRAG for knowledge graph
    querying and document indexing with configurable parameters.

    ## Inputs

    - **mode**: Operation mode (query or index)
    - **question**: Natural language query (for query mode)
    - **documents**: List of documents to index (for index mode)
    - **kg_id**: Knowledge graph identifier
    - **tenant_id**: Tenant identifier for multi-tenant isolation
    - **temperature**: Sampling temperature (0.0 to 1.0) - lower is more deterministic
    - **top_p**: Nucleus sampling parameter (0.0 to 1.0)
    - **context_tokens**: Maximum context tokens for query processing
    - **max_hops**: Maximum graph traversal hops for query processing
    - **safety_settings**: Safety filter level for Gemini LLM
    - **validate_ontology**: Whether to validate extracted triples against ontology (for indexing)
    - **ontology_version_id**: Ontology version for validation (for indexing)

    ## Outputs

    - **results**: Query results or indexing status
    - **explanation**: Explanation of query results (for query mode)
    - **triple_count**: Number of triples extracted (for index mode)

    ## Example Usage

    ```python
    # Query mode example
    result = gemini_graphrag(
        mode="query",
        question="What is the relationship between Alice and Bob?",
        kg_id="my_knowledge_graph",
        temperature=0.5,
        context_tokens=2048
    )

    # Index mode example
    result = gemini_graphrag(
        mode="index",
        documents=["Alice is Bob's sister.", "Bob works at Acme Corp."],
        kg_id="my_knowledge_graph",
        validate_ontology=True
    )
    ```
    """

    icon_path: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "gemini_icon.svg"
    )

    category: ComponentCategory = ComponentCategory.KNOWLEDGE

    def build_config(self) -> Dict[str, Any]:
        """Build component configuration.

        Returns:
            Dictionary containing component configuration
        """
        return {
            "mode": {
                "display_name": "Mode",
                "options": ["query", "index"],
                "value": "query",
                "info": "Operation mode: query knowledge graph or index documents"
            },
            "question": {
                "display_name": "Question",
                "value": "",
                "info": "Natural language query (for query mode)",
                "required": False
            },
            "documents": {
                "display_name": "Documents",
                "list": True,
                "value": [],
                "info": "List of documents to index (for index mode)",
                "required": False
            },
            "kg_id": {
                "display_name": "Knowledge Graph ID",
                "value": "default",
                "info": "Identifier for the knowledge graph"
            },
            "tenant_id": {
                "display_name": "Tenant ID",
                "value": "default",
                "info": "Tenant identifier for multi-tenant isolation"
            },
            "temperature": {
                "display_name": "Temperature",
                "value": 0.7,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "info": "Sampling temperature (0.0 to 1.0) - lower is more deterministic"
            },
            "top_p": {
                "display_name": "Top P",
                "value": 0.95,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "info": "Nucleus sampling parameter (0.0 to 1.0)"
            },
            "context_tokens": {
                "display_name": "Context Tokens",
                "value": 4096,
                "min": 1024,
                "max": 8192,
                "step": 1024,
                "info": "Maximum context tokens for query processing"
            },
            "max_hops": {
                "display_name": "Max Hops",
                "value": 2,
                "min": 1,
                "max": 5,
                "step": 1,
                "info": "Maximum graph traversal hops for query processing"
            },
            "safety_settings": {
                "display_name": "Safety Settings",
                "options": ["standard", "high", "maximum", "none"],
                "value": "standard",
                "info": "Safety filter level for Gemini LLM"
            },
            "validate_ontology": {
                "display_name": "Validate Ontology",
                "value": True,
                "info": "Whether to validate extracted triples against ontology (for indexing)"
            },
            "ontology_version_id": {
                "display_name": "Ontology Version ID",
                "value": "latest",
                "info": "Ontology version for validation (for indexing)"
            }
        }

    def build(
        self,
        mode: str,
        question: Optional[str] = None,
        documents: Optional[List[str]] = None,
        kg_id: str = "default",
        tenant_id: str = "default",
        temperature: float = 0.7,
        top_p: float = 0.95,
        context_tokens: int = 4096,
        max_hops: int = 2,
        safety_settings: str = "standard",
        validate_ontology: bool = True,
        ontology_version_id: str = "latest"
    ) -> Dict[str, Any]:
        """Build component for execution.

        Args:
            mode: Operation mode (query or index)
            question: Natural language query (for query mode)
            documents: List of documents to index (for index mode)
            kg_id: Knowledge graph identifier
            tenant_id: Tenant identifier for multi-tenant isolation
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            context_tokens: Maximum context tokens for query processing
            max_hops: Maximum graph traversal hops for query processing
            safety_settings: Safety filter level for Gemini LLM
            validate_ontology: Whether to validate extracted triples against ontology
            ontology_version_id: Ontology version for validation

        Returns:
            Dictionary containing execution result

        Raises:
            ValueError: When required parameters are missing
        """
        # Map safety settings to Gemini format
        safety_settings_map = {
            "standard": {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE"
            },
            "high": {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_LOW_AND_ABOVE"
            },
            "maximum": {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_LOW_AND_ABOVE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_LOW_AND_ABOVE"
            },
            "none": {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
            }
        }

        # Create options object
        opts = {
            "temperature": temperature,
            "top_p": top_p,
            "context_tokens": context_tokens,
            "max_hops": max_hops,
            "safety_settings": safety_settings_map.get(safety_settings, safety_settings_map["standard"]),
            "llm_provider": "gemini"
        }

        try:
            # Import GraphRAG adapter
            from langflow.custom.customs import graphrag_adapter

            if not graphrag_adapter:
                raise ValueError("GraphRAG adapter not found. Make sure the adapter is properly initialized.")

            # Process based on mode
            if mode == "query":
                # Validate required parameters
                if not question:
                    raise ValueError("Question is required for query mode")

                # Log execution parameters
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Executing Gemini GraphRAG query: '{question[:50]}...' with parameters: "
                    f"kg_id={kg_id}, tenant_id={tenant_id}, temperature={temperature}, "
                    f"top_p={top_p}, context_tokens={context_tokens}, max_hops={max_hops}"
                )

                # Execute query
                result = graphrag_adapter.query_knowledge_graph(
                    question=question,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    opts=opts
                )

                return result

            elif mode == "index":
                # Validate required parameters
                if not documents:
                    raise ValueError("Documents are required for index mode")

                # Log execution parameters
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Executing Gemini GraphRAG indexing: {len(documents)} documents with parameters: "
                    f"kg_id={kg_id}, tenant_id={tenant_id}, validate_ontology={validate_ontology}, "
                    f"ontology_version_id={ontology_version_id}"
                )

                # Execute indexing
                result = graphrag_adapter.index_documents(
                    docs=documents,
                    kg_id=kg_id,
                    tenant_id=tenant_id,
                    validate=validate_ontology,
                    ontology_version_id=ontology_version_id
                )

                return result

            else:
                raise ValueError(f"Invalid mode: {mode}")

        except Exception as e:
            # Log the error
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini GraphRAG component error: {str(e)}")
            logger.debug(traceback.format_exc())

            # Return user-friendly error response
            return {
                "error": str(e),
                "status": "failed",
                "kg_id": kg_id,
                "tenant_id": tenant_id,
                "suggestions": [
                    "Check that the GraphRAG adapter is properly initialized",
                    "Verify that your input parameters are correct",
                    "Ensure that the knowledge graph exists",
                    "Check that the Gemini API key is valid and has sufficient quota"
                ]
            }