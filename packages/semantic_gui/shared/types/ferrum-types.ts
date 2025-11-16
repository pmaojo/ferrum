/**
 * Ferrum Framework Type Definitions
 *
 * This module defines comprehensive interfaces for Ferrum framework integration
 * with the Semantic Code Graph (SCG) system, including graph data exchange,
 * DSL parsing, and validation schemas.
 */

import { z } from 'zod';

// ============================================================================
// Core Ferrum Graph Data Types
// ============================================================================

/**
 * Position coordinates for visual graph nodes
 */
export interface Position {
  x: number;
  y: number;
}

/**
 * Ferrum-specific node data structure
 */
export interface FerrumNodeData {
  input?: Array<{ name: string; type: string }>;
  output?: string;
  depends_on?: string[];
  implements?: string;
  fields?: Record<string, string>;
  methods?: Array<{ name: string; parameters?: string[]; returnType?: string }>;
  protocol?: string;
  driver?: string;
  expose?: {
    method?: string;
    protocol?: string;
    path?: string;
    generateHook?: boolean;
  };
  code?: string;
  features?: string[];
}

/**
 * Ferrum graph node definition
 */
export interface FerrumGraphNode {
  id: string;
  type: "module" | "usecase" | "adapter" | "port" | "entity" | "event" | "handler" | "service" | "iot";
  position: Position;
  data: FerrumNodeData;
  metadata?: {
    filePath?: string;
    lineNumber?: number;
    description?: string;
    tags?: string[];
  };
}

/**
 * Ferrum graph edge definition
 */
export interface FerrumGraphEdge {
  id: string;
  source: string;
  target: string;
  type: "dependency" | "implementation" | "data_flow" | "calls" | "extends" | "aggregates";
  metadata?: {
    parameters?: Array<{
      name: string;
      type: string;
      direction: "input" | "output" | "bidirectional";
      required?: boolean;
    }>;
    methodCalls?: Array<{
      methodName: string;
      parameters?: string[];
      returnType?: string;
    }>;
  };
}

/**
 * Complete Ferrum graph data structure for SCG integration
 */
export interface FerrumGraphData {
  framework: "ferrum";
  version: string;
  nodes: FerrumGraphNode[];
  edges: FerrumGraphEdge[];
  metadata: {
    module: string;
    created_at: string;
    last_modified: string;
    app_name?: string;
    features?: string[];
    project_path?: string;
  };
}

// ============================================================================
// Ferrum DSL Structure Types
// ============================================================================

/**
 * Ferrum application configuration
 */
export interface FerrumApp {
  name: string;
  features?: string[];
}

/**
 * Ferrum entity definition
 */
export interface FerrumEntity {
  fields: Record<string, string>;
  methods?: Array<{
    name: string;
    parameters?: Record<string, string>;
    returnType?: string;
  }>;
}

/**
 * Ferrum use case definition
 */
export interface FerrumUseCase {
  input?: Array<{ name: string; type: string }>;
  output?: string;
  depends_on?: string[];
  implements?: string;
  code?: string;
}

/**
 * Ferrum adapter definition
 */
export interface FerrumAdapter {
  implements: string;
  depends_on?: string[];
  config?: Record<string, any>;
  code?: string;
}

/**
 * Ferrum port definition
 */
export interface FerrumPort {
  methods: Array<{
    name: string;
    parameters?: Record<string, string>;
    returnType?: string;
  }>;
}

/**
 * Ferrum IoT component definition
 */
export interface FerrumIoTComponent {
  name: string;
  code?: string;
  protocol: string;
  driver?: string;
  expose?: {
    method?: string;
    protocol?: string;
    path?: string;
    generateHook?: boolean;
  };
}

/**
 * Ferrum module definition
 */
export interface FerrumModule {
  entity?: FerrumEntity;
  usecases?: Record<string, FerrumUseCase>;
  adapters?: Record<string, FerrumAdapter>;
  ports?: Record<string, FerrumPort>;
  services?: Record<string, any>;
  handlers?: Record<string, any>;
}

/**
 * Complete Ferrum DSL structure
 */
export interface FerrumDSL {
  app: FerrumApp;
  modules?: Record<string, FerrumModule>;
  iot?: FerrumIoTComponent[];
}

// ============================================================================
// Validation Schemas
// ============================================================================

/**
 * Position validation schema
 */
export const PositionSchema = z.object({
  x: z.number(),
  y: z.number(),
});

/**
 * Ferrum node data validation schema
 */
export const FerrumNodeDataSchema = z.object({
  input: z.array(z.object({
    name: z.string(),
    type: z.string(),
  })).optional(),
  output: z.string().optional(),
  depends_on: z.array(z.string()).optional(),
  implements: z.string().optional(),
  fields: z.record(z.string()).optional(),
  methods: z.array(z.object({
    name: z.string(),
    parameters: z.array(z.string()).optional(),
    returnType: z.string().optional(),
  })).optional(),
  protocol: z.string().optional(),
  driver: z.string().optional(),
  expose: z.object({
    method: z.string().optional(),
    protocol: z.string().optional(),
    path: z.string().optional(),
    generateHook: z.boolean().optional(),
  }).optional(),
  code: z.string().optional(),
  features: z.array(z.string()).optional(),
});

/**
 * Ferrum graph node validation schema
 */
export const FerrumGraphNodeSchema = z.object({
  id: z.string(),
  type: z.enum(["module", "usecase", "adapter", "port", "entity", "event", "handler", "service", "iot"]),
  position: PositionSchema,
  data: FerrumNodeDataSchema,
  metadata: z.object({
    filePath: z.string().optional(),
    lineNumber: z.number().optional(),
    description: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }).optional(),
});

/**
 * Ferrum graph edge validation schema
 */
export const FerrumGraphEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  type: z.enum(["dependency", "implementation", "data_flow", "calls", "extends", "aggregates"]),
  metadata: z.object({
    parameters: z.array(z.object({
      name: z.string(),
      type: z.string(),
      direction: z.enum(["input", "output", "bidirectional"]),
      required: z.boolean().optional(),
    })).optional(),
    methodCalls: z.array(z.object({
      methodName: z.string(),
      parameters: z.array(z.string()).optional(),
      returnType: z.string().optional(),
    })).optional(),
  }).optional(),
});

/**
 * Complete Ferrum graph data validation schema
 */
export const FerrumGraphDataSchema = z.object({
  framework: z.literal("ferrum"),
  version: z.string(),
  nodes: z.array(FerrumGraphNodeSchema),
  edges: z.array(FerrumGraphEdgeSchema),
  metadata: z.object({
    module: z.string(),
    created_at: z.string(),
    last_modified: z.string(),
    app_name: z.string().optional(),
    features: z.array(z.string()).optional(),
    project_path: z.string().optional(),
  }),
});

/**
 * Ferrum DSL validation schema
 */
export const FerrumDSLSchema = z.object({
  app: z.object({
    name: z.string(),
    features: z.array(z.string()).optional(),
  }),
  modules: z.record(z.object({
    entity: z.object({
      fields: z.record(z.string()),
      methods: z.array(z.object({
        name: z.string(),
        parameters: z.record(z.string()).optional(),
        returnType: z.string().optional(),
      })).optional(),
    }).optional(),
    usecases: z.record(z.object({
      input: z.array(z.object({
        name: z.string(),
        type: z.string(),
      })).optional(),
      output: z.string().optional(),
      depends_on: z.array(z.string()).optional(),
      implements: z.string().optional(),
      code: z.string().optional(),
    })).optional(),
    adapters: z.record(z.object({
      implements: z.string(),
      depends_on: z.array(z.string()).optional(),
      config: z.record(z.any()).optional(),
      code: z.string().optional(),
    })).optional(),
    ports: z.record(z.object({
      methods: z.array(z.object({
        name: z.string(),
        parameters: z.record(z.string()).optional(),
        returnType: z.string().optional(),
      })),
    })).optional(),
    services: z.record(z.any()).optional(),
    handlers: z.record(z.any()).optional(),
  })).optional(),
  iot: z.array(z.object({
    name: z.string(),
    code: z.string().optional(),
    protocol: z.string(),
    driver: z.string().optional(),
    expose: z.object({
      method: z.string().optional(),
      protocol: z.string().optional(),
      path: z.string().optional(),
      generateHook: z.boolean().optional(),
    }).optional(),
  })).optional(),
});

// ============================================================================
// Utility Types and Functions
// ============================================================================

/**
 * Type guard for Ferrum graph data
 */
export function isFerrumGraphData(data: any): data is FerrumGraphData {
  try {
    FerrumGraphDataSchema.parse(data);
    return true;
  } catch {
    return false;
  }
}

/**
 * Type guard for Ferrum DSL
 */
export function isFerrumDSL(data: any): data is FerrumDSL {
  try {
    FerrumDSLSchema.parse(data);
    return true;
  } catch {
    return false;
  }
}

/**
 * Ferrum validation result type
 */
export interface FerrumValidationResult {
  valid: boolean;
  errors?: Array<{
    path: string;
    message: string;
    code: string;
  }>;
}

/**
 * Validate Ferrum graph data
 */
export function validateFerrumGraphData(data: any): FerrumValidationResult {
  try {
    FerrumGraphDataSchema.parse(data);
    return { valid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        valid: false,
        errors: error.errors.map(err => ({
          path: err.path.join('.'),
          message: err.message,
          code: err.code,
        })),
      };
    }
    return {
      valid: false,
      errors: [{ path: '', message: 'Unknown validation error', code: 'UNKNOWN' }],
    };
  }
}

/**
 * Validate Ferrum DSL
 */
export function validateFerrumDSL(data: any): FerrumValidationResult {
  try {
    FerrumDSLSchema.parse(data);
    return { valid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        valid: false,
        errors: error.errors.map(err => ({
          path: err.path.join('.'),
          message: err.message,
          code: err.code,
        })),
      };
    }
    return {
      valid: false,
      errors: [{ path: '', message: 'Unknown validation error', code: 'UNKNOWN' }],
    };
  }
}

// ============================================================================
// JSON Serialization/Deserialization
// ============================================================================

/**
 * Serialize Ferrum graph data to JSON string
 */
export function serializeFerrumGraphData(data: FerrumGraphData): string {
  return JSON.stringify(data, null, 2);
}

/**
 * Deserialize JSON string to Ferrum graph data
 */
export function deserializeFerrumGraphData(json: string): FerrumGraphData {
  const data = JSON.parse(json);
  const validation = validateFerrumGraphData(data);
  
  if (!validation.valid) {
    throw new Error(`Invalid Ferrum graph data: ${validation.errors?.map(e => e.message).join(', ')}`);
  }
  
  return data as FerrumGraphData;
}

/**
 * Serialize Ferrum DSL to JSON string
 */
export function serializeFerrumDSL(data: FerrumDSL): string {
  return JSON.stringify(data, null, 2);
}

/**
 * Deserialize JSON string to Ferrum DSL
 */
export function deserializeFerrumDSL(json: string): FerrumDSL {
  const data = JSON.parse(json);
  const validation = validateFerrumDSL(data);
  
  if (!validation.valid) {
    throw new Error(`Invalid Ferrum DSL: ${validation.errors?.map(e => e.message).join(', ')}`);
  }
  
  return data as FerrumDSL;
}