#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(PYTHONPATH="$ROOT" python3 -c 'from notryn_version import VERSION; print(VERSION)')
BUILD="$ROOT/.build/macos"
OUTPUT="$ROOT/dist"
VENV="$ROOT/.build/packaging-venv"

test "$(uname -s)" = Darwin || { echo "Build this package on macOS." >&2; exit 1; }
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$ROOT/packaging/build-requirements.txt"
mkdir -p "$BUILD" "$OUTPUT"
sips -s format png "$ROOT/web/favicon.svg" --out "$BUILD/icon.png" >/dev/null
sips -z 1024 1024 "$BUILD/icon.png" --out "$BUILD/icon-1024.png" >/dev/null
ICONSET="$BUILD/Notryn.iconset"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
  sips -z "$SIZE" "$SIZE" "$BUILD/icon-1024.png" --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
  DOUBLE=$((SIZE * 2))
  sips -z "$DOUBLE" "$DOUBLE" "$BUILD/icon-1024.png" --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$BUILD/Notryn.icns"
"$VENV/bin/pyinstaller" --noconfirm --clean --distpath "$BUILD/sidecar" --workpath "$BUILD/work" "$ROOT/packaging/macos/Notryn.spec"
"$BUILD/sidecar/notryn/notryn" version | grep -Fx "$VERSION"
NOTRYN_SIDECAR_DIR="$BUILD/sidecar/notryn" NOTRYN_ELECTRON_OUTPUT="$BUILD/electron" "$ROOT/node_modules/.bin/electron-builder" --config "$ROOT/desktop/electron-builder.cjs" --mac dir --x64 --publish never
APP="$BUILD/electron/mac/Notryn.app"
test -x "$APP/Contents/MacOS/Notryn"
test -x "$APP/Contents/Resources/notryn/notryn"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
"$APP/Contents/Resources/notryn/notryn" version | grep -Fx "$VERSION"
ARCHIVE="$OUTPUT/Notryn-$VERSION-macos-x86_64.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ARCHIVE"
(cd "$OUTPUT" && shasum -a 256 "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")
cp "$ROOT/packaging/macos/install-alpha.sh" "$OUTPUT/install-notryn-macos.sh"
echo "$ARCHIVE"
