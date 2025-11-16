#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
DEMO_DIR="$SCRIPT_DIR/demo-repos/laravel-hexagonal"
TEMPLATE="$SCRIPT_DIR/../../../templates/semantic_gui/laravel-hexagonal.json"

if [ ! -d "$DEMO_DIR" ]; then
  echo "Cloning example repository..."
  mkdir -p "$(dirname "$DEMO_DIR")"
  git clone https://github.com/fSchettino/ddd-hexagonal-architecture-laravel "$DEMO_DIR"
fi

if command -v jq >/dev/null 2>&1; then
  NEW_CMD=$(jq -r '.cli.operations.new.command' "$TEMPLATE" | sed 's/{name}/demo-app/')
  if command -v laravel >/dev/null 2>&1; then
    echo "Running template CLI: $NEW_CMD"
    (cd "$DEMO_DIR" && eval "$NEW_CMD")
  else
    echo "Laravel installer not found, skipping project generation"
  fi
else
  echo "jq not installed, skipping CLI extraction"
fi

if command -v php >/dev/null 2>&1; then
  echo "Starting PHP development server..."
  (cd "$DEMO_DIR" && php -S localhost:8000 -t public) &
  PID=$!
  echo "Laravel demo running at http://localhost:8000 (PID $PID)"
  wait $PID
else
  echo "PHP not installed. Please start your services manually."
fi
