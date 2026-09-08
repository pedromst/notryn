#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=$(PYTHONPATH="$ROOT" python3 -c 'from notryn_version import VERSION; print(VERSION)')
BUILD="$ROOT/.build/linux"
OUTPUT="$ROOT/dist"
VENV="$ROOT/.build/packaging-venv"

test "$(uname -s)" = Linux || { echo "Build this package on Linux." >&2; exit 1; }
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$ROOT/packaging/build-requirements.txt"
mkdir -p "$BUILD" "$OUTPUT"
"$VENV/bin/pyinstaller" --noconfirm --clean --distpath "$BUILD/sidecar" --workpath "$BUILD/work" "$ROOT/packaging/linux/Notryn.spec"
"$BUILD/sidecar/notryn/notryn" version | grep -Fx "$VERSION"
NOTRYN_SIDECAR_DIR="$BUILD/sidecar/notryn" NOTRYN_ELECTRON_OUTPUT="$BUILD/electron" "$ROOT/node_modules/.bin/electron-builder" --config "$ROOT/desktop/electron-builder.cjs" --linux AppImage --x64 --publish never

STAGE="$BUILD/Notryn-$VERSION"
python3 - "$STAGE" <<'PY'
import shutil, sys
from pathlib import Path
path=Path(sys.argv[1])
if path.exists(): shutil.rmtree(path)
path.mkdir(parents=True)
PY
cp -R "$BUILD/sidecar/notryn" "$STAGE/sidecar"
cp "$BUILD/electron/Notryn-$VERSION-linux-x86_64.AppImage" "$STAGE/Notryn.AppImage"
chmod 755 "$STAGE/Notryn.AppImage"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$STAGE/"
cp "$ROOT/web/favicon.svg" "$STAGE/notryn.svg"
ARCHIVE="$OUTPUT/Notryn-$VERSION-linux-x86_64.tar.gz"
tar -C "$BUILD" -czf "$ARCHIVE" "Notryn-$VERSION"
(cd "$OUTPUT" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")
sh "$ROOT/packaging/build-setup.sh"
echo "$ARCHIVE"
