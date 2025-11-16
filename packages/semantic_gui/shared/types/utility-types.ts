/**
 * Utility Types for Common Patterns
 *
 * This module defines utility types that provide better type safety
 * and reusable patterns throughout the SCG application.
 */

// ============================================================================
// Array Utility Types
// ============================================================================

/**
 * Non-empty array type - ensures array has at least one element
 */
export type NonEmptyArray<T> = [T, ...T[]];

/**
 * Array with minimum length
 */
export type MinLengthArray<T, N extends number> = T[] & { length: N };

/**
 * Array with maximum length
 */
export type MaxLengthArray<T, N extends number> = T[] & {
  length: number;
} & (T[] | (T[] & { length: N }));

/**
 * Fixed length array (tuple-like)
 */
export type FixedLengthArray<T, N extends number> = T[] & { length: N };

// ============================================================================
// Object Utility Types
// ============================================================================

/**
 * Make specific keys required while keeping others optional
 */
export type RequiredKeys<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Make specific keys optional while keeping others required
 */
export type OptionalKeys<T, K extends keyof T> = Omit<T, K> &
  Partial<Pick<T, K>>;

/**
 * Deep partial - makes all properties optional recursively
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Deep required - makes all properties required recursively
 */
export type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object ? DeepRequired<T[P]> : T[P];
};

/**
 * Deep readonly - makes all properties readonly recursively
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * Nullable type - allows null values
 */
export type Nullable<T> = T | null;

/**
 * Optional type - allows undefined values
 */
export type Optional<T> = T | undefined;

/**
 * Maybe type - allows null or undefined values
 */
export type Maybe<T> = T | null | undefined;

/**
 * Non-nullable type - excludes null and undefined
 */
export type NonNullable<T> = T extends null | undefined ? never : T;

// ============================================================================
// String Utility Types
// ============================================================================

/**
 * Non-empty string type
 */
export type NonEmptyString = string & { readonly __brand: unique symbol };

/**
 * Email string type
 */
export type EmailString = string & { readonly __emailBrand: unique symbol };

/**
 * URL string type
 */
export type UrlString = string & { readonly __urlBrand: unique symbol };

/**
 * UUID string type
 */
export type UuidString = string & { readonly __uuidBrand: unique symbol };

/**
 * ISO date string type
 */
export type IsoDateString = string & { readonly __isoDateBrand: unique symbol };

/**
 * File path string type
 */
export type FilePathString = string & {
  readonly __filePathBrand: unique symbol;
};

// ============================================================================
// Function Utility Types
// ============================================================================

/**
 * Async function type
 */
export type AsyncFunction<T extends any[] = any[], R = any> = (
  ...args: T
) => Promise<R>;

/**
 * Event handler type
 */
export type EventHandler<T = any> = (event: T) => void;

/**
 * Callback function type
 */
export type Callback<T = void> = () => T;

/**
 * Predicate function type
 */
export type Predicate<T> = (value: T) => boolean;

/**
 * Mapper function type
 */
export type Mapper<T, U> = (value: T) => U;

/**
 * Reducer function type
 */
export type Reducer<T, U> = (accumulator: U, current: T) => U;

// ============================================================================
// Result and Error Handling Types
// ============================================================================

/**
 * Result type for error handling without exceptions
 */
export type Result<T, E = Error> = Success<T> | Failure<E>;

export interface Success<T> {
  success: true;
  data: T;
}

export interface Failure<E> {
  success: false;
  error: E;
}

/**
 * Option type for nullable values
 */
export type Option<T> = Some<T> | None;

export interface Some<T> {
  isSome: true;
  isNone: false;
  value: T;
}

export interface None {
  isSome: false;
  isNone: true;
}

// ============================================================================
// API and HTTP Utility Types
// ============================================================================

/**
 * HTTP methods
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD';

/**
 * HTTP status codes
 */
export type HttpStatusCode =
  | 200
  | 201
  | 204
  | 400
  | 401
  | 403
  | 404
  | 409
  | 422
  | 500
  | 502
  | 503;

/**
 * Content types
 */
export type ContentType =
  | 'application/json'
  | 'application/xml'
  | 'text/plain'
  | 'text/html'
  | 'multipart/form-data'
  | 'application/x-www-form-urlencoded';

/**
 * Request headers
 */
export interface RequestHeaders {
  'Content-Type'?: ContentType;
  Authorization?: string;
  'X-API-Key'?: string;
  'User-Agent'?: string;
  Accept?: string;
  [key: string]: string | undefined;
}

// ============================================================================
// Validation Utility Types
// ============================================================================

/**
 * Validation result type
 */
export interface ValidationResult<T = any> {
  isValid: boolean;
  value?: T;
  errors: ValidationError[];
}

/**
 * Validation error type
 */
export interface ValidationError {
  field: string;
  message: string;
  code: string;
  value?: any;
}

/**
 * Validator function type
 */
export type Validator<T> = (value: T) => ValidationResult<T>;

// ============================================================================
// State Management Utility Types
// ============================================================================

/**
 * Loading state type
 */
export interface LoadingState {
  isLoading: boolean;
  error?: string;
  lastUpdated?: Date;
}

/**
 * Async state type
 */
export interface AsyncState<T> extends LoadingState {
  data?: T;
}

/**
 * Pagination state type
 */
export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
}

/**
 * Sort state type
 */
export interface SortState {
  field: string;
  direction: 'asc' | 'desc';
}

/**
 * Filter state type
 */
export interface FilterState {
  [key: string]: any;
}

// ============================================================================
// Component Utility Types
// ============================================================================

/**
 * Base component props
 */
export interface BaseComponentProps {
  className?: string;
  testId?: string;
  id?: string;
  'aria-label'?: string;
  'aria-describedby'?: string;
}

/**
 * Children prop type
 */
export interface WithChildren {
  children: React.ReactNode;
}

/**
 * Optional children prop type
 */
export interface WithOptionalChildren {
  children?: React.ReactNode;
}

/**
 * Ref forwarding type
 */
export type RefForwardingComponent<T, P = {}> = React.ForwardRefExoticComponent<
  P & React.RefAttributes<T>
>;

// ============================================================================
// Event Utility Types
// ============================================================================

/**
 * Custom event type
 */
export interface CustomEvent<T = any> {
  type: string;
  data: T;
  timestamp: Date;
  source?: string;
}

/**
 * Event emitter type
 */
export interface EventEmitter<T = any> {
  on(event: string, listener: (data: T) => void): void;
  off(event: string, listener: (data: T) => void): void;
  emit(event: string, data: T): void;
}

// ============================================================================
// Configuration Utility Types
// ============================================================================

/**
 * Environment type
 */
export type Environment = 'development' | 'staging' | 'production' | 'test';

/**
 * Log level type
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/**
 * Configuration type
 */
export interface Config {
  environment: Environment;
  apiUrl: string;
  logLevel: LogLevel;
  features: Record<string, boolean>;
  [key: string]: any;
}

// ============================================================================
// Type Guards and Utilities
// ============================================================================

/**
 * Type guard for non-null values
 */
export const isNotNull = <T>(value: T | null): value is T => value !== null;

/**
 * Type guard for non-undefined values
 */
export const isNotUndefined = <T>(value: T | undefined): value is T =>
  value !== undefined;

/**
 * Type guard for non-nullable values
 */
export const isNotNullable = <T>(value: T | null | undefined): value is T =>
  value != null;

/**
 * Type guard for non-empty strings
 */
export const isNonEmptyString = (value: string): value is NonEmptyString =>
  value.length > 0;

/**
 * Type guard for non-empty arrays
 */
export const isNonEmptyArray = <T>(value: T[]): value is NonEmptyArray<T> =>
  value.length > 0;

/**
 * Type guard for objects
 */
export const isObject = (value: any): value is Record<string, any> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * Type guard for functions
 */
export const isFunction = (value: any): value is Function =>
  typeof value === 'function';

/**
 * Type guard for promises
 */
export const isPromise = <T>(value: any): value is Promise<T> =>
  value && typeof value.then === 'function';

// ============================================================================
// Brand Types for Type Safety
// ============================================================================

/**
 * Brand type utility for creating nominal types
 */
export type Brand<T, B> = T & { readonly __brand: B };

/**
 * Entity ID types
 */
export type ProjectId = Brand<string, 'ProjectId'>;
export type UserId = Brand<string, 'UserId'>;
export type TemplateId = Brand<string, 'TemplateId'>;
export type NodeId = Brand<string, 'NodeId'>;
export type EdgeId = Brand<string, 'EdgeId'>;

/**
 * Timestamp types
 */
export type Timestamp = Brand<number, 'Timestamp'>;
export type IsoTimestamp = Brand<string, 'IsoTimestamp'>;

/**
 * Measurement types
 */
export type Percentage = Brand<number, 'Percentage'>;
export type Score = Brand<number, 'Score'>;
export type Confidence = Brand<number, 'Confidence'>;

// ============================================================================
// Conditional Types
// ============================================================================

/**
 * Extract keys of a specific type
 */
export type KeysOfType<T, U> = {
  [K in keyof T]: T[K] extends U ? K : never;
}[keyof T];

/**
 * Extract properties of a specific type
 */
export type PropertiesOfType<T, U> = Pick<T, KeysOfType<T, U>>;

/**
 * Exclude properties of a specific type
 */
export type ExcludePropertiesOfType<T, U> = Omit<T, KeysOfType<T, U>>;

/**
 * Make properties of a specific type optional
 */
export type OptionalPropertiesOfType<T, U> = ExcludePropertiesOfType<T, U> &
  Partial<PropertiesOfType<T, U>>;

/**
 * Make properties of a specific type required
 */
export type RequiredPropertiesOfType<T, U> = ExcludePropertiesOfType<T, U> &
  Required<PropertiesOfType<T, U>>;
