#!/usr/bin/env bash
# Install optional development dependencies for testing
set -euo pipefail

REPO_ROOT="$(dirname "$(dirname "$0")")"
REQUIREMENTS_FILE="$REPO_ROOT/requirements-dev.txt"

install_requirements() {
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        echo "Requirements file not found: $REQUIREMENTS_FILE" >&2
        exit 1
    fi

    echo "📦 Installing test dependencies from $REQUIREMENTS_FILE"
    pip install -r "$REQUIREMENTS_FILE"
}

main() {
    install_requirements
    echo "✅ Test environment ready"
}

main "$@"
