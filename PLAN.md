# 🗺️ Ferrum Development Plan

## 📋 Overview

This document outlines the development roadmap for Ferrum, an AI-first scaffolding system that generates full-stack (Rust + React + TypeScript) code structured by layers following Hexagonal Architecture and SOLID principles.

## 🎯 Current Status

- ✅ Basic project structure implemented
- ✅ Core AST for `grafo.yaml` parsing
- ✅ CLI commands for `compile` and `prompt` (placeholder)
- ✅ Template system with Tera
- ✅ Code generation for backend and frontend

## 🚀 Phase 1: Core Functionality (Current)

### 1.1 Infrastructure & Architecture

- [x] Set up project structure
- [x] Define AST for `grafo.yaml`
- [x] Implement YAML parser
- [x] Create CLI interface
- [x] Implement template rendering system

### 1.2 Code Generation

- [x] Backend templates (handlers, routes, adapters, ports)
- [x] Frontend templates (hooks, components, schemas)
- [x] Shared model templates
- [x] Implement post-processing (run typeshare & formatting)
- [x] Add error handling and validation
- [x] Add `--with-auth`, `--with-jobs`, etc. flags to enable batteries-included templates
- [x] Add `--with-db` flag for Diesel support
- [x] Add `--with-graph` flag for Neo4j setup
- [x] Implement `ferrum sync` command to push graph to Neo4j

### 1.3 Typeshare Step

The `typeshare` CLI keeps our Rust models synchronized with TypeScript on both the Studio dashboard and any generated project.

1. Annotate structs in `shared-models/*.rs` with `#[typeshare]`.
2. Invoke the CLI at the end of the generation pipeline:

   ```rust
   let typeshare_status = Command::new("typeshare")
       .arg("--lang=typescript")
       .arg("--output-dir")
       .arg(output_dir.join("frontend/src/types"))
       .arg(output_dir.join("shared-models"))
       .status();
   ```

3. Generated `.ts` files appear under `frontend/src/types` (and under `studio/src/types` for the SaaS).
4. Import these types directly in your frontend code:

   ```ts
   import type { Usuario } from '@/types/usuario';
   ```

Automate this step via Docker or Make tasks so types remain aligned across the stack. The Makefile now provides `typeshare-studio` and `typeshare-project` targets, and the backend Dockerfile installs the `typeshare-cli` to generate TypeScript during CI builds.

### 1.4 Testing & Documentation

- [x] Unit tests for parser and validator
- [ ] Unit tests for generator
- [ ] Integration tests for end-to-end flow
- [ ] Example projects with different complexity levels
- [ ] Comprehensive documentation with examples

## 🧠 Phase 2: AI Integration

### 2.1 RAG System

- [ ] Set up vector database for architectural patterns
- [ ] Implement knowledge base for hexagonal architecture
- [ ] Create embeddings for common code patterns
- [ ] Develop retrieval system for relevant patterns

### 2.2 OWL Reasoning

- [ ] Define ontology for software architecture
- [ ] Implement reasoning engine for architectural decisions
- [ ] Create rules for validating architecture
- [ ] Develop explanation system for architectural choices
-
### 2.3 Prompt-to-YAML Generation

- [x] Integrate with LLM API (OpenAI, Anthropic, local)
- [ ] Develop prompt engineering for architecture extraction
- [x] Implement validation for generated YAML
- [ ] Create feedback loop for refinement

## 🧠 Phase 2.5: WASP-inspired UX Enhancements

### 2.5.1 DSL Enhancements
- [ ] Extend YAML syntax to support auth, jobs, pages, RPC
- [ ] Introduce semantic keywords inspired by Wasp DSL

### 2.5.2 AI Generation CLI
- [ ] Implement `ferrum init --ai` for guided prompts
- [x] Generate full-stack `grafo.yaml` from prompt using Python microservice

### 2.5.3 Full-stack Typed RPC
- [ ] Scaffold shared RPC functions with typed input/output
- [ ] Sync request/response models via `typeshare`

### 2.5.4 Batteries Included
- [ ] Optional modules: `auth`, `jobs`, `email`, `db`
- [ ] Templates auto-importable via `--with-X` flags

### 2.5.5 Smart README + Metadata
- [ ] Generate `README.md` with usage & architecture summary
- [ ] Export `metadata.json` describing modules & endpoints

## 🛠️ Phase 3: Advanced Features

### 3.1 Template Marketplace

- [ ] Create template repository structure
- [ ] Implement template discovery and installation
- [ ] Add versioning for templates
- [ ] Develop template validation

### 3.3 Plugin System

- [ ] Design plugin architecture
- [ ] Implement core plugin system
- [ ] Create authentication plugin
- [ ] Create database migration plugin

### 3.3 Diesel Migrations Integration

- [ ] Generate migration files based on entity nodes
- [ ] Apply migrations using Diesel's migration API
- [ ] Add a ferrum migrate command to the CLI
- [ ] Schema Generation from Entities
- [ ] Add a template for SQL schema generation
- [ ] Generate CREATE TABLE statements from entity definitions
- [ ] Support for relationships between entities
- [ ] Migration Management
- [ ] Track schema versions in a dedicated table
- [ ] Generate migration files with proper up/down methods
- [ ] Support for schema evolution over time

### 3.4 GraphQL Plugin

- [ ] Create GraphQL plugin
- [ ] Scaffold shared RPC functions with typed input/output
- [ ] Sync request/response models via `typeshare`

## 🧩 Phase 4: Visual Editor

### 4.1 Architecture Visualization

- [x] Implement graph visualization for architecture
- [x] Create interactive node editor
- [x] Add real-time validation
- [x] Implement export/import functionality

### 4.2 Studio

- [x] Create web application for Ferrum
- [ ] Implement user authentication
- [ ] Add project management
- [ ] Create dashboard for projects

### 4.3 Collaboration Features

- [ ] Add real-time collaboration
- [ ] Implement version control integration
- [ ] Add commenting and feedback system
- [ ] Create sharing functionality

## 📅 Timeline

- **Phase 1**: Q2-Q3 2025
- **Phase 2 + 2.5**: Q3-Q4 2025
- **Phase 3**: Q1-Q2 2026
- **Phase 4**: Q3-Q4 2026

## 🔄 Immediate Next Steps

1. Finalize testing efforts
   - Parser and validator tests complete
   - Add generator tests
   - Integration tests for CLI
   - End-to-end tests for full workflow

2. Continue improving error handling
   - Expand validation messages
   - Add recovery mechanisms for common errors

3. Implement WASP-inspired `ferrum init --ai` CLI flow
   - Connect to Python prompt service
   - Output `grafo.yaml` with modules
   - Trigger compilation to full project

## 🤝 Contribution Guidelines

We welcome contributions to Ferrum! Here's how you can help:

1. **Code**: Implement features, fix bugs, improve performance
2. **Templates**: Create new templates for different frameworks
3. **Documentation**: Improve docs, write tutorials, create examples
4. **Testing**: Write tests, report bugs, suggest improvements

Please follow our coding standards and submit PRs with clear descriptions.

## 📚 Resources

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Rust Book](https://doc.rust-lang.org/book/)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tera Templates](https://tera.netlify.app/)
- [Wasp](https://wasp-lang.dev/)
