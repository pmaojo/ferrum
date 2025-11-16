/**
 * Unit tests for Pattern Matching Utilities
 *
 * These tests verify the accuracy and performance of pattern matching
 * for file paths, code patterns, and directory structures.
 */

import { PatternMatchingUtils } from '../PatternMatchingUtils';

describe('PatternMatchingUtils', () => {
  beforeEach(() => {
    // Clear cache before each test to ensure clean state
    PatternMatchingUtils.clearCache();
  });

  describe('matchesPattern (File Path Matching)', () => {
    describe('Basic glob patterns', () => {
      test('should match exact file names', () => {
        const result = PatternMatchingUtils.matchesPattern(
          'test.js',
          'test.js'
        );
        expect(result.matches).toBe(true);
        expect(result.matchedText).toBe('test.js');
      });

      test('should not match different file names', () => {
        const result = PatternMatchingUtils.matchesPattern(
          'test.js',
          'other.js'
        );
        expect(result.matches).toBe(false);
      });

      test('should match single wildcard patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern('test.js', '*.js').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('app.ts', '*.ts').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('component.tsx', '*.tsx').matches
        ).toBe(true);
      });

      test('should match question mark patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern('test1.js', 'test?.js').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('test2.js', 'test?.js').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('test10.js', 'test?.js').matches
        ).toBe(false);
      });
    });

    describe('Directory path patterns', () => {
      test('should match double wildcard patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'src/components/Button.tsx',
            '**/*.tsx'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern(
            'deep/nested/path/file.js',
            '**/*.js'
          ).matches
        ).toBe(true);
      });

      test('should match specific directory patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'src/components/Button.tsx',
            'src/components/*.tsx'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern(
            'src/utils/helper.ts',
            'src/utils/*.ts'
          ).matches
        ).toBe(true);
      });

      test('should handle mixed wildcard patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'backend/internal/modules/user.go',
            'backend/**/*.go'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern(
            'frontend/src/pages/Home.tsx',
            '**/src/**/*.tsx'
          ).matches
        ).toBe(true);
      });
    });

    describe('Framework-specific patterns', () => {
      test('should match Kthulu patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'backend/internal/modules/user/usecase.go',
            'backend/**/*.go'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('go.mod', 'go.mod').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('project/go.mod', '**/go.mod')
            .matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('.kthulu.yml', '.kthulu.yml')
            .matches
        ).toBe(true);
      });

      test('should match Laravel patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'app/Http/Controllers/UserController.php',
            'app/**/*.php'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('composer.json', 'composer.json')
            .matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern(
            'project/composer.json',
            '**/composer.json'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('artisan', 'artisan').matches
        ).toBe(true);
      });

      test('should match Spring Boot patterns', () => {
        expect(
          PatternMatchingUtils.matchesPattern(
            'src/main/java/com/example/Controller.java',
            '**/*.java'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('pom.xml', 'pom.xml').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('project/pom.xml', '**/pom.xml')
            .matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('build.gradle', 'build.gradle')
            .matches
        ).toBe(true);
      });
    });

    describe('Case sensitivity', () => {
      test('should be case insensitive by default', () => {
        expect(
          PatternMatchingUtils.matchesPattern('Test.JS', '*.js').matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('COMPONENT.TSX', '*.tsx').matches
        ).toBe(true);
      });

      test('should respect case sensitive option', () => {
        expect(
          PatternMatchingUtils.matchesPattern('Test.JS', '*.js', {
            caseSensitive: true,
          }).matches
        ).toBe(false);
        expect(
          PatternMatchingUtils.matchesPattern('test.js', '*.js', {
            caseSensitive: true,
          }).matches
        ).toBe(true);
      });
    });

    describe('Edge cases', () => {
      test('should handle empty strings', () => {
        expect(PatternMatchingUtils.matchesPattern('', '').matches).toBe(true);
        expect(PatternMatchingUtils.matchesPattern('test.js', '').matches).toBe(
          false
        );
        expect(PatternMatchingUtils.matchesPattern('', '*.js').matches).toBe(
          false
        );
      });

      test('should handle special characters', () => {
        expect(
          PatternMatchingUtils.matchesPattern('test-file.js', 'test-*.js')
            .matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('test_file.js', 'test_*.js')
            .matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesPattern('test.file.js', 'test.*.js')
            .matches
        ).toBe(true);
      });

      test('should handle invalid patterns gracefully', () => {
        // This should not throw an error
        const result = PatternMatchingUtils.matchesPattern(
          'test.js',
          '[invalid'
        );
        expect(result.matches).toBe(false);
      });
    });
  });

  describe('matchesRegex (Code Pattern Matching)', () => {
    const sampleGoCode = `
package main

import "fmt"

// @kthulu:module user
type UserModule struct {}

// @kthulu:usecase CreateUser
func (m *UserModule) CreateUser() error {
    return nil
}

type UserEntity struct {
    ID   int
    Name string
}
`;

    const sampleJavaCode = `
package com.example.demo;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @GetMapping
    public List<User> getUsers() {
        return userService.findAll();
    }
    
    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}
`;

    describe('Basic regex matching', () => {
      test('should match simple patterns', () => {
        const result = PatternMatchingUtils.matchesRegex(
          'hello world',
          'hello'
        );
        expect(result.matches).toBe(true);
        expect(result.matchedText).toBe('hello');
      });

      test('should match with groups', () => {
        const result = PatternMatchingUtils.matchesRegex(
          'version 1.2.3',
          'version (\\d+\\.\\d+\\.\\d+)'
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['1.2.3']);
      });

      test('should count multiple matches', () => {
        const result = PatternMatchingUtils.matchesRegex(
          'test test test',
          'test',
          { global: true }
        );
        expect(result.matches).toBe(true);
        expect(result.matchCount).toBe(3);
      });
    });

    describe('Framework-specific patterns', () => {
      test('should match Kthulu annotations', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleGoCode,
          '@kthulu:(\\w+)\\s+(\\w+)'
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['module', 'user']);
      });

      test('should match Go package declarations', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleGoCode,
          'package\\s+(\\w+)'
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['main']);
      });

      test('should match Spring Boot annotations', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleJavaCode,
          '@(RestController|Controller)'
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['RestController']);
      });

      test('should match Java method annotations', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleJavaCode,
          '@(GetMapping|PostMapping|PutMapping|DeleteMapping)'
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['GetMapping']);
      });
    });

    describe('Multiline patterns', () => {
      test('should match across multiple lines', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleGoCode,
          'type\\s+(\\w+)\\s+struct\\s*\\{[^}]*\\}',
          { multiline: true, dotAll: true }
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['UserModule']);
      });

      test('should match function definitions', () => {
        const result = PatternMatchingUtils.matchesRegex(
          sampleGoCode,
          'func\\s+\\([^)]*\\)\\s+(\\w+)\\([^)]*\\)',
          { multiline: true }
        );
        expect(result.matches).toBe(true);
        expect(result.matchGroups).toEqual(['CreateUser']);
      });
    });

    describe('Error handling', () => {
      test('should handle invalid regex patterns', () => {
        const result = PatternMatchingUtils.matchesRegex('test', '[invalid');
        expect(result.matches).toBe(false);
      });

      test('should handle empty input', () => {
        const result = PatternMatchingUtils.matchesRegex('', 'test');
        expect(result.matches).toBe(false);
      });
    });

    describe('Timeout handling', () => {
      test('should timeout for catastrophic patterns', () => {
        const longString = 'a'.repeat(30000);
        const result = PatternMatchingUtils.matchesRegex(longString, '(a+)+b', {
          timeout: 50,
        });
        expect(result.matches).toBe(false);
      });
    });
  });

  describe('matchesDirectoryStructure', () => {
    const sampleDirectories = [
      'src',
      'src/components',
      'src/components/ui',
      'src/utils',
      'src/hooks',
      'backend',
      'backend/internal',
      'backend/internal/modules',
      'backend/internal/modules/user',
      'backend/internal/handlers',
      'app',
      'app/Http',
      'app/Http/Controllers',
      'app/Models',
      'node_modules',
      '.git',
      'vendor',
    ];

    describe('Basic directory matching', () => {
      test('should match exact directory names', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          'src'
        );
        expect(result.matches).toBe(true);
        expect(result.matchedText).toBe('src');
      });

      test('should match wildcard patterns', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          'src/*'
        );
        expect(result.matches).toBe(true);
        expect(result.matchCount).toBeGreaterThan(1);
      });

      test('should match deep path patterns', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          '**/modules/**'
        );
        expect(result.matches).toBe(true);
      });

      test('should match patterns with trailing slashes', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          'src/'
        );
        expect(result.matches).toBe(true);
      });

      test('should respect recursive option', () => {
        const dirs = ['src', 'src/components'];
        const nonRecursive = PatternMatchingUtils.matchesDirectoryStructure(
          dirs,
          'src/components',
          { recursive: false }
        );
        expect(nonRecursive.matches).toBe(false);
        const recursive = PatternMatchingUtils.matchesDirectoryStructure(
          dirs,
          'src/components',
          { recursive: true }
        );
        expect(recursive.matches).toBe(true);
      });
    });

    describe('Framework-specific directory patterns', () => {
      test('should match Kthulu directory structure', () => {
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            'backend/internal/**'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            '**/modules/**'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            '**/handlers'
          ).matches
        ).toBe(true);
      });

      test('should match Laravel directory structure', () => {
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            'app/Http/**'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            'app/Models'
          ).matches
        ).toBe(true);
      });

      test('should match React directory structure', () => {
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            'src/components/**'
          ).matches
        ).toBe(true);
        expect(
          PatternMatchingUtils.matchesDirectoryStructure(
            sampleDirectories,
            'src/hooks'
          ).matches
        ).toBe(true);
      });
    });

    describe('Directory filtering options', () => {
      test('should exclude hidden directories by default', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          '.git'
        );
        expect(result.matches).toBe(false);
      });

      test('should include hidden directories when specified', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          '.git',
          { includeHidden: true }
        );
        expect(result.matches).toBe(true);
      });

      test('should respect exclude patterns', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          '*',
          { excludePatterns: ['node_modules', 'vendor'] }
        );
        expect(result.matches).toBe(true);
        expect(result.matchedText).not.toBe('node_modules');
        expect(result.matchedText).not.toBe('vendor');
      });

      test('should respect max depth', () => {
        const result = PatternMatchingUtils.matchesDirectoryStructure(
          sampleDirectories,
          '**',
          { maxDepth: 1 }
        );
        expect(result.matches).toBe(true);
        // Should not match deeply nested directories
        expect(result.matchedText).not.toContain('backend/internal/modules');
      });
    });
  });

  describe('findAllMatches', () => {
    const sampleCode = `
// @kthulu:module user
type UserModule struct {}

// @kthulu:usecase CreateUser  
func CreateUser() {}

// @kthulu:usecase UpdateUser
func UpdateUser() {}
`;

    test('should find all pattern matches', () => {
      const matches = PatternMatchingUtils.findAllMatches(
        sampleCode,
        '@kthulu:(\\w+)\\s+(\\w+)'
      );
      expect(matches).toHaveLength(3);
      expect(matches[0].groups).toEqual(['module', 'user']);
      expect(matches[1].groups).toEqual(['usecase', 'CreateUser']);
      expect(matches[2].groups).toEqual(['usecase', 'UpdateUser']);
    });

    test('should provide line and column information', () => {
      const matches = PatternMatchingUtils.findAllMatches(
        sampleCode,
        '@kthulu:module'
      );
      expect(matches).toHaveLength(1);
      expect(matches[0].line).toBe(2);
      expect(matches[0].column).toBeGreaterThan(0);
    });

    test('should respect max matches limit', () => {
      const matches = PatternMatchingUtils.findAllMatches(
        sampleCode,
        '@kthulu:\\w+',
        { maxMatches: 2 }
      );
      expect(matches).toHaveLength(2);
    });

    test('should handle no matches', () => {
      const matches = PatternMatchingUtils.findAllMatches(
        sampleCode,
        '@nonexistent'
      );
      expect(matches).toHaveLength(0);
    });
  });

  describe('validatePattern', () => {
    test('should validate correct regex patterns', () => {
      expect(PatternMatchingUtils.validatePattern('\\d+', 'regex').valid).toBe(
        true
      );
      expect(
        PatternMatchingUtils.validatePattern('[a-zA-Z]+', 'regex').valid
      ).toBe(true);
      expect(
        PatternMatchingUtils.validatePattern('test.*', 'regex').valid
      ).toBe(true);
    });

    test('should validate correct glob patterns', () => {
      expect(PatternMatchingUtils.validatePattern('*.js', 'glob').valid).toBe(
        true
      );
      expect(
        PatternMatchingUtils.validatePattern('**/*.ts', 'glob').valid
      ).toBe(true);
      expect(
        PatternMatchingUtils.validatePattern('src/components/*.tsx', 'glob')
          .valid
      ).toBe(true);
    });

    test('should reject invalid regex patterns', () => {
      const result = PatternMatchingUtils.validatePattern('[invalid', 'regex');
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
    });

    test('should reject invalid glob patterns', () => {
      // This would be caught during glob-to-regex conversion
      const result = PatternMatchingUtils.validatePattern('[invalid', 'glob');
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('escapeRegex', () => {
    test('should escape special regex characters', () => {
      expect(PatternMatchingUtils.escapeRegex('test.js')).toBe('test\\.js');
      expect(PatternMatchingUtils.escapeRegex('file*')).toBe('file\\*');
      expect(PatternMatchingUtils.escapeRegex('path?')).toBe('path\\?');
      expect(PatternMatchingUtils.escapeRegex('(group)')).toBe('\\(group\\)');
      expect(PatternMatchingUtils.escapeRegex('[class]')).toBe('\\[class\\]');
    });

    test('should handle empty strings', () => {
      expect(PatternMatchingUtils.escapeRegex('')).toBe('');
    });

    test('should handle strings without special characters', () => {
      expect(PatternMatchingUtils.escapeRegex('normaltext')).toBe('normaltext');
    });
  });

  describe('Performance and Caching', () => {
    test('should cache compiled patterns', () => {
      // First call
      const start1 = Date.now();
      PatternMatchingUtils.matchesPattern('test.js', '*.js');
      const time1 = Date.now() - start1;

      // Second call (should be faster due to caching)
      const start2 = Date.now();
      PatternMatchingUtils.matchesPattern('other.js', '*.js');
      const time2 = Date.now() - start2;

      // Cache hit should be faster (though this might be flaky in fast environments)
      expect(time2).toBeLessThanOrEqual(time1 + 5); // Allow some margin
    });

    test('should cache regex patterns', () => {
      const start1 = Date.now();
      PatternMatchingUtils.matchesRegex('test test', 'test');
      const time1 = Date.now() - start1;

      const start2 = Date.now();
      PatternMatchingUtils.matchesRegex('another test', 'test');
      const time2 = Date.now() - start2;

      expect(time2).toBeLessThanOrEqual(time1 + 5);
    });

    test('should provide cache statistics', () => {
      PatternMatchingUtils.clearCache();
      const initialStats = PatternMatchingUtils.getCacheStats();
      expect(initialStats.size).toBe(0);

      // Add some patterns to cache
      PatternMatchingUtils.matchesPattern('test.js', '*.js');
      PatternMatchingUtils.matchesRegex('code', 'test');

      const afterStats = PatternMatchingUtils.getCacheStats();
      expect(afterStats.size).toBeGreaterThan(0);
      expect(afterStats.limit).toBeGreaterThan(0);
    });

    test('should clear cache properly', () => {
      PatternMatchingUtils.matchesPattern('test.js', '*.js');
      expect(PatternMatchingUtils.getCacheStats().size).toBeGreaterThan(0);

      PatternMatchingUtils.clearCache();
      expect(PatternMatchingUtils.getCacheStats().size).toBe(0);
    });
  });

  describe('Execution time tracking', () => {
    test('should track execution time for pattern matching', () => {
      const result = PatternMatchingUtils.matchesPattern('test.js', '*.js');
      expect(result.executionTime).toBeDefined();
      expect(result.executionTime).toBeGreaterThanOrEqual(0);
    });

    test('should track execution time for regex matching', () => {
      const result = PatternMatchingUtils.matchesRegex('test code', 'test');
      expect(result.executionTime).toBeDefined();
      expect(result.executionTime).toBeGreaterThanOrEqual(0);
    });

    test('should track execution time for directory matching', () => {
      const result = PatternMatchingUtils.matchesDirectoryStructure(
        ['src', 'app'],
        'src'
      );
      expect(result.executionTime).toBeDefined();
      expect(result.executionTime).toBeGreaterThanOrEqual(0);
    });
  });
});
