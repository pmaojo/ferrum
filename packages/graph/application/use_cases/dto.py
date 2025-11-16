"""Data Transfer Objects (DTOs) for application use cases."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from application.contracts import Contract

T = TypeVar("T")


class SortDirection(str, Enum):
    """Sort direction for paginated queries."""

    ASC = "asc"
    DESC = "desc"


@dataclass
class PaginationParams:
    """Common pagination parameters for list operations."""

    page: int = 1
    page_size: int = 20

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be greater than or equal to 1")

        if self.page_size < 1:
            raise ValueError("Page size must be greater than or equal to 1")

        if self.page_size > 100:
            raise ValueError("Page size must be less than or equal to 100")


@dataclass
class SortParams:
    """Common sorting parameters for list operations."""

    sort_by: str
    direction: SortDirection = SortDirection.ASC


@dataclass
class FilterParams:
    """Base class for filter parameters."""


@dataclass
class BaseRequestDTO:
    """Base class for all request DTOs."""


@dataclass
class PaginatedRequest(Generic[T]):
    """Base request for paginated operations."""

    pagination: PaginationParams
    filters: Optional[T] = None
    sort: Optional[SortParams] = None


@dataclass
class PaginatedResponse(Generic[T]):
    """Base response for paginated operations."""

    items: List[T]
    total_items: int
    total_pages: int
    page: int
    page_size: int
    has_next_page: bool
    has_previous_page: bool


@dataclass
class BaseResponseDTO:
    """Base class for all response DTOs."""

    success: bool
    processing_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorResponseDTO:
    """Standard error response DTO."""

    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationErrorDetail:
    """Detailed validation error information."""

    field: str
    message: str
    code: str
    value: Optional[Any] = None


@dataclass
class ValidationErrorResponseDTO(ErrorResponseDTO):
    """Validation error response DTO."""

    validation_errors: List[ValidationErrorDetail] = field(default_factory=list)


@dataclass
class IdResponseDTO:
    """Simple response containing an ID."""

    id: str
    success: bool = True


@dataclass
class BulkOperationResponseDTO:
    """Response for bulk operations."""

    success_count: int
    failure_count: int
    total_count: int
    success_ids: List[str] = field(default_factory=list)
    failure_details: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True


@dataclass
class AuditInfoDTO:
    """Audit information for entities."""

    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


@dataclass
class TenantScopedRequestDTO:
    """Base request DTO for tenant-scoped operations."""

    tenant_id: str
    user_id: str


# Ontology DTOs
@dataclass
class CreateOntologyRequestDTO(TenantScopedRequestDTO):
    """Request to create a new ontology."""

    name: str
    domain: str  # ScientificDomain value
    content: str
    format: str  # owl, rdf, ttl, json-ld
    description: Optional[str] = None
    parent_version_id: Optional[str] = None
    competency_questions: Optional[List[Dict[str, str]]] = None
    contract: Optional[Contract] = None


@dataclass
class OntologyDTO:
    """Ontology data transfer object."""

    id: str
    name: str
    description: Optional[str]
    domain: str
    version: str
    parent_version_id: Optional[str]
    tenant_id: str
    created_at: datetime
    checksum: str
    axiom_count: int
    competency_questions: Optional[List[Dict[str, str]]] = None


@dataclass
class UpdateOntologyRequestDTO(TenantScopedRequestDTO):
    """Request to update an ontology (creates new version)."""

    ontology_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    competency_questions: Optional[List[Dict[str, str]]] = None


@dataclass
class ValidateOntologyRequestDTO(TenantScopedRequestDTO):
    """Request to validate an ontology."""

    ontology_version_id: str
    triples: Optional[List[Dict[str, str]]] = (
        None  # Optional triples to validate against ontology
    )


@dataclass
class OntologyValidationResultDTO:
    """Ontology validation result."""

    is_consistent: bool
    unsat_classes: List[str]
    repair_suggestions: List[str]
    validation_errors: List[str]
    processing_time_ms: float


@dataclass
class ListOntologyVersionsRequestDTO(TenantScopedRequestDTO):
    """Request to list ontology versions."""

    ontology_name: Optional[str] = None
    domain: Optional[str] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class OntologyVersionDTO:
    """Ontology version data transfer object."""

    id: str
    ontology_name: str
    version: str
    parent_version_id: Optional[str]
    domain: str
    tenant_id: str
    created_at: datetime
    checksum: str
    axiom_count: int
    is_latest: bool


@dataclass
class CompareOntologyVersionsRequestDTO(TenantScopedRequestDTO):
    """Request to compare two ontology versions."""

    version1_id: str
    version2_id: str


@dataclass
class OntologyVersionDiffDTO:
    """Ontology version comparison result."""

    added_axioms: List[str]
    removed_axioms: List[str]
    modified_axioms: List[Dict[str, str]]  # old -> new mappings
    summary: str


@dataclass
class ImportOntologyRequestDTO(TenantScopedRequestDTO):
    """Request to import an ontology from external source."""

    name: str
    description: Optional[str]
    domain: str
    source_url: Optional[str] = None
    source_content: Optional[str] = None
    format: Optional[str] = None  # Auto-detect if not provided
    competency_questions: Optional[List[Dict[str, str]]] = None


# User and Organization DTOs
@dataclass
class CreateUserRequestDTO:
    """Request to create a new user."""

    email: str
    name: str
    password: str
    organization_id: str
    role: str = "viewer"
    created_by_user_id: str = ""  # ID of user creating this user


@dataclass
class UserDTO:
    """User data transfer object."""

    id: str
    email: str
    name: str
    organization_id: str
    role: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


@dataclass
class UpdateUserRequestDTO:
    """Request to update a user."""

    user_id: str
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    updated_by_user_id: str = ""  # ID of user making the update


@dataclass
class CreateOrganizationRequestDTO:
    """Request to create a new organization."""

    name: str
    subscription_tier: str = "free"
    admin_email: str = ""
    admin_name: str = ""
    admin_password: str = ""


@dataclass
class OrganizationDTO:
    """Organization data transfer object."""

    id: str
    name: str
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


@dataclass
class ManageTeamMembersRequestDTO:
    """Request to manage team members."""

    organization_id: str
    action: str  # "add" or "remove"
    user_ids: List[str]
    manager_user_id: str  # ID of user performing the action


@dataclass
class GetUserPermissionsRequestDTO:
    """Request to get user permissions."""

    user_id: str
    resource_id: Optional[str] = None  # Optional specific resource
    requesting_user_id: str = ""  # ID of user requesting permissions


@dataclass
class UserPermissionsDTO:
    """User permissions data transfer object."""

    user_id: str
    organization_id: str
    role: str
    permissions: List[str]
    resource_permissions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class AuditUserActivityRequestDTO:
    """Request to audit user activity."""

    user_id: Optional[str] = None  # If None, get all users in organization
    organization_id: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    activity_types: Optional[List[str]] = None
    pagination: Optional[PaginationParams] = None
    requesting_user_id: str = ""  # ID of user requesting audit


@dataclass
class UserActivityDTO:
    """User activity data transfer object."""

    id: str
    user_id: str
    activity_type: str
    description: str
    resource_id: Optional[str]
    resource_type: Optional[str]
    metadata: Dict[str, Any]
    timestamp: datetime


# Subscription and Billing DTOs
@dataclass
class CreateSubscriptionRequestDTO:
    """Request to create a new subscription."""

    organization_id: str
    tier: str  # free, basic, professional, enterprise
    payment_method_id: Optional[str] = None
    billing_cycle: str = "monthly"  # monthly, yearly
    created_by_user_id: str = ""


@dataclass
class SubscriptionDTO:
    """Subscription data transfer object."""

    id: str
    organization_id: str
    external_subscription_id: Optional[str]
    tier: str
    billing_cycle: str
    starts_at: datetime
    expires_at: datetime
    payment_method_id: Optional[str]
    status: str  # active, cancelled, expired, past_due
    created_at: datetime
    updated_at: datetime


@dataclass
class UpdateSubscriptionRequestDTO:
    """Request to update a subscription."""

    subscription_id: str
    tier: Optional[str] = None
    billing_cycle: Optional[str] = None
    payment_method_id: Optional[str] = None
    updated_by_user_id: str = ""


@dataclass
class CancelSubscriptionRequestDTO:
    """Request to cancel a subscription."""

    subscription_id: str
    cancel_at_period_end: bool = True
    cancellation_reason: Optional[str] = None
    cancelled_by_user_id: str = ""


@dataclass
class UsageMetricsRequestDTO:
    """Request to get usage metrics."""

    organization_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metric_types: Optional[List[str]] = (
        None  # knowledge_graphs, users, api_calls, storage_gb
    )


@dataclass
class UsageMetricDTO:
    """Usage metric data transfer object."""

    metric_type: str
    current_value: float
    limit_value: Optional[float]
    unit: str
    period_start: datetime
    period_end: datetime


@dataclass
class UsageMetricsDTO:
    """Usage metrics response."""

    organization_id: str
    subscription_tier: str
    metrics: List[UsageMetricDTO]
    period_start: datetime
    period_end: datetime


@dataclass
class BillingHistoryRequestDTO:
    """Request to get billing history."""

    organization_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class InvoiceDTO:
    """Invoice data transfer object."""

    id: str
    organization_id: str
    subscription_id: str
    external_invoice_id: Optional[str]
    amount: float
    currency: str
    status: str  # draft, open, paid, void, uncollectible
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    created_at: datetime


@dataclass
class PaymentDTO:
    """Payment data transfer object."""

    id: str
    invoice_id: str
    external_payment_id: Optional[str]
    amount: float
    currency: str
    status: str  # pending, succeeded, failed, cancelled
    payment_method: str
    processed_at: Optional[datetime]
    created_at: datetime


@dataclass
class BillingHistoryDTO:
    """Billing history response."""

    organization_id: str
    invoices: List[InvoiceDTO]
    payments: List[PaymentDTO]
    total_invoices: int
    total_payments: int


@dataclass
class CheckSubscriptionLimitsRequestDTO:
    """Request to check subscription limits."""

    organization_id: str
    resource_type: Optional[str] = (
        None  # knowledge_graphs, users, api_calls, storage_gb
    )
    requested_amount: Optional[float] = None


@dataclass
class SubscriptionLimitDTO:
    """Subscription limit data transfer object."""

    resource_type: str
    current_usage: float
    limit: Optional[float]  # None means unlimited
    unit: str
    is_exceeded: bool
    remaining: Optional[float]


@dataclass
class SubscriptionLimitsDTO:
    """Subscription limits response."""

    organization_id: str
    subscription_tier: str
    limits: List[SubscriptionLimitDTO]
    overall_status: str  # within_limits, approaching_limits, exceeded_limits


# Graph Analytics DTOs
@dataclass
class AnalyzeGraphStructureRequestDTO(TenantScopedRequestDTO):
    """Request to analyze graph structure."""

    kg_id: str
    include_centrality: bool = True
    include_clustering: bool = True
    include_connectivity: bool = True


@dataclass
class GraphMetricDTO:
    """Individual graph metric data transfer object."""

    name: str
    value: float
    description: str
    category: str  # structure, centrality, clustering, connectivity


@dataclass
class GraphStructureAnalysisDTO:
    """Graph structure analysis result."""

    kg_id: str
    tenant_id: str
    metrics: List[GraphMetricDTO]
    analysis_timestamp: datetime
    processing_time_ms: float


@dataclass
class DetectCommunitiesRequestDTO(TenantScopedRequestDTO):
    """Request to detect communities in a graph."""

    kg_id: str
    algorithm: str = "louvain"  # louvain, leiden, label_propagation
    min_community_size: int = 3
    resolution: float = 1.0


@dataclass
class CommunityDTO:
    """Community data transfer object."""

    id: str
    size: int
    node_ids: List[str]
    centroid_node_id: Optional[str]
    modularity_score: float
    internal_edges: int
    external_edges: int


@dataclass
class CommunitiesAnalysisDTO:
    """Communities detection result."""

    kg_id: str
    tenant_id: str
    algorithm: str
    communities: List[CommunityDTO]
    total_communities: int
    modularity: float
    coverage: float
    analysis_timestamp: datetime
    processing_time_ms: float


@dataclass
class FindShortestPathRequestDTO(TenantScopedRequestDTO):
    """Request to find shortest path between nodes."""

    kg_id: str
    source_node_id: str
    target_node_id: str
    max_depth: int = 10
    weight_property: Optional[str] = None


@dataclass
class PathNodeDTO:
    """Node in a path."""

    node_id: str
    node_type: str
    properties: Dict[str, Any]


@dataclass
class PathEdgeDTO:
    """Edge in a path."""

    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: Dict[str, Any]
    weight: Optional[float] = None


@dataclass
class ShortestPathDTO:
    """Shortest path result."""

    kg_id: str
    tenant_id: str
    source_node_id: str
    target_node_id: str
    path_length: int
    total_weight: Optional[float]
    nodes: List[PathNodeDTO]
    edges: List[PathEdgeDTO]
    analysis_timestamp: datetime
    processing_time_ms: float


@dataclass
class GetNodeCentralityRequestDTO(TenantScopedRequestDTO):
    """Request to calculate node centrality measures."""

    kg_id: str
    node_ids: Optional[List[str]] = None  # If None, calculate for all nodes
    centrality_types: List[str] = (
        None  # betweenness, closeness, degree, eigenvector, pagerank
    )
    limit: int = 100


@dataclass
class NodeCentralityDTO:
    """Node centrality measures."""

    node_id: str
    node_type: str
    betweenness_centrality: Optional[float] = None
    closeness_centrality: Optional[float] = None
    degree_centrality: Optional[float] = None
    eigenvector_centrality: Optional[float] = None
    pagerank: Optional[float] = None


@dataclass
class CentralityAnalysisDTO:
    """Centrality analysis result."""

    kg_id: str
    tenant_id: str
    centrality_types: List[str]
    node_centralities: List[NodeCentralityDTO]
    total_nodes_analyzed: int
    analysis_timestamp: datetime
    processing_time_ms: float


@dataclass
class GenerateGraphVisualizationRequestDTO(TenantScopedRequestDTO):
    """Request to generate graph visualization."""

    kg_id: str
    visualization_id: Optional[str] = None
    layout_algorithm: str = (
        "force_directed"  # force_directed, circular, hierarchical, spring
    )
    node_limit: int = 1000
    include_labels: bool = True
    include_communities: bool = False
    filter_by_node_types: Optional[List[str]] = None
    filter_by_relationship_types: Optional[List[str]] = None


@dataclass
class VisualizationNodeDTO:
    """Node in visualization."""

    id: str
    label: str
    node_type: str
    x: float
    y: float
    size: float
    color: str
    properties: Dict[str, Any]
    community_id: Optional[str] = None


@dataclass
class VisualizationEdgeDTO:
    """Edge in visualization."""

    id: str
    source_id: str
    target_id: str
    label: str
    relationship_type: str
    color: str
    properties: Dict[str, Any]
    weight: Optional[float] = None


@dataclass
class GraphVisualizationDTO:
    """Graph visualization result."""

    kg_id: str
    tenant_id: str
    layout_algorithm: str
    nodes: List[VisualizationNodeDTO]
    edges: List[VisualizationEdgeDTO]
    total_nodes: int
    total_edges: int
    viewport_bounds: Dict[str, float]  # min_x, max_x, min_y, max_y
    analysis_timestamp: datetime
    processing_time_ms: float


@dataclass
class ExportVisualizationRequestDTO(TenantScopedRequestDTO):
    """Request to export visualization."""

    kg_id: str
    visualization_id: str
    export_format: str  # svg, png, pdf, json, graphml, gexf
    width: int = 1920
    height: int = 1080
    include_metadata: bool = True


@dataclass
class VisualizationExportDTO:
    """Visualization export result."""

    kg_id: str
    tenant_id: str
    export_format: str
    file_content: str  # Base64 encoded for binary formats
    file_size_bytes: int
    metadata: Dict[str, Any]
    export_timestamp: datetime
    processing_time_ms: float


# Search and Discovery DTOs
@dataclass
class SemanticSearchRequestDTO(TenantScopedRequestDTO):
    """Request to perform semantic search."""

    kg_id: str
    query: str
    limit: int = 20
    threshold: float = 0.7
    include_properties: bool = True
    filter_by_node_types: Optional[List[str]] = None


@dataclass
class SearchResultDTO:
    """Individual search result."""

    node_id: str
    node_type: str
    label: str
    properties: Dict[str, Any]
    score: float
    snippet: Optional[str] = None


@dataclass
class SemanticSearchResponseDTO:
    """Semantic search response."""

    kg_id: str
    tenant_id: str
    query: str
    results: List[SearchResultDTO]
    total_results: int
    processing_time_ms: float
    search_timestamp: datetime


@dataclass
class EntitySearchRequestDTO(TenantScopedRequestDTO):
    """Request to search for entities."""

    kg_id: str
    entity_types: Optional[List[str]] = None
    property_filters: Optional[Dict[str, Any]] = None
    text_query: Optional[str] = None
    pagination: Optional[PaginationParams] = None
    sort: Optional[SortParams] = None


@dataclass
class EntityDTO:
    """Entity data transfer object."""

    id: str
    type: str
    label: str
    properties: Dict[str, Any]
    relationship_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class EntitySearchResponseDTO:
    """Entity search response."""

    kg_id: str
    tenant_id: str
    entities: List[EntityDTO]
    total_entities: int
    filters_applied: Dict[str, Any]
    processing_time_ms: float
    search_timestamp: datetime


@dataclass
class RelationshipSearchRequestDTO(TenantScopedRequestDTO):
    """Request to search for relationship patterns."""

    kg_id: str
    source_node_id: Optional[str] = None
    target_node_id: Optional[str] = None
    relationship_types: Optional[List[str]] = None
    pattern: Optional[str] = None  # Cypher-like pattern
    property_filters: Optional[Dict[str, Any]] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class RelationshipDTO:
    """Relationship data transfer object."""

    id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: Dict[str, Any]
    source_node_label: str
    target_node_label: str
    weight: Optional[float] = None


@dataclass
class RelationshipSearchResponseDTO:
    """Relationship search response."""

    kg_id: str
    tenant_id: str
    relationships: List[RelationshipDTO]
    total_relationships: int
    pattern_matched: Optional[str]
    processing_time_ms: float
    search_timestamp: datetime


@dataclass
class FacetedSearchRequestDTO(TenantScopedRequestDTO):
    """Request for faceted search."""

    kg_id: str
    query: Optional[str] = None
    selected_facets: Optional[Dict[str, List[str]]] = None
    facet_fields: Optional[List[str]] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class FacetValueDTO:
    """Facet value with count."""

    value: str
    count: int
    selected: bool = False


@dataclass
class FacetDTO:
    """Facet with values."""

    field: str
    label: str
    values: List[FacetValueDTO]
    total_values: int


@dataclass
class FacetedSearchResponseDTO:
    """Faceted search response."""

    kg_id: str
    tenant_id: str
    query: Optional[str]
    results: List[SearchResultDTO]
    facets: List[FacetDTO]
    total_results: int
    applied_filters: Dict[str, List[str]]
    processing_time_ms: float
    search_timestamp: datetime


@dataclass
class SearchSuggestionsRequestDTO(TenantScopedRequestDTO):
    """Request for search suggestions."""

    kg_id: str
    partial_query: str
    suggestion_types: List[str] = field(
        default_factory=lambda: ["entities", "relationships", "properties"]
    )
    limit: int = 10


@dataclass
class SuggestionDTO:
    """Search suggestion."""

    text: str
    type: str  # entity, relationship, property
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComprehensiveSearchRequestDTO:
    """Request DTO for comprehensive search operations."""

    kg_id: str
    tenant_id: str
    user_id: str
    query: str
    threshold: Optional[float] = None
    filter_by_node_types: Optional[List[str]] = None


@dataclass
class ComprehensiveSearchResponseDTO:
    """Response DTO for comprehensive search operations."""

    kg_id: str
    tenant_id: str
    query: str
    semantic_results: List[Dict[str, Any]]
    entity_results: List[Dict[str, Any]]
    hybrid_results: Optional[Dict[str, Any]]
    total_kg_results: int
    total_web_results: int
    processing_time_ms: float
    search_timestamp: datetime


@dataclass
class SearchSuggestionsResponseDTO:
    """Search suggestions response."""

    kg_id: str
    tenant_id: str
    partial_query: str
    suggestions: List[SuggestionDTO]
    total_suggestions: int
    processing_time_ms: float


@dataclass
class SimilarEntitiesRequestDTO(TenantScopedRequestDTO):
    """Request to find similar entities."""

    kg_id: str
    entity_id: str
    similarity_algorithm: str = "embedding"  # embedding, structural, property
    limit: int = 10
    threshold: float = 0.7
    include_explanation: bool = True


@dataclass
class SimilarityExplanationDTO:
    """Explanation of similarity calculation."""

    algorithm: str
    factors: Dict[str, float]
    description: str


@dataclass
class SimilarEntityDTO:
    """Similar entity result."""

    entity: EntityDTO
    similarity_score: float
    explanation: Optional[SimilarityExplanationDTO] = None


@dataclass
class SimilarEntitiesResponseDTO(BaseResponseDTO):
    """Response DTO for similar entities search."""

    entities: List[SimilarEntityDTO] = field(default_factory=list)
    query_entity: Optional[EntityDTO] = None
    similarity_threshold: float = 0.0
    total_found: int = 0


# Multimodal DTOs
@dataclass(frozen=True)
class ProcessMultimodalContentRequestDTO:
    """Request DTO for processing multimodal content."""

    tenant_id: str
    user_id: str
    kg_id: str
    content_path: str
    content_type: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class MultimodalEntityDTO:
    """DTO for multimodal entity."""

    id: str
    content_type: str
    content_path: str
    extracted_text: Optional[str]
    processing_status: str
    relationships_count: int
    embeddings_count: int
    created_at: str
    updated_at: str


@dataclass
class ProcessMultimodalContentResponseDTO(BaseResponseDTO):
    """Response DTO for processing multimodal content."""

    entity: Optional[MultimodalEntityDTO] = None


# Agent DTOs
@dataclass(frozen=True)
class CreateCoordinationSessionRequestDTO:
    """Request DTO for creating coordination session."""

    tenant_id: str
    user_id: str
    kg_id: str
    strategy: str
    participating_agent_ids: List[str]
    session_goal: str
    session_parameters: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class CoordinationSessionDTO:
    """DTO for coordination session."""

    id: str
    strategy: str
    participating_agents_count: int
    session_goal: str
    status: str
    started_at: str
    completed_at: Optional[str] = None


@dataclass
class CreateCoordinationSessionResponseDTO(BaseResponseDTO):
    """Response DTO for creating coordination session."""

    session: Optional[CoordinationSessionDTO] = None


@dataclass(frozen=True)
class CreateAgentRequestDTO:
    """Request DTO for creating an agent."""

    tenant_id: str
    user_id: str
    name: str
    agent_type: str
    specialization_domain: str
    capabilities: List[str]
    configuration: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AgentDTO:
    """DTO for agent entity."""

    id: str
    name: str
    agent_type: str
    specialization_domain: str
    status: str
    capabilities: List[str]
    current_task_id: Optional[str]
    performance_score: Optional[float]
    created_at: str
    is_active: bool


@dataclass
class CreateAgentResponseDTO(BaseResponseDTO):
    """Response DTO for creating an agent."""

    agent: Optional[AgentDTO] = None


# Workflow and Job Management DTOs
@dataclass
class CreateWorkflowRequestDTO(TenantScopedRequestDTO):
    """Request to create a new workflow."""

    name: str
    description: Optional[str]
    definition: Dict[str, Any]  # Workflow definition (steps, parameters, etc.)
    workflow_type: (
        str  # ingestion, query, analytics, export, validation, transformation
    )
    version: str = "1.0.0"


@dataclass
class WorkflowDTO:
    """Workflow data transfer object."""

    id: str
    name: str
    description: Optional[str]
    tenant_id: str
    definition: Dict[str, Any]
    workflow_type: str
    version: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


@dataclass
class UpdateWorkflowRequestDTO(TenantScopedRequestDTO):
    """Request to update a workflow."""

    workflow_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@dataclass
class ExecuteWorkflowRequestDTO(TenantScopedRequestDTO):
    """Request to execute a workflow."""

    workflow_id: str
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3


@dataclass
class JobDTO:
    """Job data transfer object."""

    id: str
    workflow_id: str
    tenant_id: str
    status: str  # pending, running, completed, failed, cancelled, retrying
    input_parameters: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    progress_percentage: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    retry_count: int
    max_retries: int


@dataclass
class GetJobStatusRequestDTO(TenantScopedRequestDTO):
    """Request to get job status."""

    job_id: str


@dataclass
class CancelJobRequestDTO(TenantScopedRequestDTO):
    """Request to cancel a job."""

    job_id: str
    reason: Optional[str] = None


@dataclass
class ListJobsRequestDTO(TenantScopedRequestDTO):
    """Request to list jobs."""

    workflow_id: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pagination: Optional[PaginationParams] = None
    sort: Optional[SortParams] = None


@dataclass
class JobsListResponseDTO:
    """Response for listing jobs."""

    jobs: List[JobDTO]
    total_jobs: int
    filters_applied: Dict[str, Any]
    processing_time_ms: float


@dataclass
class RetryFailedJobRequestDTO(TenantScopedRequestDTO):
    """Request to retry a failed job."""

    job_id: str
    reset_retry_count: bool = False


@dataclass
class WorkflowExecutionResponseDTO:
    """Response for workflow execution."""

    job: JobDTO
    workflow: WorkflowDTO
    execution_started: bool
    message: str


# Neo4j GraphRAG DTOs
@dataclass
class CreateKGPipelineRequestDTO(TenantScopedRequestDTO):
    """Request to create a Neo4j GraphRAG pipeline."""

    name: str
    description: Optional[str]
    node_types: List[str]
    relationship_types: List[str]
    patterns: List[Dict[str, str]]
    llm_config: Dict[str, Any]
    embedder_config: Dict[str, Any]
    from_pdf: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 200


@dataclass
class KGPipelineDTO:
    """Neo4j GraphRAG pipeline data transfer object."""

    id: str
    name: str
    description: Optional[str]
    tenant_id: str
    node_types: List[str]
    relationship_types: List[str]
    patterns: List[Dict[str, str]]
    llm_config: Dict[str, Any]
    embedder_config: Dict[str, Any]
    from_pdf: bool
    chunk_size: int
    chunk_overlap: int
    created_at: datetime
    updated_at: datetime
    is_active: bool


@dataclass
class BuildKnowledgeGraphRequestDTO(TenantScopedRequestDTO):
    """Request to build knowledge graph using Neo4j GraphRAG."""

    pipeline_id: str
    kg_id: str
    documents: List[str]
    document_metadata: Optional[List[Dict[str, Any]]] = None


@dataclass
class KnowledgeGraphBuildResultDTO:
    """Result from knowledge graph construction."""

    kg_id: str
    pipeline_id: str
    tenant_id: str
    node_count: int
    relationship_count: int
    processing_time_ms: float
    documents_processed: int
    build_timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class CreateVectorIndexRequestDTO(TenantScopedRequestDTO):
    """Request to create vector index."""

    index_name: str
    dimensions: int
    similarity_function: str  # cosine, euclidean, dot_product
    node_label: str = "Document"
    property_name: str = "embedding"


@dataclass
class VectorIndexDTO:
    """Vector index data transfer object."""

    index_name: str
    dimensions: int
    similarity_function: str
    node_label: str
    property_name: str
    tenant_id: str
    created_at: datetime
    is_active: bool


@dataclass
class VectorSearchRequestDTO(TenantScopedRequestDTO):
    """Request for vector similarity search."""

    query: str
    index_name: str
    top_k: int = 5
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    filter_conditions: Optional[Dict[str, Any]] = None


@dataclass
class VectorSearchResultDTO:
    """Vector search result."""

    node_id: str
    score: float
    content: str
    metadata: Dict[str, Any]


@dataclass
class VectorSearchResponseDTO:
    """Vector search response."""

    query: str
    index_name: str
    tenant_id: str
    results: List[VectorSearchResultDTO]
    total_results: int
    search_time_ms: float
    search_timestamp: datetime


@dataclass
class CreateRetrieverRequestDTO(TenantScopedRequestDTO):
    """Request to create retriever."""

    name: str
    retriever_type: str  # vector, text2cypher, hybrid
    kg_id: str
    vector_index_name: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.7
    cypher_examples: Optional[List[Dict[str, str]]] = None
    hybrid_weights: Optional[Dict[str, float]] = None


@dataclass
class RetrieverDTO:
    """Retriever data transfer object."""

    id: str
    name: str
    retriever_type: str
    kg_id: str
    tenant_id: str
    vector_index_name: Optional[str]
    top_k: int
    similarity_threshold: float
    cypher_examples: Optional[List[Dict[str, str]]]
    hybrid_weights: Optional[Dict[str, float]]
    created_at: datetime
    is_active: bool


@dataclass
class RAGSearchRequestDTO(TenantScopedRequestDTO):
    """Request for RAG search."""

    retriever_id: str
    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    filter_conditions: Optional[Dict[str, Any]] = None


@dataclass
class RAGSearchResponseDTO:
    """RAG search response."""

    query: str
    retriever_id: str
    tenant_id: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    search_timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class GenerateEmbeddingsRequestDTO(TenantScopedRequestDTO):
    """Request to generate embeddings."""

    texts: List[str]
    provider: str  # openai, sentence_transformers, huggingface
    model_name: str
    batch_size: int = 100


@dataclass
class EmbeddingResultDTO:
    """Embedding result."""

    text: str
    embedding: List[float]
    dimensions: int


@dataclass
class GenerateEmbeddingsResponseDTO:
    """Generate embeddings response."""

    provider: str
    model_name: str
    tenant_id: str
    embeddings: List[EmbeddingResultDTO]
    total_texts: int
    processing_time_ms: float
    generation_timestamp: datetime


@dataclass
class ExtractEntitiesRequestDTO(TenantScopedRequestDTO):
    """Request to extract entities and relationships."""

    documents: List[str]
    entity_types: List[str]
    relationship_types: List[str]
    extraction_patterns: List[Dict[str, str]]
    llm_model: str
    temperature: float = 0.1
    max_tokens: int = 2000


@dataclass
class ExtractedEntityDTO:
    """Extracted entity."""

    id: str
    type: str
    name: str
    properties: Dict[str, Any]
    confidence: float
    source_document_index: int


@dataclass
class ExtractedRelationshipDTO:
    """Extracted relationship."""

    id: str
    type: str
    source_entity_id: str
    target_entity_id: str
    properties: Dict[str, Any]
    confidence: float
    source_document_index: int


@dataclass
class EntityExtractionResponseDTO:
    """Entity extraction response."""

    tenant_id: str
    entities: List[ExtractedEntityDTO]
    relationships: List[ExtractedRelationshipDTO]
    total_entities: int
    total_relationships: int
    extraction_time_ms: float
    confidence_scores: Dict[str, float]
    extraction_timestamp: datetime


@dataclass
class RunGraphAnalyticsRequestDTO(TenantScopedRequestDTO):
    """Request to run graph analytics."""

    kg_id: str
    algorithms: List[str]  # pagerank, betweenness, closeness, community_detection
    parameters: Dict[str, Any]
    node_filters: Optional[Dict[str, Any]] = None
    relationship_filters: Optional[Dict[str, Any]] = None


@dataclass
class GraphAnalyticsResultDTO:
    """Graph analytics result."""

    algorithm: str
    results: Dict[str, Any]
    processing_time_ms: float
    metadata: Dict[str, Any]


@dataclass
class GraphAnalyticsResponseDTO:
    """Graph analytics response."""

    kg_id: str
    tenant_id: str
    analytics_results: List[GraphAnalyticsResultDTO]
    total_algorithms: int
    total_processing_time_ms: float
    analysis_timestamp: datetime


@dataclass
class OptimizeQueriesRequestDTO(TenantScopedRequestDTO):
    """Request to optimize graph queries."""

    kg_id: str
    queries: List[str]
    optimization_level: str = "standard"  # basic, standard, aggressive


@dataclass
class QueryOptimizationResultDTO:
    """Query optimization result."""

    original_query: str
    optimized_query: str
    optimization_techniques: List[str]
    estimated_performance_improvement: float
    explanation: str


@dataclass
class OptimizeQueriesResponseDTO:
    """Query optimization response."""

    kg_id: str
    tenant_id: str
    optimization_results: List[QueryOptimizationResultDTO]
    total_queries: int
    optimization_time_ms: float
    optimization_timestamp: datetime


# Security DTOs
@dataclass(frozen=True)
class CreateAPIKeyRequestDTO:
    """Request DTO for creating API key."""

    tenant_id: str
    user_id: str
    name: str
    scopes: List[str]
    expires_at: Optional[str] = None  # ISO format datetime
    rate_limit: Optional[int] = None


@dataclass(frozen=True)
class APIKeyDTO:
    """DTO for API key (without sensitive data)."""

    id: str
    name: str
    scopes: List[str]
    status: str
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    usage_count: int
    rate_limit: Optional[int]


@dataclass
class CreateAPIKeyResponseDTO(BaseResponseDTO):
    """Response DTO for creating API key."""

    api_key: Optional[APIKeyDTO] = None
    key_value: str = ""  # Only returned on creation


@dataclass(frozen=True)
class AuditLogRequestDTO:
    """Request DTO for querying audit logs."""

    tenant_id: str
    user_id: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    start_date: Optional[str] = None  # ISO format datetime
    end_date: Optional[str] = None  # ISO format datetime
    pagination: Optional[PaginationParams] = None


# Collaboration and Sharing DTOs
@dataclass
class ShareKnowledgeGraphRequestDTO(TenantScopedRequestDTO):
    """Request to share a knowledge graph."""

    kg_id: str
    share_type: str  # "public", "organization", "specific_users"
    permissions: List[str]  # "read", "write", "admin"
    expires_at: Optional[datetime] = None
    shared_with_user_ids: Optional[List[str]] = None
    message: Optional[str] = None


@dataclass
class ShareLinkDTO:
    """Share link data transfer object."""

    id: str
    kg_id: str
    tenant_id: str
    share_type: str
    permissions: List[str]
    shared_by: str
    shared_with_user_ids: Optional[List[str]]
    share_url: str
    access_token: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    last_accessed_at: Optional[datetime]
    access_count: int


@dataclass
class ShareKnowledgeGraphResponseDTO(BaseResponseDTO):
    """Response for sharing knowledge graph."""

    share_link: Optional[ShareLinkDTO] = None


@dataclass
class AddCommentRequestDTO(TenantScopedRequestDTO):
    """Request to add a comment."""

    resource_type: str  # "knowledge_graph", "node", "edge", "ontology"
    resource_id: str
    content: str
    parent_comment_id: Optional[str] = None  # For threaded comments
    mentions: Optional[List[str]] = None  # User IDs mentioned in comment


@dataclass
class CommentDTO:
    """Comment data transfer object."""

    id: str
    resource_type: str
    resource_id: str
    parent_comment_id: Optional[str]
    content: str
    author_id: str
    author_name: str
    mentions: List[str]
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    reply_count: int


@dataclass
class AddCommentResponseDTO(BaseResponseDTO):
    """Response for adding comment."""

    comment: Optional[CommentDTO] = None


@dataclass
class GetActivityFeedRequestDTO(TenantScopedRequestDTO):
    """Request to get activity feed."""

    resource_type: Optional[str] = None  # Filter by resource type
    resource_id: Optional[str] = None  # Filter by specific resource
    activity_types: Optional[List[str]] = None  # Filter by activity types
    user_ids: Optional[List[str]] = None  # Filter by specific users
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class ActivityDTO:
    """Activity data transfer object."""

    id: str
    activity_type: (
        str  # "created", "updated", "deleted", "shared", "commented", "annotated"
    )
    resource_type: str
    resource_id: str
    resource_name: str
    user_id: str
    user_name: str
    description: str
    metadata: Dict[str, Any]
    tenant_id: str
    timestamp: datetime


@dataclass
class GetActivityFeedResponseDTO(BaseResponseDTO):
    """Response for activity feed."""

    activities: List[ActivityDTO] = field(default_factory=list)
    total_activities: int = 0
    has_more: bool = False


@dataclass
class CreateAnnotationRequestDTO(TenantScopedRequestDTO):
    """Request to create an annotation."""

    resource_type: str  # "node", "edge", "graph_area"
    resource_id: str
    annotation_type: str  # "note", "highlight", "tag", "question"
    content: str
    is_private: bool = False
    position: Optional[Dict[str, float]] = (
        None  # x, y coordinates for visual annotations
    )
    style: Optional[Dict[str, str]] = None  # color, size, etc.


@dataclass
class AnnotationDTO:
    """Annotation data transfer object."""

    id: str
    resource_type: str
    resource_id: str
    annotation_type: str
    content: str
    position: Optional[Dict[str, float]]
    style: Optional[Dict[str, str]]
    author_id: str
    author_name: str
    tenant_id: str
    is_private: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class CreateAnnotationResponseDTO(BaseResponseDTO):
    """Response for creating annotation."""

    annotation: Optional[AnnotationDTO] = None


@dataclass
class ManagePermissionsRequestDTO(TenantScopedRequestDTO):
    """Request to manage resource permissions."""

    resource_type: str  # "knowledge_graph", "ontology", "workflow"
    resource_id: str
    action: str  # "grant", "revoke", "update"
    role: Optional[str] = None  # "viewer", "editor", "admin"
    permissions: Optional[List[str]] = None  # Specific permissions
    target_user_id: Optional[str] = None


@dataclass
class ResourcePermissionDTO:
    """Resource permission data transfer object."""

    id: str
    resource_type: str
    resource_id: str
    user_id: str
    user_name: str
    role: str
    permissions: List[str]
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


@dataclass
class ManagePermissionsResponseDTO(BaseResponseDTO):
    """Response for managing permissions."""

    permission: Optional[ResourcePermissionDTO] = None
    affected_permissions: List[ResourcePermissionDTO] = field(default_factory=list)


@dataclass
class GetCollaborationHistoryRequestDTO(TenantScopedRequestDTO):
    """Request to get collaboration history."""

    resource_type: str
    resource_id: str
    collaboration_types: Optional[List[str]] = (
        None  # "edit", "comment", "share", "annotate"
    )
    user_ids: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pagination: Optional[PaginationParams] = None


@dataclass
class CollaborationEventDTO:
    """Collaboration event data transfer object."""

    id: str
    event_type: str  # "edit", "comment", "share", "annotate", "permission_change"
    resource_type: str
    resource_id: str
    user_id: str
    user_name: str
    description: str
    changes: Dict[str, Any]  # What was changed
    metadata: Dict[str, Any]
    tenant_id: str
    timestamp: datetime


@dataclass
class GetCollaborationHistoryResponseDTO(BaseResponseDTO):
    """Response for collaboration history."""

    events: List[CollaborationEventDTO] = field(default_factory=list)
    total_events: int = 0
    contributors: List[str] = field(
        default_factory=list
    )  # List of user IDs who contributedone


@dataclass(frozen=True)
class AuditLogDTO:
    """DTO for audit log entry."""

    id: str
    action: str
    resource_type: str
    resource_id: str
    user_id: Optional[str]
    timestamp: str  # ISO format datetime
    ip_address: Optional[str]
    details: Dict[str, Any]


@dataclass
class AuditLogResponseDTO(BaseResponseDTO):
    """Response DTO for audit log query."""

    logs: List[AuditLogDTO] = field(default_factory=list)
    total_count: int = 0
    summary: Optional[Dict[str, int]] = None


# Webhook and Integration DTOs
@dataclass
class CreateWebhookRequestDTO(TenantScopedRequestDTO):
    """Request to create a new webhook."""

    name: str
    url: str
    events: List[str]
    description: Optional[str] = None
    is_active: bool = True


@dataclass
class WebhookDTO:
    """Webhook data transfer object."""

    id: str
    name: str
    url: str
    events: List[str]
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    secret: Optional[str] = None  # Only included in creation response
    description: Optional[str] = None
    last_triggered_at: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


@dataclass
class UpdateWebhookRequestDTO(TenantScopedRequestDTO):
    """Request to update a webhook."""

    webhook_id: str
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class TestWebhookRequestDTO(TenantScopedRequestDTO):
    """Request to test a webhook."""

    webhook_id: str
    test_event_type: str = "test"
    test_payload: Optional[Dict[str, Any]] = None


@dataclass
class WebhookTestResultDTO:
    """Webhook test result."""

    webhook_id: str
    test_event_type: str
    success: bool
    tested_at: datetime
    response_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class GetIntegrationStatusRequestDTO(TenantScopedRequestDTO):
    """Request to get integration status."""

    integration_type: Optional[str] = None  # webhook, api, external_system


@dataclass
class IntegrationStatusDTO:
    """Integration status information."""

    integration_type: str
    integration_id: str
    name: str
    status: str  # active, inactive, error, pending
    last_check_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationStatusResponseDTO:
    """Response for integration status check."""

    integrations: List[IntegrationStatusDTO]
    overall_status: str  # healthy, degraded, critical
    total_integrations: int
    active_integrations: int
    failed_integrations: int
    checked_at: datetime


@dataclass
class SyncExternalDataRequestDTO(TenantScopedRequestDTO):
    """Request to sync data from external system."""

    source_type: str  # api, database, file, webhook
    source_config: Dict[str, Any]
    target_kg_id: str
    sync_mode: str = "incremental"  # full, incremental, delta
    transformation_rules: Optional[Dict[str, Any]] = None


@dataclass
class ExternalDataSyncResultDTO:
    """Result of external data synchronization."""

    sync_id: str
    source_type: str
    target_kg_id: str
    sync_mode: str
    status: str  # completed, failed, partial
    records_processed: int
    records_imported: int
    records_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportToExternalSystemRequestDTO(TenantScopedRequestDTO):
    """Request to export data to external system."""

    kg_id: str
    target_type: str  # api, database, file, webhook
    target_config: Dict[str, Any]
    export_format: str = "json"  # json, rdf, csv, xml
    export_filters: Optional[Dict[str, Any]] = None
    transformation_rules: Optional[Dict[str, Any]] = None


@dataclass
class ExternalDataExportResultDTO:
    """Result of external data export."""

    export_id: str
    kg_id: str
    target_type: str
    export_format: str
    status: str  # completed, failed, partial
    records_exported: int
    records_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    export_location: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManageAPIKeysRequestDTO(TenantScopedRequestDTO):
    """Request to manage API keys."""

    action: str  # create, update, delete, list, rotate
    api_key_id: Optional[str] = None
    name: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    rate_limit: Optional[int] = None


@dataclass
class APIKeyDTO:
    """API key data transfer object."""

    id: str
    name: str
    tenant_id: str
    scopes: List[str]
    key_prefix: str  # First 8 characters for identification
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    rate_limit: Optional[int] = None
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class APIKeyManagementResponseDTO:
    """Response for API key management operations."""

    action: str
    success: bool
    api_key: Optional[APIKeyDTO] = None
    api_keys: Optional[List[APIKeyDTO]] = None
    full_key: Optional[str] = None  # Only returned on creation
    message: str = ""
