#!/usr/bin/env tsx

import { readFileSync, existsSync, writeFileSync } from 'fs';
import { join } from 'path';

import type { QualityReport } from './quality-metrics';

class QualityBadgeGenerator {
  private metricsFile: string;

  constructor() {
    this.metricsFile = join(process.cwd(), 'quality-metrics.json');
  }

  private loadReport(): QualityReport | null {
    if (!existsSync(this.metricsFile)) {
      return null;
    }

    try {
      const data = readFileSync(this.metricsFile, 'utf8');
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  private calculateQualityScore(report: QualityReport): number {
    const metrics = report.current;

    // Calculate score based on various factors (0-100)
    let score = 100;

    // Deduct points for issues
    score -= Math.min(metrics.consoleStatements * 0.5, 20); // Max 20 points deduction
    score -= Math.min(metrics.anyTypes * 0.1, 20); // Max 20 points deduction
    score -= Math.min(metrics.unusedVariables * 1, 10); // Max 10 points deduction
    score -= Math.min(metrics.lintErrors * 2, 15); // Max 15 points deduction
    score -= Math.min(metrics.lintWarnings * 0.5, 10); // Max 10 points deduction
    score -= Math.min(metrics.typeErrors * 0.1, 15); // Max 15 points deduction

    // Add points for good coverage
    if (metrics.testCoverage >= 80) {
      score += 10;
    } else if (metrics.testCoverage >= 60) {
      score += 5;
    }

    return Math.max(0, Math.min(100, Math.round(score)));
  }

  private getQualityGrade(score: number): string {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  private getQualityColor(score: number): string {
    if (score >= 90) return 'brightgreen';
    if (score >= 80) return 'green';
    if (score >= 70) return 'yellow';
    if (score >= 60) return 'orange';
    return 'red';
  }

  generateBadgeUrl(): string {
    const report = this.loadReport();

    if (!report) {
      return 'https://img.shields.io/badge/quality-unknown-lightgrey';
    }

    const score = this.calculateQualityScore(report);
    const grade = this.getQualityGrade(score);
    const color = this.getQualityColor(score);

    return `https://img.shields.io/badge/quality-${grade}%20(${score}%25)-${color}`;
  }

  generateMarkdownBadge(): string {
    const url = this.generateBadgeUrl();
    return `![Code Quality](${url})`;
  }

  generateDetailedBadges(): string {
    const report = this.loadReport();

    if (!report) {
      return '![Code Quality](https://img.shields.io/badge/quality-unknown-lightgrey)';
    }

    const metrics = report.current;
    const score = this.calculateQualityScore(report);
    const grade = this.getQualityGrade(score);
    const color = this.getQualityColor(score);

    const badges = [
      `![Code Quality](https://img.shields.io/badge/quality-${grade}%20(${score}%25)-${color})`,
      `![Test Coverage](https://img.shields.io/badge/coverage-${metrics.testCoverage.toFixed(1)}%25-${metrics.testCoverage >= 80 ? 'brightgreen' : metrics.testCoverage >= 60 ? 'yellow' : 'red'})`,
      `![Console Statements](https://img.shields.io/badge/console%20statements-${metrics.consoleStatements}-${metrics.consoleStatements === 0 ? 'brightgreen' : metrics.consoleStatements <= 5 ? 'yellow' : 'red'})`,
      `![Any Types](https://img.shields.io/badge/any%20types-${metrics.anyTypes}-${metrics.anyTypes <= 10 ? 'brightgreen' : metrics.anyTypes <= 20 ? 'yellow' : 'red'})`,
      `![Type Errors](https://img.shields.io/badge/type%20errors-${metrics.typeErrors}-${metrics.typeErrors === 0 ? 'brightgreen' : 'red'})`,
    ];

    return badges.join('\n');
  }

  generateQualitySection(): string {
    const report = this.loadReport();

    if (!report) {
      return `## Code Quality

![Code Quality](https://img.shields.io/badge/quality-unknown-lightgrey)

Quality metrics not available. Run \`npm run quality:metrics\` to generate.`;
    }

    const metrics = report.current;
    const score = this.calculateQualityScore(report);
    const grade = this.getQualityGrade(score);

    return `## Code Quality

${this.generateDetailedBadges()}

### Current Status

- **Overall Grade**: ${grade} (${score}/100)
- **Test Coverage**: ${metrics.testCoverage.toFixed(1)}%
- **Console Statements**: ${metrics.consoleStatements}
- **'any' Types**: ${metrics.anyTypes}
- **Type Errors**: ${metrics.typeErrors}
- **Lint Errors**: ${metrics.lintErrors}
- **Lint Warnings**: ${metrics.lintWarnings}

### Trends

- Console Statements: ${this.getTrendEmoji(report.trends.consoleStatements)} ${report.trends.consoleStatements}
- 'any' Types: ${this.getTrendEmoji(report.trends.anyTypes)} ${report.trends.anyTypes}
- Unused Variables: ${this.getTrendEmoji(report.trends.unusedVariables)} ${report.trends.unusedVariables}
- **Overall**: ${this.getTrendEmoji(report.trends.overall)} ${report.trends.overall}

*Last updated: ${new Date(metrics.timestamp).toLocaleString()}*`;
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

  updateReadme(readmePath: string = 'README.md'): void {
    if (!existsSync(readmePath)) {
      console.log(`❌ README file not found: ${readmePath}`);
      return;
    }

    let content = readFileSync(readmePath, 'utf8');
    const qualitySection = this.generateQualitySection();

    // Look for existing quality section
    const qualityRegex = /## Code Quality[\s\S]*?(?=\n## |\n# |$)/;

    if (qualityRegex.test(content)) {
      // Replace existing section
      content = content.replace(qualityRegex, qualitySection);
      console.log('✅ Updated existing Code Quality section in README');
    } else {
      // Add new section at the end
      content += `\n\n${qualitySection}\n`;
      console.log('✅ Added new Code Quality section to README');
    }

    writeFileSync(readmePath, content);
  }
}

// Main execution
async function main() {
  const generator = new QualityBadgeGenerator();
  const args = process.argv.slice(2);

  if (args.includes('--url')) {
    console.log(generator.generateBadgeUrl());
  } else if (args.includes('--markdown')) {
    console.log(generator.generateMarkdownBadge());
  } else if (args.includes('--detailed')) {
    console.log(generator.generateDetailedBadges());
  } else if (args.includes('--section')) {
    console.log(generator.generateQualitySection());
  } else if (args.includes('--update-readme')) {
    const readmePath = args[args.indexOf('--update-readme') + 1] || 'README.md';
    generator.updateReadme(readmePath);
  } else {
    console.log('Quality Badge Generator');
    console.log('Usage:');
    console.log('  --url              Generate badge URL');
    console.log('  --markdown         Generate markdown badge');
    console.log('  --detailed         Generate detailed badges');
    console.log('  --section          Generate complete quality section');
    console.log('  --update-readme    Update README with quality section');
  }
}

// Check if this is the main module (ES module equivalent)
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { QualityBadgeGenerator };
