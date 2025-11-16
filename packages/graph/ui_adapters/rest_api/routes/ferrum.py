"""Ferrum-specific PermaGraph integration endpoints."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ui_adapters.rest_api.dependencies import ServiceContainer, get_container
from ui_adapters.rest_api.models import ID_PATTERN, ErrorResponse
from domain.auth import Role, User
from ui_adapters.rest_api.server import require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/permagraph/ferrum", tags=["ferrum"])


# Ferrum-specific models
class FerrumNodeData(BaseModel):
    """Data structure for Ferrum graph nodes."""
    input: Optional[List[Dict[str, str]]] = None
    output: Optional[str] = None
    depends_on: Optional[List[str]] = None
    implements: Optional[str] = None


class FerrumGraphNode(BaseModel):
    """Ferrum graph node representation."""
    id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    type: str = Field(..., pattern=r"^(usecase|adapter|port|entity)$")
    position: Dict[str, float] = Field(..., description="Node position with x, y coordinates")
    data: FerrumNodeData


class FerrumGraphEdge(BaseModel):
    """Ferrum graph edge representation."""
    id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    source: str = Field(..., max_length=100, pattern=ID_PATTERN)
    target: str = Field(..., max_length=100, pattern=ID_PATTERN)
    type: str = Field(..., pattern=r"^(dependency|implementation|data_flow)$")


class FerrumGraphMetadata(BaseModel):
    """Metadata for Ferrum graph data."""
    module: str = Field(..., max_length=200)
    created_at: str
    last_modified: str
    framework_version: Optional[str] = Field(None, max_length=50)


class FerrumGraphData(BaseModel):
    """Complete Ferrum graph data structure."""
    framework: str = Field("ferrum", max_length=50)
    version: str = Field(..., max_length=50)
    nodes: List[FerrumGraphNode]
    edges: List[FerrumGraphEdge]
    metadata: FerrumGraphMetadata


class FerrumProjectStoreRequest(BaseModel):
    """Request to store a Ferrum project architecture."""
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    graph_data: FerrumGraphData
    commit_message: Optional[str] = Field(None, max_length=500)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)


class FerrumProjectStoreResponse(BaseModel):
    """Response from storing a Ferrum project."""
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    version_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    stored_at: str
    commit_message: Optional[str] = None


class FerrumProjectVersion(BaseModel):
    """A specific version of a Ferrum project."""
    version_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    graph_data: FerrumGraphData
    commit_message: Optional[str] = None
    created_at: str
    created_by: Optional[str] = None


class FerrumProjectHistoryResponse(BaseModel):
    """History of versions for a Ferrum project."""
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    versions: List[Dict[str, Any]]  # Simplified version info
    total_versions: int


@router.post("/projects", response_model=FerrumProjectStoreResponse)
async def store_ferrum_project(
    request: FerrumProjectStoreRequest,
    container: ServiceContainer = Depends(get_container),
    user: User = Depends(require_role(Role.ADMIN, Role.WRITE)),
) -> FerrumProjectStoreResponse:
    """Store a Ferrum project architecture in PermaGraph.
    
    This endpoint stores the visual graph representation of a Ferrum project,
    enabling version tracking and architectural evolution analysis.
    """
    try:
        # Generate version ID
        version_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Create storage key for the project version
        storage_key = f"ferrum:project:{request.project_id}:version:{version_id}"
        
        # Prepare data for storage
        storage_data = {
            "project_id": request.project_id,
            "version_id": version_id,
            "graph_data": request.graph_data.dict(),
            "commit_message": request.commit_message,
            "tenant_id": request.tenant_id,
            "created_at": timestamp,
            "created_by": user.username,
            "framework": "ferrum",
        }
        
        # Store in graph database (using the existing infrastructure)
        # This would typically use the semantic knowledge base service
        from ui_adapters.rest_api.dependencies import resolve
        knowledge_service = resolve(container, "semantic_knowledge_base")
        
        if knowledge_service:
            # Convert to triples for storage in the knowledge graph
            triples = _convert_ferrum_data_to_triples(storage_data)
            
            # Store the triples
            for triple in triples:
                knowledge_service.store_triple(
                    subject=triple["subject"],
                    predicate=triple["predicate"],
                    object=triple["object"],
                    tenant_id=request.tenant_id
                )
        
        # Also store in cache for quick retrieval
        cache_service = resolve(container, "cache_service")
        if cache_service:
            cache_service.set(storage_key, storage_data, ttl=3600)  # 1 hour TTL
        
        # Update project history index
        history_key = f"ferrum:project:{request.project_id}:history"
        history_entry = {
            "version_id": version_id,
            "created_at": timestamp,
            "commit_message": request.commit_message,
            "created_by": user.username,
        }
        
        if cache_service:
            # Get existing history and append new version
            existing_history = cache_service.get(history_key) or []
            existing_history.append(history_entry)
            cache_service.set(history_key, existing_history, ttl=7200)  # 2 hours TTL
        
        logger.info(f"Stored Ferrum project {request.project_id} version {version_id}")
        
        return FerrumProjectStoreResponse(
            project_id=request.project_id,
            version_id=version_id,
            stored_at=timestamp,
            commit_message=request.commit_message,
        )
        
    except Exception as e:
        logger.error(f"Failed to store Ferrum project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store project: {str(e)}"
        )


@router.get("/projects/{project_id}/history", response_model=FerrumProjectHistoryResponse)
async def get_ferrum_project_history(
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN),
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN),
    container: ServiceContainer = Depends(get_container),
    user: User = Depends(require_role(Role.ADMIN, Role.WRITE, Role.QUERY)),
) -> FerrumProjectHistoryResponse:
    """Get version history for a Ferrum project.
    
    Returns a list of all versions for the specified project,
    including metadata about each version.
    """
    try:
        from ui_adapters.rest_api.dependencies import resolve
        
        # Try cache first
        cache_service = resolve(container, "cache_service")
        history_key = f"ferrum:project:{project_id}:history"
        
        versions = []
        if cache_service:
            cached_history = cache_service.get(history_key)
            if cached_history:
                versions = cached_history
        
        # If not in cache, query the knowledge graph
        if not versions:
            knowledge_service = resolve(container, "semantic_knowledge_base")
            if knowledge_service:
                # Query for all versions of this project
                query_result = knowledge_service.query(
                    f"SELECT ?version ?created_at ?commit_message ?created_by WHERE {{ "
                    f"?project <http://ferrum.dev/project_id> '{project_id}' . "
                    f"?project <http://ferrum.dev/version_id> ?version . "
                    f"?project <http://ferrum.dev/created_at> ?created_at . "
                    f"OPTIONAL {{ ?project <http://ferrum.dev/commit_message> ?commit_message }} . "
                    f"OPTIONAL {{ ?project <http://ferrum.dev/created_by> ?created_by }} "
                    f"}} ORDER BY DESC(?created_at)",
                    tenant_id=tenant_id
                )
                
                if query_result and hasattr(query_result, 'results'):
                    versions = [
                        {
                            "version_id": result.get("version"),
                            "created_at": result.get("created_at"),
                            "commit_message": result.get("commit_message"),
                            "created_by": result.get("created_by"),
                        }
                        for result in query_result.results
                    ]
        
        if not versions:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for project {project_id}"
            )
        
        logger.info(f"Retrieved {len(versions)} versions for Ferrum project {project_id}")
        
        return FerrumProjectHistoryResponse(
            project_id=project_id,
            versions=versions,
            total_versions=len(versions),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project history: {str(e)}"
        )


@router.get("/projects/{project_id}/versions/{version_id}", response_model=FerrumProjectVersion)
async def get_ferrum_project_version(
    project_id: str = Field(..., max_length=100, pattern=ID_PATTERN),
    version_id: str = Field(..., max_length=100, pattern=ID_PATTERN),
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN),
    container: ServiceContainer = Depends(get_container),
    user: User = Depends(require_role(Role.ADMIN, Role.WRITE, Role.QUERY)),
) -> FerrumProjectVersion:
    """Get a specific version of a Ferrum project.
    
    Returns the complete graph data for the specified project version,
    including all nodes, edges, and metadata.
    """
    try:
        from ui_adapters.rest_api.dependencies import resolve
        
        # Try cache first
        cache_service = resolve(container, "cache_service")
        storage_key = f"ferrum:project:{project_id}:version:{version_id}"
        
        project_data = None
        if cache_service:
            project_data = cache_service.get(storage_key)
        
        # If not in cache, query the knowledge graph
        if not project_data:
            knowledge_service = resolve(container, "semantic_knowledge_base")
            if knowledge_service:
                # Query for the specific version
                query_result = knowledge_service.query(
                    f"SELECT ?data WHERE {{ "
                    f"?project <http://ferrum.dev/project_id> '{project_id}' . "
                    f"?project <http://ferrum.dev/version_id> '{version_id}' . "
                    f"?project <http://ferrum.dev/graph_data> ?data "
                    f"}}",
                    tenant_id=tenant_id
                )
                
                if query_result and hasattr(query_result, 'results') and query_result.results:
                    # Reconstruct the project data from stored triples
                    project_data = _reconstruct_ferrum_data_from_triples(
                        query_result.results[0], project_id, version_id
                    )
        
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_id} not found for project {project_id}"
            )
        
        # Validate and construct response
        graph_data = FerrumGraphData(**project_data["graph_data"])
        
        logger.info(f"Retrieved Ferrum project {project_id} version {version_id}")
        
        return FerrumProjectVersion(
            version_id=version_id,
            project_id=project_id,
            graph_data=graph_data,
            commit_message=project_data.get("commit_message"),
            created_at=project_data["created_at"],
            created_by=project_data.get("created_by"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project version: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project version: {str(e)}"
        )


def _convert_ferrum_data_to_triples(storage_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convert Ferrum project data to RDF triples for storage."""
    triples = []
    base_uri = f"http://ferrum.dev/project/{storage_data['project_id']}/version/{storage_data['version_id']}"
    
    # Basic project metadata
    triples.extend([
        {
            "subject": base_uri,
            "predicate": "http://ferrum.dev/project_id",
            "object": storage_data["project_id"]
        },
        {
            "subject": base_uri,
            "predicate": "http://ferrum.dev/version_id",
            "object": storage_data["version_id"]
        },
        {
            "subject": base_uri,
            "predicate": "http://ferrum.dev/framework",
            "object": storage_data["framework"]
        },
        {
            "subject": base_uri,
            "predicate": "http://ferrum.dev/created_at",
            "object": storage_data["created_at"]
        },
    ])
    
    # Optional fields
    if storage_data.get("commit_message"):
        triples.append({
            "subject": base_uri,
            "predicate": "http://ferrum.dev/commit_message",
            "object": storage_data["commit_message"]
        })
    
    if storage_data.get("created_by"):
        triples.append({
            "subject": base_uri,
            "predicate": "http://ferrum.dev/created_by",
            "object": storage_data["created_by"]
        })
    
    # Store graph data as JSON (simplified approach)
    import json
    triples.append({
        "subject": base_uri,
        "predicate": "http://ferrum.dev/graph_data",
        "object": json.dumps(storage_data["graph_data"])
    })
    
    return triples


def _reconstruct_ferrum_data_from_triples(
    triple_data: Dict[str, Any], 
    project_id: str, 
    version_id: str
) -> Dict[str, Any]:
    """Reconstruct Ferrum project data from stored triples."""
    import json
    
    # This is a simplified reconstruction - in a real implementation,
    # you would parse the actual triple structure
    graph_data_json = triple_data.get("data", "{}")
    
    try:
        graph_data = json.loads(graph_data_json)
    except (json.JSONDecodeError, TypeError):
        # Fallback to empty structure
        graph_data = {
            "framework": "ferrum",
            "version": "1.0.0",
            "nodes": [],
            "edges": [],
            "metadata": {
                "module": "unknown",
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
            }
        }
    
    return {
        "project_id": project_id,
        "version_id": version_id,
        "graph_data": graph_data,
        "created_at": datetime.utcnow().isoformat(),
        "framework": "ferrum",
    }