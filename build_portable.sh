#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

mkdir -p bin

echo "[build] validating pixi environment"
pixi run mojo --version

echo "[build] running phonological seed validation"
pixi run mojo -I src/1_gateway tests/phonological_seed.mojo

echo "[build] emitting generic x86_64 object with SSE4.2 + AVX"
pixi run mojo build \
  -I src/1_gateway \
  -I src/2_execution \
  --target-triple x86_64-unknown-linux-gnu \
  --march=x86-64 \
  --target-features +sse4.2,+avx \
  --emit object \
  -o bin/logic_engine_portable.o \
  src/logic_engine_portable.mojo

echo "[build] emitting assembly for inspection"
pixi run mojo build \
  -I src/1_gateway \
  -I src/2_execution \
  --target-triple x86_64-unknown-linux-gnu \
  --march=x86-64 \
  --target-features +sse4.2,+avx \
  --emit asm \
  -o bin/logic_engine_portable.s \
  src/logic_engine_portable.mojo

echo "[build] note: cross-linked executables are not currently produced by mojo build."
echo "[build] use the emitted object/assembly from WSL with a target linker for final packaging."

