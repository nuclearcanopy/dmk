#!/usr/bin/env bash
# nxmk build script: HHKB Hybrid (ANSI, STM32L072) only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEYBOARD="hhkb"
MCU="stm32l072"
CLEAN=false
DEFINE=""
MODULES=""
BUILD_DIR="${SCRIPT_DIR}/build/hhkb-script"
RT_SELECTION=true

usage() {
    cat <<USAGE
Usage: ./build_all.sh [-c] [-d HHKB_HYBRID] [-m MODULE_DIRS] [--build-dir PATH]

  -c, --clean         clean build
  -d, --define DEF    comma-separated defines including HHKB_HYBRID
  -m, --modules MODS  extra user modules (semicolon-separated paths)
  --build-dir PATH    build directory (default: build/hhkb-script)
  --legacy-rt         leave RT selection features at their config defaults
  -h, --help          this help

Example: ./build_all.sh -b hhkb -d HHKB_HYBRID -c
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--clean) CLEAN=true; shift ;;
        -b|--keyboard)
            [[ "${2:-}" == hhkb ]] || { echo "nxmk only builds the hhkb keyboard" >&2; exit 1; }
            shift 2 ;;
        -d|--define) DEFINE="${2:?--define needs a value}"; shift 2 ;;
        -m|--modules|--module) MODULES="${2:?--modules needs a value}"; shift 2 ;;
        --legacy-rt) RT_SELECTION=false; shift ;;
        --build-dir)
            mkdir -p "${2:?--build-dir needs a directory}"
            BUILD_DIR="$(cd "$2" && pwd)"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ "$RT_SELECTION" == true ]]; then
    DEFINE="${DEFINE},HHKB_RT_KEYMASK=1"
fi

TARGET_NAME="nxmk_${KEYBOARD}_${MCU}"

if [[ "$CLEAN" == true ]]; then
    echo "=== Cleaning build directory ==="
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR"

echo "=== Initializing CMake ==="
CMAKE_ARGS=(-G "Unix Makefiles" -S "$SCRIPT_DIR" -B "$BUILD_DIR"
    -DKEYBOARD="${KEYBOARD}" -DKEYBOARD_DIR="${SCRIPT_DIR}/keyboards/${KEYBOARD}"
    -DMCU="${MCU}" -DDMK_PLATFORM_DIR= -DCMAKE_BUILD_TYPE="MinSizeRel"
    -DDEFINE="${DEFINE}")
[[ -n "$MODULES" ]] && CMAKE_ARGS+=(-DDMK_MODULES="${MODULES}")
cmake "${CMAKE_ARGS[@]}"

echo "=== Building ${TARGET_NAME} ==="
cmake --build "$BUILD_DIR" -j"$(nproc 2>/dev/null || echo 4)"

echo "=== Build successful: ${TARGET_NAME} ==="
echo "Binary: ${BUILD_DIR}/${TARGET_NAME}.bin"
