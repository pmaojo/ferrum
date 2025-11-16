/**
 * Type validation tests for Universal Tag System
 *
 * These tests ensure that all the core interfaces and types are properly defined
 * and can be used correctly by the Universal Tag System implementation.
 */

import {
  isValidSCGTag,
  isValidNativeTag,
  isValidFrameworkDetectionResult,
  isValidTagSuggestion,
  SCG_TAG_TYPES,
  SCG_LAYERS,
  SUPPORTED_FRAMEWORKS,
  type SCGTag,
  type NativeTag,
  type UniversalTagSystemConfig,
  type FrameworkDetectionResult,
  type TagSuggestion,
  type TagPattern,
  type IUniversalTagSystem,
  type Template,
} from '../index';

describe('Universal Tag System Types', () => {
  describe('SCGTag Interface', () => {
    it('should accept valid SCGTag objects', () => {
      const validSCGTag: SCGTag = {
        type: 'module',
        layer: 'domain',
        domain: 'user-management',
        framework: 'kthulu',
        language: 'go',
        filePath: '/src/modules/user.go',
        dependencies: ['user-repository'],
        implements: ['user-port'],
        uses: ['user-entity'],
        metadata: {
          isPublic: true,
          complexity: 'medium',
        },
        originalTags: [],
      };

      expect(isValidSCGTag(validSCGTag)).toBe(true);
      expect(validSCGTag.type).toBe('module');
      expect(validSCGTag.layer).toBe('domain');
    });

    it('should reject invalid SCGTag objects', () => {
      const invalidSCGTag = {
        type: 'invalid-type', // Invalid type
        layer: 'domain',
        domain: 'test',
        // Missing required fields
      };

      expect(isValidSCGTag(invalidSCGTag)).toBe(false);
    });
  });

  describe('NativeTag Interface', () => {
    it('should accept valid NativeTag objects', () => {
      const validNativeTag: NativeTag = {
        type: '@kthulu:module',
        value: 'user-management',
        framework: 'kthulu',
        filePath: '/src/modules/user.go',
        lineNumber: 5,
        context: {
          className: 'UserModule',
          packageName: 'modules',
        },
        rawMatch: '// @kthulu:module user-management',
        extractedData: {
          moduleName: 'user-management',
        },
        confidence: 0.95,
        isValidated: true,
      };

      expect(isValidNativeTag(validNativeTag)).toBe(true);
      expect(validNativeTag.framework).toBe('kthulu');
      expect(validNativeTag.confidence).toBe(0.95);
    });
  });

  describe('FrameworkDetectionResult Interface', () => {
    it('should accept valid detection results', () => {
      const validResult: FrameworkDetectionResult = {
        templateId: 'kthulu-hexagonal',
        framework: 'kthulu',
        confidence: 0.9,
        detectedPatterns: ['go-files', 'kthulu-annotations'],
        metadata: {
          version: '1.0.0',
          variant: 'hexagonal',
        },
      };

      expect(isValidFrameworkDetectionResult(validResult)).toBe(true);
      expect(validResult.confidence).toBeGreaterThan(0.8);
    });
  });

  describe('TagSuggestion Interface', () => {
    it('should accept valid tag suggestions', () => {
      const validSuggestion: TagSuggestion = {
        suggestedTag: {
          type: 'usecase',
          layer: 'application',
          domain: 'user-management',
        },
        confidence: 0.85,
        reason: 'Detected UseCase suffix in class name',
        filePath: '/src/usecases/CreateUserUseCase.go',
        lineNumber: 10,
        codeContext: 'type CreateUserUseCase struct {}',
        canAutoApply: true,
        template: '// @kthulu:usecase {name}',
        source: 'pattern',
        alternatives: [],
      };

      expect(isValidTagSuggestion(validSuggestion)).toBe(true);
      expect(validSuggestion.canAutoApply).toBe(true);
    });
  });

  describe('UniversalTagSystemConfig Interface', () => {
    it('should accept valid configuration objects', () => {
      const validConfig: UniversalTagSystemConfig = {
        detection: {
          filePatterns: [{ pattern: '**/*.go', weight: 1 }],
          codePatterns: [{ regex: '@kthulu:', weight: 3 }],
          directoryPatterns: [{ pattern: '**/modules/**', weight: 2 }],
        },
        extraction: {
          nativePatterns: {
            module: [
              {
                regex: '// @kthulu:module\\s+(\\w+)',
                extractors: {
                  type: 'module',
                  layer: 'domain',
                },
              },
            ],
          },
          conventions: {
            directoryMapping: {
              'modules/': { type: 'module', layer: 'domain' },
            },
            fileNamePatterns: {
              '*Module.go': { type: 'module', layer: 'domain' },
            },
            classNamePatterns: {
              '*Module': { type: 'module', layer: 'domain' },
            },
          },
        },
        translation: {
          toSCG: {
            module: { scgType: 'module', scgLayer: 'domain' },
          },
          fromSCG: {
            module: '// @kthulu:module {name}',
          },
        },
        autoTagging: {
          enabled: true,
          confidence: 'high',
          patterns: [
            {
              regex: 'type\\s+(\\w+)Module\\s+struct',
              suggestedTag: {
                type: 'module',
                layer: 'domain',
                template: '// @kthulu:module $1',
              },
            },
          ],
        },
      };

      expect(validConfig.detection).toBeDefined();
      expect(validConfig.extraction).toBeDefined();
      expect(validConfig.translation).toBeDefined();
      expect(validConfig.autoTagging).toBeDefined();
    });
  });

  describe('TagPattern Interface', () => {
    it('should accept valid tag patterns', () => {
      const validPattern: TagPattern = {
        id: 'kthulu-module-pattern',
        name: 'Kthulu Module Pattern',
        description: 'Detects Kthulu module annotations',
        pattern: '// @kthulu:module\\s+(\\w+)',
        type: 'regex',
        weight: 3,
        context: {
          filePattern: '**/*.go',
          directoryPattern: '**/modules/**',
        },
        extractors: {
          moduleName: '$1',
          type: 'module',
        },
      };

      expect(validPattern.id).toBe('kthulu-module-pattern');
      expect(validPattern.type).toBe('regex');
      expect(validPattern.weight).toBe(3);
    });
  });

  describe('Constants and Enums', () => {
    it('should have correct SCG tag types', () => {
      expect(SCG_TAG_TYPES).toContain('module');
      expect(SCG_TAG_TYPES).toContain('usecase');
      expect(SCG_TAG_TYPES).toContain('entity');
      expect(SCG_TAG_TYPES).toContain('controller');
    });

    it('should have correct SCG layers', () => {
      expect(SCG_LAYERS).toContain('domain');
      expect(SCG_LAYERS).toContain('application');
      expect(SCG_LAYERS).toContain('infrastructure');
      expect(SCG_LAYERS).toContain('presentation');
    });

    it('should have supported frameworks', () => {
      expect(SUPPORTED_FRAMEWORKS).toContain('kthulu');
      expect(SUPPORTED_FRAMEWORKS).toContain('laravel');
      expect(SUPPORTED_FRAMEWORKS).toContain('spring-boot');
      expect(SUPPORTED_FRAMEWORKS).toContain('django');
    });
  });

  describe('Template Integration', () => {
    it('should extend Template interface with Universal Tag System config', () => {
      const templateWithUTS: Template = {
        id: 'kthulu-hexagonal',
        name: 'Kthulu Hexagonal Architecture',
        description: 'Template for Kthulu hexagonal architecture',
        version: '1.0.0',
        metadata: {
          framework: 'kthulu',
          language: 'go',
          architecture: 'hexagonal',
        },
        universalTagSystem: {
          detection: {
            filePatterns: [{ pattern: '**/*.go', weight: 1 }],
            codePatterns: [{ regex: '@kthulu:', weight: 3 }],
            directoryPatterns: [{ pattern: '**/modules/**', weight: 2 }],
          },
          extraction: {
            nativePatterns: {},
            conventions: {
              directoryMapping: {},
              fileNamePatterns: {},
              classNamePatterns: {},
            },
          },
          translation: {
            toSCG: {},
            fromSCG: {},
          },
          autoTagging: {
            enabled: true,
            confidence: 'high',
            patterns: [],
          },
        },
      };

      expect(templateWithUTS.universalTagSystem).toBeDefined();
      expect(templateWithUTS.universalTagSystem?.detection).toBeDefined();
    });
  });

  describe('Service Interface', () => {
    it('should define IUniversalTagSystem interface correctly', () => {
      // This is a compile-time test - if the interface is properly defined,
      // we should be able to create a mock implementation
      const mockService: Partial<IUniversalTagSystem> = {
        detectFramework: async (_code: string, _filePath: string) => ({
          templateId: 'test',
          framework: 'test',
          confidence: 0.8,
          detectedPatterns: [],
          metadata: {},
        }),
        extractSCGTags: async (_code: string, _templateId: string) => [],
        suggestTags: async (_code: string, _filePath: string) => [],
      };

      expect(mockService.detectFramework).toBeDefined();
      expect(mockService.extractSCGTags).toBeDefined();
      expect(mockService.suggestTags).toBeDefined();
    });
  });
});
