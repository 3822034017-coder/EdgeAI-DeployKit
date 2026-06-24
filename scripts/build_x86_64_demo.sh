#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

edgeai generate --model outputs/model_int8.onnx --output outputs/infer_demo

cd outputs/infer_demo
rm -rf build
mkdir -p build
cd build

cmake .. \
  -DONNXRUNTIME_ROOT=/root/EdgeAI-DeployKit/third_party/onnxruntime-linux-x64-1.26.0

make -j4

export LD_LIBRARY_PATH=/root/EdgeAI-DeployKit/third_party/onnxruntime-linux-x64-1.26.0/lib:${LD_LIBRARY_PATH:-}

file arm64_infer
./arm64_infer ../model_int8.onnx || ./arm64_infer
