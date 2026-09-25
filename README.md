# 📐 Ferrum — AI-first Scaffolding System

**Ferrum** is an AI-first scaffolding framework that generates full-stack code (Rust + React + TypeScript) based on a declarative `grafo.yaml` file.
It follows **Hexagonal Architecture** and **SOLID principles** to produce clean, modular, and scalable codebases.

---

## 🚀 Getting Started

### 🛠 Installation

Ferrum builds with the stable Rust toolchain. Install it with:

```bash
rustup toolchain install stable
cargo install --path .
cargo install typeshare-cli
```

### ⚙️ Usage

#### 1. Initialize a new project

```bash
# Create a basic project
ferrum init my-project

# With graph database support
ferrum init my-project --with-graph

# With PostgreSQL setup
ferrum init my-project --with-db

# With AI/LLM integration
ferrum init my-project --with-ai

# API-only backend (skip frontend)
ferrum init my-project --api-only

# Choose the frontend: react (default) or egui (native desktop).
# NOTE: leptos-csr / leptos-ssr are accepted by the flag but not implemented —
# no templates ship for them, so they currently produce an empty frontend.
ferrum init my-project --frontend egui

# Skip starter templates
ferrum init my-project --nostarter
```

Running `ferrum init` now creates a minimal Axum server and frontend
into the new directory and start the dev environment immediately. Use
`--api-only` if you only need the backend.

#### 2. Start the development environment

```bash
# Start basic services (backend, frontend, database)
ferrum dev

# With graph database
ferrum dev --with-graph

# With AI/LLM service
ferrum dev --with-ai
```

#### 3. Compile a YAML architecture graph

```bash
ferrum compile gen/users.yaml
```

The compile command automatically runs `typeshare` to export any
shared Rust models into TypeScript types.
It will also format the generated Rust and TypeScript code using
`cargo fmt` and `prettier` when those tools are available.

#### 4. Generate architecture from a natural prompt

```bash
ferrum prompt "CRUD for user"
```

The prompt command relies on a running AI service. You can start the
service manually with:

```bash
make ai-dev
```

By default it uses OpenAI, but you can select another backend (e.g.
`local` or `anthropic`) by hitting the `/generate-yaml` endpoint of the
service. The **desktop studio** starts the Python backend automatically,
so no extra environment variables are needed. A dropdown allows choosing
the AI provider at runtime.

> **Note**
> The Python dependencies for this service are pinned in
> `ai/requirements.txt`. Keep that file and the Dockerfile in sync when
> upgrading packages to avoid version mismatches.

### 🖥 Desktop Studio

There is no Bevy desktop application any more — the `studio-desktop` crate has
been removed and the web studio below is the only graphical front end.

### 🌐 Web Studio (Semantic Code Graph)

The visual editor lives in `packages/semantic_gui`: a React + Vite app that
renders your architecture as an editable graph and talks to the same
`/graph-rag` and `/ai-team` endpoints, sharing the typed models defined under
`ferrum-shared-models`.

Run it from the repository root:

```bash
make studio-install          # npm install --legacy-peer-deps
cp packages/semantic_gui/.env.example packages/semantic_gui/.env
# edit DATABASE_URL, then push the schema and seed:
cd packages/semantic_gui && npx drizzle-kit push --force && npm run db:seed
cd ../.. && make studio      # http://127.0.0.1:3000
```

The server validates `GROQ_API_KEY`, `SESSION_SECRET` and `DATABASE_URL` at
boot and refuses to start without them. `make studio-db` brings up the bundled
Postgres, which publishes host port 5432 — change the mapping if that port is
already taken.

Or run the containerized stack instead of local processes:

```bash
docker compose -f packages/semantic_gui/docker-compose.yml up
```

The Studio serves the graph editor at `/`, a dashboard at `/dashboard`, the
template marketplace at `/templates`, PermaGraph at `/permagraph` and agent
management at `/agents`. API routes are mounted under `/api/v1` and are
JWT-gated (roles `owner` / `reader`).

Alternatively, run the native setup script on Ubuntu:

```bash
scripts/setup_native.sh
```

This installs dependencies, runs migrations and starts all services without Docker.

#### 5. Design a shared component from a prompt

```bash
ferrum component "Card with image, title and footer slot"
```

This command generates a YAML snippet under `gen/component.yaml` describing the
component props and slots. You can include it in your main `grafo.yaml`.

#### 6. Generate a usecase skeleton

```bash
ferrum generate-usecase CreatePost
```

This outputs a minimal YAML file like `gen/createpost_usecase.yaml` which you
can include in your architecture and then compile.

#### 7. Generate a usecase from a natural language description

```bash
ferrum usecase "crear post con título y cuerpo"
```

This produces a structured `usecase` YAML file ready to be compiled.

#### 8. Fill TODO markers with GraphRAG

```bash
ferrum fill-todos gen
```

Insert `// ⛳️ AI_FILL[task] --context NODE_ID` in your generated files and run the
command above to let Ferrum ask the AI service for code based on your graph
context. If the answer is empty you'll be prompted for a short description of
`NODE_ID`. The information is sent back to the AI service and stored in Neo4j
for next time. See [docs/graph-rag.md](docs/graph-rag.md) for more details.

#### 9. Cross-compile the backend

```bash
# WebAssembly
ferrum build --target wasm32-unknown-unknown

# Raspberry Pi
ferrum build --target rpi

# Cortex-M microcontrollers
ferrum build --target thumbv7em
```

Use the `--target` flag to pass any supported Rust target triple. Ferrum
automatically installs the required target with `rustup` when using the
`rpi` or `thumbv7em` aliases.

#### 10. Collaborate with the AI team

```bash
ferrum ai-team "How should I structure the payment module?"
```

This command sends your question to a coordinator agent that consults
backend, frontend and UX experts and prints their combined advice.

#### 11. Query the graph with GraphRAG

```bash
ferrum ai-team "What affects the node `saveOrder`?"
```

The experts now call `graph_rag` automatically and include a small YAML subgraph
with the dependencies related to your question. When your question is vague,
Ferrum uses Qdrant vector search to locate the most relevant node before
fetching its dependency context. See [docs/graph-rag.md](docs/graph-rag.md) for more details.

#### 12. Run the desktop studio

```bash
cargo run -p studio-desktop
```

#### 13. Deploy to production

```bash
# Fly.io
ferrum deploy fly

# Railway
ferrum deploy railway

# Render
ferrum deploy render
```

This command builds the backend and pushes the container image or code
to the selected provider. Make sure the corresponding CLI tool is
installed and you are authenticated.

### LLM configuration

Ferrum reads an optional `llm-config.yaml` file to decide which model to
use when running `ferrum prompt` or the AI service. Example:

```yaml
model: openai
openai:
  api_key: "your-openai-key"
ollama:
  endpoint: "http://localhost:1234/v1/chat/completions"
```

You can still override the model with the `MODEL` environment variable.

#### Environment variables

The AI service expects an `OPENAI_API_KEY` when using the OpenAI backend.
Create a `.env` file (see `.env.example`) and set your key:

```bash
OPENAI_API_KEY=sk-...
```

`docker-compose` automatically loads this variable so the AI service can
authenticate with OpenAI.


---

## 🐳 Docker Environment

Ferrum comes with a pre-configured Docker environment that includes:

| Service | Purpose |
|---------|----------|
| **backend** | Rust (Axum) server with hot reload |
| **db** | PostgreSQL database |
| **graphdb** (optional) | Neo4j for graph modeling |
| **llm** (optional) | Ollama for local AI inference |

The Docker environment is automatically set up when you initialize a new project and can be started with the `ferrum dev` command.

---

## 🧬 DSL Specification (`grafo.yaml`)
See [docs/dsl.md](docs/dsl.md) for a breakdown of all available sections.

### 📝 Example

```yaml
module: users
nodes:
  - id: getUser
    type: usecase
    input:
      - name: userId
        type: uuid
    output: User
    depends_on: [userRepository]

  - id: userRepository
    type: adapter
    implements: userReaderPort

  - id: userReaderPort
    type: port

forms:
  - name: LoginForm
    submitTo: loginUser
    fields:
      email: string
      password: string

validations:
  - name: emailIsValid
    appliesTo: users.registerUser.email
    rule: "email must match regex /@/"

resources:
  - name: cache
    type: redis

policies:
  - name: isAdmin
    guard: check_admin

iot:
  - name: blinkLed
    code: |
      use rppal::gpio::Gpio;
      pub fn blink_led() {
          let pin = Gpio::new().unwrap().get(17).unwrap().into_output();
          pin.set_high();
      }
```

### 🧠 Node Field Reference

| Field        | Type                                      | Required | Description                  |
| ------------ | ----------------------------------------- | -------- | ---------------------------- |
| `id`         | `string`                                  | ✅        | Unique node identifier       |
| `type`       | `usecase` / `adapter` / `port` / `entity` / `form` / `validation` / `upload` / `policy` / `resource` | ✅        | Architectural role           |
| `input`      | List of fields (`name`, `type`)           | ❌        | Input parameters             |
| `output`     | `string`                                  | ❌        | Output type name             |
| `depends_on` | `string[]`                                | ❌        | IDs of required dependencies |
| `implements` | `string`                                  | ❌        | ID of the port it implements |

---

### Extended DSL Sections

Ferrum's DSL supports high level declarations beyond modules. You can define:

- `queries` → generates Rust handlers and React hooks
- `mutations` → generates handlers and hooks (with optional auth)
- `routes` / `pages` → produces a `frontend/routes.tsx` file
- `auth-password` → scaffolds login form, refresh tokens and a `useSession` hook
- `auth-password` → scaffolds login form, refresh tokens and hook

- `jobs` → creates scheduled tasks in `backend/jobs/`
- `uploads` → file upload endpoint and React hook
- `resources` → integrate external services like APIs or queues
- `iot` → backend drivers and React hooks via `expose` ([spec](docs/iot-frontend.md#protocol-driver-and-simulate)).
Sample modules under `templates/backend/iot` show how to use `embedded-hal`, `rppal`, `rumqttc` and `ethercat-rs`. Enable them with:

```bash
cargo build -p backend --features hal,rppal,mqtt,ethercat
```
- `policies` → authorization guards reusable across routes
- standalone `entities`
- `forms` → declarative form specification
- `validations` → shared validation rules

These sections enable a Wasp-like workflow where most of the app can be
described in a single `grafo.yaml` file.

Standalone entities automatically generate Diesel models, schema entries and
migrations. Declaring an entity under `entities:` is enough to get a fully
typed Rust struct and the corresponding `diesel::table!` in `schema.rs`.

---

## 🧱 Framework Structure

```bash
ferrum/
├── apps/
│   ├── cli/             # the `ferrum` binary — every subcommand
│   ├── compiler/        # parser, AST, validators, code generation
│   ├── engine/          # plugin manager
│   ├── ferrum-service/  # runtime helpers (auth, logging, SSE)
│   └── shared-models/   # DSL types, exported to TS via typeshare
├── packages/
│   ├── ai/              # FastAPI agent team + GraphRAG
│   ├── graph/           # PermaGraph knowledge-graph framework
│   ├── mcp-server/      # MCP bridge
│   └── semantic_gui/    # Semantic Code Graph web studio
├── templates/           # Tera codegen templates + React starter files
├── gen/                 # example grafo.yaml
├── Makefile
└── Cargo.toml
```

The compose file here is only a template. It gets copied into new projects and
is not meant to be run directly from this repository.

Generated projects live outside this repo, for example:

```bash
~/projects/my-crm-app/
├── backend/
├── frontend/       # React + Vite + Tailwind + shadcn/ui
├── shared-models/
├── docs/
└── grafo.yaml
```

---

## 🔄 Output by Node Type

| Node Type | Files Generated                                           |
| --------- | --------------------------------------------------------- |
| `usecase` | `handlers/<mod>.rs`, `routes/<mod>.rs`                    |
| `adapter` | `db/<mod>.rs`, implementation of traits                   |
| `port`    | `ports.rs`                                                |
| `entity`  | `shared-models/*.rs`, auto-exported to TS via `typeshare` |
| `form`    | `frontend/src/forms/<Name>.tsx` (shadcn inputs + Zod)     |
| *any*     | Frontend: TS types, Zod schemas, React hooks/components   |

The generated React app is **Vite + Tailwind CSS + shadcn/ui**: components render
as cards and tables rather than raw JSON, forms use styled inputs, and theming is
driven by the CSS variables in `frontend/src/index.css`. Router output goes to
`frontend/src/routes.tsx` with placeholder pages under `frontend/src/pages/`.

### Plugin Framework & Services

Ferrum includes a lightweight plugin manager. Plugins can hook into
`ferrum init` or `ferrum compile` to customize the generated project.
See [docs/plugins/README.md](docs/plugins/README.md) for
instructions on writing your own plugins.

Additional runtime utilities are provided under `ferrum-engine::services`,
including a basic GraphQL schema and a helper for sending SMTP emails.

Built-in plugins:

- `graphql` – adds a default GraphQL schema file.

- `auth-password` – scaffolds login, refresh tokens, `useSession` hook and handler.

- `auth` – injects authentication nodes into the DSL and scaffolds login resources.

- [cron](docs/plugins/cron.md) – adds an example scheduled job and cron support.

- [iot-basic](docs/plugins/iot-basic.md) – scaffolds temperature/humidity drivers and a telemetry resource.

Plugins can also mutate the parsed DSL before code generation. Each plugin may
implement:

```rust
fn extend_dsl(&self, dsl: &mut FerrumDsl) -> anyhow::Result<()>
```

This hook receives the `FerrumDsl` AST and can push additional jobs, routes,
resources or policies. For example enabling the cron plugin:

```yaml
app:
  name: demo
features: [cron]
```

To enable the built-in MQTT helpers, declare:

```yaml
app:
  name: demo
  features: [mqtt]
```

results in the DSL containing:

```yaml
jobs:
  - name: example_job
    schedule: "0 0 * * *"
    handler: example_job
```

Use this mechanism to avoid repeating common structures and inject defaults
automatically.

---

## 📦 Output Example

```bash
my-crm-app/shared-models/user.rs                    # Rust model
my-crm-app/frontend/src/types/User.ts               # TypeScript model
my-crm-app/frontend/src/hooks/useUser.ts            # React data hook (TanStack Query)
my-crm-app/frontend/src/components/UserView.tsx     # Card/table view component
my-crm-app/frontend/src/schemas/user.ts             # Zod validation schema
my-crm-app/frontend/src/routes.tsx                  # react-router route objects
my-crm-app/frontend/src/pages/HomePage.tsx          # Page placeholder (never overwritten)
my-crm-app/frontend/src/components/ui/*.tsx         # shadcn/ui primitives
my-crm-app/backend/handlers/users.rs                # Axum HTTP handler
my-crm-app/backend/routes/users.rs                  # Route definition
my-crm-app/backend/db/users.rs                      # Adapter logic
my-crm-app/backend/ports.rs                         # Port traits
```

---

## 🧠 Upcoming Features

* 🤖 Prompt-to-graph via RAG + OWL reasoning
* 📦 Pluggable template marketplace
* ⚙️ Additional framework targets (e.g. Tauri, Bun, etc.)
* 🧩 Visual graph-based editor — shipped in `packages/semantic_gui` (see [Web Studio](#-web-studio-semantic-code-graph))
* 🛠 Modular plugin system (`ferrum add auth`, `ferrum add graphql`, ...)
* ⚙️ Implement the `leptos-csr` / `leptos-ssr` frontend targets (flag exists, templates do not)

---

> Ferrum is not just a scaffolder — it's an architectural compiler for modern full-stack systems, designed to evolve with AI-first engineering practices.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

