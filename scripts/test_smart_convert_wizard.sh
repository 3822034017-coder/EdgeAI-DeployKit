#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

MODEL="${1:-models/zoo/mobilenetv2/model.onnx}"
PKG="${2:-smart_convert_test_local}"

edgeai convert \
  --framework auto \
  --source-model "$MODEL" \
  --package "$PKG" \
  --opset 11 \
  --overwrite

edgeai analyze --package "outputs/packages/$PKG"
