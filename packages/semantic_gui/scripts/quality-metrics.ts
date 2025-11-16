#!/usr/bin/env tsx

import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

import { glob } from 'glob';

interface QualityMetrics {
  timestamp: string;
  consoleStatements: number;
  anyTypes: number;
  unusedVariables: number;
  importOrderViolations: number;
  structuralIssues: number;
  testCoverage: number;
  lintWarnings: number;
  lintErrors: number;
  typeErrors: number;
  totalFiles: number;
  linesOfCode: number;
}

interface QualityReport {
  current: QualityMetrics;
  history: QualityMetrics[];
  trends: {
    consoleStatements: 'improving' | 'degrading' | 'stable';
    anyTypes: 'improving' | 'degrading' | 'stable';
    unusedVariables: 'improving' | 'degrading' | 'stable';
    overall: 'improving' | 'degrading' | 'stable';
  };
}

class QualityMetricsCollector {
  private projectRoot: string;
  private metricsFile: string;

  constructor() {
    this.projectRoot = process.cwd();
    this.metricsFile = join(this.projectRoot, 'quality-metrics.json');
  }

  async collectMetrics(): Promise<QualityMetrics> {
    console.log('📊 Collecting quality metrics...');

    const metrics: QualityMetrics = {
      timestamp: new Date().toISOString(),
      consoleStatements: await this.countConsoleStatements(),
      anyTypes: await this.countAnyTypes(),
      unusedVariables: await this.countUnusedVariables(),
      importOrderViolations: await this.countImportOrderViolations(),
      structuralIssues: await this.countStructuralIssues(),
      testCoverage: await this.getTestCoverage(),
      lintWarnings: await this.getLintWarnings(),
      lintErrors: await this.getLintErrors(),
      typeErrors: await this.getTypeErrors(),
      totalFiles: await this.countTotalFiles(),
      linesOfCode: await this.countLinesOfCode(),
    };

    return metrics;
  }

  private async countConsoleStatements(): Promise<number> {
    try {
      const result = execSync(
        'grep -r "console\\." --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" client/ server/ shared/ 2>/dev/null | wc -l',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      return parseInt(result.trim()) || 0;
    } catch {
      return 0;
    }
  }

  private async countAnyTypes(): Promise<number> {
    try {
      const result = execSync(
        'grep -r ": any\\|<any>\\|any\\[\\]\\|any |" --include="*.ts" --include="*.tsx" client/ server/ shared/ 2>/dev/null | wc -l',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      return parseInt(result.trim()) || 0;
    } catch {
      return 0;
    }
  }

  private async countUnusedVariables(): Promise<number> {
    try {
      const result = execSync(
        'npx eslint . --format=json --rule="@typescript-eslint/no-unused-vars: error" 2>/dev/null',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      const lintResults = JSON.parse(result);
      return lintResults.reduce((count: number, file: any) => {
        return (
          count +
          file.messages.filter(
            (msg: any) => msg.ruleId === '@typescript-eslint/no-unused-vars'
          ).length
        );
      }, 0);
    } catch {
      return 0;
    }
  }

  private async countImportOrderViolations(): Promise<number> {
    try {
      const result = execSync(
        'npx eslint . --format=json --rule="import/order: error" 2>/dev/null',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      const lintResults = JSON.parse(result);
      return lintResults.reduce((count: number, file: any) => {
        return (
          count +
          file.messages.filter((msg: any) => msg.ruleId === 'import/order')
            .length
        );
      }, 0);
    } catch {
      return 0;
    }
  }

  private async countStructuralIssues(): Promise<number> {
    try {
      const result = execSync(
        'npx eslint . --format=json --rule="no-empty: error" --rule="no-unreachable: error" 2>/dev/null',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      const lintResults = JSON.parse(result);
      return lintResults.reduce((count: number, file: any) => {
        return (
          count +
          file.messages.filter(
            (msg: any) =>
              msg.ruleId === 'no-empty' || msg.ruleId === 'no-unreachable'
          ).length
        );
      }, 0);
    } catch {
      return 0;
    }
  }

  private async getTestCoverage(): Promise<number> {
    try {
      // Run tests with coverage and extract percentage
      const result = execSync(
        'npm run test -- --coverage --silent 2>/dev/null',
        {
          encoding: 'utf8',
          cwd: this.projectRoot,
        }
      );

      // Extract coverage percentage from output
      const coverageMatch = result.match(/All files\s+\|\s+(\d+\.?\d*)/);
      return coverageMatch ? parseFloat(coverageMatch[1]) : 0;
    } catch {
      return 0;
    }
  }

  private async getLintWarnings(): Promise<number> {
    try {
      const result = execSync('npx eslint . --format=json 2>/dev/null', {
        encoding: 'utf8',
        cwd: this.projectRoot,
      });
      const lintResults = JSON.parse(result);
      return lintResults.reduce((count: number, file: any) => {
        return count + file.warningCount;
      }, 0);
    } catch {
      return 0;
    }
  }

  private async getLintErrors(): Promise<number> {
    try {
      const result = execSync('npx eslint . --format=json 2>/dev/null', {
        encoding: 'utf8',
        cwd: this.projectRoot,
      });
      const lintResults = JSON.parse(result);
      return lintResults.reduce((count: number, file: any) => {
        return count + file.errorCount;
      }, 0);
    } catch {
      return 0;
    }
  }

  private async getTypeErrors(): Promise<number> {
    try {
      const result = execSync('npx tsc --noEmit --pretty false 2>&1', {
        encoding: 'utf8',
        cwd: this.projectRoot,
      });

      // Count error lines (lines that contain error messages)
      const errorLines = result
        .split('\n')
        .filter(line => line.includes('error TS') || line.includes('): error'));
      return errorLines.length;
    } catch (error: any) {
      // TypeScript errors are returned as non-zero exit code
      const errorLines =
        error.stdout
          ?.split('\n')
          .filter(
            (line: string) =>
              line.includes('error TS') || line.includes('): error')
          ) || [];
      return errorLines.length;
    }
  }

  private async countTotalFiles(): Promise<number> {
    const files = await glob('**/*.{ts,tsx,js,jsx}', {
      cwd: this.projectRoot,
      ignore: ['node_modules/**', 'dist/**', 'build/**'],
    });
    return files.length;
  }

  private async countLinesOfCode(): Promise<number> {
    try {
      const result = execSync(
        'find . -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | grep -v node_modules | grep -v dist | xargs wc -l | tail -1',
        { encoding: 'utf8', cwd: this.projectRoot }
      );
      const match = result.match(/(\d+)\s+total/);
      return match ? parseInt(match[1]) : 0;
    } catch {
      return 0;
    }
  }

  private loadHistory(): QualityMetrics[] {
    if (!existsSync(this.metricsFile)) {
      return [];
    }

    try {
      const data = readFileSync(this.metricsFile, 'utf8');
      const report: QualityReport = JSON.parse(data);
      return report.history || [];
    } catch {
      return [];
    }
  }

  private calculateTrends(
    current: QualityMetrics,
    history: QualityMetrics[]
  ): QualityReport['trends'] {
    if (history.length === 0) {
      return {
        consoleStatements: 'stable',
        anyTypes: 'stable',
        unusedVariables: 'stable',
        overall: 'stable',
      };
    }

    const previous = history[history.length - 1];

    const getTrend = (
      current: number,
      previous: number
    ): 'improving' | 'degrading' | 'stable' => {
      if (current < previous) return 'improving';
      if (current > previous) return 'degrading';
      return 'stable';
    };

    const consoleStatements = getTrend(
      current.consoleStatements,
      previous.consoleStatements
    );
    const anyTypes = getTrend(current.anyTypes, previous.anyTypes);
    const unusedVariables = getTrend(
      current.unusedVariables,
      previous.unusedVariables
    );

    // Calculate overall trend based on key metrics
    const improvingCount = [
      consoleStatements,
      anyTypes,
      unusedVariables,
    ].filter(t => t === 'improving').length;
    const degradingCount = [
      consoleStatements,
      anyTypes,
      unusedVariables,
    ].filter(t => t === 'degrading').length;

    let overall: 'improving' | 'degrading' | 'stable';
    if (improvingCount > degradingCount) overall = 'improving';
    else if (degradingCount > improvingCount) overall = 'degrading';
    else overall = 'stable';

    return { consoleStatements, anyTypes, unusedVariables, overall };
  }

  async generateReport(): Promise<QualityReport> {
    const current = await this.collectMetrics();
    const history = this.loadHistory();
    const trends = this.calculateTrends(current, history);

    const report: QualityReport = {
      current,
      history: [...history, current].slice(-50), // Keep last 50 entries
      trends,
    };

    // Save the report
    writeFileSync(this.metricsFile, JSON.stringify(report, null, 2));

    return report;
  }

  printReport(report: QualityReport): void {
    const { current, trends } = report;

    console.log('\n📊 Code Quality Metrics Report');
    console.log('================================');
    console.log(
      `📅 Generated: ${new Date(current.timestamp).toLocaleString()}`
    );
    console.log(`📁 Total Files: ${current.totalFiles}`);
    console.log(`📏 Lines of Code: ${current.linesOfCode.toLocaleString()}`);
    console.log('');

    console.log('🔍 Quality Issues:');
    console.log(
      `  Console Statements: ${current.consoleStatements} ${this.getTrendEmoji(trends.consoleStatements)}`
    );
    console.log(
      `  'any' Types: ${current.anyTypes} ${this.getTrendEmoji(trends.anyTypes)}`
    );
    console.log(
      `  Unused Variables: ${current.unusedVariables} ${this.getTrendEmoji(trends.unusedVariables)}`
    );
    console.log(`  Import Order Issues: ${current.importOrderViolations}`);
    console.log(`  Structural Issues: ${current.structuralIssues}`);
    console.log('');

    console.log('🧪 Code Quality:');
    console.log(`  Test Coverage: ${current.testCoverage.toFixed(1)}%`);
    console.log(`  Lint Warnings: ${current.lintWarnings}`);
    console.log(`  Lint Errors: ${current.lintErrors}`);
    console.log(`  Type Errors: ${current.typeErrors}`);
    console.log('');

    console.log(
      `📈 Overall Trend: ${this.getTrendEmoji(trends.overall)} ${trends.overall.toUpperCase()}`
    );

    if (
      current.consoleStatements > 0 ||
      current.anyTypes > 10 ||
      current.unusedVariables > 0
    ) {
      console.log('\n⚠️  Quality Issues Detected:');
      if (current.consoleStatements > 0) {
        console.log(
          `  - Replace ${current.consoleStatements} console statements with proper logging`
        );
      }
      if (current.anyTypes > 10) {
        console.log(
          `  - Replace ${current.anyTypes} 'any' types with specific types`
        );
      }
      if (current.unusedVariables > 0) {
        console.log(`  - Remove ${current.unusedVariables} unused variables`);
      }
    } else {
      console.log('\n✅ No major quality issues detected!');
    }
  }

  private getTrendEmoji(trend: 'improving' | 'degrading' | 'stable'): string {
    switch (trend) {
      case 'improving':
        return '📈';
      case 'degrading':
        return '📉';
      case 'stable':
        return '➡️';
    }
  }
}

// Main execution
async function main() {
  const collector = new QualityMetricsCollector();

  try {
    const report = await collector.generateReport();
    collector.printReport(report);

    // Exit with error code if quality is degrading
    if (report.trends.overall === 'degrading') {
      console.log(
        '\n❌ Quality is degrading. Please address the issues above.'
      );
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Failed to generate quality metrics:', error);
    process.exit(1);
  }
}

// Check if this is the main module (ES module equivalent)
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { QualityMetricsCollector, type QualityMetrics, type QualityReport };
