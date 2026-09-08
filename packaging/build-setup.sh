#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
case "$(uname -s)" in Linux) OS=linux ;; Darwin) OS=macos ;; *) exit 1 ;; esac
ARCH=$(uname -m)
NAME="notryn-setup-$OS-$ARCH"
"$ROOT/.build/packaging-venv/bin/pyinstaller" --noconfirm --clean --onefile --name "$NAME" --distpath "$ROOT/dist" --workpath "$ROOT/.build/setup-work" --specpath "$ROOT/.build" "$ROOT/notryn_install.py"
if test "$OS" = macos; then codesign --force --sign - "$ROOT/dist/$NAME"; fi
(cd "$ROOT/dist" && if command -v sha256sum >/dev/null 2>&1; then sha256sum "$NAME"; else shasum -a 256 "$NAME"; fi) > "$ROOT/dist/$NAME.sha256"
cp "$ROOT/packaging/install.sh" "$ROOT/dist/install.sh"
