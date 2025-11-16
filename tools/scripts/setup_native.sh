#!/usr/bin/env bash
# Native Ferrum setup script for Ubuntu
# Installs dependencies, prepares the database, runs migrations
# and starts backend, frontend and AI services without Docker.

set -euo pipefail

check_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_postgres() {
  if ! check_cmd psql; then
    echo "Installing PostgreSQL..."
    sudo apt-get update && sudo apt-get install -y postgresql libpq-dev
  fi
}

install_diesel() {
  if ! check_cmd diesel; then
    echo "Installing Diesel CLI..."
    cargo install diesel_cli --no-default-features --features postgres
  fi
}

install_node() {
  if ! check_cmd node; then
    echo "Installing Node.js..."
    sudo apt-get update && sudo apt-get install -y nodejs npm
  fi
}

install_python_deps() {
  if ! check_cmd uvicorn; then
    echo "Installing Python dependencies..."
    python3 -m pip install --user -r ai/requirements.txt
  fi
}

start_postgres() {
  sudo service postgresql start
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='ferrum'" | grep -q 1 || \
    sudo -u postgres createdb ferrum
  sudo -u postgres psql -c "DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname='ferrum') THEN
      CREATE ROLE ferrum LOGIN PASSWORD 'password';
    END IF;
  END$$;"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ferrum TO ferrum;"
}

run_migrations() {
  export DATABASE_URL="postgres://ferrum:password@localhost/ferrum"
  cargo run -- migrate
}

start_backend() {
  cargo run --manifest-path backend/Cargo.toml &
}

start_frontend() {
  if [ -d frontend ]; then
    npm install --prefix frontend
    npm run dev --prefix frontend &
  elif [ -d frontend_leptos ]; then
    cargo leptos serve -- --host 0.0.0.0 &
  fi
}

start_ai() {
  ( cd ai && uvicorn main:app --reload --host 0.0.0.0 --port 8001 ) &
}

main() {
  install_postgres
  install_diesel
  install_node
  install_python_deps
  start_postgres
  run_migrations
  start_backend
  start_frontend
  start_ai
  echo "Services running. Press Ctrl+C to stop."
  trap 'kill $(jobs -p)' EXIT
  wait
}

main "$@"
