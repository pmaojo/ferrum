from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


ID_PATTERN = r"^[A-Za-z0-9_-]+$"


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=1000)
    kg_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    user_id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)
    include_explanation: bool = False
    include_subgraph: bool = False
    max_results: int = 50
    query_opts: Optional[Dict[str, Any]] = None


class SparqlExecuteRequest(BaseModel):
    """Request payload for executing a SPARQL preset."""

    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)


class IngestDocument(BaseModel):
    """Single document for ingestion."""

    content: str = Field(..., max_length=10000)
    id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """Request payload for ingestion endpoints."""

    documents: List[IngestDocument]
    kg_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    ontology_version_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    user_id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)
    ingestion_opts: Optional[Dict[str, Any]] = None


class DocsIngestFile(BaseModel):
    """Single file for direct document ingestion."""

    path: str = Field(..., max_length=500)
    content: str = Field(..., max_length=10000)


class DocsIngestRequest(BaseModel):
    """Request payload for docs ingestion endpoint."""

    files: List[DocsIngestFile]
    kg_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    ontology_version_id: str = Field("default", max_length=100, pattern=ID_PATTERN)




class RepoIngestRequest(BaseModel):
    """Request model for repository ingestion."""

    repo_url: Optional[str] = Field(None, max_length=2048, pattern=r"^https?://")
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    ontology_version_id: str = Field("default", max_length=100, pattern=ID_PATTERN)




class WorkflowRegisterRequest(BaseModel):
    """Request model for workflow registration."""

    workflow_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    steps: List[Dict[str, Any]]
    framework: str = Field(..., max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    user_id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)
    parameters: Optional[Dict[str, Any]] = None


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing an existing workflow."""

    workflow_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    input_data: Dict[str, Any]
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    user_id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)


# Resolve forward references for Python <3.12 compatibility


class LLMGenerateRequest(BaseModel):
    prompt: str = Field(..., max_length=5000)
    model: str = Field("gemini", max_length=100, pattern=ID_PATTERN)
    max_tokens: int = Field(1000, ge=1, le=100000)
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)


class CacheStatsResponse(BaseModel):
    size: int
    hit_rate: float
    miss_rate: float
    total_requests: int


class CacheClearResponse(BaseModel):
    cleared_keys: int
    status: str = Field("success", max_length=50, pattern=ID_PATTERN)


class TokenBudgetRequest(BaseModel):
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    amount: float
    description: Optional[str] = Field(None, max_length=1000)


class TokenBudgetResponse(BaseModel):
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    current_balance: float
    total_spent: float
    last_updated: str


class ErrorResponse(BaseModel):
    error: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    context: Optional[Dict[str, Any]] = None


class ValidationReportModel(BaseModel):
    """Serialized form of domain ``ValidationReport``."""

    is_consistent: bool
    unsat_classes: List[str]
    repair_suggestions: List[str]
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    ontology_version_id: str = Field(..., max_length=100, pattern=ID_PATTERN)


class AsyncJobResponse(BaseModel):
    """Metadata returned when an async job is created."""

    job_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    status: str = Field(..., max_length=50, pattern=ID_PATTERN)
    created_at: str
    estimated_completion: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Current status for an async ingestion job."""

    job_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    status: str = Field(..., max_length=50, pattern=ID_PATTERN)
    progress: float = Field(..., ge=0.0, le=1.0)
    created_at: float
    updated_at: float
    result: Optional[ValidationReportModel] = None
    error: Optional[str] = Field(None, max_length=1000)


class TokenUsageRequest(BaseModel):
    """Request body for tracking token usage."""

    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    tokens: int = Field(..., ge=0)
    model: str = Field(..., max_length=100, pattern=ID_PATTERN)
    operation_type: str = Field(..., max_length=100, pattern=ID_PATTERN)
    cost_usd: Optional[float] = Field(None, ge=0.0)
    metadata: Optional[Dict[str, Any]] = None


class SetBudgetRequest(BaseModel):
    """Request body for setting a tenant's budget."""

    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    monthly_budget_usd: float = Field(..., ge=0.0)
    alert_threshold_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    enable_degradation: Optional[bool] = None


class TripleModel(BaseModel):
    subject: str = Field(..., max_length=1000)
    predicate: str = Field(..., max_length=1000)
    object: str = Field(..., max_length=1000)


class OntologyVersionCreateRequest(BaseModel):
    triples: List[TripleModel]
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)
    parent_version_id: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)


class OntologyVersionResponse(BaseModel):
    id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    checksum: str = Field(..., max_length=1000)
    parent_version: Optional[str] = Field(None, max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    domain: str = Field(..., max_length=100)
    created_at: str
    axioms: List[str]


class CrossModalRetrievalRequest(BaseModel):
    """Request model for cross-modal retrieval."""

    kg_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    user_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    text_query: Optional[str] = Field(None, max_length=1000)
    image_path: Optional[str] = Field(None, max_length=500)
    audio_path: Optional[str] = Field(None, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    threshold: float = Field(0.7, ge=0.0, le=1.0)


class RepoFileModel(BaseModel):
    path: str = Field(..., max_length=500)
    content: str = Field(..., max_length=10000)


class RepositoryIngestRequest(BaseModel):
    repo_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    tenant_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    ontology_version_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    files: List[RepoFileModel]


class SyncInitRequest(BaseModel):
    """Request payload for initialization of synchronization."""

    project_path: str = Field(..., max_length=500)


class SyncRequest(BaseModel):
    """Request payload for synchronization operations."""

    mode: Literal["full", "incremental"]
    triples: List[TripleModel]


class FeatureRequestInput(BaseModel):
    """Request model for processing a feature request via HyDRA."""

    description: str = Field(..., max_length=5000)
    tenant_id: str = Field("default", max_length=100, pattern=ID_PATTERN)


class FeatureRequestResponse(BaseModel):
    """Response model containing generated artifacts."""

    feature_request_id: str = Field(..., max_length=100, pattern=ID_PATTERN)
    scope_document: str = Field(..., max_length=10000)
    personas: List[str]
    clarifying_questions: List[str]


