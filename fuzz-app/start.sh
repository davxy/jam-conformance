#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$HOME/.local/pip/fuzz-app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR"
    echo "Run ./install.sh first"
    exit 1
fi

source "$VENV_DIR/bin/activate"
cd "$SCRIPT_DIR"
exec uvicorn main:app --host 0.0.0.0 --port 8000
