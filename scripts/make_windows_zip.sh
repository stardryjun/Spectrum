#!/usr/bin/env bash
# Zip the folder produced by `flet build windows` into a portable archive.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-1.0.0}"
mkdir -p "${ROOT}/release"

SRC="$(find "${ROOT}/build/windows" -iname 'Spectrum.exe' 2>/dev/null | head -n1 || true)"
if [[ -z "${SRC}" ]]; then
  echo "Spectrum.exe not found under build/windows" >&2
  exit 1
fi

DIR="$(dirname "${SRC}")"
(cd "${DIR}" && zip -r "${ROOT}/release/Spectrum-${VERSION}-windows.zip" .)
echo "Windows zip ready: ${ROOT}/release/Spectrum-${VERSION}-windows.zip"
