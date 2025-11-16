#!/usr/bin/env bash
# Generate HTML documentation using pdoc.

set -euo pipefail

REPO_ROOT="$(dirname "$(dirname "$0")")"
OUTPUT_DIR="$REPO_ROOT/docs"

mkdir -p "$OUTPUT_DIR"

cd "$REPO_ROOT"

echo "📚 Generating documentation in $OUTPUT_DIR"

pdoc --html -o "$OUTPUT_DIR" permagraph adapters domain application

echo "✅ Documentation available in $OUTPUT_DIR"
