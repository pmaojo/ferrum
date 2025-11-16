/**
 * Framework-specific configuration types and utilities
 *
 * This module defines types for framework-specific configurations
 * that are used by the Universal Tag System for detection, extraction,
 * and translation of framework-native tags.
 */

import type {
  TagPattern,
  UniversalTagSystemConfig,
} from './universal-tag-system';

// ============================================================================
// Framework Detection Types
// ============================================================================

/**
 * Framework detection pattern with scoring
 */
export interface DetectionPattern extends TagPattern {
  // Detection-specific properties
  priority: number; // Higher priority patterns are checked first
  exclusive: boolean; // If true, finding this pattern excludes other frameworks

  // Scoring configuration
  baseScore: number; // Base score for this pattern
  multiplier: number; // Score multiplier based on match quality

  // Validation
  validator?: (match: RegExpMatchArray, context: DetectionContext) => boolean;
}

/**
 * Context for framework detection
 */
export interface DetectionContext {
  filePath: string;
  fileContent: string;
  projectPath: string;

  // Project structure information
  allFiles: string[];
  directories: string[];
  configFiles: string[];

  // Previously detected information
  detectedLanguages: string[];
  detectedDependencies: string[];
  detectedPatterns: string[];
}

/**
 * Framework detection configuration
 */
export interface FrameworkDetectionConfig {
  framework: string;
  displayName: string;
  description: string;

  // Detection patterns
  patterns: DetectionPattern[];

  // Requirements
  requiredPatterns: string[]; // Pattern IDs that must match
  optionalPatterns: string[]; // Pattern IDs that boost confidence
  excludingPatterns: string[]; // Pattern IDs that exclude this framework

  // Confidence thresholds
  minConfidence: number; // Minimum confidence to consider detected
  highConfidence: number; // Confidence threshold for high certainty

  // Post-detection validation
  validator?: (context: DetectionContext) => Promise<boolean>;
}

// ============================================================================
// Tag Extraction Types
// ============================================================================

/**
 * Extraction pattern with context awareness
 */
export interface ExtractionPattern extends TagPattern {
  // Extraction-specific properties
  tagType: string; // Type of tag this pattern extracts
  layer: string; // Architectural layer

  // Context requirements
  requiredContext?: {
    fileExtensions?: string[];
    directoryPatterns?: string[];
    nearbyCode?: string[];
    imports?: string[];
  };

  // Extraction logic
  extractor: (
    match: RegExpMatchArray,
    context: ExtractionContext
  ) => NativeTagData;

  // Post-processing
  postProcessor?: (
    tag: NativeTagData,
    context: ExtractionContext
  ) => NativeTagData;
}

/**
 * Context for tag extraction
 */
export interface ExtractionContext {
  filePath: string;
  fileContent: string;
  framework: string;

  // AST information (if available)
  ast?: any;

  // File metadata
  fileStats: {
    size: number;
    lines: number;
    lastModified: Date;
  };

  // Code analysis
  imports: string[];
  exports: string[];
  classes: string[];
  functions: string[];

  // Project context
  projectStructure: {
    directories: string[];
    configFiles: string[];
    dependencies: string[];
  };
}

/**
 * Raw native tag data before processing
 */
export interface NativeTagData {
  type: string;
  value: string;
  rawMatch: string;

  // Location
  line: number;
  column: number;
  endLine?: number;
  endColumn?: number;

  // Extracted metadata
  metadata: Record<string, any>;

  // Context
  context: {
    className?: string;
    methodName?: string;
    namespace?: string;
    parentElement?: string;
  };

  // Quality metrics
  confidence: number;
  completeness: number; // How complete the extraction is (0-1)
}

// ============================================================================
// Translation Types
// ============================================================================

/**
 * Translation rule with conditional logic
 */
export interface TranslationRule {
  // Rule identification
  id: string;
  name: string;
  description: string;

  // Source pattern
  sourcePattern: {
    framework: string;
    tagType: string;
    valuePattern?: string; // Optional pattern for tag value
  };

  // Target mapping
  target: {
    scgType: string;
    scgLayer: string;

    // Dynamic mapping
    typeMapper?: (sourceTag: NativeTagData) => string;
    layerMapper?: (sourceTag: NativeTagData) => string;

    // Metadata transformation
    metadataTransform?: (
      sourceMetadata: Record<string, any>
    ) => Record<string, any>;
  };

  // Conditions
  conditions?: Array<{
    field: string;
    operator: 'equals' | 'contains' | 'matches' | 'exists';
    value?: any;
  }>;

  // Quality
  confidence: number; // Base confidence for this translation
  priority: number; // Priority when multiple rules match
}

/**
 * Translation context with framework information
 */
export interface TranslationContext {
  sourceFramework: string;
  targetFramework?: string; // For reverse translation

  // Template information
  sourceTemplate: UniversalTagSystemConfig;
  targetTemplate?: UniversalTagSystemConfig;

  // Project context
  projectPath: string;
  projectMetadata: {
    name: string;
    version: string;
    dependencies: string[];
    architecture: string;
  };

  // Translation options
  options: {
    preserveOriginal: boolean;
    includeMetadata: boolean;
    validateResult: boolean;
    generateSuggestions: boolean;
  };
}

// ============================================================================
// Convention-based Detection Types
// ============================================================================

/**
 * Convention pattern for implicit tag detection
 */
export interface ConventionPattern {
  // Pattern identification
  id: string;
  name: string;
  description: string;

  // Pattern type
  type: 'directory' | 'filename' | 'classname' | 'namespace' | 'import';

  // Pattern definition
  pattern: string; // Glob or regex pattern

  // Mapping
  mapping: {
    tagType: string;
    layer: string;
    confidence: number;
  };

  // Context requirements
  context?: {
    fileExtensions?: string[];
    requiredImports?: string[];
    excludePatterns?: string[];
  };

  // Validation
  validator?: (filePath: string, content: string) => boolean;
}

/**
 * Convention-based extraction configuration
 */
export interface ConventionConfig {
  framework: string;
  enabled: boolean;

  // Convention patterns
  patterns: ConventionPattern[];

  // Global settings
  settings: {
    caseSensitive: boolean;
    requireExactMatch: boolean;
    allowPartialMatches: boolean;
    minConfidence: number;
  };

  // Conflict resolution
  conflictResolution: {
    strategy:
      | 'first-match'
      | 'highest-confidence'
      | 'most-specific'
      | 'user-choice';
    tieBreaker: 'pattern-order' | 'alphabetical' | 'confidence';
  };
}

// ============================================================================
// Auto-tagging Types
// ============================================================================

/**
 * Auto-tagging pattern with injection template
 */
export interface AutoTagPattern {
  // Pattern identification
  id: string;
  name: string;
  description: string;

  // Detection pattern
  detectionPattern: TagPattern;

  // Suggested tag
  suggestedTag: {
    type: string;
    layer: string;
    metadata?: Record<string, any>;
  };

  // Injection configuration
  injection: {
    template: string; // Template for tag injection
    position: 'before' | 'after' | 'inline' | 'separate-line';
    indentation: 'auto' | 'none' | number; // Indentation strategy
  };

  // Quality and safety
  confidence: number;
  safetyLevel: 'safe' | 'moderate' | 'risky'; // Safety level for auto-application

  // Validation
  preInjectionValidator?: (code: string, position: number) => boolean;
  postInjectionValidator?: (modifiedCode: string) => boolean;
}

/**
 * Auto-tagging configuration
 */
export interface AutoTaggingConfig {
  framework: string;
  enabled: boolean;

  // Patterns
  patterns: AutoTagPattern[];

  // Global settings
  settings: {
    autoApplyThreshold: number; // Confidence threshold for auto-application
    requireUserConfirmation: boolean;
    preserveExistingTags: boolean;
    backupOriginalFiles: boolean;
  };

  // Safety settings
  safety: {
    maxTagsPerFile: number;
    maxFilesPerBatch: number;
    requireSyntaxValidation: boolean;
    allowOverwrite: boolean;
  };
}

// ============================================================================
// Validation Types
// ============================================================================

/**
 * Framework-specific validation rule
 */
export interface FrameworkValidationRule {
  // Rule identification
  id: string;
  framework: string;
  name: string;
  description: string;

  // Rule definition
  condition: {
    type:
      | 'tag-exists'
      | 'tag-pattern'
      | 'relationship'
      | 'convention'
      | 'custom';
    parameters: Record<string, any>;
  };

  // Validation logic
  validator: (tags: any[], context: ValidationContext) => ValidationViolation[];

  // Rule metadata
  severity: 'error' | 'warning' | 'info';
  category:
    | 'architecture'
    | 'naming'
    | 'structure'
    | 'relationships'
    | 'quality';

  // Auto-fix capability
  autoFixable: boolean;
  autoFixer?: (violation: ValidationViolation) => string;
}

/**
 * Validation context
 */
export interface ValidationContext {
  framework: string;
  projectPath: string;

  // All tags in the project
  allTags: any[];

  // File context
  currentFile?: string;
  fileContent?: string;

  // Project metadata
  projectMetadata: {
    structure: string[];
    dependencies: string[];
    configuration: Record<string, any>;
  };

  // Validation options
  options: {
    strictMode: boolean;
    includeWarnings: boolean;
    checkRelationships: boolean;
    validateNaming: boolean;
  };
}

/**
 * Validation violation
 */
export interface ValidationViolation {
  ruleId: string;
  severity: 'error' | 'warning' | 'info';
  message: string;

  // Location
  file?: string;
  line?: number;
  column?: number;

  // Context
  tagId?: string;
  relatedTags?: string[];

  // Fix information
  autoFixable: boolean;
  suggestedFix?: string;
  fixPreview?: string;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Framework capability matrix
 */
export interface FrameworkCapabilities {
  framework: string;

  // Detection capabilities
  detection: {
    accuracy: number; // 0-1 accuracy score
    speed: 'fast' | 'medium' | 'slow';
    reliability: 'high' | 'medium' | 'low';
  };

  // Extraction capabilities
  extraction: {
    nativeTagSupport: boolean;
    conventionSupport: boolean;
    astSupport: boolean;
    coverage: number; // 0-1 coverage of framework features
  };

  // Translation capabilities
  translation: {
    bidirectional: boolean;
    lossless: boolean;
    accuracy: number; // 0-1 translation accuracy
  };

  // Auto-tagging capabilities
  autoTagging: {
    supported: boolean;
    safetyLevel: 'high' | 'medium' | 'low';
    accuracy: number; // 0-1 auto-tagging accuracy
  };

  // Validation capabilities
  validation: {
    architecturalRules: boolean;
    namingConventions: boolean;
    relationshipValidation: boolean;
    customRules: boolean;
  };
}

/**
 * Performance metrics for framework processing
 */
export interface FrameworkPerformanceMetrics {
  framework: string;

  // Processing times (in milliseconds)
  detection: {
    averageTime: number;
    maxTime: number;
    minTime: number;
  };

  extraction: {
    averageTimePerFile: number;
    averageTimePerTag: number;
    throughput: number; // Tags per second
  };

  translation: {
    averageTime: number;
    successRate: number; // 0-1 success rate
  };

  // Memory usage
  memory: {
    peakUsage: number; // Peak memory usage in MB
    averageUsage: number; // Average memory usage in MB
  };

  // Quality metrics
  quality: {
    falsePositiveRate: number; // 0-1 false positive rate
    falseNegativeRate: number; // 0-1 false negative rate
    accuracy: number; // 0-1 overall accuracy
  };
}
