# Graph Components

This directory contains React Flow components for rendering and editing architecture graphs.

## Node semantics

- **module** – container node that groups related use cases and adapters. Modules can be expanded or collapsed.
- **use case** – represents a core application behaviour.
- **adapter** – describes infrastructure or external interface components.
- **domain entity** – domain model element.

Nodes flagged by validation results adopt a red "violation" style and expose the violation message as a tooltip.

## Hierarchical grouping

Child nodes declare a `moduleId` (or `parentId`) in their metadata. The editor uses React Flow's `parentNode` feature so that use cases and adapters are nested inside their owning modules. Clicking a module toggles its collapsed state, hiding or revealing its children and any attached edges.

## Edges

Edge colour reflects the semantic relationship:

- `dependsOnModule` – indigo
- `usesAdapter` – orange
- other types – matrix green

Edges with violations turn red and surface the validation message on hover.

## Validation integration

The editor fetches validation results via `useValidationResults` and marks offending nodes and edges. Offending nodes receive a red border and warning icon, while edges become red with a tooltip describing the violation.
