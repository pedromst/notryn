#!/bin/sh
# Linux/macOS launcher. No package installation or changes to desktop settings.
set -eu
notryn_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$notryn_dir/server.py" --open "$@"
