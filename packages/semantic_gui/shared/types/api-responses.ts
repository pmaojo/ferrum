/**
 * API Response Type Definitions
 *
 * This module defines comprehensive interfaces for all API responses
 * used throughout the SCG application, ensuring type safety for
 * client-server communication.
 */

// ============================================================================
// Base API Response Types
// ============================================================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp?: string;
  requestId?: string;
}

/**
 * Paginated API response
 */
export interface PaginatedResponse<T = any> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

/**
 * API error response
 */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  stack?: string;
  timestamp: string;
}

// ============================================================================
// Knowledge Base API Responses
// ============================================================================

export interface KnowledgeQuery {
  queryType:
    | 'pattern_search'
    | 'practice_search'
    | 'violation_analysis'
    | 'improvement_suggestions'
    | 'community_content'
    | 'architectural_guidance';
  queryText: string;
  context?: Record<string, any>;
  filters?: Record<string, any>;
  maxResults?: number;
}

export interface KnowledgeResult {
  queryId: string;
  resultType: string;
  title: string;
  description: string;
  content: Record<string, any>;
  relevanceScore: number;
  source: 'library' | 'community' | 'generated';
  metadata: Record<string, any>;
}

export interface ArchitecturalComponent {
  iri: string;
  componentType: string;
  name: string;
  moduleNamespace: string;
  properties: Record<string, any>;
  relationships: Array<{
    subjectIri: string;
    predicateIri: string;
    objectIri: string;
    relationshipType: string;
  }>;
}

export interface ArchitecturalInsight {
  id: string;
  title: string;
  description: string;
  insightType:
    | 'pattern_opportunity'
    | 'violation_risk'
    | 'improvement_potential';
  confidence: number;
  supportingEvidence: string[];
  recommendedActions: string[];
  relatedPatterns: string[];
  relatedPractices: string[];
  impactAssessment: Record<string, any>;
  createdAt: string;
}

export interface PatternMatch {
  patternId: string;
  patternName: string;
  confidence: number;
  matchedComponents: string[];
  missingComponents: string[];
  violations: string[];
  evidence: Record<string, any>;
  context: Record<string, any>;
}

export interface ImprovementSuggestion {
  id: string;
  suggestionType: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  rationale: string;
  affectedComponents: string[];
  implementationSteps: string[];
  codeExamples: Record<string, string>;
  estimatedEffort: string;
  benefits: string[];
  risks: string[];
  relatedPatterns: string[];
  relatedPractices: string[];
  confidence: number;
  createdAt: string;
}

// ============================================================================
// AI Service API Responses
// ============================================================================

export interface NaturalLanguageQueryRequest {
  query: string;
  session_id?: string;
  context?: {
    timestamp?: string;
    source?: string;
  };
}

export interface NaturalLanguageQueryResponse {
  response: string;
  confidence: number;
  session_id: string;
  suggestions?: string[];
  relatedQueries?: string[];
  metadata: Record<string, any>;
}

export interface CodeReviewRequest {
  files: string[];
  context: {
    project_type: string;
    architecture_style: string;
    review_focus: string[];
  };
}

export interface CodeReviewResponse {
  reviewId: string;
  overallScore: number;
  issues: Array<{
    file: string;
    line: number;
    column?: number;
    severity: 'error' | 'warning' | 'info';
    category: string;
    message: string;
    suggestion?: string;
    autoFixable: boolean;
  }>;
  suggestions: string[];
  metrics: {
    complexity: number;
    maintainability: number;
    testCoverage?: number;
  };
}

export interface SemanticCompletionRequest {
  context: {
    file_path: string;
    cursor_line: number;
    cursor_column: number;
    current_line: string;
    preceding_lines: string[];
    following_lines: string[];
    project_type: string;
    language: string;
    module_name?: string;
    component_type?: string;
  };
  partial_input: string;
  completion_type: string;
  max_suggestions?: number;
}

export interface SemanticCompletionResponse {
  suggestions: Array<{
    text: string;
    confidence: number;
    type: 'method' | 'property' | 'class' | 'variable' | 'import';
    description?: string;
    documentation?: string;
    insertText?: string;
  }>;
  context: Record<string, any>;
}

// ============================================================================
// Kthulu Service API Responses
// ============================================================================

export interface KthuluProject {
  id: string;
  name: string;
  path: string;
  status: 'active' | 'inactive' | 'error';
  lastSync?: string;
  metadata?: Record<string, any>;
}

export interface KthuluInitializeResponse extends ApiResponse {
  data: {
    project: KthuluProject;
    initialized: boolean;
    configPath?: string;
  };
}

export interface KthuluCommand {
  name: string;
  description: string;
  parameters: Array<{
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }>;
  examples?: string[];
}

export interface KthuluCommandResponse extends ApiResponse {
  data: {
    output: string;
    exitCode: number;
    duration: number;
    command: string;
    args: string[];
  };
}

export interface KthuluValidationResponse extends ApiResponse {
  data: {
    isValid: boolean;
    violations: Array<{
      rule: string;
      severity: 'error' | 'warning' | 'info';
      message: string;
      file?: string;
      line?: number;
      column?: number;
    }>;
    summary: {
      totalFiles: number;
      validFiles: number;
      errors: number;
      warnings: number;
    };
  };
}

export interface KthuluAnalysisResponse extends ApiResponse {
  data: {
    project: KthuluProject;
    architecture: {
      layers: string[];
      components: number;
      dependencies: number;
    };
    metrics: {
      complexity: number;
      coupling: number;
      cohesion: number;
    };
    suggestions: ImprovementSuggestion[];
  };
}

// ============================================================================
// Monitoring API Responses
// ============================================================================

export interface SystemHealthResponse extends ApiResponse {
  data: {
    status: 'healthy' | 'degraded' | 'unhealthy';
    services: Array<{
      name: string;
      status: 'up' | 'down' | 'degraded';
      responseTime?: number;
      lastCheck: string;
      details?: Record<string, any>;
    }>;
    metrics: {
      cpu: number;
      memory: number;
      disk: number;
      network?: number;
    };
    uptime: number;
    version: string;
  };
}

export interface MetricValue {
  value: number | string;
  timestamp?: string;
  [key: string]: any;
}

export interface AlertData {
  id: string;
  name: string;
  severity: 'critical' | 'warning' | 'info';
  status: 'active' | 'resolved' | 'suppressed';
  message: string;
  timestamp: string;
  [key: string]: any;
}

export interface MetricsQueryResponse extends ApiResponse {
  data: {
    metricName: string;
    values: MetricValue[];
    timeRange: {
      start: string;
      end: string;
    };
    labels?: Record<string, string>;
  };
}

// ============================================================================
// Graph API Responses
// ============================================================================

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  filePath?: string;
  description?: string;
  metadata?: Record<string, any>;
  sourceMap?: { file: string; line: number };
  violation?: boolean;
  violationMessage?: string;
  collapsed?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  metadata?: Record<string, any>;
  parameters?: EdgeParameter[];
  methodCalls?: MethodCall[];
  createdAt?: string;
  updatedAt?: string;
}

export interface EdgeParameter {
  name: string;
  type: string;
  direction: 'input' | 'output' | 'bidirectional';
  dataType?: string;
  required?: boolean;
  description?: string;
  defaultValue?: any;
}

export interface MethodCall {
  methodName: string;
  parameters?: string[];
  returnType?: string;
}

export interface GraphResponse extends ApiResponse {
  data: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    metadata?: {
      totalNodes: number;
      totalEdges: number;
      lastUpdated: string;
    };
  };
}

// ============================================================================
// Project API Responses
// ============================================================================

export interface Project {
  id: string;
  name: string;
  description?: string;
  templateId: string;
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'archived' | 'draft';
  owner?: {
    id: string;
    name: string;
    email: string;
  };
}

export type ProjectResponse = ApiResponse<Project>;

export type ProjectListResponse = PaginatedResponse<Project>;

export interface ProjectScoreResponse extends ApiResponse {
  data: {
    projectId: string;
    overallScore: number;
    scores: {
      architecture: number;
      codeQuality: number;
      testCoverage: number;
      documentation: number;
      performance: number;
    };
    trends: Array<{
      date: string;
      score: number;
    }>;
    recommendations: string[];
  };
}

// ============================================================================
// Template API Responses
// ============================================================================

export interface Template {
  id: string;
  name: string;
  description: string;
  version: string;
  metadata: {
    framework: string;
    language: string;
    architecture: string;
    versionRegex?: string;
    [key: string]: any;
  };
  nodeTypes: Array<{
    type: string;
    pattern: string;
    color: string;
    icon: string;
  }>;
  validationRules: Array<{
    rule: string;
    type: 'required' | 'prohibited';
    description: string;
  }>;
  createdAt: string;
  updatedAt: string;
}

export type TemplateResponse = ApiResponse<Template>;

export type TemplateListResponse = ApiResponse<Template[]>;

// ============================================================================
// WebSocket Message Types
// ============================================================================

export interface WebSocketMessage<T = unknown> {
  type: string;
  projectId?: string;
  data: T;
  timestamp: string;
}

export interface RealtimeEvent {
  eventType: string;
  timestamp: string;
  projectId: string;
  data: any;
  source?: string;
  correlationId?: string;
}

export interface WebSocketConnectionStatus {
  connected: boolean;
  reconnecting: boolean;
  lastConnected?: string;
  error?: string;
}
