# Requirements Document

## Introduction

This document specifies the requirements for completely removing Leptos support from Ferrum. Leptos was partially implemented but never completed, and needs to be removed to simplify the codebase and avoid confusion. All references, code, templates, and documentation related to Leptos must be eliminated.

## Glossary

- **Ferrum**: The AI-first scaffolding framework
- **Leptos**: The incomplete Rust web framework integration being removed
- **CLI**: Command Line Interface - the ferrum executable
- **Frontend Enum**: The Rust enum defining available frontend options

## Requirements

### Requirement 1

**User Story:** As a maintainer, I want to remove all Leptos code from the CLI, so that the codebase only contains supported frontend options

#### Acceptance Criteria

1. THE CLI SHALL remove the LeptosCsr variant from the Frontend enum
2. THE CLI SHALL remove the LeptosSsr variant from the Frontend enum
3. THE CLI SHALL remove all Leptos-related conditional logic from init.rs
4. THE CLI SHALL remove the write_leptos_starter function
5. WHEN the CLI compiles, THE Compiler SHALL not produce any warnings about unused Leptos code

### Requirement 2

**User Story:** As a maintainer, I want to remove all Leptos templates and directories, so that the repository contains no Leptos artifacts

#### Acceptance Criteria

1. THE Cleanup Process SHALL delete any templates/leptos directory if it exists
2. THE Cleanup Process SHALL delete any templates/frontend_leptos directory if it exists
3. THE Cleanup Process SHALL remove Leptos-related template files from templates/
4. WHEN searching the templates directory, THE Search SHALL return zero results for "leptos"

### Requirement 3

**User Story:** As a maintainer, I want to remove all Leptos documentation, so that users are not confused by incomplete features

#### Acceptance Criteria

1. THE Cleanup Process SHALL remove all mentions of Leptos from README.md
2. THE Cleanup Process SHALL remove docs/leptos.md if it exists
3. THE Cleanup Process SHALL remove Leptos entries from PLAN.md session history
4. THE Cleanup Process SHALL update any documentation that lists frontend options to exclude Leptos
5. WHEN searching documentation for "leptos", THE Search SHALL return zero results

### Requirement 4

**User Story:** As a maintainer, I want to remove Leptos from build configurations, so that CI/CD and Docker setups are clean

#### Acceptance Criteria

1. THE Cleanup Process SHALL remove cargo-leptos installation from Dockerfile
2. THE Cleanup Process SHALL remove any Leptos-related scripts from tools/scripts/
3. THE Cleanup Process SHALL remove Leptos references from docker-compose templates
4. WHEN Docker builds, THE Build SHALL not install or reference Leptos tools

### Requirement 5

**User Story:** As a maintainer, I want to remove Leptos from MCP server configurations, so that external tools don't reference it

#### Acceptance Criteria

1. THE Cleanup Process SHALL remove 'leptos-csr' from frontend enum in packages/mcp-server/index.js
2. THE Cleanup Process SHALL remove 'leptos-ssr' from frontend enum in packages/mcp-server/index.js
3. THE Cleanup Process SHALL update FERRUM_MCP_TOOLS.md to remove Leptos options
4. WHEN the MCP server lists frontend options, THE List SHALL only contain 'react' and 'egui'

### Requirement 6

**User Story:** As a developer, I want the CLI to reject Leptos frontend flags, so that users get clear feedback

#### Acceptance Criteria

1. WHEN a user executes `ferrum init --frontend leptos-csr`, THE CLI SHALL display an error message stating Leptos is no longer supported
2. WHEN a user executes `ferrum init --frontend leptos-ssr`, THE CLI SHALL display an error message stating Leptos is no longer supported
3. THE Error Message SHALL suggest using --frontend egui or --frontend react instead
4. THE CLI SHALL exit with a non-zero status code when invalid frontend is specified
