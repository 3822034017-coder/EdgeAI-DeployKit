#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/root/edge-ai-deploy-kit}"
cd "$ROOT"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

edgeai convert \
  --framework onnx \
  --source-model models/zoo/mobilenetv2/model.onnx \
  --package mobilenetv2_convert_local \
  --overwrite

edgeai analyze --package outputs/packages/mobilenetv2_convert_local
edgeai prepare-input --package outputs/packages/mobilenetv2_convert_local --input photo/cat.png
edgeai local-run --package outputs/packages/mobilenetv2_convert_local
edgeai report --package outputs/packages/mobilenetv2_convert_local

ls -lh outputs/packages/mobilenetv2_convert_local/model.onnx \
       outputs/packages/mobilenetv2_convert_local/convert_result.json \
       outputs/packages/mobilenetv2_convert_local/report.md
