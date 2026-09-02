#!/usr/bin/env python3
"""Render terminal output as the DanielSite article code block (.article-code), ready for capture.sh.

usage: terminal.py output.txt out.html [--label bash] [--right ""] [--width 660] [--font 13.5]
Render at the article column width so the PNG is not scaled down on the page; trim columns you do not discuss before rendering.
Lines starting with "$ " are prompts. Words in OK/ERR lists get the Prism string/keyword inks.
"""
import sys, html, argparse

OK = ("Running", "Completed", "Succeeded")
ERR = ("ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "Error", "Failed", "Pending", "Warning", "NotReady")

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--label", default="bash"); ap.add_argument("--right", default="")
ap.add_argument("--width", type=int, default=660, help="CSS px, the article column width on danieldias.dev")
ap.add_argument("--font", type=float, default=12, help="px; 15.5 matches the code block, 12 fits ~85 columns in a 660px column")
a = ap.parse_args()

lines = []
for l in open(a.src).read().rstrip("\n").split("\n"):
    e = html.escape(l)
    if l.startswith("$ "):
        e = f'<span class="p">$</span> <span class="c">{html.escape(l[2:])}</span>'
    for w in OK:  e = e.replace(w, f'<span class="ok">{w}</span>')
    for w in ERR: e = e.replace(w, f'<span class="err">{w}</span>')
    lines.append(e)

# Values copied from paper.css: .article-body pre, .article-code__bar, .article-code__name, .article-code__copy, Prism inks
open(a.out, "w").write(f'''<meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet"><style>
body{{margin:0;background:#EEDFC7;padding:6px 10px 10px 6px;display:inline-block}}
.code{{width:{a.width}px;border-radius:4px;box-shadow:4px 4px 0 rgba(0,0,0,.15)}}
.bar{{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:6px 16px 5px;box-sizing:border-box;background:#2B2824;border:1px solid #3A3530;border-bottom:none;border-radius:4px 4px 0 0;min-height:44px}}
.name{{font:13.5px 'Courier Prime',monospace;letter-spacing:.08em;text-transform:uppercase;color:#9C9184}}
.right{{font:700 13.5px 'Courier Prime',monospace;letter-spacing:.14em;text-transform:uppercase;color:#E08A5E}}
pre{{margin:0;padding:22px 18px 22px 22px;background:#23211E;border:1px solid #3A3530;border-radius:0 0 4px 4px;font:{a.font}px/1.7 'Courier Prime',monospace;color:#E8DFD2;white-space:pre-wrap;word-break:normal;overflow-wrap:break-word;tab-size:4}}
.p{{color:#E08A5E;font-weight:700}}.c{{color:#E8DFD2}}.err{{color:#DE8B62;font-weight:700}}.ok{{color:#C9CFA4}}
</style><div class="code"><div class="bar"><span class="name">{html.escape(a.label)}</span><span class="right">{html.escape(a.right)}</span></div><pre>{chr(10).join(lines)}</pre></div>''')
print(f"wrote {a.out}")
