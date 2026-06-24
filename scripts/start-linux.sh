#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  ROOT="$SCRIPT_DIR"
fi
API_PORT="${EDGEAI_API_PORT:-8000}"
UI_PORT="${EDGEAI_UI_PORT:-3000}"
API_HOST="${EDGEAI_API_HOST:-127.0.0.1}"
UI_HOST="${EDGEAI_UI_HOST:-127.0.0.1}"
LAN=0
ACTION="start"

usage() {
  cat <<'EOF'
Usage: scripts/start-linux.sh [start|stop|status] [options]

Options:
  --lan               Listen on 0.0.0.0 and advertise the first LAN IP.
  --api-port PORT     Preferred FastAPI port. Default: 8000.
  --ui-port PORT      Preferred WebUI port. Default: 3000.
  --api-host HOST     FastAPI listen host. Default: 127.0.0.1.
  --ui-host HOST      WebUI listen host. Default: 127.0.0.1.
  -h, --help          Show help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    start|stop|status)
      ACTION="$1"; shift ;;
    --lan)
      LAN=1; API_HOST="0.0.0.0"; UI_HOST="0.0.0.0"; shift ;;
    --api-port)
      API_PORT="${2:?missing API port}"; shift 2 ;;
    --ui-port)
      UI_PORT="${2:?missing UI port}"; shift 2 ;;
    --api-host)
      API_HOST="${2:?missing API host}"; shift 2 ;;
    --ui-host)
      UI_HOST="${2:?missing UI host}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

LOG_DIR="$ROOT/outputs/logs"
PID_DIR="$ROOT/outputs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="${PYTHON_BIN:-python3}"
fi

port_in_use() {
  "$PY" - "$1" <<'PY'
import socket, sys
port = int(sys.argv[1])
sock = socket.socket()
sock.settimeout(0.2)
try:
    sock.connect(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
else:
    raise SystemExit(0)
finally:
    sock.close()
PY
}

next_free_port() {
  local port="$1"
  while port_in_use "$port"; do
    port=$((port + 1))
  done
  printf '%s\n' "$port"
}

lan_ip() {
  hostname -I 2>/dev/null | awk '{print $1}'
}

stop_pid() {
  local file="$1"
  if [ -f "$file" ]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$file"
  fi
}

kill_port() {
  local port="$1"
  if [ -z "$port" ]; then
    return
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
    return
  fi
  ss -ltnp 2>/dev/null | awk -v needle=":${port}" '$4 ~ needle {print $0}' \
    | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' \
    | sort -u \
    | while read -r pid; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
      done
}

status_pid() {
  local name="$1"
  local file="$2"
  if [ -f "$file" ]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "$name: running pid=$pid"
      return
    fi
  fi
  echo "$name: stopped"
}

if [ "$ACTION" = "stop" ]; then
  RECORDED_API_PORT="$(cat "$PID_DIR/api.port" 2>/dev/null || true)"
  RECORDED_UI_PORT="$(cat "$PID_DIR/webui.port" 2>/dev/null || true)"
  stop_pid "$PID_DIR/webui.pid"
  stop_pid "$PID_DIR/api.pid"
  kill_port "${RECORDED_UI_PORT:-$UI_PORT}"
  kill_port "${RECORDED_API_PORT:-$API_PORT}"
  rm -f "$PID_DIR/api.port" "$PID_DIR/webui.port"
  echo "[EdgeAI] stopped"
  exit 0
fi

if [ "$ACTION" = "status" ]; then
  status_pid "api" "$PID_DIR/api.pid"
  status_pid "webui" "$PID_DIR/webui.pid"
  exit 0
fi

cd "$ROOT"
API_PORT="$(next_free_port "$API_PORT")"
UI_PORT="$(next_free_port "$UI_PORT")"

if [ "$LAN" -eq 1 ]; then
  PUBLIC_HOST="$(lan_ip)"
  PUBLIC_HOST="${PUBLIC_HOST:-127.0.0.1}"
else
  PUBLIC_HOST="127.0.0.1"
fi

API_BASE="${NEXT_PUBLIC_API_BASE:-http://${PUBLIC_HOST}:${API_PORT}}"

echo "[EdgeAI] project root: $ROOT"
echo "[EdgeAI] API:  http://${PUBLIC_HOST}:${API_PORT}"
echo "[EdgeAI] UI:   http://${PUBLIC_HOST}:${UI_PORT}"
echo "[EdgeAI] logs: $LOG_DIR"

if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

nohup "$PY" -m uvicorn backend.main:app --host "$API_HOST" --port "$API_PORT" > "$LOG_DIR/api.log" 2>&1 &
echo $! > "$PID_DIR/api.pid"
echo "$API_PORT" > "$PID_DIR/api.port"

for _ in $(seq 1 30); do
  if "$PY" - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:${API_PORT}/api/health", timeout=1).read()
PY
  then
    break
  fi
  sleep 1
done

cd "$ROOT/product-ui"
export NEXT_PUBLIC_API_BASE="$API_BASE"
if command -v corepack >/dev/null 2>&1; then
  corepack pnpm install --frozen-lockfile >> "$LOG_DIR/ui.log" 2>&1
  nohup corepack pnpm dev --hostname "$UI_HOST" --port "$UI_PORT" >> "$LOG_DIR/ui.log" 2>&1 &
elif command -v pnpm >/dev/null 2>&1; then
  pnpm install --frozen-lockfile >> "$LOG_DIR/ui.log" 2>&1
  nohup pnpm dev --hostname "$UI_HOST" --port "$UI_PORT" >> "$LOG_DIR/ui.log" 2>&1 &
else
  echo "[ERROR] pnpm/Corepack not found. Install Node.js 20+ or run scripts/install-linux.sh." >&2
  exit 1
fi
echo $! > "$PID_DIR/webui.pid"
echo "$UI_PORT" > "$PID_DIR/webui.port"

echo "[EdgeAI] started"
echo "[EdgeAI] open: http://${PUBLIC_HOST}:${UI_PORT}/workspace"
