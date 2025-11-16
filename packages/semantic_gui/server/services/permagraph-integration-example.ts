/**
 * PermaGraph Integration Example
 * 
 * Demonstrates how to use the PermaGraph Query Engine for 2FA payment service integration
 */

import { PermaGraphQueryService } from './permagraph-query-service';
import { PermaGraphController } from './permagraph-controller';

/**
 * Example usage of the PermaGraph Query Engine for 2FA payment service integration
 */
export class PermaGraphIntegrationExample {
  private queryService: PermaGraphQueryService;

  constructor(projectRoot: string) {
    const permagraphController = new PermaGraphController('2fa-payment-project');
    
    const config = {
      projectRoot,
      permagraphController,
      cacheTTL: 300000, // 5 minutes
      enableOptimization: true,
      enableScoring: true
    };

    this.queryService = new PermaGraphQueryService(config);
  }

  /**
   * Example: Query 2FA authentication patterns for a Kthulu-based payment service
   */
  async example2FAPatternQuery() {
    console.log('🔍 Querying 2FA authentication patterns...');

    const request = {
      type: 'authentication' as const,
      parameters: {
        authType: '2fa',
        framework: 'kthulu',
        securityLevel: '80'
      },
      context: {
        projectType: 'payment-service',
        framework: 'kthulu',
        securityRequirements: ['2fa', 'totp', 'backup-codes'],
        complianceStandards: ['owasp', 'pci-dss'],
        teamExperience: 'intermediate' as const,
        timeConstraints: 'moderate' as const,
        budgetConstraints: 'medium' as const
      },
      includeScoring: true,
      includeRelationships: true
    };

    try {
      const response = await this.queryService.queryAuthenticationPatterns(request);
      
      console.log(`✅ Found ${response.patterns.length} authentication patterns`);
      console.log(`📊 Execution time: ${response.metadata.executionTime.toFixed(2)}ms`);
      console.log(`🎯 Overall confidence: ${(response.metadata.confidence * 100).toFixed(1)}%`);

      if (response.scores && response.scores.length > 0) {
        console.log('\n🏆 Top scored patterns:');
        response.scores.slice(0, 3).forEach((score, index) => {
          console.log(`  ${index + 1}. ${score.patternId} - Score: ${(score.overallScore * 100).toFixed(1)}%`);
          console.log(`     Success Rate: ${(score.successRateScore * 100).toFixed(1)}%`);
          console.log(`     Architectural Fit: ${(score.architecturalFitScore * 100).toFixed(1)}%`);
          console.log(`     Compliance: ${(score.complianceScore * 100).toFixed(1)}%`);
        });
      }

      return response;
    } catch (error) {
      console.error('❌ Error querying authentication patterns:', error);
      throw error;
    }
  }

  /**
   * Example: Query payment service patterns
   */
  async examplePaymentServiceQuery() {
    console.log('\n💳 Querying payment service patterns...');

    const request = {
      type: 'payment' as const,
      parameters: {
        serviceType: 'payment_gateway',
        complianceRequirements: ['pci-dss', 'gdpr']
      },
      context: {
        projectType: 'e-commerce',
        framework: 'kthulu',
        securityRequirements: ['encryption', 'tokenization'],
        complianceStandards: ['pci-dss', 'gdpr'],
        teamExperience: 'expert' as const,
        timeConstraints: 'flexible' as const,
        budgetConstraints: 'high' as const
      },
      includeScoring: true,
      includeRelationships: false
    };

    try {
      const response = await this.queryService.queryPaymentServicePatterns(request);
      
      console.log(`✅ Found ${response.patterns.length} payment service patterns`);
      console.log(`📊 Execution time: ${response.metadata.executionTime.toFixed(2)}ms`);

      if (response.scores && response.scores.length > 0) {
        console.log('\n🏆 Top scored payment patterns:');
        response.scores.slice(0, 3).forEach((score, index) => {
          console.log(`  ${index + 1}. ${score.patternId} - Score: ${(score.overallScore * 100).toFixed(1)}%`);
        });
      }

      return response;
    } catch (error) {
      console.error('❌ Error querying payment service patterns:', error);
      throw error;
    }
  }

  /**
   * Example: Analyze code dependencies
   */
  async exampleDependencyAnalysis() {
    console.log('\n🔗 Analyzing code dependencies...');

    const filePaths = [
      '/src/domain/user.ts',
      '/src/application/auth-service.ts',
      '/src/infrastructure/payment-adapter.ts',
      '/src/presentation/auth-controller.ts'
    ];

    const request = {
      filePaths,
      includeArchitecturalPatterns: true,
      includeRequirementLinkages: true,
      requirements: [
        'Implement 2FA authentication',
        'Add payment processing',
        'Ensure PCI DSS compliance',
        'Create audit logging'
      ],
      context: '2FA payment service integration'
    };

    try {
      const response = await this.queryService.analyzeDependencies(request);
      
      console.log(`✅ Analyzed ${response.metadata.fileCount} files`);
      console.log(`🔗 Found ${response.metadata.dependencyCount} dependencies`);
      console.log(`🔄 Detected ${response.metadata.cycleCount} circular dependencies`);
      console.log(`🏗️ Recognized ${response.metadata.patternCount} architectural patterns`);
      console.log(`📊 Execution time: ${response.metadata.executionTime.toFixed(2)}ms`);

      if (response.architecturalPatterns && response.architecturalPatterns.length > 0) {
        console.log('\n🏗️ Detected architectural patterns:');
        response.architecturalPatterns.forEach(pattern => {
          console.log(`  • ${pattern.name} (${pattern.type}) - Confidence: ${(pattern.confidence * 100).toFixed(1)}%`);
          if (pattern.violations.length > 0) {
            console.log(`    ⚠️ ${pattern.violations.length} violations detected`);
          }
        });
      }

      return response;
    } catch (error) {
      console.error('❌ Error analyzing dependencies:', error);
      throw error;
    }
  }

  /**
   * Example: Comprehensive pattern analysis
   */
  async exampleComprehensiveAnalysis() {
    console.log('\n🎯 Running comprehensive pattern analysis...');

    const filePaths = [
      '/src/domain/user.ts',
      '/src/application/auth-service.ts',
      '/src/infrastructure/payment-adapter.ts'
    ];

    const context = {
      projectType: 'fintech-app',
      framework: 'kthulu',
      securityRequirements: ['2fa', 'encryption', 'audit'],
      complianceStandards: ['owasp', 'pci-dss', 'gdpr'],
      teamExperience: 'intermediate' as const,
      timeConstraints: 'moderate' as const,
      budgetConstraints: 'medium' as const
    };

    try {
      const result = await this.queryService.getComprehensivePatternAnalysis(
        '2fa',
        'payment_gateway',
        filePaths,
        context
      );

      console.log('✅ Comprehensive analysis completed');
      console.log(`🔐 Auth patterns: ${result.authPatterns.patterns.length}`);
      console.log(`💳 Service patterns: ${result.servicePatterns.patterns.length}`);
      console.log(`🔗 Dependencies: ${result.dependencies.dependencies.length}`);
      console.log(`💡 Recommendations: ${result.recommendations.length}`);

      if (result.recommendations.length > 0) {
        console.log('\n💡 Recommendations:');
        result.recommendations.forEach((rec, index) => {
          console.log(`  ${index + 1}. ${rec}`);
        });
      }

      return result;
    } catch (error) {
      console.error('❌ Error in comprehensive analysis:', error);
      throw error;
    }
  }

  /**
   * Example: Query security requirements
   */
  async exampleSecurityRequirements() {
    console.log('\n🔒 Querying security requirements...');

    const context = {
      projectType: 'payment-service',
      framework: 'kthulu',
      securityRequirements: ['2fa', 'encryption'],
      complianceStandards: ['owasp', 'pci-dss'],
      teamExperience: 'intermediate' as const,
      timeConstraints: 'moderate' as const,
      budgetConstraints: 'medium' as const
    };

    try {
      const requirementChains = await this.queryService.querySecurityRequirements(
        '2fa-payment-integration',
        ['owasp', 'pci-dss'],
        context
      );

      console.log(`✅ Found ${requirementChains.length} requirement chains`);

      if (requirementChains.length > 0) {
        console.log('\n📋 Security requirement chains:');
        requirementChains.slice(0, 3).forEach((chain, index) => {
          console.log(`  ${index + 1}. ${chain.sourceRequirement}`);
          console.log(`     Linked requirements: ${chain.linkedRequirements.length}`);
          console.log(`     Dependencies: ${chain.dependencies.length}`);
          console.log(`     Compliance mappings: ${chain.complianceMapping.length}`);
        });
      }

      return requirementChains;
    } catch (error) {
      console.error('❌ Error querying security requirements:', error);
      throw error;
    }
  }

  /**
   * Run all examples
   */
  async runAllExamples() {
    console.log('🚀 Starting PermaGraph Query Engine Examples\n');
    console.log('=' .repeat(60));

    try {
      // Run all examples
      await this.example2FAPatternQuery();
      await this.examplePaymentServiceQuery();
      await this.exampleDependencyAnalysis();
      await this.exampleSecurityRequirements();
      await this.exampleComprehensiveAnalysis();

      console.log('\n' + '='.repeat(60));
      console.log('✅ All examples completed successfully!');

      // Show cache statistics
      const stats = this.queryService.getStatistics();
      console.log('\n📊 Cache Statistics:');
      console.log(`  Query cache size: ${stats.queryCache.size}`);
      console.log(`  Pattern scorer cache size: ${stats.patternScorer.size}`);

    } catch (error) {
      console.error('\n❌ Example execution failed:', error);
      throw error;
    }
  }
}

/**
 * Usage example
 */
export async function runPermaGraphExample() {
  const example = new PermaGraphIntegrationExample('/path/to/project');
  await example.runAllExamples();
}

// Export for use in other modules
export { PermaGraphIntegrationExample };