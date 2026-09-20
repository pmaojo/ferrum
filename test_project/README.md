# test_project

An AI-first full-stack application scaffolded with Ferrum.

## Getting Started

```bash
# Start the development environment
ferrum dev

# With graph database
ferrum dev --with-graph

# With AI/LLM service
ferrum dev --with-ai
# With authentication templates
ferrum init myapp --with-auth

# With job templates
ferrum init myapp --with-jobs
```

## Database Setup

```bash
diesel setup       # create database
diesel migration run
```

Run optional seeds:

```bash
psql $DATABASE_URL -f backend/seeds/usuarios.sql
```

## Project Structure

- `backend/`: Rust backend using Axum
- `frontend/`: React frontend with TypeScript
- `shared-models/`: Shared models between backend and frontend
- `templates/`: Templates for code generation
- `gen/`: YAML architecture files
- `data/`: Persistent data for Docker services
