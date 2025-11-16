
"""REST API routes for StructRAG functionality."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ui_adapters.rest_api.dependencies import get_llm_adapter, get_tracer
from application.use_cases.structrag.query_with_structrag_use_case import (
    QueryWithStructRAGUseCase,
    IndexDocumentsWithStructRAGUseCase,
)
from domain.services import GraphRAGException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/structrag", tags=["structrag"])


class StructRAGQueryRequest(BaseModel):
    """Request model for StructRAG query processing."""
    
    query: str = Field(..., description="Natural language query")
    documents: List[str] = Field(..., description="List of documents to process")
    kg_id: str = Field(default="default", description="Knowledge graph identifier")
    tenant_id: str = Field(default="default", description="Tenant identifier")
    return_metadata: bool = Field(default=False, description="Return detailed metadata")
    structure_type: Optional[str] = Field(
        default=None,
        description="Force specific structure type (graph, table, algorithm, catalogue, chunk)"
    )
    max_iterations: Optional[int] = Field(
        default=None,
        description="Override maximum iterations"
    )


class StructRAGQueryResponse(BaseModel):
    """Response model for StructRAG query processing."""
    
    answer: str = Field(..., description="Generated answer")
    success: bool = Field(..., description="Whether processing was successful")
    structure_type: str = Field(..., description="Structure type used")
    subqueries: Optional[List[str]] = Field(None, description="Generated subqueries")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")
    processing_details: Optional[Dict] = Field(None, description="Processing details")


class StructRAGIndexRequest(BaseModel):
    """Request model for StructRAG document indexing."""
    
    documents: List[str] = Field(..., description="List of documents to index")
    kg_id: str = Field(default="default", description="Knowledge graph identifier")
    tenant_id: str = Field(default="default", description="Tenant identifier")
    metadata: Optional[Dict] = Field(None, description="Optional metadata")


class StructRAGIndexResponse(BaseModel):
    """Response model for StructRAG document indexing."""
    
    success: bool = Field(..., description="Whether indexing was successful")
    document_count: int = Field(..., description="Number of documents indexed")
    chunks_created: int = Field(..., description="Number of chunks created")
    data_id: str = Field(..., description="Data identifier for retrieval")
    storage_path: str = Field(..., description="Storage path")
    metadata: Dict = Field(..., description="Indexing metadata")


@router.post("/query", response_model=StructRAGQueryResponse)
async def query_with_structrag(
    request: StructRAGQueryRequest,
    llm_adapter=Depends(get_llm_adapter),
    tracer=Depends(get_tracer),
):
    """Process a query using StructRAG multi-agent framework.
    
    StructRAG analyzes the query to determine the optimal structure type
    (graph, table, algorithm, catalogue, or chunk) and constructs hybrid
    structured knowledge representations for enhanced reasoning.
    """
    try:
        use_case = QueryWithStructRAGUseCase(llm=llm_adapter, tracer=tracer)
        
        result = use_case.execute(
            query=request.query,
            documents=request.documents,
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            return_metadata=request.return_metadata,
            structure_type=request.structure_type,
            max_iterations=request.max_iterations,
        )
        
        return StructRAGQueryResponse(**result)
        
    except GraphRAGException as e:
        logger.error(f"StructRAG query failed: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": e.error_code,
                "message": e.message,
                "context": e.context,
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in StructRAG query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during StructRAG processing",
            }
        )


@router.post("/index", response_model=StructRAGIndexResponse)
async def index_documents_with_structrag(
    request: StructRAGIndexRequest,
    llm_adapter=Depends(get_llm_adapter),
    tracer=Depends(get_tracer),
):
    """Index documents for future StructRAG processing.
    
    This endpoint prepares documents for StructRAG by storing them in
    a format that allows for on-demand structure construction during queries.
    """
    try:
        use_case = IndexDocumentsWithStructRAGUseCase(llm=llm_adapter, tracer=tracer)
        
        result = use_case.execute(
            documents=request.documents,
            tenant_id=request.tenant_id,
            kg_id=request.kg_id,
            metadata=request.metadata,
        )
        
        return StructRAGIndexResponse(**result)
        
    except GraphRAGException as e:
        logger.error(f"StructRAG indexing failed: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": e.error_code,
                "message": e.message,
                "context": e.context,
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in StructRAG indexing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during StructRAG indexing",
            }
        )


@router.get("/status/{tenant_id}/{kg_id}")
async def get_structrag_status(
    tenant_id: str,
    kg_id: str,
    llm_adapter=Depends(get_llm_adapter),
    tracer=Depends(get_tracer),
):
    """Get StructRAG status and statistics for a specific knowledge graph."""
    try:
        from adapters.structrag_adapter import StructRAGAdapter
        
        adapter = StructRAGAdapter(llm_adapter=llm_adapter, tracer=tracer)
        status = adapter.get_status()
        
        # Add specific tenant/kg info
        status["tenant_id"] = tenant_id
        status["kg_id"] = kg_id
        
        # Check if documents exist for this tenant/kg
        documents = adapter._load_documents(kg_id, tenant_id)
        status["documents_available"] = len(documents) > 0
        status["document_count"] = len(documents)
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get StructRAG status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "STATUS_RETRIEVAL_FAILED",
                "message": "Failed to retrieve StructRAG status",
            }
        )


@router.delete("/storage/{tenant_id}/{kg_id}")
async def clear_structrag_storage(
    tenant_id: str,
    kg_id: str,
    llm_adapter=Depends(get_llm_adapter),
    tracer=Depends(get_tracer),
):
    """Clear StructRAG storage for a specific tenant and knowledge graph."""
    try:
        from adapters.structrag_adapter import StructRAGAdapter
        
        adapter = StructRAGAdapter(llm_adapter=llm_adapter, tracer=tracer)
        adapter.clear_storage(kg_id=kg_id, tenant_id=tenant_id)
        
        return {
            "success": True,
            "message": f"Cleared StructRAG storage for tenant {tenant_id}, kg {kg_id}",
            "tenant_id": tenant_id,
            "kg_id": kg_id,
        }
        
    except Exception as e:
        logger.error(f"Failed to clear StructRAG storage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "STORAGE_CLEAR_FAILED",
                "message": "Failed to clear StructRAG storage",
            }
        )


@router.get("/structures")
async def get_available_structures():
    """Get information about available StructRAG structure types."""
    return {
        "structures": {
            "chunk": {
                "description": "Basic document chunks for general queries",
                "best_for": ["General information retrieval", "Simple Q&A", "Document search"],
            },
            "graph": {
                "description": "Entity-relationship graphs for connected information",
                "best_for": ["Relationship queries", "Network analysis", "Connected concepts"],
            },
            "table": {
                "description": "Structured tabular data for comparative analysis",
                "best_for": ["Data comparison", "Statistics", "Structured information"],
            },
            "algorithm": {
                "description": "Step-by-step procedures and processes",
                "best_for": ["Process queries", "How-to questions", "Procedural knowledge"],
            },
            "catalogue": {
                "description": "Hierarchical classifications and taxonomies",
                "best_for": ["Category queries", "Classification", "Hierarchical information"],
            },
        },
        "selection_strategy": "StructRAG automatically analyzes queries to select the optimal structure type",
        "multi_agent_process": [
            "Analysis Agent: Decomposes query and selects structure type",
            "Construction Agent: Builds structured knowledge representation",
            "Retrieval Agent: Extracts relevant information from structures",
            "Merging Agent: Synthesizes final coherent answer",
        ],
    }
