#!/bin/sh
set -eu

usage() {
  echo "Usage: sh install-notryn-linux.sh ARCHIVE [--state-source DIRECTORY] [--no-open]" >&2
  exit 2
}

test "$(uname -s)" = Linux || { echo "This installer is for Linux." >&2; exit 1; }
test "$(uname -m)" = x86_64 || { echo "This private alpha currently supports x86_64 Linux." >&2; exit 1; }
test "${1:-}" != "" || usage
ARCHIVE=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
shift
STATE_SOURCE=
OPEN=1
while test "$#" -gt 0; do
  case "$1" in
    --state-source) test "$#" -ge 2 || usage; STATE_SOURCE=$2; shift 2 ;;
    --no-open) OPEN=0; shift ;;
    *) usage ;;
  esac
done

test -f "$ARCHIVE" || { echo "Package not found: $ARCHIVE" >&2; exit 1; }
CHECKSUM="$ARCHIVE.sha256"
test -f "$CHECKSUM" || { echo "Missing checksum: $CHECKSUM" >&2; exit 1; }
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$CHECKSUM")")
if tar -tzf "$ARCHIVE" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "Unsafe package paths were refused." >&2
  exit 1
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/notryn-install.XXXXXX")
trap 'test ! -d "$TMP" || find "$TMP" -depth -delete' EXIT HUP INT TERM
tar -xzf "$ARCHIVE" -C "$TMP"
ROOT=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)
test -x "$ROOT/Notryn.AppImage" || { echo "The application shell is incomplete." >&2; exit 1; }
test -x "$ROOT/sidecar/notryn" || { echo "The local server is incomplete." >&2; exit 1; }
VERSION=$($ROOT/sidecar/notryn version)

INSTALL="$HOME/.local/lib/notryn"
BACKUPS="$HOME/.local/lib/.notryn-backups"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$BIN" "$APPS" "$ICONS" "$BACKUPS"
NEW="$HOME/.local/lib/.notryn-new-$$"
mkdir -p "$NEW"
cp -R "$ROOT/sidecar" "$NEW/sidecar"
cp "$ROOT/Notryn.AppImage" "$NEW/Notryn.AppImage"
chmod 755 "$NEW/Notryn.AppImage"
if test -d "$INSTALL"; then mv "$INSTALL" "$BACKUPS/notryn-$(date +%Y%m%d-%H%M%S)"; fi
mv "$NEW" "$INSTALL"

WRAPPER="$BIN/.notryn-new-$$"
cat > "$WRAPPER" <<EOF
#!/bin/sh
export NOTRYN_INSTALL_DIR="\$HOME/.local/lib/notryn"
exec "\$NOTRYN_INSTALL_DIR/sidecar/notryn" "\$@"
EOF
chmod 755 "$WRAPPER"
mv "$WRAPPER" "$BIN/notryn"
cp "$ROOT/notryn.svg" "$ICONS/notryn.svg"
cat > "$APPS/com.notryn.Notryn.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Notryn
Comment=Local-first Markdown workspace
Exec=env APPIMAGE_EXTRACT_AND_RUN=1 $INSTALL/Notryn.AppImage
Icon=notryn
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF
chmod 644 "$APPS/com.notryn.Notryn.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true

if test -n "$STATE_SOURCE"; then "$BIN/notryn" migrate-state --source "$STATE_SOURCE"; fi
echo "Notryn $VERSION installed for this user. No system files were changed."
echo "Your Brains are stored separately in ${XDG_DATA_HOME:-$HOME/.local/share}/notryn."
if test "$OPEN" -eq 1; then APPIMAGE_EXTRACT_AND_RUN=1 "$INSTALL/Notryn.AppImage" >/dev/null 2>&1 & fi
