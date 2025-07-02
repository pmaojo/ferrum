# Ferrus · Plan de evolución para superar a Wasp 🚀

Este plan detalla las fases de desarrollo necesarias para convertir a Ferrus en el framework full-stack más potente del ecosistema Rust/React, superando a Wasp tanto en experiencia de desarrollo como en arquitectura, extensibilidad y automatización.

---

## Fase 1 · Consolidación base (actual)

🎯 Objetivo: sentar una base sólida de scaffolding full-stack hexagonal con generación AI-aware y entorno DX dockerizado.

- [x] CLI `ferrum init`, `ferrum compile`, `ferrum dev`, `ferrum prompt`
- [x] Generación de backend en Rust (Axum) y frontend en React (Vite + TS)
- [x] Integración básica con PostgreSQL (Diesel) y Neo4j
- [x] Compartición de tipos con `typeshare`
- [x] Arquitectura hexagonal (entities, ports, adapters, usecases)
- [x] Hot reload en entorno Docker
- [x] Plantillas Tera editables (`templates/`)
- [x] Esqueleto de autenticación (`--with-auth`)
- [x] Comando `ferrum sync` para grafo en Neo4j

---

## Fase 2 · DSL enriquecido y AI productiva 🤖

🎯 Objetivo: ampliar la capacidad declarativa del YAML y permitir generación semántica completa desde IA.

### DSL

- [x] Añadir soporte para:
  - [x] `auth` `{ userEntity, methods }`
  - [x] `route` `{ path, screen, authRequired }`
  - [x] `job`, `mutation`, `query` declarativas
  - [x] `policy` o `guard` para autorización
  - [x] `resource` para definir integraciones externas (APIs, colas)

- [x] Validación del DSL con errores claros y sugerencias AI-powered
- [ ] Documentación del YAML enriquecido con ejemplos

### AI-first

- [x] `ferrum prompt` debe generar YAML completo desde instrucciones tipo:
  _"Quiero una app de tareas con login por Google y tareas compartidas entre usuarios"_
- [ ] Sugerencias de nombres, validaciones, comentarios en los módulos
- [x] Incluir `llm-config.yaml` para usar OpenAI u Ollama

---

## Fase 3 · Plugins, módulos y marketplace 🔌

🎯 Objetivo: crear un sistema extensible, inspirando un ecosistema colaborativo de módulos reutilizables.

- [x] Sistema de plugins:
  - [x] `onInit`, `onCompile`, `onEntity`, `onRoute` hooks
  - [x] Plugins pueden extender DSL (YAML) y añadir comandos CLI

- [x] Comando `ferrum add <plugin>`:
  - [x] `auth-password`
  - [x] `auth-oauth`
  - [x] `graphql`
  - [x] `stripe`
  - [x] `cms-notion`
  - [x] `jobs-cron`
  - [x] `realtime-sse`

- [x] Registry de plugins:
  - [x] Buscar y añadir desde GitHub o fuente remota (`ferrum add user/plugin-name`)
  - [ ] Documentar detalladamente el sistema de plugins y su carga dinámica
  - [ ] Añadir hooks de extensión posgeneración para facilitar integraciones

---

## Fase 4 · Experiencia de desarrollo top-tier 🧑‍💻

🎯 Objetivo: entregar una experiencia comparable o superior a Wasp/Rails, orientada a velocidad, feedback y documentación.

- [ ] CLI avanzada:
  - [ ] `ferrum init` interactivo
  - [x] `ferrum generate usecase CreatePost`
  - [x] `ferrum doctor`
  - [ ] `ferrum graph`
  - [x] `ferrum explain`

- [x] UI Studio (visual):
  - [x] Crear entidades, rutas y relaciones en un editor visual
  - [x] Exportar/importar YAML
  - [x] Mostrar rutas, casos de uso y flujo hexagonal

- [ ] Mejorar DX:
  - [ ] Recarga fuera de Docker (`cargo-watch`, `vite dev`)
  - [ ] Logs combinados en terminal
  - [ ] Test templates generados automáticamente (`*.test.ts`, `*_test.rs`)
  - [ ] Mensajes de error descriptivos y logging en todos los comandos
  - [ ] Opción `--dry-run` y barra de progreso en `ferrum fill-todos`
  - [ ] Formateo automático con `rustfmt` y linters tras la generación

- [ ] Deploy:
  - [ ] `ferrum build` para producción
  - [ ] `ferrum deploy fly` / `railway` / `render`
  - [ ] `Dockerfile` y `compose.prod.yaml` auto-generados

---

## Fase 5 · DevOps, i18n y polish ✨

🎯 Objetivo: completar el ciclo con internacionalización, validaciones, seguridad y calidad de producción.

- [ ] i18n:
  - [ ] Extracción automática de mensajes de YAML/plantillas
  - [ ] Generar `i18n.ts` y uso con `FormattedMessage`

- [ ] Validación:
  - [x] Validación declarativa con Zod generada desde Rust
  - [x] Hooks de validación en backend y frontend

- [ ] File uploads:
  - [x] Endpoint Axum + multipart handler
  - [x] React dropzone component

- [ ] Auth avanzada:
  - [x] OAuth con Google/GitHub via `ferrum add auth-oauth`
  - [ ] Refresh tokens y sesiones via JWT/Redis
  - [x] Roles y permisos en DSL
    - [x] Integración con `Role` extraído del JWT
    - [x] Hook `useCurrentUserRoles()` para evaluación real de policies
    - [x] Mostrar/ocultar NavItem o Button con `<PolicyGate policy="...">`
    - [x] Ruta `/api/policies/:name` que devuelva `bool` para tests de políticas

- [ ] Documentación:
  - [ ] Storybook generado desde DSL (`*.stories.tsx`)
  - [ ] Documentación por módulo (`docs/modules/user.md` generados)
  - [ ] Web de documentación pública (`ferrum docs`)

- [ ] Calidad de código y pruebas:
  - [ ] Cobertura de tests para generadores (jobs, forms, validaciones)
  - [ ] Tests de integración de `ferrum fill-todos` con servicio AI simulado
  - [ ] Refactorizar generadores para reutilizar lógica común
  - [ ] Modularizar el compilador en crates (parser, generadores, validaciones)
  - [ ] Usar motor de plantillas para separar código y vistas
  - [ ] Concurrencia y optimización de I/O en `fill-todos`
  - [ ] Abstraer la comunicación con el servicio de IA en un módulo configurable
  - [ ] Añadir docstrings y ejemplos en README/Wiki para uso de GraphRAG

---

## Fase 6 · Experimentos visionarios 🤯

🎯 Objetivo: ir más allá de Wasp, Rails y Blitz.  
Construir el *framework del futuro*, donde el grafo semántico + IA generen sistemas autónomos.

- [ ] `ferrum simulate`: simular flujo de datos entre módulos (end-to-end tracing)
- [ ] `ferrum explain`: IA explica módulo, ruta o grafo completo
- [ ] `ferrum plan`: IA sugiere qué crear a partir de funcionalidades deseadas
- [ ] `ferrum studio` colaborativo con exportación en tiempo real (WebRTC o CRDT)

---

## Leyenda de versiones

| Versión | Objetivo principal                            |
|---------|-----------------------------------------------|
| 0.5.0   | Scaffolding estable, generación AI y DSL base |
| 0.6.0   | Plugins, DSL extendido y deploy básico        |
| 0.7.0   | UI Studio + CLI avanzada                      |
| 0.8.0   | Auth completo + i18n + marketplace            |
| 0.9.0   | LLM-powered refactors y generación semántica  |
| 1.0.0   | Versión estable superior a Wasp 🏆             |

---

## Registro de sesiones

- 2025-06-30: Revisión de los últimos commits y corrección de configuraciones
  en `docker-compose.yml` y `ai/router.py`.
- 2025-06-30: Implementación inicial de extracción de mensajes i18n y generación
  automática de `i18n.ts`.

---

**"La arquitectura no debe escribirse... debe declararse, compilarse y entenderse."**  
— *Ferrus Manifesto, 2025*

### Session 2024-05-04
- Added initial cms-notion plugin implementation and tests.
 codex/mejorar-estructura-inicial-y-automatización
### Session 2025-06-30
- Added minimal backend and frontend skeleton to `ferrum init` and
  documented automatic typeshare execution during compil

### Session 2025-06-30
- Added i18n extraction command and generator.
### Session 2025-06-30
- Reviewed dev server proposal to run Cargo and Vite in parallel with hot reload.
- Planned automatic route generation from YAML and shared-models support.
- Discussed single command script for starting backend and frontend.


### Session 2025-06-30
- Implemented parallel dev server using cargo and vite with `ferrum dev`.
- Automatic route generation now outputs backend and frontend files.
- Added preliminary shared component model.

### Session 2025-06-30
- Reviewed grafo.yaml example; components section not recognized by parser.

### Session 2025-06-30
- Added components field to FerrumDsl for parsing component definitions.

### Session 2025-06-30
- Implemented SharedComponent generator producing TSX files and index exports.

### Session 2025-06-30
- Added ComponentDesignerAgent for generating component YAML via AI.
- New CLI command `ferrum component` and API endpoint `/generate-component`.

### Session 2025-06-30
- Implemented `ferrum generate-usecase` command to scaffold YAML for new usecases.
### Session 2025-06-30
- Added ferrum usecase command powered by AI to generate YAML.
### Session 2025-06-30
- Reviewed AST and Neo4j sync service for potential GraphRAG validation.
- Planned new validator using graph context and integration with `design_usecase`.
### Session 2025-06-30
- Implemented GraphRAG validator using Neo4j context and integrated with design_usecase. Added /validate/usecase endpoint.

### Session 2025-06-30
- Added `--api-only` flag to `ferrum init` for backend-only projects; dev and docker-compose skip frontend when used.
### Session 2025-06-30
- Added refresh token and session support via Redis for generated auth templates.
 
### Session 2025-07-01
- Added useSession hook and re

### Session 2025-07-03
- Added interactive mode to `ferrum init` using dialoguer.
- Introduced `ferrum graph` command to generate GraphViz DOT files.

### Session 2025-07-04
- Integrated initial GraphRAG TODO filler.
- Added CLI command `ferrum fill-todos` and AI service endpoint `/fill-todo`.

### Session 2025-07-05
- Updated plan with recommendations sobre calidad de código, arquitectura
  modular y mejoras de UX.


### Session 2025-07-06
- Documented GraphRAG usage and added docstrings for filler agent.

### Session 2025-07-07
- Added IoT code generator and cross-compilation command.

### Session 2025-07-08
- Documented IoT expose feature and added bullet in README.

### Session 2025-07-09
- Fixed AI service import error by ensuring router is imported correctly and adding `__init__.py`.
### Session 2025-07-01
- Fixed Tailwind build in Studio by using 'tailwindcss' PostCSS plugin.

### Session 2025-07-10
- Fixed invalid format string in compiler when generating React components.

### Session 2025-07-11
- Reconfigured Tailwind for Studio using @tailwindcss/postcss plugin and new globals.css.

### Session 2025-07-12
- Added dependency graph analysis using petgraph and new `ferrum analyze` CLI command.

### Session 2025-07-01
- Added layer classification and JSON analyzer output.
- Integrated structural lint button in Studio and /analyze API.

### Session 2025-07-15
- Added layer visualization with color-coded nodes in Studio.
- Bottleneck threshold configurable from UI and passed to CLI.
- Save action now triggers compile and automatic lint with alerts.

### Session 2025-07-16
- Added feature expansion for cron, realtime_sse and uploads in compiler.
- Updated tests accordingly.
### Session 2025-07-17
- Updated AI router to align with schemas and added route tests.

### Session 2025-07-18
- Introduced coordinator agent delegating to backend, frontend and UX experts.
- Added `/ai-team` route and `ferrum ai-team` CLI command using it.
- Documented workflow in README.
### Session 2025-07-19
- Introduced Toolset class and injected it into AI team agents for shared graph analysis and validation.
### Session 2025-07-20
- Added YAML stdin support for `ferrum ai-team`.
- Extended Toolset with refactor, AST and flow simulation helpers.
- Coordinator and ChatAgent now keep conversation history for multi-turn chats.
- Added AI Team tab in Studio with segmented role responses.

### Session 2025-07-21
- Integrated graph analysis into expert replies.
- Added Coach agent for pattern detection and tips.
- New UI actions: "Refactorizar YAML" and "Simular flujo".


### Session 2025-07-21
- Documented Stripe payments plugin.

### Session 2025-07-22
- Added `graph_rag` helper in Toolset returning YAML subgraphs from Neo4j.
- Experts now include graph context automatically using this method.
- Documented the feature in README.
 

### Session 2025-07-22
- Added Qdrant fuzzy search and expanded fetch_context with incoming relations.
- New /graph-rag endpoint and Studio widget to visualize retrieved subgraph.
### Session 2025-07-22
- Improved YAML validator to ensure parsed documents are dictionaries before processing.
- Added unit test covering invalid structures.
### Session 2025-07-23
- Extended fetch_context to include description and story fields from Neo4j.
- Updated filler to return enriched context and added tests.

### Session 2025-07-24
- Added GraphRAG documentation and linked it in README.

### Session 2025-07-25
- Deduplicated copy_if_missing and ensure_dep helpers by moving them to engine/src/plugins/utils.rs. Updated all plugins to import these shared functions.
### Session 2025-07-26
- Added unit tests for ensure_dep and copy_if_missing.
- Centralized ProjectPaths and file writing helpers under compiler/utils.


### Session 2025-07-02
- Added full-demo example demonstrating multiple plugins and GraphRAG flows.

### Session 2025-07-26
- Documented Cron plugin and linked it from README.

- Added GitHub workflow to run Rust and Python tests with dependency caching.

### Session 2025-07-26
- Added CLI flow command using AI toolset to simulate YAML execution.

### Session 2025-07-27
- Verified filler context enrichment with description and story fields.
- Added unit test ensuring fill_code forwards these fields to the LLM.

- Verified filler context enrichment with description and story fields.
- Added unit test ensuring fill_code forwards these fields to the LLM.


### Session 2025-07-27
- Added test for Toolset.graph_rag mocking fetch_context.

### Session 2025-07-28
- Improved `ferrum fill-todos` with interactive prompts when the filler service
  returns empty code.
- New `/node-info` API route stores the provided description or story in Neo4j.
- Updated docs and README to explain the new flow.

### Session 2025-07-29
- Created `studio-desktop` Bevy crate launching the Python backend before the app.
- Implemented minimal graph viewer calling `/graph-rag`.

### Session 2025-07-30
- Parsed GraphRAG YAML into nodes and edges for the desktop studio.
- Rendered nodes and edges using egui with tooltips and selection panel.
- Added AI Team query button and upgraded `bevy_egui` to 0.26.

### Session 2025-07-31
- Documented desktop studio in new README and linked it from the root README.
- Added Makefile target and compose service to run the desktop studio with `cargo run -p studio-desktop`.
- Documented the command in README and new `docs/studio-desktop.md` page.
- CI workflow now builds the `studio-desktop` crate.

### Session 2025-07-02
- Added viewport resource with zoom and pan.
- Updated graph viewer to use mouse wheel and drag controls.
- Documented controls in studio-desktop/README.md.

### Session 2025-07-03
- Implemented node position storage and dragging in the desktop viewer.
- Added context menu to edit calls, used_by, description and story.
- Persisted description and story via new `/node-info` API using `store_node_info`.
- Updated graph viewer to keep relationships in memory when saving or regenerating.

### Session 2025-07-04
- Added text field and **Regenerate** button to the desktop graph viewer.
- Reloading now fetches a fresh graph from the question and clears any selection.

### Session 2025-07-02
- Implemented `store_node_info` to persist node details via `/node-info`.
- Saving descriptions or stories now updates GraphData only after the request succeeds.
- Documented this persistence in `docs/graph-rag.md`.

### Session 2025-07-02
- Added API helpers for `/simulate/flow`, `/generate/component` and `/validate/yaml` in the desktop studio.
- Extended the node context menu with **Simulate**, **Generate** and **Validate** options showing results in a popup.
- Documented these new actions in the README.
- Added log viewer in desktop studio capturing backend logs.
- Forwarded Python and API logs to UI via LogBuffer.

### Session 2025-07-02
- Migrated studio-desktop API calls to async reqwest on a shared Tokio runtime.
- Spawned network requests on background threads and updated UI with a loading spinner.


### Session 2025-07-05
- Documented NodePositions resource initialization and purpose.

### Session 2025-07-06
- Refactored `graph_viewer` to use `NodePositions` for both nodes and edges.
- Removed the temporary positions map so edges react to dragging.
- Updated variable names and comments for clarity.

### Session 2025-07-07
- Added script `ai/build_binary.sh` to bundle the Python backend with PyInstaller.
- Updated Makefile with `ai-build` target and updated .PHONY list.
- Desktop studio now executes the bundled `ai_service` binary when present.

### Session 2025-07-08
- Added `--target-arch` and macOS bundle support in `ai/build_binary.sh`.
- CI workflow builds the AI binary and stores it as an artifact.
- AI service launch errors are now pushed to the desktop log buffer.
- Documented that the final desktop zip includes the bundled `ai_service`.

### Session 2025-07-09
- Documented IoT expose fields and linked the page from README.

### Session 2025-07-10
- Added optional `expose` field to IoT DSL models and updated tests.
### Session 2025-07-11
- Generated Axum handlers and React hooks for IoT expose entries.
- Added MQTT endpoint template and tests covering file creation.

### Session 2025-07-02
- Added protocol, driver and simulate fields to IoT models. Regenerated TypeScript types and updated tests.
### Session 2025-07-12
- Added GPIO, MQTT and EtherCAT helpers in compiler iotgen.
- Updated compile tests to verify protocol stubs are generated.

### Session 2025-07-13
- Added IoT sample modules using embedded-hal, rppal, rumqttc and ethercat-rs.
- Cargo template now includes optional features for these crates.
- Documented enabling them via cargo build.

