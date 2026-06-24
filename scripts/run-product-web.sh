#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/product-ui"

API_PORT="${EDGEAI_API_PORT:-8000}"
UI_PORT="${EDGEAI_UI_PORT:-3000}"
UI_HOST="${EDGEAI_UI_HOST:-0.0.0.0}"

if [ -z "${NEXT_PUBLIC_API_BASE:-}" ]; then
  HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  export NEXT_PUBLIC_API_BASE="http://${HOST_IP:-127.0.0.1}:${API_PORT}"
fi

echo "[EdgeAI] Web UI: http://${UI_HOST}:${UI_PORT}"
echo "[EdgeAI] API base: ${NEXT_PUBLIC_API_BASE}"

if command -v corepack >/dev/null 2>&1; then
  corepack pnpm install --frozen-lockfile
  corepack pnpm dev --hostname "$UI_HOST" --port "$UI_PORT"
elif command -v pnpm >/dev/null 2>&1; then
  pnpm install --frozen-lockfile
  pnpm dev --hostname "$UI_HOST" --port "$UI_PORT"
else
  echo "[ERROR] pnpm/Corepack not found. Install Node.js 20+ or run scripts/install-linux.sh." >&2
  exit 1
fi
