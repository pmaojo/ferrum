/**
 * Type Guards for Runtime Type Validation
 *
 * This module provides type guards for validating external API data
 * and ensuring type safety at runtime.
 */

import type {
  ApiResponse,
  GraphNode,
  GraphEdge,
  Template,
  Project,
  KthuluCommand,
  MetricValue,
  AlertData,
} from './api-responses';

// Import ValidationResult from utility-types to avoid conflict
import type { ValidationResult } from './utility-types';

// ============================================================================
// Utility Type Guards
// ============================================================================

/**
 * Type guard for checking if a value is a non-null object
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Type guard for checking if a value is a non-empty string
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

/**
 * Type guard for checking if a value is a valid number
 */
export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

/**
 * Type guard for checking if a value is a valid array
 */
export function isArray<T>(
  value: unknown,
  itemGuard?: (item: unknown) => item is T
): value is T[] {
  if (!Array.isArray(value)) return false;
  if (!itemGuard) return true;
  return value.every(itemGuard);
}

/**
 * Type guard for checking if a value is a valid date string
 */
export function isDateString(value: unknown): value is string {
  if (!isNonEmptyString(value)) return false;
  const date = new Date(value);
  return !isNaN(date.getTime());
}

// ============================================================================
// API Response Type Guards
// ============================================================================

/**
 * Type guard for ApiResponse
 */
export function isApiResponse<T>(
  value: unknown,
  dataGuard?: (data: unknown) => data is T
): value is ApiResponse<T> {
  if (!isObject(value)) return false;

  const response = value;

  // Check required success field
  if (typeof response.success !== 'boolean') return false;

  // Check optional fields
  if (response.error !== undefined && !isNonEmptyString(response.error))
    return false;
  if (response.message !== undefined && !isNonEmptyString(response.message))
    return false;
  if (response.timestamp !== undefined && !isDateString(response.timestamp))
    return false;
  if (response.requestId !== undefined && !isNonEmptyString(response.requestId))
    return false;

  // Check data field if guard provided
  if (dataGuard && response.data !== undefined) {
    return dataGuard(response.data);
  }

  return true;
}

/**
 * Type guard for GraphNode
 */
export function isGraphNode(value: unknown): value is GraphNode {
  if (!isObject(value)) return false;

  const node = value;

  return (
    isNonEmptyString(node.id) &&
    isNonEmptyString(node.name) &&
    isNonEmptyString(node.type) &&
    (node.filePath === undefined || isNonEmptyString(node.filePath)) &&
    (node.description === undefined || typeof node.description === 'string') &&
    (node.metadata === undefined || isObject(node.metadata)) &&
    (node.violation === undefined || typeof node.violation === 'boolean') &&
    (node.violationMessage === undefined ||
      typeof node.violationMessage === 'string') &&
    (node.collapsed === undefined || typeof node.collapsed === 'boolean') &&
    (node.createdAt === undefined || isDateString(node.createdAt)) &&
    (node.updatedAt === undefined || isDateString(node.updatedAt))
  );
}

/**
 * Type guard for GraphEdge
 */
export function isGraphEdge(value: unknown): value is GraphEdge {
  if (!isObject(value)) return false;

  const edge = value;

  return (
    isNonEmptyString(edge.id) &&
    isNonEmptyString(edge.source) &&
    isNonEmptyString(edge.target) &&
    isNonEmptyString(edge.type) &&
    (edge.metadata === undefined || isObject(edge.metadata)) &&
    (edge.createdAt === undefined || isDateString(edge.createdAt)) &&
    (edge.updatedAt === undefined || isDateString(edge.updatedAt))
  );
}

/**
 * Type guard for Template
 */
export function isTemplate(value: unknown): value is Template {
  if (!isObject(value)) return false;

  const template = value;

  return (
    isNonEmptyString(template.id) &&
    isNonEmptyString(template.name) &&
    isNonEmptyString(template.description) &&
    isNonEmptyString(template.version) &&
    isObject(template.metadata) &&
    isArray(template.nodeTypes, isObject) &&
    isArray(template.validationRules, isObject) &&
    isDateString(template.createdAt) &&
    isDateString(template.updatedAt)
  );
}

/**
 * Type guard for Project
 */
export function isProject(value: unknown): value is Project {
  if (!isObject(value)) return false;

  const project = value;

  return (
    isNonEmptyString(project.id) &&
    isNonEmptyString(project.name) &&
    isNonEmptyString(project.templateId) &&
    (project.description === undefined ||
      typeof project.description === 'string') &&
    (project.metadata === undefined || isObject(project.metadata)) &&
    isDateString(project.createdAt) &&
    isDateString(project.updatedAt) &&
    (project.status === 'active' ||
      project.status === 'archived' ||
      project.status === 'draft') &&
    (project.owner === undefined || isObject(project.owner))
  );
}

/**
 * Type guard for KthuluCommand
 */
export function isKthuluCommand(value: unknown): value is KthuluCommand {
  if (!isObject(value)) return false;

  const command = value;

  return (
    isNonEmptyString(command.name) &&
    isNonEmptyString(command.description) &&
    isArray(command.parameters, isObject) &&
    (command.examples === undefined ||
      isArray(command.examples, isNonEmptyString))
  );
}

/**
 * Type guard for ValidationResult
 */
export function isValidationResult(value: unknown): value is ValidationResult {
  if (!isObject(value)) return false;

  const result = value;

  return (
    typeof result.isValid === 'boolean' && isArray(result.errors, isObject)
  );
}

/**
 * Type guard for MetricValue
 */
export function isMetricValue(value: unknown): value is MetricValue {
  if (!isObject(value)) return false;

  const metric = value;

  return (
    (typeof metric.value === 'number' || typeof metric.value === 'string') &&
    (metric.timestamp === undefined || isDateString(metric.timestamp))
  );
}

/**
 * Type guard for AlertData
 */
export function isAlertData(value: unknown): value is AlertData {
  if (!isObject(value)) return false;

  const alert = value;

  return (
    isNonEmptyString(alert.id) &&
    isNonEmptyString(alert.name) &&
    (alert.severity === 'critical' ||
      alert.severity === 'warning' ||
      alert.severity === 'info') &&
    (alert.status === 'active' ||
      alert.status === 'resolved' ||
      alert.status === 'suppressed') &&
    isNonEmptyString(alert.message) &&
    isDateString(alert.timestamp)
  );
}

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validates and transforms API response data
 */
export function validateApiResponse<T>(
  data: unknown,
  dataGuard: (data: unknown) => data is T,
  errorMessage = 'Invalid API response'
): T {
  if (!isApiResponse(data, dataGuard)) {
    throw new Error(errorMessage);
  }

  if (!data.success) {
    throw new Error(data.error || data.message || 'API request failed');
  }

  if (data.data === undefined) {
    throw new Error('API response missing data');
  }

  return data.data;
}

/**
 * Validates array of items using a type guard
 */
export function validateArray<T>(
  data: unknown,
  itemGuard: (item: unknown) => item is T,
  errorMessage = 'Invalid array data'
): T[] {
  if (!isArray(data, itemGuard)) {
    throw new Error(errorMessage);
  }

  return data;
}

/**
 * Safely parses JSON with type validation
 */
export function safeJsonParse<T>(
  jsonString: string,
  typeGuard: (data: unknown) => data is T,
  errorMessage = 'Invalid JSON data'
): T {
  try {
    const parsed = JSON.parse(jsonString);
    if (!typeGuard(parsed)) {
      throw new Error(errorMessage);
    }
    return parsed;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error('Invalid JSON format');
    }
    throw error;
  }
}

/**
 * Creates a type-safe fetch wrapper
 */
export async function typedFetch<T>(
  url: string,
  typeGuard: (data: unknown) => data is T,
  options?: RequestInit,
  errorMessage = 'Failed to fetch data'
): Promise<T> {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!typeGuard(data)) {
      throw new Error(errorMessage);
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Network error or invalid URL');
    }
    throw error;
  }
}

/**
 * Creates a type-safe API response fetch wrapper
 */
export async function typedApiResponseFetch<T>(
  url: string,
  dataGuard: (data: unknown) => data is T,
  options?: RequestInit,
  errorMessage = 'Failed to fetch API data'
): Promise<T> {
  const response = await typedFetch(
    url,
    (data): data is ApiResponse<T> => isApiResponse(data, dataGuard),
    options,
    errorMessage
  );

  return validateApiResponse(response, dataGuard, errorMessage);
}
