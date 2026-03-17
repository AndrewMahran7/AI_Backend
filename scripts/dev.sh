#!/usr/bin/env bash
# Development helper – start the backend with hot reload.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtualenv if it exists.
if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

export PYTHONPATH="."

echo "Starting development server …"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
