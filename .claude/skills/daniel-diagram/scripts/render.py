#!/usr/bin/env python3
"""Check a daniel-diagram spec, then render it to a rough.js HTML page.

usage: render.py spec.json [out.html] [--bake out.excalidraw] [--force]

Without out.html it only runs the checks. A FAIL stops the render unless --force;
a WARN may stay only for a reason you can say out loud. Spec format: SKILL.md.
"""
import json, math, re, sys, html as H
from pathlib import Path

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# role: (fill, stroke, text) - DanielSite tokens.css
ROLES = {
    "zone-warm": ("#F7EDDA", "#79513C", "#79513C"),
    "zone-light": ("#FDF7EA", "#3F6472", "#3F6472"),
    "group": ("#A8AE8B", "#555E3C", "#26211C"),
    "component": ("#C9D6DC", "#3F6472", "#26211C"),
    "focal": ("#EFCDB4", "#C85A32", "#8F3D22"),
    "external": ("#FBF4E6", "#79513C", "#51463C"),
    "start": ("#26211C", "#26211C", "#26211C"),
    "end": ("#FBF4E6", "#26211C", "#26211C"),
}
CONTAINERS = {"zone-warm", "zone-light", "group"}
SHAPES = ("rectangle", "diamond", "ellipse", "cylinder", "tiles")
STYLES = ("pencil", "sketch")
# pencil style, role: (paper base, coloured-pencil hatch or None, title-pill fill) - still tokens.css only
PENCIL = {
    "zone-warm": ("#F7EDDA", None, "#EFCDB4"),
    "zone-light": ("#FFF9F1", None, "#C9D6DC"),
    "group": ("#EEDFC7", "#66704B", "#A8AE8B"),
    "component": ("#DCE4E8", "#46708D", None),
    "focal": ("#F3E7D0", "#C85A32", None),
    "external": ("#FBF4E6", None, None),
    "start": ("#26211C", None, None),
    "end": ("#FBF4E6", None, None),
}
SHADOW = {"node": 6, "zone": 8, "tile": 4, "pill": 3}
# pencil: titles that sit on paper (zone and group titles, a tile grid's name) take the role's strong ink; text on a hatched fill stays graphite
TITLE_INK = {"zone-warm": "#79513C", "zone-light": "#3F6472", "group": "#555E3C",
             "component": "#3F6472", "focal": "#8F3D22", "external": "#51463C"}
CANVAS, ARROW, INK, MUTED, HAND = "#FBF4E6", "#51463C", "#26211C", "#51463C", "#8F3D22"
ACCENT = "#C85A32"
TOKENS = set((                        # every hex in tokens.css (frozen there); the roles use a few of them
    "#26211C #2E261F #2F6B5E #3A2A1E #3A2F26 #3E3831 #3F6472 #46708D #4E5639 #512BD4 #51463C #555E3C #56607F #5B5F7A "
    "#5F4B8B #66704B #6A5A8C #79513C #7A4A2E #8A6532 #8A6A20 #8E4767 #8F3D22 #9A4B33 #A84A28 #A8AE8B #C05A2E #C85A32 "
    "#C9D6DC #DCE4E8 #E4C6BE #E6CFA3 #E7E2ED #EEDFC7 #EFCDB4 #F3E7D0 #F7EDDA #FBF4E6 #FDF7EA #FFF9F1").split())
PRESETS = {"article": 660, "readme": 880, "fit": None, "video": 660}
VIDEO_H = 371                         # size video: 16:9 at the post column's width, so a daniel-video frame shows the text 1:1
PAD = 24
SIZE = {"zone": 18, "group": 16, "label": 16, "code": 16, "sub": 13.5, "edge": 13}   # zone/group: mono titles only
LS_EDGE = 0.12                        # --ls-label: the site's uppercase mono labels
MIN_FONT = 13
BUDGET = {"boxes": 10, "arrows": 12, "containers": 4, "focal": 3, "callouts": 2, "steps": 6}
MAX_WORDS = 4                         # the PNG ships unchanged in five editions: terms, not sentences
FACE_FILES = {"sans": "karla-latin", "mono": "courier-prime-400-latin", "slab": "zilla-slab-600-latin", "slabi": "zilla-slab-400italic-latin"}
# role: (face, weight, size, letter-spacing). Zilla carries boundaries and asides, Karla names, Courier everything you could type.
TYPE = {"zone": ("slab", 600, 20, 0), "group": ("slab", 600, 17, 0), "stamp": ("mono", 400, 13, LS_EDGE), "note": ("slabi", 400, 17, 0)}

BOLD = False                          # pencil: heavier type, set in main() before anything is measured
def bump(fam, w):
    """pencil weights: Karla 800 for names, Courier Prime Bold for anything typed, Zilla Slab 700 for titles."""
    if not BOLD: return w
    return {"sans": 800, "mono": 700, "slab": 700}.get(fam, w)

KEPT = set()                           # id(op) of free text whose spec set fontWeight: pencil leaves that weight alone
OWN = {}                               # id(op) -> the element that drew it ("s1", "s1:sub", "a1:label"): daniel-video animates by it
def tag(op, oid):
    OWN[id(op)] = oid
    return op

notes = []
def fail(m): notes.append(("FAIL", m))
def warn(m): notes.append(("WARN", m))

# ---------------------------------------------------------------- measuring
_faces = {}
def _load(fam, weight):
    key = (fam, weight)
    if key not in _faces:
        try:
            from fontTools.ttLib import TTFont
            from fontTools.varLib.instancer import instantiateVariableFont
            faces = []
            for n in (f"{FACE_FILES[fam]}{s}.woff2" for s in ("", "-ext")):
                f = TTFont(FONTS / n)
                if "fvar" in f:
                    f = instantiateVariableFont(f, {"wght": weight})
                faces.append((f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm))
            _faces[key] = faces
        except Exception:
            _faces[key] = None
    return _faces[key]

def text_w(t, fam, weight, size, ls=0, exact=False):
    """exact: the weight is final (a spec's own fontWeight, or an op already bumped), so pencil doesn't bump it again."""
    fam = {True: "mono", False: "sans"}.get(fam, fam)
    if not exact: weight = bump(fam, weight)
    slack = 1.03 if fam == "slab" and weight > 600 else 1   # only the 600 Zilla file ships; 700 runs a little wider
    return slack * _text_w(t, fam, weight, size, ls)

def _text_w(t, fam, weight, size, ls):
    faces = _load(fam, weight)
    if not faces:
        return len(t) * size * (0.6 if fam == "mono" else 0.56) + len(t) * ls * size
    em = 0
    for ch in t:
        for cmap, hm, upm in faces:
            g = cmap.get(ord(ch))
            if g:
                em += hm[g][0] / upm
                break
        else:
            em += 0.6
    return (em + len(t) * ls) * size

# ---------------------------------------------------------------- geometry
def box(e): return (e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"])
def inside(p, r, m=0): return r[0] - m <= p[0] <= r[2] + m and r[1] - m <= p[1] <= r[3] + m
def hit(a, b, m=0): return a[0] < b[2] - m and b[0] < a[2] - m and a[1] < b[3] - m and b[1] < a[3] - m
def r4(v): return int(round(v / 4) * 4)

def seg_hits_rect(p, q, r):
    """Axis-aligned segment p-q crosses the interior of r (shrunk 2px)."""
    x0, y0, x1, y1 = r[0] + 2, r[1] + 2, r[2] - 2, r[3] - 2
    if p[1] == q[1]:
        return y0 < p[1] < y1 and min(p[0], q[0]) < x1 and max(p[0], q[0]) > x0
    return x0 < p[0] < x1 and min(p[1], q[1]) < y1 and max(p[1], q[1]) > y0

def mix(bg, fg, a):
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(f[i] * a + b[i] * (1 - a)) for i in range(3))

def lines(v): return [] if v is None else str(v).split("\n")

# ---------------------------------------------------------------- validation
KINDS = set(SHAPES) | {"arrow", "text", "callout", "frame"}
SIDES = ("top", "bottom", "left", "right")
ANCHORS = ("start", "middle", "end")

def validate(spec):
    """Drop, with a FAIL, every element the geometry below could not handle."""
    clean, seen = [], set()
    for i, e in enumerate(spec["elements"]):
        kind = e.get("type") if isinstance(e, dict) else None
        if kind not in KINDS:
            fail(f"element #{i}: type {kind!r} is not one of {', '.join(sorted(KINDS))}"); continue
        if not isinstance(e.get("id"), str) or not e["id"]:
            fail(f"element #{i} ({kind}): needs an id"); continue
        if e["id"] in seen:
            fail(f"{e['id']}: duplicate id"); continue
        seen.add(e["id"])
        num = lambda k: isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool)
        bad = None
        if kind == "arrow":
            if "from" in e or "to" in e:
                bad = next((f"{k} {e[k]!r} is not one of {', '.join(SIDES)}" for k in ("fromSide", "toSide") if k in e and e[k] not in SIDES), None)
            elif not (num("x") and num("y") and isinstance(e.get("points"), list) and len(e["points"]) >= 2
                      and all(isinstance(q, list) and len(q) == 2 for q in e["points"])):
                bad = "needs from/to, or x, y and at least two [dx, dy] points"
            bad = bad or next((f"{k} must be between 0 and 1" for k in ("fromAt", "toAt", "labelAt") if k in e and not (num(k) and 0 <= e[k] <= 1)), None)
        elif kind == "text":
            if not (num("x") and num("y") and num("fontSize") and isinstance(e.get("text"), str)): bad = "needs x, y, fontSize and text"
        elif kind == "callout":
            if not (num("x") and num("y") and e.get("text")): bad = "needs x, y and text"
        elif kind == "frame":
            if not all(num(k) for k in ("x", "y", "width", "height")): bad = "needs x, y, width and height"
            elif e.get("op", "alt") not in ("alt", "opt", "loop"): bad = f"op {e['op']!r} is not alt, opt or loop"
            elif "split" in e and not (num("split") and e["y"] + 28 < e["split"] < e["y"] + e["height"] - 12):
                bad = "split must fall inside the frame, below its tab"
            elif e.get("guard2") and "split" not in e: bad = "guard2 needs a split"
        elif kind == "tiles":
            items = e.get("items")
            if not (isinstance(items, list) and items and all(isinstance(t, (str, dict)) for t in items)):
                bad = "needs items: a list of codes (\"v1\") or {code, role}"
            elif any(isinstance(t, dict) and t.get("role", "component") not in ROLES for t in items):
                bad = "every tile role must be a palette role"
            elif any(k in e and not num(k) for k in ("x", "y", "cx", "cy", "cols", "size", "gap")):
                bad = "x, y, cx, cy, cols, size and gap must be numbers"
        else:
            bad = next((f"{k} must be a number" for k in ("x", "y", "cx", "cy", "width", "height") if k in e and not num(k)), None)
        if not bad and e.get("anchor", "start") not in ANCHORS: bad = f"anchor {e['anchor']!r} is not one of {', '.join(ANCHORS)}"
        if bad:
            fail(f"{e['id']}: {bad}"); continue
        clean.append(e)
    legend = []
    for item in spec.get("legend", []):
        if not isinstance(item, dict) or not item.get("text"):
            fail("legend: every item needs a text"); continue
        if "box" in item and item["box"] not in ROLES:
            fail(f"legend: box {item['box']!r} is not a role"); continue
        if "box" not in item and item.get("line", "solid") not in ("solid", "dashed", "accent"):
            fail(f"legend: line {item['line']!r} is not solid, dashed or accent"); continue
        legend.append(item)
    return clean, legend

# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    force = "--force" in args
    bake = args[args.index("--bake") + 1] if "--bake" in args else None
    scene_out = args[args.index("--scene") + 1] if "--scene" in args else None     # the drawing as ops + owners, for daniel-video
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--bake", "--scene"))]
    if not pos:
        print(__doc__); sys.exit(1)
    src, out = pos[0], (pos[1] if len(pos) > 1 else None)
    spec = json.load(open(src))
    preset = spec.get("size", "article")
    if preset not in PRESETS:
        fail(f"size '{preset}' is not one of {', '.join(PRESETS)}")
        preset = "article"
    style = spec.get("style", "pencil")
    if style not in STYLES:
        fail(f"style '{style}' is not one of {', '.join(STYLES)}")
        style = "pencil"
    pencil = style == "pencil"
    global BOLD
    BOLD = pencil
    if not isinstance(spec.get("elements"), list):
        print("FAIL  the spec needs an \"elements\" list"); sys.exit(2)
    els, legend = validate(spec)
    if not els:
        fail("nothing left to draw")
        for lvl, m in notes: print(f"{lvl}  {m}")
        sys.exit(2)
    shapes = [e for e in els if e["type"] in SHAPES]
    ids = {e["id"]: e for e in els if "id" in e}
    explicit = {e["id"]: {k for k in ("x", "y", "width", "height") if k in e} for e in shapes}

    # -- shapes: colours, auto size, text blocks
    for e in shapes:
        if e["type"] == "tiles":                   # a grid of small same-size tiles (pods, replicas): one box in the budget
            size, gap = e.get("size", 44), e.get("gap", 10)
            n = len(e["items"]); cols = int(e.get("cols", n)); rows = math.ceil(n / cols)
            head = 26 if e.get("code") or e.get("label") else 0     # an optional name above the grid (the Deployment)
            e["_tiles"] = []
            for i, t in enumerate(e["items"]):
                t = {"code": t} if isinstance(t, str) else t
                role = t.get("role", "component")
                e["_tiles"].append((i % cols * (size + gap), head + i // cols * (size + gap), size, role, str(t.get("code", ""))))
                if text_w(str(t.get("code", "")), "mono", 700, SIZE["code"]) > size - 8:
                    fail(f"{e['id']}: tile text {t.get('code')!r} is wider than a {size}px tile")
            e["width"], e["height"] = cols * size + (cols - 1) * gap, head + rows * size + (rows - 1) * gap
            name = e.get("code") or e.get("label")
            if name:
                mono = "code" in e
                if text_w(name, mono, 400 if mono else 600, 15) > e["width"]: fail(f"{e['id']}: name is wider than the tiles")
                e["_name"] = (name, mono)
            e.setdefault("role", "component")
            e.update(backgroundColor=ROLES["component"][0], strokeColor=ROLES["component"][1], opacity=100,
                     _tc=INK, _container=False, _block=[], _bh=0)
            if "x" not in e and "cx" not in e or "y" not in e and "cy" not in e: fail(f"{e['id']}: needs x/cx and y/cy")
            if "x" not in e: e["x"] = e["cx"] - e["width"] / 2 if "cx" in e else 0
            if "y" not in e: e["y"] = e["cy"] - e["height"] / 2 if "cy" in e else 0
            continue
        role = e.get("role")
        if role and role not in ROLES:
            fail(f"{e['id']}: unknown role '{role}'")
        fill, stroke, tc = ROLES.get(role, (CANVAS, ARROW, INK))
        e.setdefault("backgroundColor", fill); e.setdefault("strokeColor", stroke)
        e.setdefault("opacity", 75 if role == "group" else 100)
        e["_tc"] = tc
        e["_container"] = role in CONTAINERS
        if role == "external": e.setdefault("dashed", True)
        block = []
        if not e["_container"]:
            for t in lines(e.get("label")): block.append((t, False, 600, e.get("fontSize", SIZE["label"]), tc, "main"))
            for t in lines(e.get("code")): block.append((t, True, 400, e.get("fontSize", SIZE["code"]), tc, "main"))
            sub_c = tc if role == "focal" else MUTED
            for t in lines(e.get("sub")): block.append((t, True, 400, SIZE["sub"], sub_c, "sub"))
        e["_block"] = block
        bw = max((text_w(t, m, w, s) for t, m, w, s, _, _ in block), default=0)
        gap = 4 if e.get("sub") and (e.get("label") or e.get("code")) else 0
        bh = sum(s * 1.3 for _, _, _, s, _, _ in block) + gap          # same geometry in both styles
        e["_bh"] = bh
        if "width" not in e:
            if not block: fail(f"{e['id']}: needs width (no text to size it by)"); e["width"] = 120
            else: e["width"] = r4({"diamond": 2 * bw + 40, "ellipse": 1.42 * bw + 36}.get(e["type"], bw + 40) + 3)
        if "height" not in e:
            if not block: fail(f"{e['id']}: needs height"); e["height"] = 56
            else: e["height"] = max(56, r4({"diamond": 2 * bh + 32, "ellipse": 1.42 * bh + 28, "cylinder": bh + 40}.get(e["type"], bh + 24) + 3))
        if "x" not in e:
            if "cx" in e: e["x"] = e["cx"] - e["width"] / 2
            else: fail(f"{e['id']}: needs x or cx"); e["x"] = 0
        if "y" not in e:
            if "cy" in e: e["y"] = e["cy"] - e["height"] / 2
            else: fail(f"{e['id']}: needs y or cy"); e["y"] = 0
        for k in ("backgroundColor", "strokeColor"):
            if e[k].upper() not in TOKENS: fail(f"{e['id']}: {k} {e[k]} is not a tokens.css colour")
        room_w = {"diamond": e["width"] / 2 - 8, "ellipse": e["width"] * 0.7 - 16}.get(e["type"], e["width"] - 24)
        room_h = {"diamond": e["height"] / 2 - 4, "ellipse": e["height"] * 0.7 - 8, "cylinder": e["height"] - 36}.get(e["type"], e["height"] - 16)
        if block and bw > room_w + 0.5: fail(f"{e['id']}: text is {bw:.0f}px wide, the box leaves {room_w:.0f}px")
        if block and bh > room_h + 0.5: fail(f"{e['id']}: text is {bh:.0f}px tall, the box leaves {room_h:.0f}px")

    rects = {e["id"]: box(e) for e in shapes}
    tile_names = []
    for e in shapes:                                # arrows aim at the grid itself; the name above it is text
        if e["type"] == "tiles" and "_name" in e:
            x0, y0, x1, y1 = rects[e["id"]]
            rects[e["id"]] = (x0, y0 + 26, x1, y1)
            name, mono = e["_name"]
            tile_names.append(((x0, y0, x0 + text_w(name, mono, 400 if mono else 600, 15), y0 + 20), f"{e['id']} name"))
    containers = sorted([e for e in shapes if e["_container"]], key=lambda e: -e["width"] * e["height"])
    nodes = [e for e in shapes if not e["_container"]]
    holds = lambda o, i: o[0] <= i[0] and o[1] <= i[1] and i[2] <= o[2] and i[3] <= o[3]
    for i, a in enumerate(shapes):
        for b in shapes[i + 1:]:
            ra, rb = rects[a["id"]], rects[b["id"]]
            if not hit(ra, rb) or holds(ra, rb) or holds(rb, ra): continue
            if a["_container"] or b["_container"]:
                warn(f"{a['id']} and {b['id']} cross each other's border - a box sits fully inside its zone or outside it")
            else:
                fail(f"{a['id']} and {b['id']} overlap - move one")

    def bg_at(p, skip=None):
        c = CANVAS
        for z in containers:
            if z is not skip and inside(p, rects[z["id"]]): c = mix(c, z["backgroundColor"], z["opacity"] / 100)
        return c

    texts = list(tile_names)                # (rect, what) for overlap checks
    scene_text, scene_mask = [], []

    # -- container titles
    for z in containers:
        name = z.get("label") or z.get("code")
        if not name: continue
        is_code = "code" in z and "label" not in z
        x0, y0, x1, _ = rects[z["id"]]
        fam, wt, fs, _ = TYPE["group" if z["role"] == "group" else "zone"]
        if is_code: fam, wt, fs = "mono", 400, SIZE["group" if z["role"] == "group" else "zone"] - 2
        w = text_w(name, fam, wt, fs)
        if pencil:                                  # a tag pill straddling the top border
            ph, pw = fs * 1.3 + 10, w + 28
            px = x1 - 18 - pw if z.get("titleAt") == "right" else x0 + 18
            rt = (px, y0 - ph / 2, px + pw, y0 + ph / 2)
            z["_pill"] = tag(["pill", px, y0 - ph / 2, pw, ph, (PENCIL.get(z["role"]) or (None, None, "#C9D6DC"))[2] or "#C9D6DC", INK, SHADOW["pill"], 0], z["id"] + ":title")
            scene_text.append(tag(["text", px + pw / 2, y0 + 0.5, name, fs, TITLE_INK.get(z["role"], INK), fam, wt, "middle", "central", 0], z["id"] + ":title"))
        else:
            tx, ty = (x1 - 12 - w if z.get("titleAt") == "right" else x0 + 12), y0 + 10
            scene_text.append(tag(["text", tx, ty + fs * 0.65, name, fs, z["_tc"], fam, wt, "start", "central", 0], z["id"] + ":title"))
            rt = (tx, ty, tx + w, ty + fs * 1.3)
        if rt[2] > x1 - 8: fail(f"{z['id']}: title is wider than the {'group' if z['role'] == 'group' else 'zone'}")
        texts.append((rt, f"{z['id']} title"))
        z["_title"] = rt
        for o in shapes:
            if o is not z and hit(rt, rects[o["id"]]) and inside((rects[o["id"]][0] + 1, rects[o["id"]][1] + 1), rects[z["id"]]):
                fail(f"{z['id']}: title collides with {o['id']} - push the children down")

    # -- node text blocks
    for e in nodes:
        if not e["_block"]: continue
        x0, y0, x1, y1 = rects[e["id"]]
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2 + (6 if e["type"] == "cylinder" else 0)
        top = cy - e["_bh"] / 2
        prev = None
        for t, mono, w, fs, c, part in e["_block"]:
            if prev == "main" and part == "sub": top += 4
            if pencil and part == "main": c = INK            # on a hatched fill only graphite keeps its contrast
            if pencil and part == "sub":                 # the sub line sits in a small pill, as wide as the box allows
                pw = min(text_w(t, "mono", w, fs) + 20, (x1 - x0) - 12)
                scene_mask.append(tag(["pill", cx - pw / 2, top - 1, pw, fs * 1.3 + 3, "#FFF9F1", INK, 2, 0], e["id"] + ":sub"))
                c = INK
            scene_text.append(tag(["text", cx, top + fs * 0.65, t, fs, c, "mono" if mono else "sans", w, "middle", "central", 0],
                                  e["id"] + (":sub" if part == "sub" else "")))
            top += fs * 1.3; prev = part
        bw = max(text_w(t, m, w, s) for t, m, w, s, _, _ in e["_block"])
        texts.append(((cx - bw / 2, cy - e["_bh"] / 2, cx + bw / 2, cy + e["_bh"] / 2), f"{e['id']} text"))

    # -- arrows: resolve routes
    horiz = lambda side: side in ("left", "right")
    arrows = [e for e in els if e["type"] == "arrow"]
    for a in arrows:
        a.setdefault("head", True)
        a.setdefault("strokeColor", ACCENT if a.get("accent") else INK if pencil else ARROW)
        if a["strokeColor"].upper() not in TOKENS: fail(f"{a['id']}: strokeColor {a['strokeColor']} is not a tokens.css colour")
        if "from" in a or "to" in a:
            if a.get("from") not in rects or a.get("to") not in rects:
                fail(f"{a['id']}: from/to must name shapes"); a["_pts"] = []; continue
            s, t = rects[a["from"]], rects[a["to"]]
            gaps = {("bottom", "top"): t[1] - s[3], ("top", "bottom"): s[1] - t[3],
                    ("right", "left"): t[0] - s[2], ("left", "right"): s[0] - t[2]}
            # top/bottom ports whenever there is room: a mainly vertical arrow entering a side reads as puncturing the box
            vert = [k for k in gaps if not horiz(k[0]) and gaps[k] >= 24]
            auto = vert[0] if vert else max(gaps, key=gaps.get)
            a["_sides"] = (a.get("fromSide", auto[0]), a.get("toSide", auto[1]))
    routed = [a for a in arrows if "_sides" in a]

    def along(r, side, f):
        x0, y0, x1, y1 = r
        return {"top": (x0 + (x1 - x0) * f, y0), "bottom": (x0 + (x1 - x0) * f, y1),
                "left": (x0, y0 + (y1 - y0) * f), "right": (x1, y0 + (y1 - y0) * f)}[side]

    forks, merges = {}, {}
    for a in routed:
        forks.setdefault((a["from"], a["_sides"][0]), []).append(a)
        merges.setdefault((a["to"], a["_sides"][1]), []).append(a)
    for a in routed:
        s, t = rects[a["from"]], rects[a["to"]]
        ss, ts = a["_sides"]
        p0 = along(s, ss, a.get("fromAt", 0.5))
        group = merges[(a["to"], ts)]
        if "toAt" in a:
            p1 = along(t, ts, a["toAt"])
        elif ids[a["to"]]["_container"] and not horiz(ts) and t[0] + 16 <= p0[0] <= t[2] - 16:
            p1 = (p0[0], t[1] if ts == "top" else t[3])
        elif ids[a["to"]]["_container"] and horiz(ts) and t[1] + 16 <= p0[1] <= t[3] - 16:
            p1 = (t[0] if ts == "left" else t[2], p0[1])
        elif len(group) > 1 and ids[a["to"]]["type"] == "rectangle":
            key = (lambda g: (rects[g["from"]][1] + rects[g["from"]][3]) / 2) if horiz(ts) else (lambda g: (rects[g["from"]][0] + rects[g["from"]][2]) / 2)
            k = sorted(group, key=key).index(a) + 1
            p1 = along(t, ts, k / (len(group) + 1))
        else:
            p1 = along(t, ts, 0.5)
        p0 = (r4(p0[0]) if not horiz(ss) else p0[0], r4(p0[1]) if horiz(ss) else p0[1])
        p1 = (r4(p1[0]) if not horiz(ts) else p1[0], r4(p1[1]) if horiz(ts) else p1[1])
        fork = forks[(a["from"], ss)]
        if ss == ts:                         # U-route around, e.g. bottom -> bottom
            d = {"bottom": 1, "right": 1, "top": -1, "left": -1}[ss]
            if horiz(ss):
                x = a.get("mid", (max if d > 0 else min)(p0[0], p1[0]) + 28 * d)
                pts = [p0, (x, p0[1]), (x, p1[1]), p1]
            else:
                y = a.get("mid", (max if d > 0 else min)(p0[1], p1[1]) + 28 * d)
                pts = [p0, (p0[0], y), (p1[0], y), p1]
        elif horiz(ss) == horiz(ts):         # Z or straight
            if horiz(ss):
                if abs(p0[1] - p1[1]) < 1: pts = [p0, (p1[0], p0[1])]
                else:
                    near = (min if ss == "right" else max)(rects[g["to"]][0] if ss == "right" else rects[g["to"]][2] for g in fork)
                    x = a.get("mid", r4((p0[0] + near) / 2) if len(fork) > 1 else r4((p0[0] + p1[0]) / 2))
                    pts = [p0, (x, p0[1]), (x, p1[1]), p1]
            else:
                if abs(p0[0] - p1[0]) < 1: pts = [p0, (p0[0], p1[1])]
                else:
                    near = (min if ss == "bottom" else max)(rects[g["to"]][1] if ss == "bottom" else rects[g["to"]][3] for g in fork)
                    y = a.get("mid", r4((p0[1] + near) / 2) if len(fork) > 1 else r4((p0[1] + p1[1]) / 2))
                    pts = [p0, (p0[0], y), (p1[0], y), p1]
        else:                                # L
            pts = [p0, (p1[0], p0[1]) if horiz(ss) else (p0[0], p1[1]), p1]
        a["_pts"] = pts
    manual = [a for a in arrows if "_pts" not in a]
    for a in manual:
        a["_pts"] = [(a["x"] + p[0], a["y"] + p[1]) for p in a["points"]]
    lifelines = [a for a in arrows if not a["head"] and a["_pts"]]
    for a in manual:
        pts = a["_pts"]
        for p, q in zip(pts, pts[1:]):
            if p[0] != q[0] and p[1] != q[1]: fail(f"{a['id']}: segment {p}->{q} is diagonal - use right angles")
        for end in ((pts[0], pts[-1]) if a["head"] else ()):
            on_box = any(inside(end, rects[n["id"]], 3) and not inside(end, rects[n["id"]], -3) for n in shapes)
            on_line = any(l is not a and any(inside(end, (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1])), 3)
                                             for p, q in zip(l["_pts"], l["_pts"][1:])) for l in lifelines)
            if not on_box and not on_line:
                warn(f"{a['id']}: end {end} does not touch any box edge or lifeline")

    for a in arrows:
        pts = a["_pts"]
        for p, q in zip(pts, pts[1:]):
            if 0 < abs(q[0] - p[0]) + abs(q[1] - p[1]) < 12 and 0 < pts.index(p) < len(pts) - 2:
                warn(f"{a['id']}: {abs(q[0] - p[0]) + abs(q[1] - p[1]):.0f}px jog - align the two box centres instead")
            for z in containers:
                x0, y0, x1, y1 = rects[z["id"]]
                if p[1] == q[1] and any(0 < abs(p[1] - yy) < 10 for yy in (y0, y1)) and min(p[0], q[0]) < x1 and max(p[0], q[0]) > x0:
                    warn(f"{a['id']}: runs along the border of {z['id']} - move it (mid) into open space")
                if p[0] == q[0] and any(0 < abs(p[0] - xx) < 10 for xx in (x0, x1)) and min(p[1], q[1]) < y1 and max(p[1], q[1]) > y0:
                    warn(f"{a['id']}: runs along the border of {z['id']} - move it (mid) into open space")
                if "_title" in z and seg_hits_rect(p, q, z["_title"]):
                    fail(f"{a['id']}: runs under the title of {z['id']} - reroute (mid) or move the title")

    # -- arrow checks: through boxes, shared strokes, crossings (hops)
    def ends(a):
        if "from" in a: return {a["from"], a["to"]}
        return {n["id"] for n in shapes if any(inside(p, rects[n["id"]], 3) for p in (a["_pts"][0], a["_pts"][-1]))}
    hops = {a["id"]: [] for a in arrows}
    for a in arrows:
        pts, own = a["_pts"], ends(a)
        for p, q in zip(pts, pts[1:]):
            for n in nodes:
                if not a["head"] and min(n["width"], n["height"]) <= 24: continue   # a lifeline runs through its activation bars
                if seg_hits_rect(p, q, rects[n["id"]]):
                    if n["id"] not in own: fail(f"{a['id']}: passes behind {n['id']} - reroute (fromSide/toSide/mid)")
                    else: fail(f"{a['id']}: runs through its own end box {n['id']} - use the side that faces the other box (fromSide/toSide)")
            for z in containers:
                if z["id"] in own: continue
                r = rects[z["id"]]
                if not inside(pts[0], r) and not inside(pts[-1], r) and seg_hits_rect(p, q, r):
                    warn(f"{a['id']}: crosses {z['id']} without starting or ending in it")
    heads = [a for a in arrows if a["head"] and a["_pts"]]
    for i, a in enumerate(heads):
        for b in heads[i + 1:]:
            if a["_pts"][0] == b["_pts"][0] or a["_pts"][-1] == b["_pts"][-1]: continue   # fork or merge
            for sa in zip(a["_pts"], a["_pts"][1:]):
                for sb in zip(b["_pts"], b["_pts"][1:]):
                    ha, hb = sa[0][1] == sa[1][1], sb[0][1] == sb[1][1]
                    if ha == hb:
                        k, j = (1, 0) if ha else (0, 1)
                        if sa[0][k] == sb[0][k] and min(max(sa[0][j], sa[1][j]), max(sb[0][j], sb[1][j])) - max(min(sa[0][j], sa[1][j]), min(sb[0][j], sb[1][j])) > 1:
                            warn(f"{a['id']} and {b['id']} share a stroke - move one by 12px or more (mid/fromAt/toAt)")
                        continue
                    h, v = (sa, sb) if ha else (sb, sa)
                    x, y = v[0][0], h[0][1]
                    if min(h[0][0], h[1][0]) + 1 < x < max(h[0][0], h[1][0]) - 1 and min(v[0][1], v[1][1]) + 1 < y < max(v[0][1], v[1][1]) - 1:
                        hopper = b if b.get("dashed") or not a.get("dashed") else a
                        seg = (sa if hopper is a else sb)
                        c = x if seg[0][1] == seg[1][1] else y
                        k = 0 if seg[0][1] == seg[1][1] else 1
                        if min(abs(c - seg[0][k]), abs(c - seg[1][k])) < 12:
                            warn(f"{a['id']} crosses {b['id']} too close to a bend for a hop - move one")
                        hops[hopper["id"]].append((seg, c))

    def hopped(a):
        out = [a["_pts"][0]]
        for p, q in zip(a["_pts"], a["_pts"][1:]):
            horizontal = p[1] == q[1]
            mine = sorted([c for s, c in hops[a["id"]] if s == (p, q)], key=lambda c: abs(c - (p[0] if horizontal else p[1])))
            for c in mine:
                if horizontal:
                    d = 1 if q[0] > p[0] else -1
                    out += [(c - d * 7 * math.cos(math.pi * k / 6), p[1] - 7 * math.sin(math.pi * k / 6)) for k in range(7)]
                else:
                    d = 1 if q[1] > p[1] else -1
                    out += [(p[0] + 7 * math.sin(math.pi * k / 6), c - d * 7 * math.cos(math.pi * k / 6)) for k in range(7)]
            out.append(q)
        return out

    # -- arrow labels and step markers
    scene_arrows, scene_marks, edge_labels = [], [], []
    for a in arrows:
        pts = a["_pts"]
        if not pts: continue
        scene_arrows.append(tag(["arrow", [list(p) for p in hopped(a)], a["strokeColor"], bool(a.get("dashed")), a["head"],
                                 int(pts[0][0] * 3 + pts[0][1])], a["id"]))
        segs = list(zip(pts, pts[1:]))
        ln = lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1])

        step_at = None
        if "step" in a:
            i = 1 if len(segs) > 1 and ln(segs[0]) < 30 else 0
            p, q = segs[i]; L = ln(segs[i]) or 1
            def clear(f):
                x, y = p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f
                return all(min(abs(y - r[1]), abs(y - r[3])) > 14 if p[0] == q[0] else min(abs(x - r[0]), abs(x - r[2])) > 14
                           for r in (rects[z["id"]] for z in containers))
            first = min(0.25, 32 / L) if i else min(20, L / 2) / L
            f = next((c for c in (first, 0.5, 0.35, 0.65, 0.2, 0.8) if clear(c)), first)
            mx, my = p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f
            scene_marks.append(tag(["step", mx, my, str(a["step"])], a["id"] + ":step"))
            texts.append(((mx - 11, my - 11, mx + 11, my + 11), f"{a['id']} step"))
            step_at = (i, f)
        text = a.get("label") or a.get("code")
        if not text: continue
        upper = "label" in a
        t_lines = [t.upper() for t in lines(text)] if upper else lines(text)
        efam, _, fs, ls = TYPE["stamp"] if upper else ("mono", 400, SIZE["edge"], 0)
        tw = max(text_w(t, efam, 400, fs, ls) for t in t_lines); th = fs * 1.3 * len(t_lines)
        fork = "from" in a and len(forks[(a["from"], a["_sides"][0])]) > 1
        merge = "to" in a and len(merges[(a["to"], a["_sides"][1])]) > 1
        idx = a.get("labelSegment")
        if idx is not None and not (isinstance(idx, int) and 0 <= idx < len(segs)):
            fail(f"{a['id']}: labelSegment {idx!r} - this arrow has segments 0 to {len(segs) - 1}"); idx = None
        if idx is None: idx = len(segs) - 1 if fork else 0 if merge else max(range(len(segs)), key=lambda i: ln(segs[i]))
        (x1, y1), (x2, y2) = segs[idx]
        fl = 0.5
        if step_at and step_at[0] == idx:        # keep the label clear of the step marker on its segment
            half = tw / 2 + 5 if y1 == y2 else th / 2 + 2
            fl = max(0.5, step_at[1] + (17 + half) / (ln(segs[idx]) or 1))
        def mask_at(f):
            if y1 == y2:
                cx = x1 + (x2 - x1) * f
                my0 = y1 - 6 - th - 4 if a.get("labelSide", "above") == "above" else y1 + 6
                return (cx - tw / 2 - 5, my0, cx + tw / 2 + 5, my0 + th + 4)
            cy = y1 + (y2 - y1) * f
            mx0 = x1 + 8 if a.get("labelSide", "right") == "right" else x1 - 8 - tw - 10
            return (mx0, cy - th / 2 - 2, mx0 + tw + 10, cy + th / 2 + 2)
        def on_border(m):                       # a mask across a zone edge cuts the zone open
            return any(m[1] < r[k] < m[3] and m[0] < r[2] and m[2] > r[0] for r in (rects[z["id"]] for z in containers) for k in (1, 3)) \
                or any(m[0] < r[k] < m[2] and m[1] < r[3] and m[3] > r[1] for r in (rects[z["id"]] for z in containers) for k in (0, 2))
        clear = lambda m: not on_border(m) and not any(hit(m, rects[n["id"]]) for n in nodes)
        m = mask_at(fl)
        if not clear(m) and "labelAt" not in a:         # slide along the arrow to open canvas, never onto a box
            m = next((mask_at(f) for f in (fl + d for d in (0.25, -0.25, 0.15, -0.15, 0.35, -0.35)) if 0.1 <= f <= 0.9 and clear(mask_at(f))), m)
        if "labelAt" in a: m = mask_at(a["labelAt"])
        if on_border(m): warn(f"{a['id']}: label sits on a zone border - labelAt/labelSegment or more room")
        if pencil:                                   # a pill; the main path's label becomes a tilted stamp
            stamp = bool(a.get("accent"))
            scene_mask.append(tag(["pill", m[0] - 4, m[1] - 1, m[2] - m[0] + 8, m[3] - m[1] + 2, "#EFCDB4" if stamp else "#FFF9F1",
                                   INK, SHADOW["pill"], -4 if stamp else 0], a["id"] + ":label"))
        else:
            scene_mask.append(tag(["mask", m[0], m[1], m[2] - m[0], m[3] - m[1], bg_at(((m[0] + m[2]) / 2, (m[1] + m[3]) / 2))], a["id"] + ":label"))
        for i, t in enumerate(t_lines):
            scene_text.append(tag(["text", (m[0] + m[2]) / 2, m[1] + 2 + fs * 1.3 * (i + 0.5), t, fs, INK if pencil else MUTED, efam, 400, "middle", "central", ls]
                                  + ([-4] if pencil and a.get("accent") else []), a["id"] + ":label"))
        texts.append((m, f"{a['id']} label"))
        edge_labels.append((m, a))
        for n in nodes:
            if hit(m, rects[n["id"]]): fail(f"{a['id']}: label sits on {n['id']} - labelSide/labelSegment or more room")

    # -- frames: a thin outline, the operator on a tab, guards in mono, an optional dashed split
    scene_frames = []
    for e in els:
        if e["type"] != "frame": continue
        x, y, w, h = e["x"], e["y"], e["width"], e["height"]
        sfam, _, sfs, sls = TYPE["stamp"]
        op = e.get("op", "alt").upper(); ow = text_w(op, sfam, 400, sfs, sls)
        tab = (x, y, x + ow + 16, y + sfs * 1.3 + 8)
        scene_frames.append(tag(["frame", x, y, w, h, tab[2] - x, tab[3] - y, e.get("split")], e["id"]))
        scene_text.append(tag(["text", x + 8, y + (tab[3] - y) / 2, op, sfs, MUTED, sfam, 400, "start", "central", sls], e["id"]))
        texts.append((tab, f"{e['id']} op"))
        for g, gy in ((e.get("guard"), y + (tab[3] - y) / 2), (e.get("guard2"), (e.get("split") or 0) + 14)):
            if not g: continue
            gx = tab[2] + 10 if gy < tab[3] else x + 12
            gw = text_w(g, "mono", 400, SIZE["edge"])
            scene_mask.append(tag(["mask", gx - 4, gy - 10, gw + 8, 20, bg_at((gx, gy))], e["id"]))
            scene_text.append(tag(["text", gx, gy, g, SIZE["edge"], MUTED, "mono", 400, "start", "central", 0], e["id"]))
            texts.append(((gx, gy - 9, gx + gw, gy + 9), f"{e['id']} guard"))
        e["_r"] = (x, y, x + w, y + h)

    # -- free text and callouts
    scene_callouts = []
    for e in els:
        if e["type"] == "text":
            sans = e.get("font") == "sans"
            fs = e["fontSize"]; w = int(e.get("fontWeight", 600 if sans else 400)); kept = "fontWeight" in e
            anchor = e.get("anchor", "start")
            legacy = ids.get(e["id"][:-1], {})          # old specs coloured "<box>t" by its box
            c = e.get("strokeColor") or ids.get(e.get("in"), {}).get("_tc") or legacy.get("_tc") or INK
            if c.upper() not in TOKENS: fail(f"{e['id']}: colour {c} is not a tokens.css colour")
            tl = lines(e["text"]); tw = max(text_w(t, not sans, w, fs, exact=kept) for t in tl)
            x0 = e["x"] - {"start": 0, "middle": tw / 2, "end": tw}[anchor]
            for i, t in enumerate(tl):
                op = tag(["text", e["x"], e["y"] + fs * 0.95 + i * fs * 1.25, t, fs, c, "sans" if sans else "mono", w, anchor, "", 0], e["id"])
                if kept: KEPT.add(id(op))
                scene_text.append(op)
            e["_r"] = (x0, e["y"], x0 + tw, e["y"] + fs * 1.25 * len(tl))
            texts.append((e["_r"], f"{e['id']} text"))
            for n in nodes:
                if n["_block"] and hit(e["_r"], rects[n["id"]]): warn(f"{e['id']}: free text over {n['id']}, which has its own text - put it in label/code/sub")
            if fs < MIN_FONT: warn(f"{e['id']}: {fs}px text is below the {MIN_FONT}px floor")
        elif e["type"] == "callout":
            nfam, _, fs, _ = TYPE["note"]
            fs = e.get("fontSize", fs)
            tl = lines(e["text"]); tw = max(text_w(t, nfam, 400, fs) for t in tl)
            lh = fs * 1.3
            anchor = e.get("anchor", "start")
            x0 = e["x"] - {"start": 0, "middle": tw / 2, "end": tw}[anchor]
            r = (x0, e["y"], x0 + tw, e["y"] + lh * len(tl))
            for i, t in enumerate(tl):
                scene_callouts.append(tag(["text", e["x"], e["y"] + lh * (i + 0.5), t, fs, HAND, nfam, 400, anchor, "central", 0], e["id"]))
            c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            if "at" in e: tgt = tuple(e["at"])
            elif e.get("to") in rects:
                b = rects[e["to"]]
                tgt = (min(max(c[0], b[0] + 12), b[2] - 12), b[1] if c[1] < b[1] else b[3] if c[1] > b[3] else c[1])
                if b[1] <= c[1] <= b[3]: tgt = (b[0] if c[0] < b[0] else b[2], min(max(c[1], b[1] + 8), b[3] - 8))
            else:
                fail(f"{e['id']}: callout needs 'to' (a shape id) or 'at' [x, y]"); tgt = (r[2], r[3])
            st = (min(max(tgt[0], r[0] - 6), r[2] + 6), min(max(tgt[1], r[1] - 6), r[3] + 6))
            if inside(st, r): st = (st[0], r[3] + 6)
            mx, my = (st[0] + tgt[0]) / 2, (st[1] + tgt[1]) / 2
            dx, dy = tgt[0] - st[0], tgt[1] - st[1]
            ctrl = (mx - dy * 0.25, my + dx * 0.25)
            scene_callouts.append(tag(["leader", f"M{st[0]:.1f},{st[1]:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {tgt[0]:.1f},{tgt[1]:.1f}"], e["id"]))
            scene_callouts.append(tag(["dot", tgt[0], tgt[1], 3.5, HAND], e["id"]))
            texts.append((r, f"{e['id']} callout"))
            e["_r"] = (min(r[0], tgt[0]), min(r[1], tgt[1]), max(r[2], tgt[0]), max(r[3], tgt[1]))
            for n in nodes:
                if hit(r, rects[n["id"]]): fail(f"{e['id']}: callout text sits on {n['id']} - callouts live in the margin")

    for i, (ra, wa) in enumerate(texts):
        for rb, wb in texts[i + 1:]:
            if hit(ra, rb, 1): fail(f"text collision: {wa} / {wb}")
    for m, a in edge_labels:
        for b in heads:
            near = (m[0] - 4, m[1] - 4, m[2] + 4, m[3] + 4)
            if b is not a and any(seg_hits_rect(p, q, near) for p, q in zip(b["_pts"], b["_pts"][1:])):
                warn(f"{a['id']}: label hides or touches {b['id']} - space the arrows 32px apart or move the label")

    for e in els:                            # whole elements, so a label split over two lines still counts once
        for k in ("label", "code", "sub", "text", "guard", "guard2"):
            if isinstance(e.get(k), str) and len(e[k].split()) > MAX_WORDS:
                warn(f"{e.get('id', '?')}: \"{e[k][:40]}\" reads like a sentence - the PNG ships unchanged in five editions; move it to the post")
    for item in legend:
        if len(item["text"].split()) > MAX_WORDS: warn(f"legend: \"{item['text'][:40]}\" reads like a sentence - keep legend items to a term")

    # -- budget, grid, size
    count = lambda f: sum(1 for e in els if f(e))
    checks = {
        "boxes": count(lambda e: e["type"] in SHAPES and not e.get("_container") and min(e["width"], e["height"]) > 24),
        "arrows": count(lambda e: e["type"] == "arrow" and e.get("head", True)),
        "containers": count(lambda e: e.get("_container")),
        "focal": count(lambda e: e.get("role") == "focal"),
        "callouts": count(lambda e: e["type"] == "callout"),
        "steps": count(lambda e: "step" in e),
    }
    for k, v in checks.items():
        if v > BUDGET[k]: warn(f"{v} {k} (budget {BUDGET[k]}) - cut, merge, or split into overview + detail")
    off = [f"{e['id']}.{k}" for e in shapes for k in explicit[e["id"]] if e[k] % 4]
    if off: warn(f"off the 4px grid: {', '.join(off[:6])}{' …' if len(off) > 6 else ''}")

    bounds = [rects[e["id"]] for e in shapes] + [t for t, _ in texts] + [e["_r"] for e in els if "_r" in e]
    # pencil shadows (max 8px) reach right and down into the 24px page margin, so they never count against the width
    for a in arrows:
        for p in a["_pts"]: bounds.append((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7))
    minx = min(b[0] for b in bounds); miny = min(b[1] for b in bounds)
    maxx = max(b[2] for b in bounds); maxy = max(b[3] for b in bounds)
    scene_legend = []
    if legend:
        ly = maxy + 28; lx = minx
        for item in legend:
            tw = text_w(item["text"], "sans", 400, 14)
            if "box" in item:
                f, st_, _ = ROLES[item["box"]]
                scene_legend.append(["shape", "rectangle", lx, ly - 8, 28, 16, f, st_, 1, item["box"] == "external", 1.5, 0.6, False])
            else:
                kind = item.get("line", "solid")
                scene_legend.append(["arrow", [[lx, ly], [lx + 28, ly]], ACCENT if kind == "accent" else ARROW, kind == "dashed", True, int(lx)])
            scene_legend.append(["text", lx + 38, ly, item["text"], 14, MUTED, "sans", 400, "start", "central", 0])
            lx += 38 + tw + 28
        maxx = max(maxx, lx - 28)
        scene_legend.insert(0, ["rule", minx, ly - 14, maxx, ly - 14])
        maxy = ly + 12
    cw, ch = maxx - minx, maxy - miny
    W = PRESETS[preset]
    if W:
        if cw > W - 2 * PAD + 0.5:
            fail(f"content is {cw:.0f}px wide; '{preset}' leaves {W - 2 * PAD}px - narrow the layout, never shrink the type")
        sw, dx = W, (W - cw) / 2 - minx
    else:
        sw, dx = cw + 2 * PAD, PAD - minx
        fonts = [t[4] for t in scene_text]
        if fonts and min(fonts) * min(1, 660 / sw) < MIN_FONT:
            warn(f"in the 660px article column this shows at {min(1, 660 / sw):.0%}; the smallest text becomes {min(fonts) * min(1, 660 / sw):.1f}px")
    sh, dy = ch + 2 * PAD, PAD - miny
    if preset == "video":
        if ch > VIDEO_H - 2 * PAD + 0.5:
            fail(f"content is {ch:.0f}px tall; 'video' leaves {VIDEO_H - 2 * PAD}px - widen and flatten the layout, or split it into two diagrams")
        sh, dy = VIDEO_H, (VIDEO_H - ch) / 2 - miny
    sw, sh = math.ceil(sw), math.ceil(sh)

    fails = [n for n in notes if n[0] == "FAIL"]
    for lvl, m in notes: print(f"{lvl}  {m}")
    print(f"check: {len(fails)} fail, {len(notes) - len(fails)} warn · {checks['boxes']} boxes, {checks['arrows']} arrows, {checks['focal']} focal · {preset} {sw}x{sh}")
    if not out: sys.exit(2 if fails else 0)
    if fails and not force: print("not rendered (fix the FAILs, or --force)"); sys.exit(2)

    # -- scene, in paint order: containers, arrows, nodes, masks, text, markers, callouts
    scene = []
    base_of = lambda e: (PENCIL.get(e.get("role")) or (e["backgroundColor"],))[0]
    for z in containers:
        if pencil:
            scene.append(tag(["pzone", *rects[z["id"]][:2], z["width"], z["height"], base_of(z), INK, bool(z.get("dashed")),
                              (PENCIL.get(z["role"]) or (0, None))[1], SHADOW["zone"]], z["id"]))
            if "_pill" in z: scene.append(z["_pill"])
        else:
            scene.append(tag(["shape", "rectangle", *rects[z["id"]][:2], z["width"], z["height"], z["backgroundColor"], z["strokeColor"],
                              z["opacity"] / 100, bool(z.get("dashed")), 1.5, 0.9, False], z["id"]))
    scene += scene_frames + ([tag(["parrow", *op[1:]], OWN.get(id(op))) for op in scene_arrows] if pencil else scene_arrows)
    for n in nodes:
        if n["type"] == "tiles":                    # one op per tile, so a video can flip a single replica
            for k, (ox_, oy_, s_, r, t) in enumerate(n["_tiles"]):    # ox_/oy_: never reuse dx/dy, the page offset
                scene.append(tag(["pshape", "rectangle", n["x"] + ox_, n["y"] + oy_, s_, s_, PENCIL[r][0], PENCIL[r][1], INK, False, False,
                                  SHADOW["tile"]], f"{n['id']}:{k}"))
                if t: scene.append(tag(["text", n["x"] + ox_ + s_ / 2, n["y"] + oy_ + s_ / 2 + 0.5, t, 16, INK, "mono", 700, "middle", "central", 0],
                                       f"{n['id']}:{k}"))
            if "_name" in n:
                name, mono = n["_name"]
                scene_text.append(tag(["text", n["x"], n["y"] + 9, name, 15, TITLE_INK["component"] if pencil else INK, "mono" if mono else "sans",
                                       400 if mono else 600, "start", "central", 0], n["id"] + ":name"))
            continue
        if pencil and n.get("role") not in ("start", "end"):
            scene.append(tag(["pshape", n["type"], *rects[n["id"]][:2], n["width"], n["height"], base_of(n),
                              (PENCIL.get(n.get("role")) or (0, None))[1], INK, bool(n.get("dashed")), bool(n.get("pill")), SHADOW["node"]], n["id"]))
            continue
        scene.append(tag(["shape", n["type"], *rects[n["id"]][:2], n["width"], n["height"], n["backgroundColor"], n["strokeColor"],
                          n["opacity"] / 100, bool(n.get("dashed")), 2, 1.2, bool(n.get("pill"))], n["id"]))
        if n.get("role") == "end":
            scene.append(tag(["shape", "ellipse", n["x"] + 5, n["y"] + 5, n["width"] - 10, n["height"] - 10, INK, INK, 1, False, 1, 0.5, False], n["id"]))
    scene += scene_mask + scene_text + scene_marks + scene_callouts + scene_legend
    if pencil:
        restyle = {"frame": "pframe", "step": "pstep", "arrow": "parrow"}      # legend, frames and steps follow the pencil look too
        for i, op in enumerate(scene):
            if op[0] == "text":
                if id(op) not in KEPT: op[7] = bump(op[6], op[7])
            elif op[0] in restyle: scene[i] = tag([restyle[op[0]], *op[1:]], OWN.get(id(op)))
            elif op[0] == "shape" and op in scene_legend:                        # legend swatch: _, typ, x, y, w, h, fill, stroke, op, dashed, ...
                role = next((r for r, v in ROLES.items() if v[0] == op[6]), "component")
                base, hatch, _ = PENCIL.get(role, (op[6], None, None))
                scene[i] = tag(["pshape", op[1], op[2], op[3], op[4], op[5], base, hatch, INK, op[9], False, 2], "legend")
    slug = Path(out).stem
    page = (PAGE.replace("{W}", str(sw)).replace("{H}", str(sh)).replace("{DX}", f"{dx:.1f}").replace("{DY}", f"{dy:.1f}")
            .replace("{SLUG}", H.escape(slug)).replace("{TITLE}", H.escape(spec.get("title", slug)))
            .replace("{DESC}", H.escape(spec.get("alt", "")))
            .replace("{EXACT}", "" if preset == "fit" else ' data-exact="1"').replace("{SCENE}", json.dumps(scene))
            .replace("{BG}", '<rect width="100%" height="100%" fill="url(#dots)"/>' if pencil else ""))
    open(out, "w").write(page)
    if bake: write_bake(bake, scene)
    if scene_out:
        json.dump({"width": sw, "height": sh, "dx": round(dx, 1), "dy": round(dy, 1), "style": style, "pencil": PENCIL,
                   "ops": scene, "owners": [OWN.get(id(op)) for op in scene]}, open(scene_out, "w"))
    print(f"wrote {out}")

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>{TITLE}</title>
<link href="https://fonts.googleapis.com/css2?family=Karla:wght@400;600;800&family=Courier+Prime:wght@400;700&family=Zilla+Slab:ital,wght@0,600;0,700;1,400&display=block" rel="stylesheet">
<script src="https://unpkg.com/roughjs@4.6.6/bundled/rough.js"></script>
<style>body{margin:0;background:#FBF4E6} svg{display:block}</style></head><body>
<svg id="s" xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{SLUG}-title {SLUG}-desc"{EXACT}>
<title id="{SLUG}-title">{TITLE}</title><desc id="{SLUG}-desc">{DESC}</desc>
<defs><!--DEFS-->
 <filter id="grain" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="1.15" numOctaves="2" seed="7" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.4 1.75" result="a"/><feComposite in="SourceGraphic" in2="a" operator="in"/></filter>
 <filter id="graphite" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="3" result="w"/>
  <feDisplacementMap in="SourceGraphic" in2="w" scale="1.8" xChannelSelector="R" yChannelSelector="G" result="d"/>
  <feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="1" seed="11" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.5 1.6" result="a"/><feComposite in="d" in2="a" operator="in"/></filter>
 <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#E6CFA3"/></pattern>
<!--/DEFS--></defs>
<rect width="100%" height="100%" fill="#FBF4E6"/>{BG}<g id="g" transform="translate({DX},{DY})"></g></svg>
<script>
const SCENE={SCENE};
const svg=document.getElementById('s'), g=document.getElementById('g'), rc=rough.svg(svg), NS='http://www.w3.org/2000/svg';
let TARGET=g;
/*OPS*/const FAM={sans:"'Karla', sans-serif",mono:"'Courier Prime', monospace",slab:"'Zilla Slab', serif",slabi:"'Zilla Slab', serif"};
const add=n=>(TARGET.appendChild(n),n);
const dash=d=>d?{strokeLineDash:[8,6],disableMultiStroke:true}:{};
const rr=(x,y,w,h,r)=>`M${x+r},${y} h${w-2*r} a${r},${r} 0 0 1 ${r},${r} v${h-2*r} a${r},${r} 0 0 1 -${r},${r} h-${w-2*r} a${r},${r} 0 0 1 -${r},-${r} v-${h-2*r} a${r},${r} 0 0 1 ${r},-${r} z`;
const OPS={
 shape(type,x,y,w,h,fill,stroke,op,d,sw,rough_,pill){
  const o={fill,stroke,strokeWidth:sw,fillStyle:'solid',roughness:rough_,bowing:1,seed:Math.floor(x*7+y*13),...dash(d)};
  const draw=opt=>{
   if(type==='diamond') return rc.polygon([[x+w/2,y],[x+w,y+h/2],[x+w/2,y+h],[x,y+h/2]],opt);
   if(type==='ellipse') return rc.ellipse(x+w/2,y+h/2,w,h,opt);
   if(type==='cylinder'){const ry=Math.min(10,h*.18),rx=w/2;
     return rc.path(`M${x},${y+ry} V${y+h-ry} A${rx},${ry} 0 0 0 ${x+w},${y+h-ry} V${y+ry} A${rx},${ry} 0 0 0 ${x},${y+ry} A${rx},${ry} 0 0 0 ${x+w},${y+ry}`,opt);}
   return rc.path(rr(x,y,w,h,pill?h/2:Math.min(12,w/2,h/2)),opt);};
  add(draw(o)).setAttribute('opacity',op);},
 arrow(pts,stroke,d,head,seed){add(rc.linearPath(pts,{stroke,strokeWidth:2,roughness:1,seed,...dash(d)}));
  if(!head)return;const [a,b]=[pts[pts.length-2],pts[pts.length-1]],ang=Math.atan2(b[1]-a[1],b[0]-a[0]),L=12,W=6;
  const p1=[b[0]-L*Math.cos(ang)+W*Math.sin(ang),b[1]-L*Math.sin(ang)-W*Math.cos(ang)],p2=[b[0]-L*Math.cos(ang)-W*Math.sin(ang),b[1]-L*Math.sin(ang)+W*Math.cos(ang)];
  add(rc.linearPath([p1,b,p2],{stroke,strokeWidth:2,roughness:0.8,seed:seed+1}));},
 mask(x,y,w,h,fill){const r=document.createElementNS(NS,'rect');Object.entries({x,y,width:w,height:h,rx:3,fill}).forEach(([k,v])=>r.setAttribute(k,v));add(r);},
 text(x,y,t,fs,c,fam,w,anchor,base,ls,rot){const e=document.createElementNS(NS,'text');
  Object.entries({x,y,'font-size':fs,fill:c,'font-family':FAM[fam],'font-weight':w,'text-anchor':anchor}).forEach(([k,v])=>e.setAttribute(k,v));
  if(base)e.setAttribute('dominant-baseline',base);if(ls)e.setAttribute('letter-spacing',ls+'em');if(fam==='slabi')e.setAttribute('font-style','italic');
  if(rot)e.setAttribute('transform',`rotate(${rot} ${x} ${y})`);e.textContent=t;add(e);},
 // ---- pencil style: hard graphite shadow, paper base, coloured-pencil hatch, graphite outline
 pgeom(type,x,y,w,h,pill,opt){
  if(type==='diamond') return rc.polygon([[x+w/2,y],[x+w,y+h/2],[x+w/2,y+h],[x,y+h/2]],opt);
  if(type==='ellipse') return rc.ellipse(x+w/2,y+h/2,w,h,opt);
  if(type==='cylinder'){const ry=Math.min(10,h*.18),rx=w/2;
    return rc.path(`M${x},${y+ry} V${y+h-ry} A${rx},${ry} 0 0 0 ${x+w},${y+h-ry} V${y+ry} A${rx},${ry} 0 0 0 ${x},${y+ry} A${rx},${ry} 0 0 0 ${x+w},${y+ry}`,opt);}
  return rc.path(rr(x,y,w,h,pill?h/2:Math.min(4,w/2,h/2)),opt);},
 filt(n,f,op){n.setAttribute('filter',`url(#${f})`);if(op!=null)n.setAttribute('opacity',op);return n;},
 pshape(type,x,y,w,h,base,pencil,stroke,d,pill,sh){const seed=Math.floor(x*7+y*13);
  if(sh)OPS.filt(add(OPS.pgeom(type,x+sh,y+sh,w,h,pill,{fill:stroke,fillStyle:'solid',stroke:'none',roughness:0.5,seed})),'grain',0.92);
  add(OPS.pgeom(type,x,y,w,h,pill,{fill:base,fillStyle:'solid',stroke:'none',roughness:0.4,seed}));
  if(pencil)OPS.filt(add(OPS.pgeom(type,x+2,y+2,w-4,h-4,pill,{fill:pencil,fillStyle:'hachure',hachureGap:3.2,hachureAngle:-41,fillWeight:1.3,roughness:1.6,stroke:'none',seed:seed+3})),'grain',0.62);
  OPS.filt(add(OPS.pgeom(type,x,y,w,h,pill,{fill:'none',stroke,strokeWidth:2.6,roughness:0.8,bowing:0.5,seed:seed+5,...dash(d)})),'graphite');},
 pzone(x,y,w,h,base,stroke,d,pencil,sh){const seed=Math.floor(x*5+y*11);
  OPS.filt(add(rc.path(rr(x+sh,y+sh,w,h,4),{fill:stroke,fillStyle:'solid',stroke:'none',roughness:0.4,seed})),'grain',0.9);
  add(rc.path(rr(x,y,w,h,4),{fill:base,fillStyle:'solid',stroke:'none',roughness:0.3,seed}));
  if(pencil)OPS.filt(add(rc.path(rr(x+3,y+3,w-6,h-6,4),{fill:pencil,fillStyle:'hachure',hachureGap:5,hachureAngle:-41,fillWeight:1,roughness:1.4,stroke:'none',seed:seed+3})),'grain',0.28);
  OPS.filt(add(rc.path(rr(x,y,w,h,4),{fill:'none',stroke,strokeWidth:2.4,roughness:0.6,bowing:0.4,seed:seed+5,...dash(d)})),'graphite');},
 pill(x,y,w,h,fill,stroke,sh,rot){const gg=document.createElementNS(NS,'g');if(rot)gg.setAttribute('transform',`rotate(${rot} ${x+w/2} ${y+h/2})`);
  const seed=Math.floor(x*3+y*5),put=n=>(gg.appendChild(n),n);
  if(sh)OPS.filt(put(rc.path(rr(x+sh,y+sh,w,h,h/2),{fill:stroke,fillStyle:'solid',stroke:'none',roughness:0.3,seed})),'grain',0.9);
  put(rc.path(rr(x,y,w,h,h/2),{fill,fillStyle:'solid',stroke:'none',roughness:0.3,seed}));
  OPS.filt(put(rc.path(rr(x,y,w,h,h/2),{fill:'none',stroke,strokeWidth:1.8,roughness:0.5,seed:seed+1})),'graphite');add(gg);},
 parrow(pts,stroke,d,head,seed){OPS.filt(add(rc.linearPath(pts,{stroke,strokeWidth:3,roughness:0.9,bowing:0.6,seed,...dash(d)})),'graphite');
  if(!head)return;const [a,b]=[pts[pts.length-2],pts[pts.length-1]],ang=Math.atan2(b[1]-a[1],b[0]-a[0]),L=14,W=8;
  const p1=[b[0]-L*Math.cos(ang)+W*Math.sin(ang),b[1]-L*Math.sin(ang)-W*Math.cos(ang)],p2=[b[0]-L*Math.cos(ang)-W*Math.sin(ang),b[1]-L*Math.sin(ang)+W*Math.cos(ang)];
  OPS.filt(add(rc.linearPath([p1,b,p2],{stroke,strokeWidth:3,roughness:0.6,seed:seed+1,disableMultiStroke:true})),'graphite');},
 pframe(x,y,w,h,tw,th,split){const o={stroke:'#26211C',strokeWidth:2,roughness:0.6,bowing:0.4,seed:Math.floor(x+y*3)};
  OPS.filt(add(rc.path(rr(x,y,w,h,4),o)),'graphite');OPS.filt(add(rc.linearPath([[x,y+th],[x+tw-6,y+th],[x+tw,y+th-6],[x+tw,y]],o)),'graphite');
  if(split)OPS.filt(add(rc.line(x+8,split,x+w-8,split,{...o,strokeWidth:1.6,strokeLineDash:[7,6],disableMultiStroke:true})),'graphite');},
 pstep(x,y,n){const seed=Math.floor(x+y);
  OPS.filt(add(rc.circle(x+2,y+2,24,{fill:'#26211C',fillStyle:'solid',stroke:'none',roughness:0.4,seed})),'grain',0.9);
  add(rc.circle(x,y,24,{fill:'#C85A32',fillStyle:'solid',stroke:'none',roughness:0.4,seed}));
  OPS.filt(add(rc.circle(x,y,24,{fill:'none',stroke:'#26211C',strokeWidth:2,roughness:0.5,seed:seed+1})),'graphite');
  OPS.text(x,y+0.5,n,13,'#FFF9F1','mono',700,'middle','central',0);},
 tiles(x,y,list,sh){for(const [dx,dy,s,base,pencil,ink,t] of list){OPS.pshape('rectangle',x+dx,y+dy,s,s,base,pencil,ink,false,false,sh);
  if(t)OPS.text(x+dx+s/2,y+dy+s/2+0.5,t,16,ink,'mono',700,'middle','central',0);}},
 step(x,y,n){add(rc.circle(x,y,22,{fill:'#A84A28',fillStyle:'solid',stroke:'#A84A28',strokeWidth:1.5,roughness:0.6,seed:Math.floor(x+y)}));
  OPS.text(x,y+0.5,n,13,'#FFF9F1','mono',700,'middle','central',0);},
 leader(d){add(rc.path(d,{stroke:'#8F3D22',strokeWidth:1.5,roughness:0.8,strokeLineDash:[6,5],disableMultiStroke:true,seed:7}));},
 frame(x,y,w,h,tw,th,split){const o={stroke:'#79513C',strokeWidth:1.25,roughness:0.7,seed:Math.floor(x+y*3)};
  add(rc.path(rr(x,y,w,h,4),o));add(rc.linearPath([[x,y+th],[x+tw-6,y+th],[x+tw,y+th-6],[x+tw,y]],o));
  if(split)add(rc.line(x+8,split,x+w-8,split,{...o,strokeLineDash:[6,5],disableMultiStroke:true}));},
 rule(x0,y,x1){add(rc.line(x0,y,x1,y,{stroke:'#79513C',strokeWidth:1,roughness:0.5,seed:3}));},
 dot(x,y,r,fill){const c=document.createElementNS(NS,'circle');Object.entries({cx:x,cy:y,r,fill}).forEach(([k,v])=>c.setAttribute(k,v));add(c);},
};/*/OPS*/
const errs=[];for(const op of SCENE){try{OPS[op[0]](...op.slice(1));}catch(e){errs.push(op[0]+': '+e.message);}}
if(errs.length){console.error(errs.join(' | '));OPS.text(12,44,'RENDER ERROR in '+errs[0],16,'#C85A32','sans',700,'start','',0);}
Promise.all(["600 16px Karla","800 16px Karla","400 16px 'Courier Prime'","700 16px 'Courier Prime'","600 20px 'Zilla Slab'","700 20px 'Zilla Slab'","italic 400 17px 'Zilla Slab'"].map(f=>document.fonts.load(f))).then(r=>{
 const fell=r.some(a=>!a.length);
 if(fell)OPS.text(12,24,'FONTS DID NOT LOAD - do not ship this PNG',18,'#C85A32','sans',700,'start','',0);
 svg.setAttribute('data-drawn',errs.length?'render-error':fell?'font-fallback':'ok');});
</script></body></html>"""

def write_bake(path, scene):
    """Each drawn op as a plain Excalidraw element (paper masks and hop bumps aside), in spec coordinates."""
    out = []
    def el(kind, **kw):
        base = {"type": kind, "id": f"e{len(out) + 1}", "strokeColor": ARROW, "backgroundColor": "transparent",
                "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100}
        out.append({**base, **kw})
    def poly(kind, pts, **kw):
        x0, y0 = pts[0]; rel = [[px - x0, py - y0] for px, py in pts]
        el(kind, x=x0, y=y0, points=rel, width=max(p[0] for p in rel) - min(p[0] for p in rel),
           height=max(p[1] for p in rel) - min(p[1] for p in rel), **kw)
    for op in scene:
        k = op[0]
        if k == "shape":
            _, typ, x, y, w, h, fill, stroke, opac, dashed, sw, _, _ = op
            el("rectangle" if typ == "cylinder" else typ, x=x, y=y, width=w, height=h, backgroundColor=fill, strokeColor=stroke,
               opacity=round(opac * 100), strokeWidth=sw, strokeStyle="dashed" if dashed else "solid",
               **({"roundness": {"type": 3}} if typ in ("rectangle", "cylinder") else {}))
        elif k == "pshape":
            _, typ, x, y, w, h, base, _p, stroke, dashed, _pill, _sh = op
            el("rectangle" if typ in ("cylinder", "tiles") else typ, x=x, y=y, width=w, height=h, backgroundColor=base,
               strokeColor=stroke, strokeWidth=2, strokeStyle="dashed" if dashed else "solid", fillStyle="hachure" if _p else "solid")
        elif k == "pzone":
            _, x, y, w, h, base, stroke, dashed, _p, _sh = op
            el("rectangle", x=x, y=y, width=w, height=h, backgroundColor=base, strokeColor=stroke, strokeStyle="dashed" if dashed else "solid")
        elif k == "pill":
            _, x, y, w, h, fill, stroke, _sh, rot = op
            el("rectangle", x=x, y=y, width=w, height=h, backgroundColor=fill, strokeColor=stroke, strokeWidth=1,
               roundness={"type": 3}, angle=math.radians(rot))
        elif k == "tiles":
            _, x, y, lst, _sh = op
            for dx, dy, s, base, _p, ink, t in lst:
                el("rectangle", x=x + dx, y=y + dy, width=s, height=s, backgroundColor=base, strokeColor=ink)
                if t: el("text", x=x + dx + 6, y=y + dy + s / 2 - 8, width=s - 12, height=16, text=t, fontSize=16, fontFamily=3,
                         textAlign="center", verticalAlign="middle", strokeColor=ink)
        elif k in ("arrow", "parrow"):
            _, pts, stroke, dashed, head, _ = op
            poly("arrow" if head else "line", pts, strokeColor=stroke, strokeStyle="dashed" if dashed else "solid",
                 **({"endArrowhead": "arrow"} if head else {}))
        elif k == "text":
            _, x, y, t, fs, c, fam, w, anchor, base, ls = op[:11]
            width = text_w(t, fam, w, fs, ls, exact=True)
            el("text", x=x - {"start": 0, "middle": width / 2, "end": width}[anchor], y=y - fs * (0.65 if base else 0.95),
               width=width, height=fs * 1.25, text=t, fontSize=fs, fontFamily=3 if fam == "mono" else 2,
               textAlign="left", verticalAlign="top", strokeColor=c)
        elif k in ("frame", "pframe"):
            _, x, y, w, h, tw, th, split = op
            el("rectangle", x=x, y=y, width=w, height=h, strokeColor="#79513C", strokeWidth=1)
            poly("line", [[x, y + th], [x + tw - 6, y + th], [x + tw, y + th - 6], [x + tw, y]], strokeColor="#79513C", strokeWidth=1)
            if split: poly("line", [[x + 8, split], [x + w - 8, split]], strokeColor="#79513C", strokeWidth=1, strokeStyle="dashed")
        elif k in ("step", "pstep"):
            _, x, y, t = op
            el("ellipse", x=x - 11, y=y - 11, width=22, height=22, backgroundColor="#A84A28", strokeColor="#A84A28")
            el("text", x=x - 4, y=y - 8, width=8, height=16, text=t, fontSize=13, fontFamily=3, textAlign="left", verticalAlign="top", strokeColor="#FFF9F1")
        elif k == "leader":
            v = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", op[1])]      # M x,y Q cx,cy x2,y2
            poly("line", [[v[0], v[1]], [v[2], v[3]], [v[4], v[5]]], strokeColor=HAND, strokeWidth=1.5, strokeStyle="dashed", roundness={"type": 2})
        elif k == "dot":
            _, x, y, r, fill = op
            el("ellipse", x=x - r, y=y - r, width=2 * r, height=2 * r, backgroundColor=fill, strokeColor=fill, strokeWidth=1)
        elif k == "rule":
            poly("line", [[op[1], op[2]], [op[3], op[2]]], strokeColor="#79513C", strokeWidth=1)
    json.dump({"type": "excalidraw", "version": 2, "source": "daniel-diagram", "elements": out,
               "appState": {"viewBackgroundColor": CANVAS}}, open(path, "w"))

if __name__ == "__main__":
    main()
