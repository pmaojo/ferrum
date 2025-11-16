/**
 * Unit tests for FrameworkDetector
 *
 * These tests verify the accuracy of framework detection using template-based
 * configuration and weighted scoring systems.
 */

import type { Template } from '../../../types/universal-tag-system';
import { FrameworkDetector } from '../FrameworkDetector';

class MockTemplateService {
  listTemplates = jest.fn();
}

describe('FrameworkDetector', () => {
  let detector: FrameworkDetector;
  let mockTemplateService: any;

  // Sample templates for testing
  const kthuluTemplate: Template = {
    id: 'kthulu-hexagonal',
    name: 'Kthulu Hexagonal Architecture',
    description: 'Kthulu Go framework template',
    version: '1.0.0',
    metadata: {
      framework: 'kthulu',
      language: 'go',
      architecture: 'hexagonal',
      versionRegex: 'go\\s+(\\d+\\.\\d+)',
    },
    universalTagSystem: {
      detection: {
        filePatterns: [
          { pattern: '**/*.go', weight: 1 },
          { pattern: '**/go.mod', weight: 3 },
          { pattern: '**/.kthulu.yml', weight: 5 },
        ],
        codePatterns: [
          { regex: 'package main', weight: 2 },
          { regex: '// @kthulu:', weight: 4 },
          { regex: 'import.*kthulu', weight: 3 },
        ],
        directoryPatterns: [
          { pattern: '**/backend/internal/**', weight: 2 },
          { pattern: '**/cmd/kthulu-cli/**', weight: 3 },
        ],
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

  const laravelTemplate: Template = {
    id: 'laravel-mvc',
    name: 'Laravel MVC Architecture',
    description: 'Laravel PHP framework template',
    version: '1.0.0',
    metadata: {
      framework: 'laravel',
      language: 'php',
      architecture: 'mvc',
      versionRegex: '"laravel/framework"\\s*:\\s*"[^\\"]*(\\d+\\.\\d+)',
    },
    universalTagSystem: {
      detection: {
        filePatterns: [
          { pattern: '**/composer.json', weight: 5 },
          { pattern: '**/artisan', weight: 4 },
          { pattern: '**/*.php', weight: 1 },
        ],
        codePatterns: [
          { regex: 'use Illuminate\\\\', weight: 4 },
          { regex: 'extends Controller', weight: 3 },
          { regex: '@scg:', weight: 2 },
        ],
        directoryPatterns: [
          { pattern: '**/app/Http/Controllers/**', weight: 3 },
          { pattern: '**/app/Models/**', weight: 2 },
        ],
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
        confidence: 'medium',
        patterns: [],
      },
    },
  };

  const springBootTemplate: Template = {
    id: 'spring-boot-layered',
    name: 'Spring Boot Layered Architecture',
    description: 'Spring Boot Java framework template',
    version: '1.0.0',
    metadata: {
      framework: 'spring-boot',
      language: 'java',
      architecture: 'layered',
      versionRegex: '<version>(\\d+\\.\\d+\\.\\d+)</version>',
    },
    universalTagSystem: {
      detection: {
        filePatterns: [
          { pattern: '**/pom.xml', weight: 4 },
          { pattern: '**/build.gradle', weight: 4 },
          { pattern: '**/*.java', weight: 1 },
        ],
        codePatterns: [
          { regex: '@SpringBootApplication', weight: 5 },
          { regex: '@RestController|@Controller', weight: 3 },
          { regex: '@Service|@Repository', weight: 2 },
        ],
        directoryPatterns: [{ pattern: '**/src/main/java/**', weight: 3 }],
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

  beforeEach(() => {
    mockTemplateService = new MockTemplateService();
    detector = new FrameworkDetector(mockTemplateService);
  });

  afterEach(() => {
    jest.clearAllMocks();
    detector.clearCache();
  });

  describe('detectFramework', () => {
    describe('Kthulu framework detection', () => {
      const kthuluGoCode = `
package main

import (
    "fmt"
    "github.com/kthulu/core"
)

// @kthulu:module user
type UserModule struct {}

// @kthulu:usecase CreateUser
func (m *UserModule) CreateUser() error {
    return nil
}

func main() {
    fmt.Println("Kthulu application")
}
`;

      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should detect Kthulu framework from Go code with annotations', async () => {
        const result = await detector.detectFramework(
          kthuluGoCode,
          'backend/internal/modules/user.go'
        );

        expect(result.framework).toBe('kthulu');
        expect(result.templateId).toBe('kthulu-hexagonal');
        expect(result.confidence).toBeGreaterThan(0.5);
        expect(result.detectedPatterns).toContain('file:**/*.go');
        expect(result.detectedPatterns).toContain('code:// @kthulu:');
        expect(result.detectedPatterns).toContain('code:package main');
      });

      test('should detect Kthulu framework from go.mod file', async () => {
        const goModContent = `
module github.com/example/kthulu-app

go 1.19

require (
    github.com/kthulu/core v1.0.0
    github.com/gin-gonic/gin v1.8.1
)
`;

        const result = await detector.detectFramework(goModContent, 'go.mod');

        expect(result.framework).toBe('kthulu');
        expect(result.confidence).toBeGreaterThan(0.3);
        expect(result.detectedPatterns).toContain('file:**/go.mod');
        expect(result.detectedPatterns).toContain('code:import.*kthulu');
      });

      test('should have high confidence with multiple matching patterns', async () => {
        const result = await detector.detectFramework(
          kthuluGoCode,
          'backend/internal/modules/user.go'
        );

        expect(result.confidence).toBeGreaterThan(0.7);
        expect(result.detectedPatterns.length).toBeGreaterThan(2);
      });
    });

    describe('Laravel framework detection', () => {
      const laravelPhpCode = `
<?php

namespace App\\Http\\Controllers;

use Illuminate\\Http\\Request;
use Illuminate\\Http\\Response;
use App\\Models\\User;

/**
 * @scg:controller UserController
 */
class UserController extends Controller
{
    public function index()
    {
        return User::all();
    }

    public function store(Request $request)
    {
        return User::create($request->all());
    }
}
`;

      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should detect Laravel framework from PHP controller', async () => {
        const result = await detector.detectFramework(
          laravelPhpCode,
          'app/Http/Controllers/UserController.php'
        );

        expect(result.framework).toBe('laravel');
        expect(result.templateId).toBe('laravel-mvc');
        expect(result.confidence).toBeGreaterThan(0.5);
        expect(result.detectedPatterns).toContain('file:**/*.php');
        expect(result.detectedPatterns).toContain('code:use Illuminate\\\\');
        expect(result.detectedPatterns).toContain('code:extends Controller');
      });

      test('should detect Laravel from composer.json', async () => {
        const composerJson = `
{
    "name": "laravel/laravel",
    "type": "project",
    "description": "The Laravel Framework.",
    "require": {
        "php": "^8.0.2",
        "laravel/framework": "^9.19"
    }
}
`;

        const result = await detector.detectFramework(
          composerJson,
          'composer.json'
        );

        expect(result.framework).toBe('laravel');
        expect(result.confidence).toBeGreaterThan(0.4);
        expect(result.detectedPatterns).toContain('file:**/composer.json');
        expect(result.metadata.version).toBe('9.19');
      });
    });

    describe('Spring Boot framework detection', () => {
      const springBootJavaCode = `
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @Autowired
    private UserService userService;
    
    @GetMapping
    public List<User> getUsers() {
        return userService.findAll();
    }
}

@Service
public class UserService {
    // Service implementation
}
`;

      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should detect Spring Boot framework from Java code', async () => {
        const result = await detector.detectFramework(
          springBootJavaCode,
          'src/main/java/com/example/demo/DemoApplication.java'
        );

        expect(result.framework).toBe('spring-boot');
        expect(result.templateId).toBe('spring-boot-layered');
        expect(result.confidence).toBeGreaterThan(0.6);
        expect(result.detectedPatterns).toContain('file:**/*.java');
        expect(result.detectedPatterns).toContain(
          'code:@SpringBootApplication'
        );
        expect(result.detectedPatterns).toContain(
          'code:@RestController|@Controller'
        );
        expect(result.detectedPatterns).toContain('code:@Service|@Repository');
      });

      test('should detect Spring Boot from pom.xml', async () => {
        const pomXml = `
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>2.7.0</version>
    </parent>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
    </dependencies>
</project>
`;

        const result = await detector.detectFramework(pomXml, 'pom.xml');

        expect(result.framework).toBe('spring-boot');
        expect(result.confidence).toBeGreaterThan(0.3);
        expect(result.detectedPatterns).toContain('file:**/pom.xml');
        expect(result.metadata.version).toBe('2.7.0');
      });
    });

    describe('Unknown framework handling', () => {
      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should return unknown for unrecognized code', async () => {
        const unknownCode = `
console.log("Hello, world!");
const x = 42;
function test() {
    return "unknown";
}
`;

        const result = await detector.detectFramework(
          unknownCode,
          'unknown.js'
        );

        expect(result.framework).toBe('unknown');
        expect(result.templateId).toBe('unknown');
        expect(result.confidence).toBe(0);
        expect(result.detectedPatterns).toHaveLength(0);
      });

      test('should handle empty code', async () => {
        const result = await detector.detectFramework('', 'empty.txt');

        expect(result.framework).toBe('unknown');
        expect(result.confidence).toBe(0);
      });
    });

    describe('Multiple framework scenarios', () => {
      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should choose framework with highest confidence', async () => {
        // Code that might match multiple frameworks but should clearly favor one
        const mixedCode = `
// This has some Go-like syntax
package main

// But also some Java-like annotations
@RestController
public class Test {
    // And some PHP-like syntax
    use SomeNamespace;
}
`;

        const result = await detector.detectFramework(mixedCode, 'mixed.go');

        // Should favor Kthulu due to package main and .go extension
        expect(result.framework).toBe('kthulu');
        expect(result.confidence).toBeGreaterThan(0);
      });
    });

    describe('Project structure analysis', () => {
      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);

        // Mock file system operations
        const fs = await import('fs');
        jest
          .spyOn(fs.promises, 'readdir')
          .mockImplementation((...args: any[]) => {
            const dirPath = args[0] as string;
            if (dirPath.includes('backend')) {
              return Promise.resolve([
                { name: 'internal', isDirectory: () => true },
                { name: 'cmd', isDirectory: () => true },
                { name: 'main.go', isDirectory: () => false },
              ]);
            }
            return Promise.resolve([]);
          });
      });

      test('should analyze project structure when projectPath is provided', async () => {
        const result = await detector.detectFramework(
          'package main',
          'backend/main.go',
          '/project/root'
        );

        expect(result.framework).toBe('kthulu');
        expect(result.detectedPatterns).toContain('dir:**/backend/internal/**');
      });
    });

    describe('Metadata extraction', () => {
      beforeEach(() => {
        mockTemplateService.listTemplates.mockResolvedValue([
          kthuluTemplate,
          laravelTemplate,
          springBootTemplate,
        ]);
      });

      test('should extract version information for Kthulu', async () => {
        const goModWithVersion = `
module example.com/app

go 1.19

require (
    github.com/kthulu/core v1.2.3
)
`;

        const result = await detector.detectFramework(
          goModWithVersion,
          'go.mod'
        );

        expect(result.metadata.version).toBe('1.19');
      });

      test('should extract version information for Laravel', async () => {
        const composerWithVersion = `
{
    "require": {
        "laravel/framework": "^9.19"
    }
}
`;

        const result = await detector.detectFramework(
          composerWithVersion,
          'composer.json'
        );

        expect(result.metadata.version).toBe('9.19');
      });

      test('should extract version information for Spring Boot', async () => {
        const pomWithVersion = `
<project>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>2.7.0</version>
    </parent>
</project>
`;

        const result = await detector.detectFramework(
          pomWithVersion,
          'pom.xml'
        );

        expect(result.metadata.version).toBe('2.7.0');
      });

      test('should extract dependencies', async () => {
        const composerWithDeps = `
{
    "require": {
        "laravel/framework": "^9.0",
        "guzzlehttp/guzzle": "^7.0"
    }
}
`;

        const result = await detector.detectFramework(
          composerWithDeps,
          'composer.json'
        );

        expect(result.metadata.dependencies).toContain('laravel/framework');
        expect(result.metadata.dependencies).toContain('guzzlehttp/guzzle');
      });
    });
  });

  describe('calculateConfidence', () => {
    beforeEach(() => {
      mockTemplateService.listTemplates.mockResolvedValue([kthuluTemplate]);
    });

    test('should calculate confidence based on weighted patterns', async () => {
      const context = {
        filePath: 'backend/internal/modules/user.go',
        fileContent: 'package main\n// @kthulu:module user',
        projectPath: '/project',
        allFiles: ['backend/internal/modules/user.go', 'go.mod'],
        directories: [
          'backend',
          'backend/internal',
          'backend/internal/modules',
        ],
      };

      const result = await detector.calculateConfidence(
        context,
        kthuluTemplate.universalTagSystem!.detection,
        'kthulu-hexagonal'
      );

      expect(result.confidence).toBeGreaterThan(0);
      expect(result.detectedPatterns.length).toBeGreaterThan(0);
    });

    test('should return zero confidence for non-matching patterns', async () => {
      const context = {
        filePath: 'test.txt',
        fileContent: 'plain text content',
        projectPath: '/project',
        directories: ['docs'],
      };

      const result = await detector.calculateConfidence(
        context,
        kthuluTemplate.universalTagSystem!.detection,
        'kthulu-hexagonal'
      );

      expect(result.confidence).toBe(0);
      expect(result.detectedPatterns).toHaveLength(0);
    });
  });

  describe('Pattern matching methods', () => {
    test('matchesPattern should work correctly', () => {
      expect(detector.matchesPattern('test.go', '**/*.go')).toBe(true);
      expect(detector.matchesPattern('test.js', '**/*.go')).toBe(false);
    });

    test('matchesRegex should work correctly', () => {
      expect(detector.matchesRegex('package main', 'package\\s+main')).toBe(
        true
      );
      expect(detector.matchesRegex('import test', 'package\\s+main')).toBe(
        false
      );
    });

    test('matchesDirectoryStructure should work correctly', () => {
      const dirs = ['src', 'src/components', 'backend/internal'];
      expect(detector.matchesDirectoryStructure(dirs, 'src/**')).toBe(true);
      expect(detector.matchesDirectoryStructure(dirs, 'nonexistent/**')).toBe(
        false
      );
    });
  });

  describe('Error handling', () => {
    test('should handle template service errors gracefully', async () => {
      mockTemplateService.listTemplates.mockRejectedValue(
        new Error('Template service error')
      );

      const result = await detector.detectFramework('test code', 'test.js');

      expect(result.framework).toBe('unknown');
      expect(result.confidence).toBe(0);
    });

    test('should handle invalid template configurations', async () => {
      const invalidTemplate = {
        ...kthuluTemplate,
        universalTagSystem: undefined,
      };

      mockTemplateService.listTemplates.mockResolvedValue([invalidTemplate]);

      const result = await detector.detectFramework('package main', 'test.go');

      expect(result.framework).toBe('unknown');
      expect(result.confidence).toBe(0);
    });
  });

  describe('Performance and caching', () => {
    beforeEach(() => {
      mockTemplateService.listTemplates.mockResolvedValue([kthuluTemplate]);
    });

    test('should cache pattern compilation for better performance', async () => {
      const code = 'package main';
      const filePath = 'test.go';

      // First call
      const start1 = Date.now();
      await detector.detectFramework(code, filePath);
      const time1 = Date.now() - start1;

      // Second call (should benefit from caching)
      const start2 = Date.now();
      await detector.detectFramework(code, filePath);
      const time2 = Date.now() - start2;

      // Second call should be faster or at least not significantly slower
      expect(time2).toBeLessThanOrEqual(time1 + 10); // Allow some margin for test flakiness
    });

    test('should clear cache when requested', () => {
      // This should not throw an error
      expect(() => detector.clearCache()).not.toThrow();
    });
  });
});
