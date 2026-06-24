#!/usr/bin/env bash
set -e

unset LD_LIBRARY_PATH

source /opt/openeuler-aarch64/environment-setup-aarch64-openeuler-linux

cd /root/EdgeAI-DeployKit

edgeai generate --model outputs/model_int8.onnx --output outputs/infer_demo

cd outputs/infer_demo
rm -rf build-arm64
mkdir -p build-arm64
cd build-arm64

cmake .. \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_CXX_COMPILER="$(echo $CXX | awk '{print $1}')" \
  -DCMAKE_SYSROOT="$SDKTARGETSYSROOT" \
  -DCMAKE_CXX_FLAGS="--sysroot=$SDKTARGETSYSROOT" \
  -DCMAKE_EXE_LINKER_FLAGS="--sysroot=$SDKTARGETSYSROOT -Wl,--allow-shlib-undefined" \
  -DONNXRUNTIME_ROOT=/root/EdgeAI-DeployKit/third_party/onnxruntime-linux-aarch64-1.26.0

make -j4

file arm64_infer
readelf -d arm64_infer | grep NEEDED
