/**
 * Rule-Based Semantic Analysis Fallback
 * 
 * Implements deterministic intent classification, domain detection, and security assessment
 * as a fallback when LLM services are unavailable.
 */

export interface IntentClassification {
  intent: string;
  confidence: number;
  keywords: string[];
  patterns: string[];
  metadata: Record<string, any>;
}

export interface DomainDetection {
  domain: string;
  confidence: number;
  indicators: string[];
  framework: string | null;
  architecture: string | null;
}

export interface SecurityAssessment {
  level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  risks: string[];
  recommendations: string[];
  complianceIssues: string[];
}

export interface ProjectStructureAnalysis {
  rootPath: string;
  frameworks: FrameworkIndicator[];
  architecture: ArchitecturePattern[];
  dependencies: DependencyInfo[];
  securityPatterns: SecurityPattern[];
}

export interface FrameworkIndicator {
  framework: string;
  confidence: number;
  files: string[];
  patterns: string[];
}

export interface ArchitecturePattern {
  pattern: string;
  confidence: number;
  indicators: string[];
}

export interface DependencyInfo {
  name: string;
  type: 'direct' | 'transitive';
  securityRisk: 'low' | 'medium' | 'high';
  version?: string;
}

export interface SecurityPattern {
  pattern: string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  files: string[];
  description: string;
}

export class RuleBasedAnalyzer {
  private intentKeywords: Map<string, { keywords: string[]; patterns: RegExp[]; weight: number }> = new Map();
  private frameworkPatterns: Map<string, { files: string[]; directories: string[]; dependencies: string[] }> = new Map();
  private securityPatterns: Map<string, { pattern: RegExp; risk: 'low' | 'medium' | 'high' | 'critical'; description: string }> = new Map();
  private architecturePatterns: Map<string, { indicators: string[]; files: string[] }> = new Map();

  constructor() {
    this.initializeIntentKeywords();
    this.initializeFrameworkPatterns();
    this.initializeSecurityPatterns();
    this.initializeArchitecturePatterns();
  }

  private initializeIntentKeywords(): void {
    // Authentication and 2FA related intents
    this.intentKeywords.set('add-2fa', {
      keywords: ['2fa', 'two-factor', 'authentication', 'totp', 'otp', 'multi-factor', 'mfa'],
      patterns: [
        /add.*2fa/i,
        /implement.*two.?factor/i,
        /enable.*authentication/i,
        /setup.*totp/i
      ],
      weight: 1.0
    });

    this.intentKeywords.set('payment-integration', {
      keywords: ['payment', 'stripe', 'paypal', 'billing', 'checkout', 'transaction'],
      patterns: [
        /payment.*integration/i,
        /add.*payment/i,
        /stripe.*setup/i,
        /checkout.*flow/i
      ],
      weight: 0.9
    });

    this.intentKeywords.set('security-audit', {
      keywords: ['security', 'audit', 'vulnerability', 'compliance', 'owasp', 'pci'],
      patterns: [
        /security.*audit/i,
        /vulnerability.*scan/i,
        /compliance.*check/i,
        /owasp.*validation/i
      ],
      weight: 0.8
    });

    this.intentKeywords.set('code-generation', {
      keywords: ['generate', 'create', 'scaffold', 'template', 'boilerplate'],
      patterns: [
        /generate.*code/i,
        /create.*component/i,
        /scaffold.*project/i,
        /add.*template/i
      ],
      weight: 0.7
    });

    this.intentKeywords.set('refactoring', {
      keywords: ['refactor', 'restructure', 'optimize', 'improve', 'cleanup'],
      patterns: [
        /refactor.*code/i,
        /restructure.*project/i,
        /optimize.*performance/i,
        /cleanup.*codebase/i
      ],
      weight: 0.6
    });
  }

  private initializeFrameworkPatterns(): void {
    // Tuetano C++ Framework
    this.frameworkPatterns.set('tuetano', {
      files: ['CMakeLists.txt', 'tuetano.yaml', 'tuetano-plugin.yaml'],
      directories: ['src', 'include', 'tests', 'cmake'],
      dependencies: ['tuetano', 'cmake', 'conan']
    });

    // Kthulu Go Framework
    this.frameworkPatterns.set('kthulu', {
      files: ['go.mod', 'go.sum', 'kthulu.yaml', 'main.go'],
      directories: ['cmd', 'internal', 'pkg', 'api'],
      dependencies: ['kthulu', 'gin', 'gorm', 'cobra']
    });

    // Ferrum Rust Framework
    this.frameworkPatterns.set('ferrum', {
      files: ['Cargo.toml', 'Cargo.lock', 'ferrum.yaml'],
      directories: ['src', 'tests', 'benches', 'examples'],
      dependencies: ['ferrum', 'tokio', 'serde', 'clap']
    });

    // Laravel PHP
    this.frameworkPatterns.set('laravel', {
      files: ['composer.json', 'artisan', '.env.example', 'webpack.mix.js'],
      directories: ['app', 'config', 'database', 'resources', 'routes'],
      dependencies: ['laravel/framework', 'php']
    });

    // Spring Boot Java
    this.frameworkPatterns.set('spring-boot', {
      files: ['pom.xml', 'build.gradle', 'application.properties', 'application.yml'],
      directories: ['src/main/java', 'src/test/java', 'src/main/resources'],
      dependencies: ['spring-boot-starter', 'spring-framework']
    });

    // React/Next.js
    this.frameworkPatterns.set('react', {
      files: ['package.json', 'next.config.js', 'tsconfig.json'],
      directories: ['src', 'components', 'pages', 'public'],
      dependencies: ['react', 'next', 'typescript']
    });

    // NestJS
    this.frameworkPatterns.set('nestjs', {
      files: ['nest-cli.json', 'package.json', 'tsconfig.json'],
      directories: ['src', 'test', 'dist'],
      dependencies: ['@nestjs/core', '@nestjs/common']
    });
  }

  private initializeSecurityPatterns(): void {
    // High-risk patterns
    this.securityPatterns.set('hardcoded-secrets', {
      pattern: /(password|secret|key|token)\s*[:=]\s*["'][^"']{8,}["']/i,
      risk: 'critical',
      description: 'Hardcoded secrets detected in source code'
    });

    this.securityPatterns.set('sql-injection', {
      pattern: /(SELECT|INSERT|UPDATE|DELETE).*\+.*\$|query.*\+.*\$/i,
      risk: 'high',
      description: 'Potential SQL injection vulnerability'
    });

    this.securityPatterns.set('xss-vulnerability', {
      pattern: /innerHTML\s*=|document\.write\(|eval\(/i,
      risk: 'high',
      description: 'Potential XSS vulnerability'
    });

    this.securityPatterns.set('weak-crypto', {
      pattern: /md5|sha1|des|rc4/i,
      risk: 'medium',
      description: 'Weak cryptographic algorithm detected'
    });

    this.securityPatterns.set('insecure-random', {
      pattern: /Math\.random|rand\(\)|random\(\)/i,
      risk: 'medium',
      description: 'Insecure random number generation'
    });

    this.securityPatterns.set('debug-info', {
      pattern: /console\.log|print\(|debug|trace/i,
      risk: 'low',
      description: 'Debug information may leak sensitive data'
    });
  }

  private initializeArchitecturePatterns(): void {
    // Hexagonal Architecture
    this.architecturePatterns.set('hexagonal', {
      indicators: ['ports', 'adapters', 'domain', 'application', 'infrastructure'],
      files: ['domain/', 'application/', 'infrastructure/', 'ports/', 'adapters/']
    });

    // Clean Architecture
    this.architecturePatterns.set('clean', {
      indicators: ['entities', 'use-cases', 'interface-adapters', 'frameworks-drivers'],
      files: ['entities/', 'usecases/', 'interfaces/', 'frameworks/']
    });

    // Layered Architecture
    this.architecturePatterns.set('layered', {
      indicators: ['controller', 'service', 'repository', 'model'],
      files: ['controllers/', 'services/', 'repositories/', 'models/']
    });

    // Microservices
    this.architecturePatterns.set('microservices', {
      indicators: ['service', 'api-gateway', 'docker', 'kubernetes'],
      files: ['docker-compose.yml', 'Dockerfile', 'k8s/', 'services/']
    });

    // MVC Pattern
    this.architecturePatterns.set('mvc', {
      indicators: ['model', 'view', 'controller'],
      files: ['models/', 'views/', 'controllers/']
    });
  }

  /**
   * Classify user intent based on keywords and patterns
   */
  classifyIntent(text: string): IntentClassification {
    const normalizedText = text.toLowerCase();
    let bestMatch: IntentClassification = {
      intent: 'unknown',
      confidence: 0,
      keywords: [],
      patterns: [],
      metadata: {}
    };

    for (const [intent, config] of this.intentKeywords) {
      let score = 0;
      const matchedKeywords: string[] = [];
      const matchedPatterns: string[] = [];

      // Check keyword matches
      for (const keyword of config.keywords) {
        if (normalizedText.includes(keyword)) {
          score += config.weight * 0.3;
          matchedKeywords.push(keyword);
        }
      }

      // Check pattern matches
      for (const pattern of config.patterns) {
        if (pattern.test(text)) {
          score += config.weight * 0.7;
          matchedPatterns.push(pattern.source);
        }
      }

      if (score > bestMatch.confidence) {
        bestMatch = {
          intent,
          confidence: Math.min(score, 1.0),
          keywords: matchedKeywords,
          patterns: matchedPatterns,
          metadata: { weight: config.weight }
        };
      }
    }

    return bestMatch;
  }

  /**
   * Detect domain and framework from project structure
   */
  async detectDomain(projectPath: string, files: string[]): Promise<DomainDetection> {
    const frameworkScores = new Map<string, number>();
    const indicators: string[] = [];

    // Analyze file patterns
    for (const file of files) {
      const fileName = file.toLowerCase();
      
      for (const [framework, config] of this.frameworkPatterns) {
        let score = frameworkScores.get(framework) || 0;

        // Check for specific files
        for (const requiredFile of config.files) {
          if (fileName.includes(requiredFile.toLowerCase())) {
            score += 0.5;
            indicators.push(`File: ${requiredFile}`);
          }
        }

        // Check for directory patterns
        for (const dir of config.directories) {
          if (fileName.includes(dir.toLowerCase() + '/')) {
            score += 0.3;
            indicators.push(`Directory: ${dir}`);
          }
        }

        frameworkScores.set(framework, score);
      }
    }

    // Find the best match
    let bestFramework = 'unknown';
    let bestScore = 0;

    for (const [framework, score] of frameworkScores) {
      if (score > bestScore) {
        bestFramework = framework;
        bestScore = score;
      }
    }

    // Determine architecture pattern
    let architecture: string | null = null;
    for (const [pattern, config] of this.architecturePatterns) {
      const matches = config.indicators.filter(indicator => 
        files.some(file => file.toLowerCase().includes(indicator))
      ).length;
      
      if (matches >= config.indicators.length * 0.6) {
        architecture = pattern;
        break;
      }
    }

    return {
      domain: bestFramework !== 'unknown' ? bestFramework : 'generic',
      confidence: Math.min(bestScore / 2, 1.0), // Normalize score
      indicators,
      framework: bestFramework !== 'unknown' ? bestFramework : null,
      architecture
    };
  }

  /**
   * Assess security level based on file patterns and dependencies
   */
  async assessSecurity(files: string[], fileContents: Map<string, string>): Promise<SecurityAssessment> {
    const risks: string[] = [];
    const recommendations: string[] = [];
    const complianceIssues: string[] = [];
    let riskScore = 0;

    // Analyze file contents for security patterns
    for (const [filePath, content] of fileContents) {
      for (const [patternName, config] of this.securityPatterns) {
        if (config.pattern.test(content)) {
          risks.push(`${patternName} in ${filePath}: ${config.description}`);
          
          switch (config.risk) {
            case 'critical':
              riskScore += 4;
              break;
            case 'high':
              riskScore += 3;
              break;
            case 'medium':
              riskScore += 2;
              break;
            case 'low':
              riskScore += 1;
              break;
          }
        }
      }
    }

    // Check for security-related files
    const hasSecurityConfig = files.some(file => 
      file.includes('security') || 
      file.includes('auth') || 
      file.includes('.env') ||
      file.includes('ssl') ||
      file.includes('cert')
    );

    if (!hasSecurityConfig) {
      recommendations.push('Add security configuration files');
      riskScore += 1;
    }

    // Check for HTTPS configuration
    const hasHttpsConfig = files.some(file => 
      file.includes('https') || 
      file.includes('ssl') || 
      file.includes('tls')
    );

    if (!hasHttpsConfig) {
      complianceIssues.push('No HTTPS/TLS configuration found');
      riskScore += 2;
    }

    // Determine security level
    let level: 'low' | 'medium' | 'high' | 'critical';
    if (riskScore >= 10) {
      level = 'critical';
    } else if (riskScore >= 6) {
      level = 'high';
    } else if (riskScore >= 3) {
      level = 'medium';
    } else {
      level = 'low';
    }

    // Add general recommendations
    if (level !== 'low') {
      recommendations.push('Implement input validation');
      recommendations.push('Use secure authentication mechanisms');
      recommendations.push('Enable security headers');
      recommendations.push('Implement proper error handling');
    }

    return {
      level,
      confidence: Math.min(riskScore / 15, 1.0), // Normalize confidence
      risks,
      recommendations,
      complianceIssues
    };
  }

  /**
   * Comprehensive project structure analysis
   */
  async analyzeProjectStructure(
    rootPath: string, 
    files: string[], 
    fileContents: Map<string, string>
  ): Promise<ProjectStructureAnalysis> {
    // Detect frameworks
    const frameworks: FrameworkIndicator[] = [];
    for (const [framework, config] of this.frameworkPatterns) {
      let confidence = 0;
      const matchedFiles: string[] = [];
      const patterns: string[] = [];

      for (const file of files) {
        const fileName = file.toLowerCase();
        
        // Check required files
        for (const requiredFile of config.files) {
          if (fileName.includes(requiredFile.toLowerCase())) {
            confidence += 0.4;
            matchedFiles.push(file);
            patterns.push(`Required file: ${requiredFile}`);
          }
        }

        // Check directories
        for (const dir of config.directories) {
          if (fileName.includes(dir.toLowerCase() + '/')) {
            confidence += 0.2;
            patterns.push(`Directory structure: ${dir}`);
          }
        }
      }

      if (confidence > 0.3) {
        frameworks.push({
          framework,
          confidence: Math.min(confidence, 1.0),
          files: matchedFiles,
          patterns
        });
      }
    }

    // Detect architecture patterns
    const architecture: ArchitecturePattern[] = [];
    for (const [pattern, config] of this.architecturePatterns) {
      const indicators: string[] = [];
      let matches = 0;

      for (const indicator of config.indicators) {
        const found = files.some(file => file.toLowerCase().includes(indicator));
        if (found) {
          matches++;
          indicators.push(indicator);
        }
      }

      const confidence = matches / config.indicators.length;
      if (confidence > 0.4) {
        architecture.push({
          pattern,
          confidence,
          indicators
        });
      }
    }

    // Analyze dependencies (simplified)
    const dependencies: DependencyInfo[] = [];
    for (const [filePath, content] of fileContents) {
      if (filePath.includes('package.json') || filePath.includes('requirements.txt') || filePath.includes('Cargo.toml')) {
        // Extract dependency information (simplified)
        const lines = content.split('\n');
        for (const line of lines) {
          if (line.includes('dependency') || line.includes('require')) {
            // This is a simplified extraction - in reality, you'd parse the specific format
            dependencies.push({
              name: 'extracted-dependency',
              type: 'direct',
              securityRisk: 'low'
            });
          }
        }
      }
    }

    // Analyze security patterns
    const securityPatterns: SecurityPattern[] = [];
    for (const [filePath, content] of fileContents) {
      for (const [patternName, config] of this.securityPatterns) {
        if (config.pattern.test(content)) {
          securityPatterns.push({
            pattern: patternName,
            risk: config.risk,
            files: [filePath],
            description: config.description
          });
        }
      }
    }

    return {
      rootPath,
      frameworks,
      architecture,
      dependencies,
      securityPatterns
    };
  }

  /**
   * Get confidence score for a specific analysis type
   */
  getAnalysisConfidence(analysisType: 'intent' | 'domain' | 'security', result: any): number {
    switch (analysisType) {
      case 'intent':
        return (result as IntentClassification).confidence;
      case 'domain':
        return (result as DomainDetection).confidence;
      case 'security':
        return (result as SecurityAssessment).confidence;
      default:
        return 0;
    }
  }

  /**
   * Combine multiple analysis results with weighted confidence
   */
  combineAnalysisResults(results: Array<{ type: string; result: any; weight: number }>): {
    combinedConfidence: number;
    results: any[];
    metadata: Record<string, any>;
  } {
    let totalWeight = 0;
    let weightedConfidence = 0;

    for (const { result, weight } of results) {
      const confidence = this.getAnalysisConfidence(result.type, result.result);
      weightedConfidence += confidence * weight;
      totalWeight += weight;
    }

    const combinedConfidence = totalWeight > 0 ? weightedConfidence / totalWeight : 0;

    return {
      combinedConfidence,
      results: results.map(r => r.result),
      metadata: {
        totalAnalyses: results.length,
        averageConfidence: combinedConfidence,
        analysisTypes: results.map(r => r.type)
      }
    };
  }
}

// Singleton instance
export const ruleBasedAnalyzer = new RuleBasedAnalyzer();