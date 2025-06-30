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

---

## Fase 4 · Experiencia de desarrollo top-tier 🧑‍💻

🎯 Objetivo: entregar una experiencia comparable o superior a Wasp/Rails, orientada a velocidad, feedback y documentación.

- [ ] CLI avanzada:
  - [ ] `ferrum init` interactivo
  - [ ] `ferrum generate usecase CreatePost`
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


