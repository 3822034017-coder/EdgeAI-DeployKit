#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  ROOT="$SCRIPT_DIR"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-"$ROOT/.venv"}"
WITH_TENSORFLOW=0
WITH_PYTORCH=0
WITH_ML=0
WITH_LLM=0
WITH_FRONTEND=1

usage() {
  cat <<'EOF'
Usage: scripts/install-macos.sh [options]

Options:
  --with-pytorch       Install PyTorch conversion dependencies.
  --with-tensorflow    Install TensorFlow/Keras conversion dependencies.
  --with-ml            Install sklearn/xgboost/lightgbm conversion dependencies.
  --with-llm           Install llama-cpp-python for GGUF chat inference.
  --no-frontend        Skip WebUI dependency install.
  --python PATH        Python executable to use. Default: python3.
  --venv PATH          Virtualenv directory. Default: .venv.
  -h, --help           Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-tensorflow) WITH_TENSORFLOW=1; shift ;;
    --with-pytorch) WITH_PYTORCH=1; shift ;;
    --with-ml) WITH_ML=1; shift ;;
    --with-llm) WITH_LLM=1; shift ;;
    --no-frontend) WITH_FRONTEND=0; shift ;;
    --python) PYTHON_BIN="${2:?missing python path}"; shift 2 ;;
    --venv) VENV_DIR="${2:?missing venv path}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERROR] unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

cd "$ROOT"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "[WARN] install-macos.sh is intended for macOS. Continuing anyway."
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] Python executable not found: $PYTHON_BIN" >&2
  echo "Install Python 3.10+ first. Recommended:" >&2
  echo "  brew install python@3.12" >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info[:2] >= (3, 9) else 1)
PY
then
  echo "[ERROR] Python 3.9+ is required. Python 3.10-3.12 is recommended." >&2
  exit 1
fi

echo "[EdgeAI] project root: $ROOT"
echo "[EdgeAI] python: $("$PYTHON_BIN" -c 'import sys; print(sys.executable + " " + sys.version.split()[0])')"

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[pdf]"

if [ "$WITH_PYTORCH" -eq 1 ]; then
  python -m pip install torch torchvision
else
  echo "[EdgeAI] PyTorch conversion deps skipped. Use --with-pytorch to enable .pt/.pth conversion."
fi

if [ "$WITH_TENSORFLOW" -eq 1 ]; then
  python -m pip install tensorflow tf2onnx h5py
else
  echo "[EdgeAI] TensorFlow conversion deps skipped. Use --with-tensorflow to enable .h5/.keras/SavedModel conversion."
fi

if [ "$WITH_ML" -eq 1 ]; then
  python -m pip install ".[traditional-ml]"
else
  echo "[EdgeAI] Traditional ML deps skipped. Use --with-ml to enable sklearn/xgboost/lightgbm conversion."
fi

if [ "$WITH_LLM" -eq 1 ]; then
  python -m pip install ".[llm]"
else
  echo "[EdgeAI] LLM runtime deps skipped. Use --with-llm or install llama.cpp to enable GGUF chat."
fi

if [ "$WITH_FRONTEND" -eq 1 ]; then
  if command -v corepack >/dev/null 2>&1; then
    corepack enable || true
    (cd product-ui && corepack pnpm install --frozen-lockfile)
  elif command -v pnpm >/dev/null 2>&1; then
    (cd product-ui && pnpm install --frozen-lockfile)
  else
    echo "[WARN] pnpm/Corepack not found. Install Node.js 20+ first. Recommended:"
    echo "       brew install node"
    echo "       corepack enable"
    echo "       cd product-ui && corepack pnpm install --frozen-lockfile"
  fi
fi

mkdir -p inputs/models inputs/images outputs/packages outputs/logs outputs/pids reports

cat <<EOF

[EdgeAI] macOS install complete.

Start both services:
  ./start-macos.sh

Stop services:
  ./start-macos.sh stop

Optional model adapter installs:
  ./install-macos.sh --with-pytorch
  ./install-macos.sh --with-tensorflow
EOF
