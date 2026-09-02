#!/usr/bin/env bash
# usage: capture.sh in.html out.png   — screenshots the rendered page at 2x with Chrome headless and crops to content.
set -euo pipefail
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
W=$(grep -o 'width="[0-9]*"' "$IN" | head -1 | tr -dc 0-9 || true); H=$(grep -o 'height="[0-9]*"' "$IN" | head -1 | tr -dc 0-9 || true)
W=${W:-1400}; H=${H:-1400}
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; command -v google-chrome >/dev/null && CHROME=google-chrome
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size="${W},${H}" --virtual-time-budget=6000 --screenshot="$OUT" "file://$IN" >/dev/null 2>&1 || true
[ -s "$OUT" ] || { echo "capture failed: $OUT"; exit 1; }
python3 - "$OUT" <<'PY'
import sys
from PIL import Image, ImageChops
p=sys.argv[1]; im=Image.open(p).convert('RGB')
bg=Image.new('RGB',im.size,im.getpixel((2,2)))
box=ImageChops.difference(im,bg).getbbox()
if box:
    pad=48; x0,y0,x1,y1=box
    im.crop((max(0,x0-pad),max(0,y0-pad),min(im.width,x1+pad),min(im.height,y1+pad))).save(p)
print('wrote',p,Image.open(p).size)
PY
