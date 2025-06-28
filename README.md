# 📐 Ferrum — AI-first Scaffolding System

**Ferrum** is an AI-first scaffolding framework that generates full-stack code (Rust + React + TypeScript) based on a declarative `grafo.yaml` file.
It follows **Hexagonal Architecture** and **SOLID principles** to produce clean, modular, and scalable codebases.

---

## 🚀 Getting Started

### 🛠 Installation

```bash
cargo install --path .
```

### ⚙️ Usage

#### 1. Initialize a new project

```bash
# Create a basic project
ferrum init my-project

# With graph database support
ferrum init my-project --with-graph

# With AI/LLM integration
ferrum init my-project --with-ai
```

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

#### 4. Generate architecture from a natural prompt

```bash
ferrum prompt "CRUD for user"
```

---

## 🐳 Docker Environment

Ferrum comes with a pre-configured Docker environment that includes:

| Service | Purpose |
|---------|----------|
| **backend** | Rust (Axum) server with hot reload |
| **frontend** | Vite + React frontend with shared types |
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
```

### 🧠 Node Field Reference

| Field        | Type                                      | Required | Description                  |
| ------------ | ----------------------------------------- | -------- | ---------------------------- |
| `id`         | `string`                                  | ✅        | Unique node identifier       |
| `type`       | `usecase` / `adapter` / `port` / `entity` | ✅        | Architectural role           |
| `input`      | List of fields (`name`, `type`)           | ❌        | Input parameters             |
| `output`     | `string`                                  | ❌        | Output type name             |
| `depends_on` | `string[]`                                | ❌        | IDs of required dependencies |
| `implements` | `string`                                  | ❌        | ID of the port it implements |

---

## 🧱 Monorepo Project Structure

```bash
ferrum/
├── gen/                # YAML modules
│   └── users.yaml
├── cli/                # CLI: `ferrum compile`, `ferrum prompt`
├── compiler/           # Parser + AST + codegen
├── templates/          # Tera-based code templates
├── shared-models/      # Rust models for typeshare
├── backend/            # Axum-compatible Rust output
├── frontend/           # Vite + React + Zod generated code
└── Cargo.toml
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

---

## 📦 Output Example

```bash
shared-models/user.rs                # Rust model
frontend/src/types/User.ts          # TypeScript model
frontend/src/hooks/useUser.ts       # React data hook
frontend/src/components/UserView.tsx# Auto-generated component
frontend/src/schemas/userSchema.ts  # Zod validation schema
backend/handlers/users.rs           # Axum HTTP handler
backend/routes/users.rs             # Route definition
backend/db/users.rs                 # Adapter logic
backend/ports.rs                    # Port traits
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

