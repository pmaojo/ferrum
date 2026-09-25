.PHONY: build install run fmt clean
.PHONY: typeshare-project
.PHONY: ai-setup ai-dev ai-build
.PHONY: studio-install studio studio-db studio-db-stop

# ── Core ────────────────────────────────────────────────────────────────────
# The CLI binary lives in apps/cli, so every cargo invocation names the package:
# the workspace root is a library-only package and has no bin target.
build:
	cargo build -p ferrum-cli

install:
	cargo install --path apps/cli

# Compiles the bundled example into projects/example (gitignored) so generated
# output never lands in the repository root.
run:
	cargo run -p ferrum-cli -- compile gen/users.yaml --output projects/example

fmt:
	cargo fmt

clean:
	cargo clean

# Exports the shared Rust models of a generated project to TypeScript.
# Usage: make typeshare-project PROJECT=my-app
typeshare-project:
	typeshare --lang=typescript --output-folder projects/$(PROJECT)/frontend/src/types projects/$(PROJECT)/shared-models

# ── AI service (packages/ai) ────────────────────────────────────────────────
ai-setup:
	cd packages/ai && python -m pip install -r requirements.txt

ai-dev:
	cd packages/ai && uvicorn main:app --reload --host 0.0.0.0 --port 8001

ai-build:
	cd packages/ai && ./build_binary.sh

# ── Semantic Code Graph Studio (packages/semantic_gui) ──────────────────────
# `--legacy-peer-deps` is required because react-diff-viewer@3 declares a
# React <=16 peer while the Studio runs React 18.
studio-install:
	cd packages/semantic_gui && npm install --legacy-peer-deps

# Dev server (Express + Vite) on http://127.0.0.1:3000.
# Requires a .env in packages/semantic_gui — copy .env.example and set
# DATABASE_URL (plus GROQ_API_KEY and SESSION_SECRET, which are validated at
# boot even for purely visual work).
studio:
	cd packages/semantic_gui && npm run dev

# Postgres for the Studio. Publishes host port 5432, so free it first — or
# change the mapping in packages/semantic_gui/docker-compose.yml.
studio-db:
	docker compose -f packages/semantic_gui/docker-compose.yml up -d db

studio-db-stop:
	docker compose -f packages/semantic_gui/docker-compose.yml down
