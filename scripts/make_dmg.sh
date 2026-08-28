#!/usr/bin/env bash
# Wrap a macOS .app into a drag-to-Applications DMG.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARG1="${1:-}"
ARG2="${2:-}"

APP_SRC=""
VERSION="1.0.0"

# 智能识别参数：如果第一个参数是目录或以 .app 结尾，则是路径；否则作为版本号
if [[ -n "${ARG1}" ]]; then
  if [[ -d "${ARG1}" || "${ARG1}" == *.app ]]; then
    APP_SRC="${ARG1}"
    VERSION="${ARG2:-1.0.0}"
  else
    VERSION="${ARG1}"
    APP_SRC="${ARG2}"
  fi
fi

OUT_DIR="${ROOT}/release"
STAGE="${ROOT}/build/dmg-stage"
VOL="Spectrum"

# 如果未指定 app 路径或路径不存在，则递归自动查找
if [[ -z "${APP_SRC}" || ! -d "${APP_SRC}" ]]; then
  echo "Searching for .app bundle in ${ROOT}/build..."
  APP_SRC=$(find "${ROOT}/build" -name "Spectrum.app" -o -name "*.app" 2>/dev/null | grep -v "dmg-stage" | head -n 1 || true)
fi

if [[ -z "${APP_SRC}" || ! -d "${APP_SRC}" ]]; then
  echo "Error: .app bundle not found in build directory. Run: flet build macos" >&2
  exit 1
fi

echo "Using App: ${APP_SRC}"
echo "Building DMG Version: ${VERSION}"

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

# 转换为压缩只读镜像
hdiutil convert "${DMG_TMP}" -format UDZO -imagekey zlib-level=9 -o "${DMG_OUT}" >/dev/null
rm -f "${DMG_TMP}"
rm -rf "${STAGE}"

echo "DMG ready: ${DMG_OUT}"
ls -lh "${DMG_OUT}"