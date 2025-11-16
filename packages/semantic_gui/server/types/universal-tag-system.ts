/**
 * Universal Tag System Core Interfaces and Data Structures
 *
 * This module defines the core types and interfaces for the Universal Tag System,
 * which enables SCG to work with any framework by translating native framework
 * tags to a universal SCG format.
 */

// ============================================================================
// Core Tag Interfaces
// ============================================================================

/**
 * Universal SCG Tag format - the standardized representation used across all SCG services
 */
export interface SCGTag {
  // Core SCG identification
  type:
    | 'module'
    | 'usecase'
    | 'entity'
    | 'port'
    | 'adapter'
    | 'service'
    | 'controller'
    | 'repository'
    | 'dto'
    | 'valueobject';
  layer: 'domain' | 'application' | 'infrastructure' | 'presentation';

  // Business context
  domain: string;
  aggregate?: string;
  boundedContext?: string;

  // Technical metadata
  framework: string;
  language: string;
  filePath: string;
  lineNumber?: number;

  // Relationships
  dependencies: string[];
  implements: string[];
  uses: string[];

  // Additional metadata
  metadata: {
    isPublic?: boolean;
    isAbstract?: boolean;
    complexity?: 'low' | 'medium' | 'high';
    testCoverage?: number;
    documentation?: string;
    [key: string]: any;
  };

  // Original framework-specific tags for traceability
  originalTags: NativeTag[];
}

/**
 * Native framework-specific tag representation
 */
export interface NativeTag {
  // Framework-specific identification
  type: string; // Framework-specific type (e.g., '@Controller', 'module', 'class')
  value: string; // The actual tag value or annotation
  framework: string; // Source framework (kthulu, laravel, spring-boot, etc.)

  // Location information
  filePath: string;
  lineNumber?: number;
  columnNumber?: number;

  // Context information
  context: {
    className?: string;
    methodName?: string;
    packageName?: string;
    namespace?: string;
    parentElement?: string;
  };

  // Raw extraction data
  rawMatch: string; // The original matched text
  extractedData: Record<string, any>; // Parsed data from the tag

  // Confidence and validation
  confidence: number; // 0-1 confidence score for the extraction
  isValidated: boolean; // Whether the tag has been validated
}

// ============================================================================
// Framework Detection
// ============================================================================

/**
 * Result of framework detection process
 */
export interface FrameworkDetectionResult {
  templateId: string; // ID of the detected template
  framework: string; // Framework name (kthulu, laravel, spring-boot, etc.)
  confidence: number; // 0-1 confidence score
  detectedPatterns: string[]; // List of patterns that matched
  metadata: {
    version?: string; // Framework version if detected
    variant?: string; // Framework variant (e.g., 'mvc', 'api', 'hexagonal')
    dependencies?: string[]; // Key dependencies found
    configFiles?: string[]; // Configuration files found
  };
}

// ============================================================================
// Tag Translation
// ============================================================================

/**
 * Result of tag translation process
 */
export interface TagTranslationResult {
  originalTags: NativeTag[]; // Input native tags
  translatedTags: SCGTag[]; // Successfully translated SCG tags
  untranslatable: NativeTag[]; // Tags that couldn't be translated
  suggestions: TagSuggestion[]; // Suggestions for untranslatable tags
  confidence: number; // Overall translation confidence
  warnings: string[]; // Translation warnings
}

/**
 * Tag suggestion for auto-tagging or manual review
 */
export interface TagSuggestion {
  // Suggested tag information
  suggestedTag: Partial<SCGTag>;
  confidence: number; // 0-1 confidence in the suggestion
  reason: string; // Explanation for the suggestion

  // Context information
  filePath: string;
  lineNumber?: number;
  codeContext: string; // Surrounding code for context

  // Application information
  canAutoApply: boolean; // Whether this can be auto-applied
  template: string; // Template for tag injection
  previewCode?: string; // Preview of code with tag applied

  // Metadata
  source: 'ast' | 'pattern' | 'convention' | 'ml' | 'user'; // How the suggestion was generated
  alternatives: Partial<SCGTag>[]; // Alternative suggestions
}

// ============================================================================
// Pattern Matching
// ============================================================================

/**
 * Base interface for tag patterns used in detection and extraction
 */
export interface TagPattern {
  // Pattern identification
  id: string;
  name: string;
  description: string;

  // Pattern definition
  pattern: string; // Regex pattern or glob pattern
  type: 'regex' | 'glob' | 'ast' | 'directory';

  // Matching configuration
  flags?: string; // Regex flags (i, g, m, etc.)
  weight: number; // Weight for confidence calculation

  // Context constraints
  context?: {
    filePattern?: string; // File must match this pattern
    directoryPattern?: string; // Directory must match this pattern
    nearbyPatterns?: string[]; // Nearby code must match these patterns
    excludePatterns?: string[]; // Exclude if these patterns match
  };

  // Extraction configuration
  extractors?: {
    [key: string]: string | number | boolean; // Field extractors
  };
}

/**
 * Framework-specific tag configuration
 */
export interface FrameworkTagConfig {
  // Framework identification
  framework: string;
  version?: string;
  variant?: string;

  // Detection patterns
  detectionPatterns: TagPattern[];

  // Extraction patterns by tag type
  extractionPatterns: {
    [tagType: string]: TagPattern[];
  };

  // Convention-based extraction
  conventions: {
    directoryMapping: Record<string, { type: string; layer: string }>;
    fileNamePatterns: Record<string, { type: string; layer: string }>;
    classNamePatterns: Record<string, { type: string; layer: string }>;
  };

  // Translation rules
  translationRules: {
    toSCG: Record<
      string,
      {
        scgType: SCGTag['type'];
        scgLayer: SCGTag['layer'];
        metadata?: Record<string, any>;
      }
    >;
    fromSCG: Record<string, string>; // Template strings for reverse translation
  };

  // Auto-tagging configuration
  autoTagging: {
    enabled: boolean;
    confidence: 'low' | 'medium' | 'high';
    patterns: Array<{
      pattern: TagPattern;
      suggestedTag: {
        type: string;
        layer: string;
        template: string; // Template string for tag injection
      };
    }>;
  };
}

// ============================================================================
// Universal Tag System Configuration
// ============================================================================

/**
 * Complete configuration for the Universal Tag System
 * This is embedded in template configurations
 */
export interface UniversalTagSystemConfig {
  // Framework detection configuration
  detection: {
    filePatterns: Array<{
      pattern: string;
      weight: number;
    }>;
    codePatterns: Array<{
      regex: string;
      weight: number;
    }>;
    directoryPatterns: Array<{
      pattern: string;
      weight: number;
    }>;
  };

  // Tag extraction configuration
  extraction: {
    nativePatterns: {
      [tagType: string]: Array<{
        regex: string;
        extractors: {
          type: string;
          layer?: string;
          domain?: string;
          metadata?: Record<string, any>;
        };
        context?: {
          filePattern?: string;
          directoryPattern?: string;
          nearbyPatterns?: string[];
        };
      }>;
    };
    conventions: {
      directoryMapping: Record<string, { type: string; layer: string }>;
      fileNamePatterns: Record<string, { type: string; layer: string }>;
      classNamePatterns: Record<string, { type: string; layer: string }>;
    };
  };

  // Translation configuration
  translation: {
    toSCG: Record<
      string,
      {
        scgType: SCGTag['type'];
        scgLayer: SCGTag['layer'];
        metadata?: Record<string, any>;
      }
    >;
    fromSCG: Record<string, string>; // Template strings for reverse translation
  };

  // Auto-tagging configuration
  autoTagging: {
    enabled: boolean;
    confidence: 'low' | 'medium' | 'high';
    patterns: Array<{
      regex: string;
      suggestedTag: {
        type: string;
        layer: string;
        template: string; // Template string for tag injection
      };
    }>;
  };
}

// ============================================================================
// Migration and Transformation
// ============================================================================

/**
 * Result of project migration between frameworks
 */
export interface MigrationResult {
  success: boolean;
  migratedFiles: string[];
  conflicts: Array<{
    file: string;
    issue: string;
    suggestion: string;
  }>;
  summary: {
    totalFiles: number;
    successfulMigrations: number;
    manualReviewRequired: number;
  };
}
// ============================================================================
// Validation and Quality Assurance
// ============================================================================

/**
 * Validation rule for tag consistency and quality
 */
export interface ValidationRule {
  id: string;
  name: string;
  description: string;
  severity: 'error' | 'warning' | 'info';

  // Rule definition
  condition: string; // Rule condition (could be a function or expression)
  message: string; // Error message template

  // Scope
  scope: 'tag' | 'file' | 'project' | 'cross-framework';
  applicableFrameworks?: string[]; // Frameworks this rule applies to

  // Auto-fix capability
  autoFixable: boolean;
  autoFixTemplate?: string; // Template for automatic fixes
}

/**
 * Result of tag validation
 */
export interface ValidationResult {
  isValid: boolean;
  violations: Array<{
    rule: ValidationRule;
    tag?: SCGTag;
    file?: string;
    message: string;
    severity: 'error' | 'warning' | 'info';
    autoFixAvailable: boolean;
  }>;
  summary: {
    totalTags: number;
    validTags: number;
    errors: number;
    warnings: number;
    infos: number;
  };
}

// ============================================================================
// Template Integration
// ============================================================================

/**
 * Extended template interface with Universal Tag System support
 */
export interface Template {
  id: string;
  name: string;
  description: string;
  version: string;

  // Existing template fields
  metadata: {
    framework: string;
    language: string;
    architecture: string;
    versionRegex?: string;
    [key: string]: any;
  };

  // Universal Tag System configuration
  universalTagSystem?: UniversalTagSystemConfig;

  // Validation rules
  validationRules?: ValidationRule[];
}

// ============================================================================
// Service Interfaces
// ============================================================================

/**
 * Main Universal Tag System service interface
 */
export interface IUniversalTagSystem {
  // Framework detection
  detectFramework(
    code: string,
    filePath: string
  ): Promise<FrameworkDetectionResult>;

  // Tag extraction and translation
  extractSCGTags(code: string, templateId: string): Promise<SCGTag[]>;
  translateToSCG(
    nativeTags: NativeTag[],
    templateId: string
  ): Promise<TagTranslationResult>;
  translateFromSCG(
    scgTags: SCGTag[],
    targetTemplateId: string
  ): Promise<NativeTag[]>;

  // Auto-tagging and suggestions
  suggestTags(
    code: string,
    filePath: string,
    templateId?: string
  ): Promise<TagSuggestion[]>;
  autoTag(
    code: string,
    filePath: string,
    suggestions: TagSuggestion[]
  ): Promise<string>;

  // Template management
  loadTemplateConfig(templateId: string): Promise<UniversalTagSystemConfig>;
  getAllSupportedTemplates(): Promise<Template[]>;

  // Migration
  migrateProject(
    fromTemplateId: string,
    toTemplateId: string,
    projectPath: string
  ): Promise<MigrationResult>;

  // Validation
  validateTags(tags: SCGTag[], templateId: string): Promise<ValidationResult>;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Configuration for pattern matching engines
 */
export interface PatternMatchConfig {
  caseSensitive: boolean;
  multiline: boolean;
  dotAll: boolean;
  unicode: boolean;
  maxMatches?: number;
  timeout?: number; // Timeout in milliseconds
}

/**
 * Context information for tag processing
 */
export interface ProcessingContext {
  projectPath: string;
  templateId: string;
  framework: string;
  language: string;

  // File context
  currentFile: string;
  relativeFilePath: string;
  fileContent: string;

  // Processing options
  options: {
    includeConventions: boolean;
    autoSuggest: boolean;
    validateTags: boolean;
    preserveComments: boolean;
  };
}

/**
 * Statistics and metrics for tag processing
 */
export interface TagProcessingStats {
  // Processing metrics
  totalFiles: number;
  processedFiles: number;
  skippedFiles: number;
  errorFiles: number;

  // Tag metrics
  totalTags: number;
  nativeTags: number;
  scgTags: number;
  suggestedTags: number;

  // Performance metrics
  processingTimeMs: number;
  averageTimePerFile: number;

  // Quality metrics
  translationAccuracy: number;
  suggestionAccuracy: number;
  validationScore: number;
}
