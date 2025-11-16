# Requirements Document

## Introduction

This document specifies the requirements for adding EGUI frontend generation support to Ferrum. EGUI is an immediate mode GUI library for Rust that enables native desktop applications. This feature will add EGUI as a first-class frontend option alongside React, replacing the incomplete Leptos implementation. EGUI will enable users to generate production-ready native desktop applications, while React remains available for web-based UIs. Both options will use the same declarative YAML approach.

## Glossary

- **Ferrum**: The AI-first scaffolding framework that generates full-stack code from declarative YAML
- **EGUI**: An immediate mode GUI library for Rust (eframe/egui)
- **Frontend Generator**: The component of Ferrum that produces UI code from DSL definitions
- **DSL**: Domain Specific Language - the YAML-based configuration format used by Ferrum
- **Compiler**: The Ferrum component that parses DSL and invokes generators
- **CLI**: Command Line Interface - the ferrum executable that users interact with
- **Template System**: Tera-based code generation templates used by Ferrum

## Requirements

### Requirement 1

**User Story:** As a developer, I want to initialize a Ferrum project with an EGUI frontend option, so that I can build native desktop applications with Rust

#### Acceptance Criteria

1. WHEN the developer executes `ferrum init my-project --frontend egui`, THE CLI SHALL create a project structure with an EGUI-based frontend
2. WHEN the developer executes `ferrum init my-project --frontend react`, THE CLI SHALL create a React-based frontend
3. WHEN the developer executes `ferrum init` in interactive mode, THE CLI SHALL present both "EGUI (native desktop)" and "React (web)" as equal options
4. THE CLI SHALL generate a valid Cargo workspace with an egui frontend crate
5. THE Frontend Generator SHALL create a main.rs file with eframe application setup
6. THE Frontend Generator SHALL include necessary dependencies in Cargo.toml (eframe, egui, serde, reqwest, tokio)

### Requirement 2

**User Story:** As a developer, I want Ferrum to generate EGUI components from my YAML entities, so that I can display and edit data in native UI widgets

#### Acceptance Criteria

1. WHEN an entity is defined in grafo.yaml, THE Frontend Generator SHALL create corresponding EGUI view modules
2. THE Frontend Generator SHALL generate form widgets for entity fields based on their types
3. WHEN a field type is string, THE Frontend Generator SHALL create a TextEdit widget
4. WHEN a field type is number, THE Frontend Generator SHALL create a DragValue widget
5. WHEN a field type is boolean, THE Frontend Generator SHALL create a Checkbox widget
6. THE Frontend Generator SHALL organize generated components in a logical module structure

### Requirement 3

**User Story:** As a developer, I want EGUI views to integrate with my backend API, so that my desktop application can perform CRUD operations

#### Acceptance Criteria

1. WHEN a usecase is defined with HTTP endpoints, THE Frontend Generator SHALL create API client code using reqwest
2. THE Frontend Generator SHALL generate async request handlers for each endpoint
3. THE Frontend Generator SHALL include error handling for network requests
4. THE Frontend Generator SHALL use shared Rust types from shared-models crate
5. WHEN the backend is running, THE EGUI Application SHALL successfully communicate with API endpoints

### Requirement 4

**User Story:** As a developer, I want to run my EGUI application in development mode, so that I can iterate quickly with hot reload

#### Acceptance Criteria

1. WHEN the developer executes `ferrum dev` with an EGUI frontend, THE CLI SHALL start the backend and EGUI application
2. THE CLI SHALL use cargo-watch for automatic recompilation when source files change
3. THE Development Environment SHALL display compilation errors in the terminal
4. THE CLI SHALL provide clear feedback about which services are running

### Requirement 5

**User Story:** As a developer, I want to compile my EGUI application for production, so that I can distribute native executables

#### Acceptance Criteria

1. WHEN the developer executes `ferrum build`, THE CLI SHALL compile the EGUI frontend as a release binary
2. THE CLI SHALL support cross-compilation targets via --target flag
3. THE Build Process SHALL produce a standalone executable in the target directory
4. THE CLI SHALL provide feedback about build progress and output location

### Requirement 6

**User Story:** As a developer, I want EGUI templates to follow Ferrum's architecture patterns, so that my code remains maintainable and consistent

#### Acceptance Criteria

1. THE Frontend Generator SHALL organize EGUI code following hexagonal architecture principles
2. THE Frontend Generator SHALL separate UI logic from business logic
3. THE Frontend Generator SHALL create reusable component modules
4. THE Generated Code SHALL include documentation comments
5. THE Generated Code SHALL follow Rust naming conventions and idioms

### Requirement 7

**User Story:** As a developer, I want to define routes and navigation in my YAML, so that EGUI generates a multi-view application

#### Acceptance Criteria

1. WHEN routes are defined in grafo.yaml, THE Frontend Generator SHALL create a navigation system
2. THE Frontend Generator SHALL generate an enum representing all application views
3. THE Frontend Generator SHALL create view switching logic in the main application loop
4. WHEN a route has authRequired: true, THE Frontend Generator SHALL include authentication checks
5. THE Navigation System SHALL maintain application state across view transitions
