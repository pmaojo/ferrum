#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Ensure dependencies are installed
pip install -r requirements.txt

# Install PyInstaller if missing
if ! command -v pyinstaller >/dev/null 2>&1; then
    pip install pyinstaller
fi

pyinstaller --onefile --name ai_service main.py
