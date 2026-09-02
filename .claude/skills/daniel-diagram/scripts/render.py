#!/usr/bin/env python3
"""Render a daniel-diagram JSON spec to a rough.js HTML page.

usage: render.py spec.json out.html [--bake baked.excalidraw]
"""
import json, sys, math

ROLES = {
    "zone-warm": ("#F7EDDA", "#79513C", "#79513C"),
    "zone-light": ("#FDF7EA", "#3F6472", "#3F6472"),
    "component": ("#C9D6DC", "#3F6472", "#26211C"),
    "group": ("#A8AE8B", "#555E3C", "#26211C"),
    "focal": ("#EFCDB4", "#C85A32", "#8F3D22"),
}
CANVAS = "#FBF4E6"; ARROW = "#51463C"
SANS = "'Karla', sans-serif"; MONO = "'Courier Prime', monospace"

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1]))
    els = spec["elements"]
    # resolve colours; remember text colour per box for texts that omit it
    box_text = {}
    for e in els:
        if e["type"] == "rectangle":
            fill, stroke, tc = ROLES.get(e.get("role", ""), (e.get("backgroundColor", "#fff"), e.get("strokeColor", ARROW), "#26211C"))
            e.setdefault("backgroundColor", fill); e.setdefault("strokeColor", stroke)
            if e.get("role") == "group": e.setdefault("opacity", 75)
            box_text[e["id"]] = tc
    js = []
    for e in els:
        if e["type"] == "rectangle":
            js.append(f"rect({e['x']},{e['y']},{e['width']},{e['height']},'{e['backgroundColor']}','{e['strokeColor']}',{e.get('opacity',100)/100});")
        elif e["type"] == "arrow":
            pts = [[e["x"] + p[0], e["y"] + p[1]] for p in e["points"]]
            js.append(f"arrow({json.dumps(pts)},'{e.get('strokeColor', ARROW)}');")
    for e in els:
        if e["type"] != "text": continue
        sans = e.get("font") == "sans"
        fam = SANS if sans else MONO
        weight = e.get("fontWeight", "600" if sans else "400")
        anchor = e.get("anchor", "start")
        color = e.get("strokeColor") or box_text.get(e["id"][:-1], "#26211C")
        fs = e["fontSize"]
        for i, line in enumerate(e["text"].split("\n")):
            y = e["y"] + fs * 0.95 + i * fs * 1.25
            js.append(f"text({e['x']},{y},{json.dumps(line)},{fs},'{color}',\"{fam}\",'{weight}','{anchor}');")
    w = max(e["x"] + e.get("width", 0) for e in els if e["type"] != "arrow") + 40
    h = max(e["y"] + e.get("height", 0) for e in els if e["type"] != "arrow") + 40
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Karla:wght@400;600&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/roughjs@4.6.6/bundled/rough.js"></script>
<style>body{{margin:0;background:{CANVAS}}} svg{{display:block}}</style></head><body>
<svg id="s" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="{CANVAS}"/></svg>
<script>
const svg=document.getElementById('s'); const rc=rough.svg(svg);
const rr=(x,y,w,h,r)=>`M${{x+r}},${{y}} h${{w-2*r}} a${{r}},${{r}} 0 0 1 ${{r}},${{r}} v${{h-2*r}} a${{r}},${{r}} 0 0 1 -${{r}},${{r}} h-${{w-2*r}} a${{r}},${{r}} 0 0 1 -${{r}},-${{r}} v-${{h-2*r}} a${{r}},${{r}} 0 0 1 ${{r}},-${{r}} z`;
function rect(x,y,w,h,fill,stroke,op){{const g=rc.path(rr(x,y,w,h,12),{{fill,stroke,strokeWidth:2,fillStyle:'solid',roughness:1.2,bowing:1,seed:Math.floor(x*7+y*13)}});g.setAttribute('opacity',op);svg.appendChild(g);}}
function arrow(pts,stroke){{svg.appendChild(rc.linearPath(pts,{{stroke,strokeWidth:2,roughness:1,seed:Math.floor(pts[0][0]*3+pts[0][1])}}));
 const [a,b]=[pts[pts.length-2],pts[pts.length-1]];const ang=Math.atan2(b[1]-a[1],b[0]-a[0]);const L=12,W=6;
 const p1=[b[0]-L*Math.cos(ang)+W*Math.sin(ang),b[1]-L*Math.sin(ang)-W*Math.cos(ang)];const p2=[b[0]-L*Math.cos(ang)-W*Math.sin(ang),b[1]-L*Math.sin(ang)+W*Math.cos(ang)];
 svg.appendChild(rc.linearPath([p1,b,p2],{{stroke,strokeWidth:2,roughness:0.8}}));}}
function text(x,y,t,fs,c,fam,w,anchor){{const e=document.createElementNS('http://www.w3.org/2000/svg','text');e.setAttribute('x',x);e.setAttribute('y',y);e.setAttribute('font-size',fs);e.setAttribute('fill',c);e.setAttribute('font-family',fam);e.setAttribute('font-weight',w);e.setAttribute('text-anchor',anchor);e.textContent=t;svg.appendChild(e);}}
{chr(10).join(js)}
</script></body></html>"""
    open(sys.argv[2], "w").write(html)
    if "--bake" in sys.argv:
        out = sys.argv[sys.argv.index("--bake") + 1]
        baked = []
        for e in els:
            b = {k: v for k, v in e.items() if k not in ("role", "font", "anchor", "fontWeight")}
            if e["type"] == "text":
                b.setdefault("fontFamily", 1); b.setdefault("textAlign", "left"); b.setdefault("verticalAlign", "top")
                lines = e["text"].split("\n"); b.setdefault("width", max(len(l) for l in lines) * e["fontSize"] * 0.5); b.setdefault("height", e["fontSize"] * 1.25 * len(lines))
                b.setdefault("strokeColor", box_text.get(e["id"][:-1], "#26211C"))
            if e["type"] == "rectangle": b.setdefault("roundness", {"type": 3}); b.setdefault("fillStyle", "solid")
            if e["type"] == "arrow": b.setdefault("strokeColor", ARROW); b.setdefault("strokeWidth", 2); b.setdefault("endArrowhead", "arrow")
            baked.append(b)
        json.dump({"type": "excalidraw", "version": 2, "source": "daniel-diagram", "elements": baked, "appState": {"viewBackgroundColor": CANVAS}}, open(out, "w"))
    print(f"wrote {sys.argv[2]} ({w}x{h})")

if __name__ == "__main__":
    main()
