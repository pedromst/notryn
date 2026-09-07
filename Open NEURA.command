#!/bin/zsh
cd -- "${0:A:h}"
if /usr/bin/curl --silent --fail http://127.0.0.1:4783/api/voice >/dev/null; then
  /usr/bin/open http://127.0.0.1:4783
  exit 0
fi
(sleep 2; /usr/bin/open http://127.0.0.1:4783) &
exec python3 server.py
