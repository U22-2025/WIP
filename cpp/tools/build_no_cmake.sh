#!/usr/bin/env bash
set -euo pipefail

# Simple non-CMake build for POSIX/MinGW
# - Detects clang++/g++
# - Builds CLI (wip_client_cli) and tests (wiplib_tests)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
INCLUDE_DIR="$ROOT_DIR/include"

mkdir -p "$BUILD_DIR"

detect_cxx() {
  if command -v clang++ >/dev/null 2>&1; then
    echo clang++
  elif command -v g++ >/dev/null 2>&1; then
    echo g++
  else
    echo "No C++ compiler found (clang++/g++)" >&2
    exit 1
  fi
}

CXX="${CXX:-$(detect_cxx)}"
CXXFLAGS="-std=c++20 -O2 -Wall -Wextra -I\"$INCLUDE_DIR\""
LDFLAGS=""

UNAME="$(uname -s 2>/dev/null || echo Unknown)"
case "$UNAME" in
  MINGW*|MSYS*|CYGWIN*)
    # MinGW needs Ws2_32 for WinSock
    LDFLAGS="$LDFLAGS -lws2_32"
    ;;
  *)
    # Linux/macOS: no extra libs needed for POSIX sockets
    ;;
esac

echo "Using compiler: $CXX"

# Sources
SRC_CODEC="$ROOT_DIR/src/proto/codec.cpp"
SRC_CLIENT="$ROOT_DIR/src/client/weather_client.cpp"
SRC_CLI="$ROOT_DIR/tools/wip_client_cli.cpp"
SRC_TEST="$ROOT_DIR/tests/test_codec.cpp"

OUT_CLI="$BUILD_DIR/wip_client_cli"
OUT_TEST="$BUILD_DIR/wiplib_tests"

echo "[1/2] Building CLI: $OUT_CLI"
"$CXX" $CXXFLAGS "$SRC_CODEC" "$SRC_CLIENT" "$SRC_CLI" -o "$OUT_CLI" $LDFLAGS

echo "[2/2] Building tests: $OUT_TEST"
"$CXX" $CXXFLAGS "$SRC_CODEC" "$SRC_TEST" -o "$OUT_TEST" $LDFLAGS

echo "Done. Binaries in: $BUILD_DIR"
echo "Run examples:"
echo "  $OUT_CLI --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature"
echo "  $OUT_TEST"

