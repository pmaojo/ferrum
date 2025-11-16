/**
 * Universal Tag System for SCG - The Rosetta Stone for Software Architecture
 *
 * This system allows SCG to understand and translate architectural components
 * across different frameworks, creating a unified view of software architecture.
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

  // Original framework-specific tags
  originalTags: NativeTag[];
}

export interface NativeTag {
  framework: string;
  type: string;
  value: string;
  attributes?: Record<string, any>;
  location: {
    filePath: string;
    lineNumber: number;
    columnNumber?: number;
  };
}

export interface TagPattern {
  // Pattern matching
  regex: string;
  multiline?: boolean;
  flags?: string;

  // Extraction rules
  extractors: {
    type?: string;
    domain?: string;
    layer?: string;
    metadata?: Record<string, string>;
  };

  // Context rules
  context?: {
    filePattern?: string;
    directoryPattern?: string;
    nearbyPatterns?: string[];
  };
}

export interface FrameworkTagConfig {
  framework: string;
  language: string;

  // Native tag patterns (framework-specific)
  nativePatterns: {
    [tagType: string]: TagPattern[];
  };

  // Convention-based detection
  conventions: {
    directoryMapping: Record<string, { type: string; layer: string }>;
    fileNamePatterns: Record<string, { type: string; layer: string }>;
    classNamePatterns: Record<string, { type: string; layer: string }>;
  };

  // Translation rules to SCG
  translationRules: {
    [nativeType: string]: {
      scgType: SCGTag['type'];
      scgLayer: SCGTag['layer'];
      metadata?: Record<string, any>;
    };
  };

  // Auto-tagging suggestions
  autoTagging: {
    enabled: boolean;
    confidence: 'low' | 'medium' | 'high';
    patterns: TagPattern[];
  };
}

export interface TagDetectionResult {
  tags: SCGTag[];
  suggestions: TagSuggestion[];
  confidence: number;
  framework: string;
  language: string;
}

export interface TagSuggestion {
  type: 'missing' | 'incorrect' | 'enhancement';
  message: string;
  suggestedTag: Partial<SCGTag>;
  confidence: number;
  autoApplicable: boolean;
}

export interface TagTranslationResult {
  originalTags: NativeTag[];
  translatedTags: SCGTag[];
  untranslatable: NativeTag[];
  suggestions: TagSuggestion[];
}

/**
 * Main interface for the Universal Tag System
 */
export interface IUniversalTagSystem {
  // Framework detection
  detectFramework(code: string, filePath: string): Promise<string>;

  // Tag extraction
  extractNativeTags(code: string, framework: string): Promise<NativeTag[]>;
  extractSCGTags(code: string, framework: string): Promise<SCGTag[]>;

  // Tag translation
  translateToSCG(
    nativeTags: NativeTag[],
    framework: string
  ): Promise<TagTranslationResult>;
  translateFromSCG(
    scgTags: SCGTag[],
    targetFramework: string
  ): Promise<NativeTag[]>;

  // Auto-tagging
  suggestTags(code: string, filePath: string): Promise<TagSuggestion[]>;
  autoTag(
    code: string,
    filePath: string,
    suggestions: TagSuggestion[]
  ): Promise<string>;

  // Tag injection
  injectSCGTags(code: string, tags: SCGTag[]): Promise<string>;
  removeTags(code: string, tagTypes?: string[]): Promise<string>;

  // Validation
  validateTags(tags: SCGTag[]): Promise<TagValidationResult>;

  // Framework management
  registerFramework(config: FrameworkTagConfig): void;
  getFrameworkConfig(framework: string): FrameworkTagConfig | null;
  listSupportedFrameworks(): string[];
}

export interface TagValidationResult {
  valid: boolean;
  errors: TagValidationError[];
  warnings: TagValidationWarning[];
}

export interface TagValidationError {
  tag: SCGTag;
  message: string;
  severity: 'error' | 'warning';
  fixSuggestion?: string;
}

export interface TagValidationWarning {
  tag: SCGTag;
  message: string;
  suggestion?: string;
}
