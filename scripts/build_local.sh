#!/usr/bin/env bash
# Build installers that this Mac can produce: macOS DMG and Android APK.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
VERSION="$(python3 -c "import tomllib,pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")"

if [[ ! -x "${ROOT}/.venv/bin/flet" ]]; then
  echo "Create a venv and install deps first:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

export PATH="${ROOT}/.venv/bin:${PATH}"
mkdir -p "${ROOT}/release"

echo "==> macOS (flet build → .app → DMG)"
# Prefer Flutter packaging. Needs network access to GitHub (python-build
# manifest + Flutter artifacts). If that is blocked, fall back to PyInstaller.
if flet build macos --yes --module-name main.py --product Spectrum --build-version "${VERSION}"; then
  bash "${ROOT}/scripts/make_dmg.sh" "" "${VERSION}"
else
  echo "flet build macos failed; trying flet pack (PyInstaller)..."
  flet pack main.py -y \
    -n Spectrum \
    -i assets/icon.png \
    --product-name Spectrum \
    --product-version "${VERSION}" \
    --file-version "${VERSION}" \
    --company-name Spectrum \
    --bundle-id com.spectrum.app \
    --distpath dist
  APP="$(find dist -name 'Spectrum.app' | head -n1)"
  bash "${ROOT}/scripts/make_dmg.sh" "${APP}" "${VERSION}"
fi

echo "==> Android APK"
flet build apk --yes --module-name main.py --product Spectrum --build-version "${VERSION}" || {
  echo "APK build failed (JDK 17 + Android SDK + GitHub access required)."
  echo "Push a v* tag and GitHub Actions will produce the APK."
}

# Copy APK if present
shopt -s nullglob
for apk in "${ROOT}"/build/apk/*.apk "${ROOT}"/build/flutter/build/app/outputs/flutter-apk/*.apk; do
  cp -f "${apk}" "${ROOT}/release/Spectrum-${VERSION}-android.apk"
  echo "APK ready: ${ROOT}/release/Spectrum-${VERSION}-android.apk"
  break
done

echo "Artifacts in ${ROOT}/release:"
ls -lh "${ROOT}/release" || true
