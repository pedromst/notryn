#!/bin/sh
# Linux/macOS launcher. No package installation or changes to desktop settings.
set -eu
neura_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$neura_dir/server.py" --open "$@"
