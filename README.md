# 📐 Ferrum — AI-first Scaffolding System

**Ferrum** is an AI-first scaffolding framework that generates full-stack code (Rust + React + TypeScript) based on a declarative `grafo.yaml` file.
It follows **Hexagonal Architecture** and **SOLID principles** to produce clean, modular, and scalable codebases.

---

## 🚀 Getting Started

### 🛠 Installation

```bash
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
```

Running `ferrum init` now creates a minimal Axum server and Vite
React frontend so you can `cd` into the new directory and start the
dev environment immediately. Use `--api-only` if you only need the
backend.

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
service. When using the **Studio** UI, set the environment variable
`VITE_AI_URL` to the base URL (default `http://localhost:8001`). A
dropdown allows choosing the backend at runtime.

### 🖥 Desktop Studio

Ferrum also provides a native desktop version of the Studio built with Bevy.
Start it with:

```bash
cargo run -p studio-desktop
```

The application automatically launches the Python backend, so you don't need
to run `make ai-dev` beforehand. See
[studio-desktop/README.md](studio-desktop/README.md) for details.

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
command above to let Ferrus ask the AI service for code based on your graph
context. If the answer is empty you'll be prompted for a short description of
`NODE_ID`. The information is sent back to the AI service and stored in Neo4j
for next time. See [docs/graph-rag.md](docs/graph-rag.md) for more details.

#### 9. Cross-compile the backend

```bash
ferrum build --target wasm32-unknown-unknown
```

Use the `--target` flag to pass any supported Rust target triple.

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


---

## 🐳 Docker Environment

Ferrum comes with a pre-configured Docker environment that includes:

| Service | Purpose |
|---------|----------|
| **backend** | Rust (Axum) server with hot reload |
| **frontend** | Vite + React frontend with shared types (omit with `--api-only`) |
| **db** | PostgreSQL database |
| **graphdb** (optional) | Neo4j for graph modeling |
| **llm** (optional) | Ollama for local AI inference |

The Docker environment is automatically set up when you initialize a new project and can be started with the `ferrum dev` command.

---

## 🧬 DSL Specification (`grafo.yaml`)

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
- `iot` → backend drivers and React hooks via `expose`
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
├── cli/            # CLI commands
├── compiler/       # Parser, AST and codegen
├── templates/      # Tera-based code templates
├── shared-models/  # Rust models exported to TypeScript
├── studio/         # Visual editor UI
├── templates/docker-compose.yml  # Docker template copied to new projects
├── Makefile
└── Cargo.toml
```

The compose file here is only a template. It gets copied into new projects and
is not meant to be run directly from this repository.

Generated projects live outside this repo, for example:

```bash
~/projects/my-crm-app/
├── backend/
├── frontend/
├── shared-models/
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
| *any*     | Frontend: TS types, Zod schemas, React hooks/components   |

### Plugin Framework & Services

Ferrum includes a lightweight plugin manager. Plugins can hook into
`ferrum init` or `ferrum compile` to customize the generated project.

Additional runtime utilities are provided under `ferrum-engine::services`,
including a basic GraphQL schema and a helper for sending SMTP emails.

Built-in plugins:

- `graphql` – adds a default GraphQL schema file.

- `auth-password` – scaffolds login, refresh tokens, `useSession` hook and handler.

- `auth` – injects authentication nodes into the DSL and scaffolds login resources.

- [cron](docs/plugins/cron.md) – adds an example scheduled job and cron support.

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
my-crm-app/shared-models/user.rs          # Rust model
my-crm-app/frontend/src/types/User.ts     # TypeScript model
my-crm-app/frontend/src/hooks/useUser.ts  # React data hook
my-crm-app/frontend/src/components/UserView.tsx # Auto-generated component
my-crm-app/frontend/src/schemas/userSchema.ts   # Zod validation schema
my-crm-app/backend/handlers/users.rs      # Axum HTTP handler
my-crm-app/backend/routes/users.rs        # Route definition
my-crm-app/backend/db/users.rs            # Adapter logic
my-crm-app/backend/ports.rs               # Port traits
```

---

## 🧠 Upcoming Features

* 🤖 Prompt-to-graph via RAG + OWL reasoning
* 📦 Pluggable template marketplace
* ⚙️ Additional framework targets (e.g. Tauri, Bun, etc.)
* 🧩 Visual graph-based editor (React Flow)
* 🛠 Modular plugin system (`ferrum add auth`, `ferrum add graphql`, ...)

---

> Ferrum is not just a scaffolder — it's an architectural compiler for modern full-stack systems, designed to evolve with AI-first engineering practices.

