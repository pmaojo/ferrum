import type { GraphNode, GraphEdge } from '../../../shared/types/api-responses';

export interface Position {
  x: number;
  y: number;
}

export interface GraphNodeData {
  id: string;
  name: string;
  type: string;
  filePath?: string | null;
  description?: string | null;
  metadata?: Record<string, any> | null;
  sourceMap?: { file: string; line: number } | null;
  violation?: boolean;
  violationMessage?: string;
  collapsed?: boolean;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  type: string;
  metadata?: Record<string, any>;
  parameters?: EdgeParameter[];
  methodCalls?: MethodCall[];
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

export interface ValidationRule {
  rule: string;
  type: 'required' | 'prohibited';
  description: string;
}

export interface ValidationResult {
  id: string;
  projectId: string;
  ruleId: string;
  status: 'valid' | 'warning' | 'violation';
  sourceNodeId?: string;
  targetNodeId?: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface NodeType {
  type: string;
  pattern: string;
  color: string;
  icon: string;
}

export interface TemplateDefinition {
  id: string;
  name: string;
  description: string;
  nodeTypes: NodeType[];
  validationRules: ValidationRule[];
}

export interface ProjectData {
  id: string;
  name: string;
  description?: string;
  templateId: string;
  metadata?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata?: {
    totalNodes: number;
    totalEdges: number;
    lastUpdated: string;
  };
}
