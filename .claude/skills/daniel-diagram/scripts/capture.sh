#!/usr/bin/env bash
# usage: capture.sh in.html out.png — screenshots the page at 2x with Chrome headless.
# A diagram rendered for a preset (data-exact) keeps its exact canvas, so 660px becomes 1320px and
# shows 1:1 in the article column; anything else is cropped to content. Fails if the fonts fell back.
# CHROME=/path/to/chrome overrides the browser.
set -euo pipefail
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
W=$(grep -o 'width="[0-9]*"' "$IN" | head -1 | tr -dc 0-9 || true); H=$(grep -o 'height="[0-9]*"' "$IN" | head -1 | tr -dc 0-9 || true)
W=${W:-1400}; H=${H:-1400}
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
[ -x "$CHROME" ] || CHROME=$(command -v google-chrome || command -v chromium || true)
[ -n "$CHROME" ] || { echo "no Chrome found - set CHROME=/path/to/chrome"; exit 1; }
if grep -q 'data-drawn' "$IN"; then            # diagram pages report how drawing went; no report means the script never ran
  DOM=$("$CHROME" --headless=new --disable-gpu --virtual-time-budget=6000 --dump-dom "file://$IN" 2>/dev/null || true)
  case "$DOM" in
    *'data-drawn="ok"'*) ;;
    *'data-drawn="font-fallback"'*) echo "fonts did not load (offline?) - not capturing $OUT"; exit 1 ;;
    *'data-drawn="render-error"'*) echo "the page threw while drawing - open $IN and read the console; not capturing"; exit 1 ;;
    *) echo "the page never finished drawing (script error or rough.js did not load) - not capturing $OUT"; exit 1 ;;
  esac
fi
rm -f "$OUT"                                  # a stale PNG must never pass for a fresh one
RC=0
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size="${W},${H}" --virtual-time-budget=6000 --screenshot="$OUT" "file://$IN" >/dev/null 2>&1 || RC=$?
[ -s "$OUT" ] || { echo "capture failed (chrome exit $RC): $OUT"; exit 1; }
EXACT=$(grep -c 'data-exact' "$IN" || true)
python3 - "$OUT" "$EXACT" "$W" "$H" <<'PY'
import math, os, sys
from PIL import Image, ImageChops, ImageStat
p, exact, w, h = sys.argv[1], sys.argv[2] != "0", int(sys.argv[3]), int(sys.argv[4])
im = Image.open(p).convert('RGB')
if exact:
    if im.width < w * 2 or im.height < h * 2:
        os.remove(p); sys.exit(f"capture came out {im.width}x{im.height}, expected {w * 2}x{h * 2} - not keeping {p}")
    im = im.crop((0, 0, w * 2, h * 2))
else:
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        pad = 48; x0, y0, x1, y1 = box
        im = im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))
# the pencil grain is noise PNG can't squeeze (a 660px diagram came out ~940 KB); a 256-colour palette
# cuts it ~70% and can't be told apart. Kept only while it stays that faithful (PSNR >= 40 dB).
q = im.quantize(256, method=Image.Quantize.FASTOCTREE)
mse = sum(v * v for v in ImageStat.Stat(ImageChops.difference(im, q.convert('RGB'))).rms) / 3
(q if mse == 0 or 10 * math.log10(255 * 255 / mse) >= 40 else im).save(p, optimize=True)
print('wrote', p, im.size, f'{os.path.getsize(p) // 1024} KB')
PY
