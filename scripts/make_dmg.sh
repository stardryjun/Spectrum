#!/usr/bin/env bash
# Wrap a macOS .app into a drag-to-Applications DMG.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_SRC="${1:-}"
VERSION="${2:-1.0.0}"
OUT_DIR="${ROOT}/release"
STAGE="${ROOT}/build/dmg-stage"
VOL="Spectrum"

if [[ -z "${APP_SRC}" ]]; then
  # flet build macos default locations
  for cand in \
    "${ROOT}/build/macos/Spectrum.app" \
    "${ROOT}/build/macos/spectrum.app" \
    "${ROOT}"/build/macos/*.app
  do
    if [[ -d "${cand}" ]]; then
      APP_SRC="${cand}"
      break
    fi
  done
fi

if [[ -z "${APP_SRC}" || ! -d "${APP_SRC}" ]]; then
  echo "Spectrum.app not found. Run: flet build macos" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}" "${STAGE}"
rm -rf "${STAGE:?}/"*
cp -R "${APP_SRC}" "${STAGE}/Spectrum.app"
ln -s /Applications "${STAGE}/Applications"

DMG_TMP="${OUT_DIR}/Spectrum-${VERSION}-macos-tmp.dmg"
DMG_OUT="${OUT_DIR}/Spectrum-${VERSION}-macos.dmg"
rm -f "${DMG_TMP}" "${DMG_OUT}"

hdiutil create \
  -volname "${VOL}" \
  -srcfolder "${STAGE}" \
  -ov -format UDRW \
  "${DMG_TMP}" >/dev/null

# Compact to a compressed, double-clickable image
hdiutil convert "${DMG_TMP}" -format UDZO -imagekey zlib-level=9 -o "${DMG_OUT}" >/dev/null
rm -f "${DMG_TMP}"
rm -rf "${STAGE}"

echo "DMG ready: ${DMG_OUT}"
ls -lh "${DMG_OUT}"
