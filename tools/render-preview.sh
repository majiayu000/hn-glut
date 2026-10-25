#!/usr/bin/env bash
# Render tools/og.html to docs/social-preview.png (1280x640) with headless Chrome.
# Usage: tools/render-preview.sh [path-to-chrome]
set -euo pipefail
cd "$(dirname "$0")/.."
chrome="${1:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
port=8765
python3 -m http.server "$port" --bind 127.0.0.1 >/dev/null 2>&1 &
server=$!
trap 'kill "$server"' EXIT
sleep 1
"$chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=1280,640 \
  --virtual-time-budget=5000 --screenshot="$PWD/docs/social-preview.png" \
  "http://127.0.0.1:$port/tools/og.html"
echo "wrote docs/social-preview.png"
