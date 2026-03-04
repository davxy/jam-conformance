#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$HOME/.local/pip/fuzz-app"

echo "Creating virtual environment at $VENV_DIR"
python3 -m venv "$VENV_DIR"

echo "Installing dependencies"
"$VENV_DIR/bin/pip" install -r "$(dirname "$0")/requirements.txt"

echo "Done. Activate with: source $VENV_DIR/bin/activate"
