# Code Quality System

This document describes the automated code quality system implemented for the SCG project.

## Overview

The quality system provides automated checks, metrics tracking, and quality gates to ensure consistent code quality throughout the development lifecycle.

## Components

### 1. Pre-commit Hooks

Automated quality checks run before each commit:

- **Lint-staged**: Runs ESLint and Prettier on staged files
- **Quality Gate**: Comprehensive quality checks using configurable thresholds

```bash
# Hooks are automatically installed via Husky
# Manual trigger:
npm run quality:gate
```

### 2. Quality Metrics Collection

Tracks various code quality metrics over time:

- Console statements count
- TypeScript 'any' types usage
- Unused variables
- Import order violations
- Structural issues
- Test coverage
- Lint warnings/errors
- TypeScript errors

```bash
# Generate metrics
npm run quality:metrics

# View dashboard
npm run quality:dashboard
```

### 3. CI/CD Quality Gates

Automated quality checks in the CI/CD pipeline:

- Runs on every pull request and push
- Fails the build if quality thresholds are exceeded
- Generates quality reports as artifacts

### 4. Quality Configuration

Centralized configuration in `quality.config.json`:

```json
{
  "thresholds": {
    "consoleStatements": { "max": 0, "warning": 5 },
    "anyTypes": { "max": 10, "warning": 20 },
    "testCoverage": { "min": 80, "warning": 70 }
  }
}
```

## Usage

### Daily Development

1. **Write code** - Quality checks run automatically on commit
2. **Review metrics** - Use `npm run quality:dashboard` to see current status
3. **Address issues** - Fix any violations before pushing

### Quality Monitoring

```bash
# Check current quality status
npm run quality:dashboard

# Generate detailed metrics
npm run quality:metrics

# Run quality gate manually
npm run quality:gate
```

### Configuration

Edit `quality.config.json` to adjust thresholds:

- **max/min**: Hard limits that fail the quality gate
- **warning**: Soft limits that generate warnings
- **description**: Human-readable explanation of the rule

## Quality Metrics

### Console Statements
- **Target**: 0
- **Why**: Console statements should be replaced with proper logging
- **Fix**: Use the Winston logger service instead

### 'any' Types
- **Target**: < 10
- **Why**: Reduces type safety and IDE support
- **Fix**: Replace with specific TypeScript types

### Unused Variables
- **Target**: 0
- **Why**: Clutters code and may indicate dead code
- **Fix**: Remove unused variables or prefix with underscore

### Test Coverage
- **Target**: > 80%
- **Why**: Ensures code reliability and catches regressions
- **Fix**: Add unit tests for uncovered code

### Lint Errors
- **Target**: 0
- **Why**: Indicates code style violations or potential bugs
- **Fix**: Run `npm run lint:fix` or fix manually

## Integration

### Git Hooks

- **pre-commit**: Runs quality checks on staged files
- **pre-push**: Runs comprehensive quality checks and tests

### CI/CD Pipeline

- **Quality Gate Job**: Runs before tests and build
- **Artifact Upload**: Saves quality metrics and reports
- **Failure Handling**: Fails the build if quality gate fails

### IDE Integration

Configure your IDE to:
- Run ESLint on save
- Show TypeScript errors inline
- Format code with Prettier

## Troubleshooting

### Quality Gate Failures

1. **Check the output** - Look for specific violations
2. **Run locally** - Use `npm run quality:gate` to debug
3. **Fix issues** - Address violations one by one
4. **Verify fix** - Run quality gate again

### Metric Collection Issues

1. **Check dependencies** - Ensure all tools are installed
2. **Verify paths** - Check that file paths are correct
3. **Run manually** - Use individual commands to isolate issues

### Configuration Issues

1. **Validate JSON** - Ensure `quality.config.json` is valid
2. **Check thresholds** - Verify thresholds are reasonable
3. **Test changes** - Run quality gate after configuration changes

## Best Practices

1. **Run quality checks locally** before pushing
2. **Address violations promptly** to avoid accumulation
3. **Monitor trends** to catch quality degradation early
4. **Adjust thresholds** as the codebase matures
5. **Review quality reports** regularly in team meetings

## Scripts Reference

| Script | Description |
|--------|-------------|
| `npm run quality:check` | Basic quality checks (lint, format, type-check) |
| `npm run quality:metrics` | Generate quality metrics |
| `npm run quality:dashboard` | Display quality dashboard |
| `npm run quality:gate` | Run quality gate with thresholds |
| `npm run quality:badge` | Generate quality badges for README |
| `npm run emergency:commit` | Emergency commit bypassing quality checks |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Fix auto-fixable lint issues |
| `npm run format` | Format code with Prettier |
| `npm run type-check` | Run TypeScript compiler checks |

## Emergency Procedures

### Bypassing Quality Checks

In emergency situations, you can bypass quality checks:

```bash
# Method 1: Use emergency commit script
npm run emergency:commit

# Method 2: Set environment variable
SKIP_QUALITY_CHECKS=true git commit -m "Emergency fix"

# Method 3: Use git commit with --no-verify
git commit --no-verify -m "Emergency fix"
```

**⚠️ Important**: Always address quality issues in follow-up commits!

## Files

- `quality.config.json` - Quality configuration and thresholds
- `quality-metrics.json` - Historical quality metrics data
- `scripts/quality-metrics.ts` - Metrics collection script
- `scripts/quality-dashboard.ts` - Dashboard display script
- `scripts/quality-gate.ts` - Quality gate enforcement script
- `.husky/pre-commit` - Pre-commit hook configuration
- `.husky/pre-push` - Pre-push hook configuration