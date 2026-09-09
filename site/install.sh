#!/bin/sh
# Notryn bootstrap. This file will be served over HTTPS after public approval.
set -eu
VERSION=0.2.0-beta.8
PRIVATE=0
OPEN=1
while test "$#" -gt 0; do
  case "$1" in
    --private) PRIVATE=1; shift ;;
    --no-open) OPEN=0; shift ;;
    --version) test "$#" -ge 2 || exit 2; VERSION=${2#v}; shift 2 ;;
    --help) echo 'Usage: sh install.sh [--private] [--version VERSION] [--no-open]'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
printf '%s\n' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$' || { echo 'Invalid version.' >&2; exit 2; }
test "$(id -u)" -ne 0 || { echo 'Run as your normal user, without sudo.' >&2; exit 1; }
case "$(uname -s)" in Linux) OS=linux ;; Darwin) OS=macos ;; *) echo 'Windows installer is not available yet.' >&2; exit 1 ;; esac
case "$(uname -m)" in x86_64|amd64) ARCH=x86_64 ;; arm64|aarch64) ARCH=arm64 ;; *) echo 'Unsupported architecture.' >&2; exit 1 ;; esac
test "$OS:$ARCH" != linux:arm64 || { echo 'This release supports Linux x86_64; Linux ARM is not yet available.' >&2; exit 1; }
if test "$PRIVATE" -eq 1; then
  command -v gh >/dev/null 2>&1 || { echo 'Install GitHub CLI from cli.github.com, then run gh auth login for private access.' >&2; exit 1; }
  gh auth status --hostname github.com >/dev/null 2>&1 || { echo 'Run gh auth login first.' >&2; exit 1; }
else
  command -v curl >/dev/null 2>&1 || { echo 'curl is required for public downloads.' >&2; exit 1; }
fi
WORK=$(mktemp -d "${TMPDIR:-/tmp}/notryn-setup.XXXXXX")
trap 'notryn_exit_code=$?; rm -rf "$WORK"; exit "$notryn_exit_code"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
NAME="notryn-setup-$OS-$ARCH"
printf '\nPreparing Notryn %s for %s %s\n\n' "$VERSION" "$OS" "$ARCH" >&2
echo 'Downloading installer...' >&2
if test "$PRIVATE" -eq 1; then
  EXPECTED=$(gh api --hostname github.com "repos/pedromst/notryn/releases/tags/v$VERSION" --jq ".assets[] | select(.name == \"$NAME\") | .digest")
  EXPECTED=${EXPECTED#sha256:}
  gh release download "v$VERSION" --repo github.com/pedromst/notryn --pattern "$NAME" --dir "$WORK"
else
  BASE="https://github.com/pedromst/notryn/releases/download/v$VERSION"
  if test -t 2 && test "${TERM:-dumb}" != dumb; then DOWNLOAD_PROGRESS=--progress-bar; else DOWNLOAD_PROGRESS=--silent; fi
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 --fail --location --show-error "$DOWNLOAD_PROGRESS" --max-time 600 "$BASE/$NAME" -o "$WORK/$NAME"
  echo 'Checking installer...' >&2
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 --fail --location --show-error --silent --max-time 60 "$BASE/$NAME.sha256" -o "$WORK/checksum"
  EXPECTED=$(awk 'NR == 1 {print $1}' "$WORK/checksum")
fi
printf '%s\n' "$EXPECTED" | grep -Eq '^[0-9a-f]{64}$' || { echo 'Missing or invalid installer checksum.' >&2; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$WORK/$NAME" | awk '{print $1}')
else
  ACTUAL=$(shasum -a 256 "$WORK/$NAME" | awk '{print $1}')
fi
test "$EXPECTED" = "$ACTUAL" || { echo 'Installer checksum mismatch. Nothing was installed.' >&2; exit 1; }
echo 'Installer verified. Starting setup...' >&2
chmod 700 "$WORK/$NAME"
set -- --version "$VERSION"
if test "$PRIVATE" -eq 1; then set -- "$@" --private; fi
if test "$OPEN" -eq 0; then set -- "$@" --no-open; fi
"$WORK/$NAME" "$@"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo 'To use notryn in this terminal:'
  echo '  export PATH="$HOME/.local/bin:$PATH"'
  echo 'Add that line to your shell profile for future terminals. No shell configuration was changed.' ;;
esac
