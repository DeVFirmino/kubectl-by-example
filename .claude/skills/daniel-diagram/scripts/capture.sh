#!/usr/bin/env bash
# usage: capture.sh in.html out.png   — screenshots the rendered diagram at 2x with Chrome headless.
set -euo pipefail
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"
W=$(grep -o 'width="[0-9]*"' "$IN" | head -1 | tr -dc 0-9); H=$(grep -o 'height="[0-9]*"' "$IN" | head -1 | tr -dc 0-9)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; command -v google-chrome >/dev/null && CHROME=google-chrome
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size="${W},${H}" --virtual-time-budget=6000 --screenshot="$OUT" "file://$IN" >/dev/null 2>&1
echo "wrote $OUT (${W}x${H} @2x)"
