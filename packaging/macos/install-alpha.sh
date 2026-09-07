#!/bin/sh
set -eu

usage() {
  echo "Usage: sh install-notryn-macos.sh ARCHIVE [--state-source DIRECTORY] [--no-open]" >&2
  exit 2
}

test "$(uname -s)" = Darwin || { echo "This installer is for macOS." >&2; exit 1; }
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
(cd "$(dirname "$ARCHIVE")" && shasum -a 256 -c "$(basename "$CHECKSUM")")
if zipinfo -1 "$ARCHIVE" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "Unsafe package paths were refused." >&2
  exit 1
fi
TMP=$(mktemp -d "${TMPDIR:-/tmp}/notryn-install.XXXXXX")
trap 'test ! -d "$TMP" || find "$TMP" -depth -delete' EXIT HUP INT TERM
ditto -x -k "$ARCHIVE" "$TMP"
test -x "$TMP/Notryn.app/Contents/MacOS/Notryn" || { echo "The application shell is incomplete." >&2; exit 1; }
test -x "$TMP/Notryn.app/Contents/Resources/notryn/notryn" || { echo "The local server is incomplete." >&2; exit 1; }
codesign --verify --deep --strict "$TMP/Notryn.app"
VERSION=$($TMP/Notryn.app/Contents/Resources/notryn/notryn version)

mkdir -p "$HOME/Applications" "$HOME/Applications/.notryn-backups" "$HOME/.local/bin"
DEST="$HOME/Applications/Notryn.app"
NEW="$HOME/Applications/.Notryn-new-$$.app"
ditto "$TMP/Notryn.app" "$NEW"
if test -d "$DEST"; then mv "$DEST" "$HOME/Applications/.notryn-backups/Notryn-$(date +%Y%m%d-%H%M%S).app"; fi
mv "$NEW" "$DEST"
WRAPPER="$HOME/.local/bin/.notryn-new-$$"
cat > "$WRAPPER" <<EOF
#!/bin/sh
export NOTRYN_APP_PATH="\$HOME/Applications/Notryn.app"
exec "\$NOTRYN_APP_PATH/Contents/Resources/notryn/notryn" "\$@"
EOF
chmod 755 "$WRAPPER"
mv "$WRAPPER" "$HOME/.local/bin/notryn"
if test -n "$STATE_SOURCE"; then "$HOME/.local/bin/notryn" migrate-state --source "$STATE_SOURCE"; fi
echo "Notryn $VERSION installed for this user. No system files were changed."
echo "Your Brains are stored separately in $HOME/Library/Application Support/Notryn."
if test "$OPEN" -eq 1; then open "$DEST"; fi
