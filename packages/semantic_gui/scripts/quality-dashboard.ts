#!/usr/bin/env tsx

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

import type { QualityReport, QualityMetrics } from './quality-metrics';

class QualityDashboard {
  private metricsFile: string;

  constructor() {
    this.metricsFile = join(process.cwd(), 'quality-metrics.json');
  }

  private loadReport(): QualityReport | null {
    if (!existsSync(this.metricsFile)) {
      console.log(
        '❌ No quality metrics found. Run "npm run quality:metrics" first.'
      );
      return null;
    }

    try {
      const data = readFileSync(this.metricsFile, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.error('❌ Failed to load quality metrics:', error);
      return null;
    }
  }

  displayDashboard(): void {
    const report = this.loadReport();
    if (!report) return;

    console.log('\n📊 Code Quality Dashboard');
    console.log('==========================');

    this.displayCurrentMetrics(report.current);
    this.displayTrends(report.trends);
    this.displayHistory(report.history);
    this.displayRecommendations(report.current);
  }

  private displayCurrentMetrics(metrics: QualityMetrics): void {
    console.log('\n📈 Current Metrics:');
    console.log('-------------------');
    console.log(
      `📅 Last Updated: ${new Date(metrics.timestamp).toLocaleString()}`
    );
    console.log(`📁 Total Files: ${metrics.totalFiles}`);
    console.log(`📏 Lines of Code: ${metrics.linesOfCode.toLocaleString()}`);
    console.log(`🧪 Test Coverage: ${metrics.testCoverage.toFixed(1)}%`);
    console.log('');

    console.log('🔍 Quality Issues:');
    console.log(`  Console Statements: ${metrics.consoleStatements}`);
    console.log(`  'any' Types: ${metrics.anyTypes}`);
    console.log(`  Unused Variables: ${metrics.unusedVariables}`);
    console.log(`  Import Order Issues: ${metrics.importOrderViolations}`);
    console.log(`  Structural Issues: ${metrics.structuralIssues}`);
    console.log(`  Lint Warnings: ${metrics.lintWarnings}`);
    console.log(`  Lint Errors: ${metrics.lintErrors}`);
    console.log(`  Type Errors: ${metrics.typeErrors}`);
  }

  private displayTrends(trends: QualityReport['trends']): void {
    console.log('\n📊 Trends:');
    console.log('----------');
    console.log(
      `Console Statements: ${this.getTrendDisplay(trends.consoleStatements)}`
    );
    console.log(`'any' Types: ${this.getTrendDisplay(trends.anyTypes)}`);
    console.log(
      `Unused Variables: ${this.getTrendDisplay(trends.unusedVariables)}`
    );
    console.log(`Overall: ${this.getTrendDisplay(trends.overall)}`);
  }

  private displayHistory(history: QualityMetrics[]): void {
    if (history.length < 2) {
      console.log('\n📈 History: Not enough data points');
      return;
    }

    console.log('\n📈 History (Last 10 entries):');
    console.log('------------------------------');

    const recentHistory = history.slice(-10);
    console.log('Date\t\t\tConsole\tAny\tUnused\tCoverage');
    console.log('----\t\t\t-------\t---\t------\t--------');

    recentHistory.forEach(entry => {
      const date = new Date(entry.timestamp).toLocaleDateString();
      console.log(
        `${date}\t\t${entry.consoleStatements}\t${entry.anyTypes}\t${entry.unusedVariables}\t${entry.testCoverage.toFixed(1)}%`
      );
    });
  }

  private displayRecommendations(metrics: QualityMetrics): void {
    console.log('\n💡 Recommendations:');
    console.log('-------------------');

    const recommendations: string[] = [];

    if (metrics.consoleStatements > 0) {
      recommendations.push(
        `🔧 Replace ${metrics.consoleStatements} console statements with proper logging`
      );
    }

    if (metrics.anyTypes > 10) {
      recommendations.push(
        `🔧 Replace ${metrics.anyTypes} 'any' types with specific types`
      );
    }

    if (metrics.unusedVariables > 0) {
      recommendations.push(
        `🔧 Remove ${metrics.unusedVariables} unused variables`
      );
    }

    if (metrics.testCoverage < 80) {
      recommendations.push(
        `🧪 Increase test coverage from ${metrics.testCoverage.toFixed(1)}% to at least 80%`
      );
    }

    if (metrics.lintErrors > 0) {
      recommendations.push(`🚨 Fix ${metrics.lintErrors} lint errors`);
    }

    if (metrics.lintWarnings > 10) {
      recommendations.push(`⚠️ Address ${metrics.lintWarnings} lint warnings`);
    }

    if (metrics.typeErrors > 0) {
      recommendations.push(`🔍 Fix ${metrics.typeErrors} TypeScript errors`);
    }

    if (recommendations.length === 0) {
      console.log('✅ No major issues found! Your code quality is excellent.');
    } else {
      recommendations.forEach(rec => console.log(`  ${rec}`));
    }
  }

  private getTrendDisplay(trend: 'improving' | 'degrading' | 'stable'): string {
    const emoji = {
      improving: '📈',
      degrading: '📉',
      stable: '➡️',
    }[trend];

    const color = {
      improving: '\x1b[32m', // Green
      degrading: '\x1b[31m', // Red
      stable: '\x1b[33m', // Yellow
    }[trend];

    const reset = '\x1b[0m';

    return `${emoji} ${color}${trend.toUpperCase()}${reset}`;
  }

  generateMarkdownReport(): string {
    const report = this.loadReport();
    if (!report) return '';

    const { current, trends } = report;

    return `# Code Quality Report

Generated: ${new Date(current.timestamp).toLocaleString()}

## Current Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Total Files | ${current.totalFiles} | - |
| Lines of Code | ${current.linesOfCode.toLocaleString()} | - |
| Test Coverage | ${current.testCoverage.toFixed(1)}% | - |
| Console Statements | ${current.consoleStatements} | ${trends.consoleStatements} |
| 'any' Types | ${current.anyTypes} | ${trends.anyTypes} |
| Unused Variables | ${current.unusedVariables} | ${trends.unusedVariables} |
| Import Order Issues | ${current.importOrderViolations} | - |
| Structural Issues | ${current.structuralIssues} | - |
| Lint Warnings | ${current.lintWarnings} | - |
| Lint Errors | ${current.lintErrors} | - |
| Type Errors | ${current.typeErrors} | - |

## Overall Trend: ${trends.overall.toUpperCase()}

## Recommendations

${this.getMarkdownRecommendations(current)}

---
*Generated by Code Quality Dashboard*
`;
  }

  private getMarkdownRecommendations(metrics: QualityMetrics): string {
    const recommendations: string[] = [];

    if (metrics.consoleStatements > 0) {
      recommendations.push(
        `- [ ] Replace ${metrics.consoleStatements} console statements with proper logging`
      );
    }

    if (metrics.anyTypes > 10) {
      recommendations.push(
        `- [ ] Replace ${metrics.anyTypes} 'any' types with specific types`
      );
    }

    if (metrics.unusedVariables > 0) {
      recommendations.push(
        `- [ ] Remove ${metrics.unusedVariables} unused variables`
      );
    }

    if (metrics.testCoverage < 80) {
      recommendations.push(
        `- [ ] Increase test coverage from ${metrics.testCoverage.toFixed(1)}% to at least 80%`
      );
    }

    if (metrics.lintErrors > 0) {
      recommendations.push(`- [ ] Fix ${metrics.lintErrors} lint errors`);
    }

    if (recommendations.length === 0) {
      return '✅ No major issues found! Your code quality is excellent.';
    }

    return recommendations.join('\n');
  }
}

// Main execution
async function main() {
  const dashboard = new QualityDashboard();

  const args = process.argv.slice(2);

  if (args.includes('--markdown')) {
    const report = dashboard.generateMarkdownReport();
    console.log(report);
  } else {
    dashboard.displayDashboard();
  }
}

// Check if this is the main module (ES module equivalent)
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { QualityDashboard };
