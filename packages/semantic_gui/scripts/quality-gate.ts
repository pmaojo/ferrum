#!/usr/bin/env tsx

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

import {
  QualityMetricsCollector,
  type QualityMetrics,
} from './quality-metrics';

interface QualityThreshold {
  max?: number;
  min?: number;
  warning?: number;
  description: string;
}

interface QualityConfig {
  thresholds: {
    [key: string]: QualityThreshold;
  };
  rules: {
    failOnThresholdExceeded: boolean;
    warnOnThresholdApproached: boolean;
    trackTrends: boolean;
    generateReports: boolean;
  };
  reporting: {
    historyLength: number;
    trendAnalysis: boolean;
    markdownReports: boolean;
    ciIntegration: boolean;
  };
}

class QualityGate {
  private config: QualityConfig;
  private collector: QualityMetricsCollector;

  constructor() {
    this.config = this.loadConfig();
    this.collector = new QualityMetricsCollector();
  }

  private loadConfig(): QualityConfig {
    const configPath = join(process.cwd(), 'quality.config.json');

    if (!existsSync(configPath)) {
      throw new Error(
        'Quality configuration file not found. Please create quality.config.json'
      );
    }

    try {
      const data = readFileSync(configPath, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      throw new Error(`Failed to load quality configuration: ${error}`);
    }
  }

  async runQualityGate(): Promise<boolean> {
    console.log('🚪 Running Quality Gate...');
    console.log('==========================');

    try {
      // Generate quality report
      const report = await this.collector.generateReport();
      const metrics = report.current;

      // Check thresholds
      const violations = this.checkThresholds(metrics);
      const warnings = this.checkWarnings(metrics);

      // Display results
      this.displayResults(violations, warnings, metrics);

      // Determine if gate should pass
      const shouldPass = violations.length === 0;

      if (shouldPass) {
        console.log('\n✅ Quality Gate PASSED');
        if (warnings.length > 0) {
          console.log(`⚠️  ${warnings.length} warning(s) detected`);
        }
      } else {
        console.log('\n❌ Quality Gate FAILED');
        console.log(`🚨 ${violations.length} violation(s) detected`);
      }

      return shouldPass;
    } catch (error) {
      console.error('❌ Quality Gate failed to run:', error);
      return false;
    }
  }

  private checkThresholds(metrics: QualityMetrics): string[] {
    const violations: string[] = [];

    Object.entries(this.config.thresholds).forEach(([key, threshold]) => {
      const value = this.getMetricValue(metrics, key);

      if (value === undefined) return;

      if (threshold.max !== undefined && value > threshold.max) {
        violations.push(
          `${key}: ${value} exceeds maximum of ${threshold.max} - ${threshold.description}`
        );
      }

      if (threshold.min !== undefined && value < threshold.min) {
        violations.push(
          `${key}: ${value} below minimum of ${threshold.min} - ${threshold.description}`
        );
      }
    });

    return violations;
  }

  private checkWarnings(metrics: QualityMetrics): string[] {
    const warnings: string[] = [];

    Object.entries(this.config.thresholds).forEach(([key, threshold]) => {
      const value = this.getMetricValue(metrics, key);

      if (value === undefined) return;

      if (threshold.warning !== undefined) {
        if (
          threshold.max !== undefined &&
          value > threshold.warning &&
          value <= threshold.max
        ) {
          warnings.push(
            `${key}: ${value} approaching maximum threshold - ${threshold.description}`
          );
        }

        if (
          threshold.min !== undefined &&
          value < threshold.warning &&
          value >= threshold.min
        ) {
          warnings.push(
            `${key}: ${value} approaching minimum threshold - ${threshold.description}`
          );
        }
      }
    });

    return warnings;
  }

  private getMetricValue(
    metrics: QualityMetrics,
    key: string
  ): number | undefined {
    const metricMap: { [key: string]: keyof QualityMetrics } = {
      consoleStatements: 'consoleStatements',
      anyTypes: 'anyTypes',
      unusedVariables: 'unusedVariables',
      testCoverage: 'testCoverage',
      lintErrors: 'lintErrors',
      lintWarnings: 'lintWarnings',
      typeErrors: 'typeErrors',
      importOrderViolations: 'importOrderViolations',
      structuralIssues: 'structuralIssues',
    };

    const metricKey = metricMap[key];
    return metricKey ? (metrics[metricKey] as number) : undefined;
  }

  private displayResults(
    violations: string[],
    warnings: string[],
    metrics: QualityMetrics
  ): void {
    console.log('\n📊 Quality Gate Results:');
    console.log('------------------------');

    if (violations.length > 0) {
      console.log('\n🚨 VIOLATIONS:');
      violations.forEach(violation => console.log(`  ❌ ${violation}`));
    }

    if (warnings.length > 0) {
      console.log('\n⚠️  WARNINGS:');
      warnings.forEach(warning => console.log(`  ⚠️  ${warning}`));
    }

    console.log('\n📈 Current Metrics:');
    console.log(`  Console Statements: ${metrics.consoleStatements}`);
    console.log(`  'any' Types: ${metrics.anyTypes}`);
    console.log(`  Unused Variables: ${metrics.unusedVariables}`);
    console.log(`  Test Coverage: ${metrics.testCoverage.toFixed(1)}%`);
    console.log(`  Lint Errors: ${metrics.lintErrors}`);
    console.log(`  Lint Warnings: ${metrics.lintWarnings}`);
    console.log(`  Type Errors: ${metrics.typeErrors}`);
    console.log(`  Import Order Issues: ${metrics.importOrderViolations}`);
    console.log(`  Structural Issues: ${metrics.structuralIssues}`);
  }

  async runWithExitCode(): Promise<void> {
    const passed = await this.runQualityGate();
    process.exit(passed ? 0 : 1);
  }
}

// Main execution
async function main() {
  const gate = new QualityGate();
  await gate.runWithExitCode();
}

// Check if this is the main module (ES module equivalent)
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { QualityGate };
