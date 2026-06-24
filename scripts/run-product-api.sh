#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi
PY="${PYTHON_BIN:-python3}"
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
fi
"$PY" -m uvicorn backend.main:app --host 0.0.0.0 --port "${EDGEAI_API_PORT:-8000}"
