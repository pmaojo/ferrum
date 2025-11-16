"""
API server for Flowise GraphRAG integration.

This module provides a FastAPI server that exposes GraphRAG functionality
to the Flowise AI framework through a REST API.
"""

import logging
import os
import secrets
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from domain.entities import Triple
from application.ports import (
    GraphRetrieverPort,
    QueryTranslatorPort,
    FlowiseAdapterPort,
)
from domain.services import WorkflowOrchestrator, QueryService
from ui_adapters.flowise.flowise_adapter import FlowiseGraphRAGAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GraphRAG API for Flowise",
    description="API server for Flowise GraphRAG integration",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API models
class QueryRequest(BaseModel):
    question: str
    kg_id: Optional[str] = Field(default="default", description="Knowledge graph ID")
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    opts: Optional[Dict[str, Any]] = Field(default=None, description="Query options")


class IndexRequest(BaseModel):
    docs: List[str]
    kg_id: Optional[str] = Field(default="default", description="Knowledge graph ID")
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    validate: Optional[bool] = Field(
        default=True, description="Validate extracted triples"
    )
    ontology_version_id: Optional[str] = Field(
        default="latest", description="Ontology version ID"
    )


class WorkflowRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any]
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    async_execution: Optional[bool] = Field(
        default=False, description="Execute asynchronously"
    )
    callback_url: Optional[str] = Field(
        default=None, description="Callback URL for async execution"
    )


class CreateWorkflowRequest(BaseModel):
    workflow_id: str
    steps: List[Dict[str, Any]]
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")


class WorkflowFallbackRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any]
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    fallback_workflow_id: str
    max_retries: Optional[int] = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(
        default=2, description="Delay between retries in seconds"
    )


class ParallelWorkflowRequest(BaseModel):
    workflow_configs: List[Dict[str, Any]]
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    timeout_seconds: Optional[int] = Field(
        default=60, description="Execution timeout in seconds"
    )
    aggregate_results: Optional[bool] = Field(
        default=True, description="Aggregate results into single response"
    )


class WorkflowTemplateRequest(BaseModel):
    template_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")


class WorkflowMonitorRequest(BaseModel):
    workflow_id: str
    check_interval_seconds: Optional[int] = Field(
        default=5, description="Check interval in seconds"
    )
    timeout_seconds: Optional[int] = Field(
        default=300, description="Monitoring timeout in seconds"
    )


# Dependency for API key validation
async def validate_api_key(
    authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)
):
    """Validate API key from request headers.

    Args:
        authorization: Authorization header (Bearer token)
        x_api_key: X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: When API key is invalid
    """
    api_key_env = os.environ.get("GRAPHRAG_API_KEY")

    # Skip validation if no API key is configured
    if not api_key_env:
        return None

    # Extract API key from headers
    api_key = None

    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.replace("Bearer ", "")
    elif x_api_key:
        api_key = x_api_key

    # Validate API key using constant-time comparison
    if not secrets.compare_digest(api_key or "", api_key_env):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


@app.on_event("startup")
async def init_adapter() -> None:
    """Initialize and store the Flowise adapter."""
    if getattr(app.state, "adapter", None) is None:
        app.state.adapter = create_default_adapter()


def create_default_adapter() -> FlowiseAdapterPort:
    """Create Flowise adapter with production components."""
    from adapters.retrievers.graphrag_adapter import GraphRAGAdapter
    from adapters.retrievers.falkordb_graph_adapter import FalkorGraphAdapter

    graph_adapter = FalkorGraphAdapter(connection_string="redis://localhost:6379")
    graph_retriever = GraphRAGAdapter(config={})

    query_service = QueryService(
        translator=graph_adapter,
        retriever=graph_retriever,
    )

    workflow_orchestrator = WorkflowOrchestrator(
        retriever=graph_retriever,
        translator=graph_adapter,
    )

    return FlowiseGraphRAGAdapter(
        query_service=query_service,
        workflow_orchestrator=workflow_orchestrator,
        graph_retriever=graph_retriever,
        query_translator=graph_adapter,
    )


def get_flowise_adapter(request: Request) -> FlowiseAdapterPort:
    """Retrieve the Flowise adapter from application state."""
    adapter = getattr(request.app.state, "adapter", None)
    if adapter is None:
        raise HTTPException(status_code=500, detail="Adapter not initialized")
    return adapter


@app.get("/")
async def root():
    """Root endpoint for API health check."""
    return {"status": "ok", "service": "GraphRAG API for Flowise"}


@app.post("/api/graphrag/query")
async def query(
    request: QueryRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Query the knowledge graph using natural language.

    Args:
        request: Query request parameters
        api_key: Validated API key

    Returns:
        Query results

    Raises:
        HTTPException: When query execution fails
    """
    try:
        result = adapter.query_knowledge_graph(
            question=request.question,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            opts=request.opts,
        )

        return result

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/index")
async def index(
    request: IndexRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Index documents into the knowledge graph.

    Args:
        request: Index request parameters
        api_key: Validated API key

    Returns:
        Indexing results

    Raises:
        HTTPException: When document indexing fails
    """
    try:
        result = adapter.index_documents(
            docs=request.docs,
            kg_id=request.kg_id,
            tenant_id=request.tenant_id,
            validate=request.validate,
            ontology_version_id=request.ontology_version_id,
        )

        return result

    except Exception as e:
        logger.error(f"Document indexing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/execute")
async def execute_workflow(
    request: WorkflowRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Execute a registered workflow.

    Args:
        request: Workflow execution request parameters
        api_key: Validated API key

    Returns:
        Workflow execution results

    Raises:
        HTTPException: When workflow execution fails
    """
    try:
        result = adapter.execute_workflow(
            workflow_id=request.workflow_id,
            input_data=request.input_data,
            tenant_id=request.tenant_id,
        )

        return result

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/create")
async def create_workflow(
    request: CreateWorkflowRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Create a new workflow.

    Args:
        request: Workflow creation request parameters
        api_key: Validated API key

    Returns:
        Created workflow ID

    Raises:
        HTTPException: When workflow creation fails
    """
    try:
        workflow_id = adapter.create_workflow(
            workflow_id=request.workflow_id,
            steps=request.steps,
            tenant_id=request.tenant_id,
        )

        return {"workflow_id": workflow_id, "status": "created"}

    except Exception as e:
        logger.error(f"Workflow creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/execute-with-fallback")
async def execute_workflow_with_fallback(
    request: WorkflowFallbackRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Execute a workflow with fallback mechanism.

    Args:
        request: Workflow fallback request parameters
        api_key: Validated API key

    Returns:
        Workflow execution results

    Raises:
        HTTPException: When workflow execution fails
    """
    try:
        orchestrator = adapter.orchestrator()
        result = orchestrator.execute_with_fallback(
            workflow_id=request.workflow_id,
            input_data=request.input_data,
            tenant_id=request.tenant_id,
            fallback_workflow_id=request.fallback_workflow_id,
            max_retries=request.max_retries,
            retry_delay_seconds=request.retry_delay_seconds,
        )

        return result

    except Exception as e:
        logger.error(
            f"Workflow execution with fallback failed: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/execute-parallel")
async def execute_parallel_workflows(
    request: ParallelWorkflowRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Execute multiple workflows in parallel.

    Args:
        request: Parallel workflow request parameters
        api_key: Validated API key

    Returns:
        Aggregated workflow execution results

    Raises:
        HTTPException: When parallel execution fails
    """
    try:
        orchestrator = adapter.orchestrator()
        result = orchestrator.execute_parallel_workflows(
            workflow_configs=request.workflow_configs,
            tenant_id=request.tenant_id,
            timeout_seconds=request.timeout_seconds,
            aggregate_results=request.aggregate_results,
        )

        return result

    except Exception as e:
        logger.error(f"Parallel workflow execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/template")
async def register_workflow_template(
    request: WorkflowTemplateRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Register a workflow template.

    Args:
        request: Workflow template request parameters
        api_key: Validated API key

    Returns:
        Template ID

    Raises:
        HTTPException: When template registration fails
    """
    try:
        orchestrator = adapter.orchestrator()
        template_id = orchestrator.register_workflow_template(
            template_id=request.template_id,
            name=request.name,
            description=request.description,
            steps=request.steps,
            input_schema=request.input_schema,
            output_schema=request.output_schema,
            tenant_id=request.tenant_id,
        )

        return {"template_id": template_id, "status": "registered"}

    except Exception as e:
        logger.error(f"Workflow template registration failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/instantiate")
async def instantiate_workflow(
    request: dict,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Instantiate a workflow from a template.

    Args:
        request: Workflow instantiation request parameters
        api_key: Validated API key

    Returns:
        Workflow ID

    Raises:
        HTTPException: When workflow instantiation fails
    """
    # Validate required parameters
    if "template_id" not in request:
        raise HTTPException(status_code=400, detail="template_id is required")

    try:
        orchestrator = adapter.orchestrator()
        workflow_id = orchestrator.instantiate_workflow(
            template_id=request["template_id"],
            workflow_id=request.get("workflow_id"),
            parameters=request.get("parameters", {}),
            tenant_id=request.get("tenant_id"),
        )

        return {"workflow_id": workflow_id, "status": "instantiated"}

    except Exception as e:
        logger.error(f"Workflow instantiation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graphrag/workflow/monitor")
async def create_workflow_monitor(
    request: WorkflowMonitorRequest,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Create a monitoring task for a workflow.

    Args:
        request: Workflow monitor request parameters
        api_key: Validated API key

    Returns:
        Monitor configuration

    Raises:
        HTTPException: When monitor creation fails
    """
    try:
        orchestrator = adapter.orchestrator()
        monitor_config = orchestrator.create_workflow_monitor(
            workflow_id=request.workflow_id,
            check_interval_seconds=request.check_interval_seconds,
            timeout_seconds=request.timeout_seconds,
        )

        return monitor_config

    except Exception as e:
        logger.error(f"Workflow monitor creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graphrag/workflow/status/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    include_history: bool = False,
    adapter: FlowiseAdapterPort = Depends(get_flowise_adapter),
    api_key: str = Depends(validate_api_key),
):
    """Get workflow status and execution information.

    Args:
        workflow_id: Workflow identifier
        include_history: Whether to include execution history
        api_key: Validated API key

    Returns:
        Workflow status information

    Raises:
        HTTPException: When workflow is not found
    """
    try:
        orchestrator = adapter.orchestrator()
        status = orchestrator.get_workflow_status(
            workflow_id=workflow_id, include_history=include_history
        )

        return status

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
