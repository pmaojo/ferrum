#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Ensure dependencies are installed
pip install -r requirements.txt

# Install PyInstaller if missing
if ! command -v pyinstaller >/dev/null 2>&1; then
    pip install pyinstaller
fi

TARGET_ARCH=${TARGET_ARCH:-}
EXTRA_ARGS=""
if [[ -n "$TARGET_ARCH" ]]; then
    EXTRA_ARGS="--target-arch $TARGET_ARCH"
fi

if [[ "$(uname)" == "Darwin" ]]; then
    # Produce a macOS .app bundle. Use --windowed so no console opens.
    pyinstaller --windowed $EXTRA_ARGS --name ai_service main.py
else
    pyinstaller --onefile $EXTRA_ARGS --name ai_service main.py
fi
