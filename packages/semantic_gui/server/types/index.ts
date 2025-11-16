/**
 * Universal Tag System Types
 *
 * This module exports all types and interfaces for the Universal Tag System.
 * Import from this module to access all Universal Tag System types.
 */

// Core Universal Tag System types
// Import the main types to ensure they're available
import type {
  SCGTag,
  NativeTag,
  FrameworkDetectionResult,
  TagSuggestion,
  ProcessingContext,
  PatternMatchConfig,
} from './universal-tag-system';

export * from './universal-tag-system';

// Framework-specific configuration types
export * from './framework-configs';

// Re-export commonly used types for convenience
export type {
  // Core interfaces
  SCGTag,
  NativeTag,
  UniversalTagSystemConfig,
  IUniversalTagSystem,

  // Detection and translation
  FrameworkDetectionResult,
  TagTranslationResult,
  TagSuggestion,

  // Patterns and configuration
  TagPattern,
  FrameworkTagConfig,

  // Migration and validation
  MigrationResult,
  ValidationResult,
  ValidationRule,

  // Template integration
  Template,

  // Processing context and stats
  ProcessingContext,
  TagProcessingStats,
} from './universal-tag-system';

export type {
  // Framework detection
  DetectionPattern,
  DetectionContext,
  FrameworkDetectionConfig,

  // Tag extraction
  ExtractionPattern,
  ExtractionContext,
  NativeTagData,

  // Translation
  TranslationRule,
  TranslationContext,

  // Convention-based detection
  ConventionPattern,
  ConventionConfig,

  // Auto-tagging
  AutoTagPattern,
  AutoTaggingConfig,

  // Validation
  FrameworkValidationRule,
  ValidationContext,
  ValidationViolation,

  // Utilities
  FrameworkCapabilities,
  FrameworkPerformanceMetrics,
} from './framework-configs';

// Type guards and utility functions
export const isValidSCGTag = (tag: any): tag is SCGTag => {
  return (
    tag &&
    typeof tag === 'object' &&
    typeof tag.type === 'string' &&
    typeof tag.layer === 'string' &&
    typeof tag.domain === 'string' &&
    typeof tag.framework === 'string' &&
    typeof tag.language === 'string' &&
    typeof tag.filePath === 'string' &&
    Array.isArray(tag.dependencies) &&
    Array.isArray(tag.implements) &&
    Array.isArray(tag.uses) &&
    typeof tag.metadata === 'object' &&
    Array.isArray(tag.originalTags)
  );
};

export const isValidNativeTag = (tag: any): tag is NativeTag => {
  return (
    tag &&
    typeof tag === 'object' &&
    typeof tag.type === 'string' &&
    typeof tag.value === 'string' &&
    typeof tag.framework === 'string' &&
    typeof tag.filePath === 'string' &&
    typeof tag.context === 'object' &&
    typeof tag.rawMatch === 'string' &&
    typeof tag.extractedData === 'object' &&
    typeof tag.confidence === 'number' &&
    typeof tag.isValidated === 'boolean'
  );
};

export const isValidFrameworkDetectionResult = (
  result: any
): result is FrameworkDetectionResult => {
  return (
    result &&
    typeof result === 'object' &&
    typeof result.templateId === 'string' &&
    typeof result.framework === 'string' &&
    typeof result.confidence === 'number' &&
    Array.isArray(result.detectedPatterns) &&
    typeof result.metadata === 'object'
  );
};

export const isValidTagSuggestion = (
  suggestion: any
): suggestion is TagSuggestion => {
  return (
    suggestion &&
    typeof suggestion === 'object' &&
    typeof suggestion.suggestedTag === 'object' &&
    typeof suggestion.confidence === 'number' &&
    typeof suggestion.reason === 'string' &&
    typeof suggestion.filePath === 'string' &&
    typeof suggestion.codeContext === 'string' &&
    typeof suggestion.canAutoApply === 'boolean' &&
    typeof suggestion.template === 'string' &&
    typeof suggestion.source === 'string' &&
    Array.isArray(suggestion.alternatives)
  );
};

// Constants for common values
export const SCG_TAG_TYPES = [
  'module',
  'usecase',
  'entity',
  'port',
  'adapter',
  'service',
  'controller',
  'repository',
  'dto',
  'valueobject',
] as const;

export const SCG_LAYERS = [
  'domain',
  'application',
  'infrastructure',
  'presentation',
] as const;

export const SUPPORTED_FRAMEWORKS = [
  'kthulu',
  'laravel',
  'spring-boot',
  'django',
  'react',
  'nextjs',
  'express',
  'nestjs',
  'generic',
] as const;

export const TAG_SUGGESTION_SOURCES = [
  'ast',
  'pattern',
  'convention',
  'ml',
  'user',
] as const;

export const VALIDATION_SEVERITIES = ['error', 'warning', 'info'] as const;

// Default configurations
export const DEFAULT_PROCESSING_CONTEXT: Partial<ProcessingContext> = {
  options: {
    includeConventions: true,
    autoSuggest: true,
    validateTags: true,
    preserveComments: true,
  },
};

export const DEFAULT_PATTERN_MATCH_CONFIG: PatternMatchConfig = {
  caseSensitive: false,
  multiline: true,
  dotAll: false,
  unicode: true,
  maxMatches: 1000,
  timeout: 5000,
};
