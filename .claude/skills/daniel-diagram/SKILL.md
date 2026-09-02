---
name: daniel-diagram
description: Draw diagrams in Daniel's house style — Excalidraw-like hand-drawn boxes and arrows, DanielSite palette (tokens.css) and fonts (Karla + Courier Prime), rendered to PNG. Use whenever Daniel asks for a diagram, architecture drawing, flow, or "desenha isso" for a blog post, README, or study notes.
---

# Daniel diagram

Repo copy of the `daniel-diagram` skill. Every diagram and terminal print in this repo is produced with it, so the style stays consistent across sections.

Hand-drawn look (rough.js, same feel as Excalidraw) with the DanielSite paper palette and fonts. Output is a PNG ready for `wwwroot/img/posts/` or a repo `img/` folder.

## Workflow

1. **Sketch the content first, not the style.** Nodes, containment, arrows. Ask only if the subject is ambiguous. Prefer few boxes: above ~12 shapes, split in two diagrams.
2. **Write the spec** as a JSON file in the scratchpad using the element format below. It is Excalidraw-compatible on purpose: the same file can be previewed with the `excalidraw` MCP (`create_view`) and committed as `<name>.excalidraw` next to the PNG.
3. **Render**: `python3 .claude/skills/daniel-diagram/scripts/render.py spec.json out.html [--bake spec.excalidraw]`
4. **Capture** to PNG at 2x. Either `scripts/capture.sh out.html out.png` (Chrome headless, waits for Google Fonts), or agent-browser when available: open `file://…/out.html`, viewport 1000×(height+40) at scale 2, wait for `networkidle`, screenshot the `svg` element, close the browser.
5. **Show Daniel the PNG before placing it** (SendUserFile + `open`). He decides; then copy the PNG, the `.excalidraw` spec and the `.html` source to the destination.

Do not use the `diagram-design` skill for these; Daniel tried it and prefers this style. Do not use excalidraw.com for the final render: it cannot load the site fonts.

## Palette (from DanielSite `wwwroot/css/tokens.css`)

Use `role` on a rectangle; the renderer maps it. Explicit `backgroundColor`/`strokeColor` override when needed.

| role | use | fill | stroke | text |
|---|---|---|---|---|
| `canvas` | page background | `#FBF4E6` paper-sheet | – | – |
| `zone-warm` | outer scope (cluster, control plane, system) | `#F7EDDA` | `#79513C` ink-400 | `#79513C` |
| `zone-light` | inner scope (node, service boundary) | `#FDF7EA` | `#3F6472` blue-500 | `#3F6472` |
| `component` | boxes that do work (API server, kubelet, service) | `#C9D6DC` blue-300 | `#3F6472` | `#26211C` ink-900 |
| `group` | grouping inside a zone (pod, module) | `#A8AE8B` olive-300 @ 75% | `#555E3C` olive-600 | `#26211C` |
| `focal` | the 1–3 things the reader should look at (client, container, runtime) | `#EFCDB4` card-cloud | `#C85A32` terracotta-500 | `#8F3D22` terracotta-700 |
| arrows | all connectors | – | `#51463C` ink-500, width 2 | – |

Rules: terracotta is an accent, not a category; do not paint more than three focal boxes. Zones nest warm → light. Never introduce colours outside tokens.css.

## Typography

- **Karla 600** for zone and group titles (`Control plane`, `Node`, `Pod: nginx`). Left-aligned at the top-left of the box, 18px zones / 16px groups. Set `"font": "sans"` on the text element.
- **Courier Prime 400** for anything technical: component names, commands, image names, `container: nginx`. Centred in its box, 14–18px. Default when `font` is omitted.
- No third font. Zilla Slab is for page headings, not diagrams.

## Element format (subset of Excalidraw)

```json
{"type":"excalidraw","version":2,"source":"daniel-diagram",
 "appState":{"viewBackgroundColor":"#FBF4E6"},
 "elements":[
  {"type":"rectangle","id":"cp","x":200,"y":120,"width":500,"height":230,"role":"zone-warm"},
  {"type":"text","id":"cpt","x":212,"y":128,"text":"Control plane","fontSize":18,"font":"sans"},
  {"type":"rectangle","id":"api","x":380,"y":160,"width":140,"height":56,"role":"component"},
  {"type":"text","id":"apit","x":450,"y":178,"text":"API server","fontSize":16,"anchor":"middle"},
  {"type":"arrow","id":"a1","x":450,"y":76,"points":[[0,0],[0,44]]}
 ]}
```

- Order = z-order. Zones first, then arrows, then boxes, then text.
- Arrows are polylines in the element's local coordinates; use right angles (`[0,0],[0,20],[dx,20],[dx,40]`). Arrowhead is added at the last point.
- `anchor: "middle"` centres text on `x`; omit for left-aligned titles. Multi-line text uses `\n`.
- When exporting the spec for real Excalidraw, the renderer's extra keys (`role`, `font`, `anchor`) are ignored by Excalidraw; add `backgroundColor`/`strokeColor` too if the `.excalidraw` must look right there (`render.py --bake` writes that copy).

## Terminal prints

Command output goes in a print that mirrors the site's article code block (`.article-code` in `paper.css`): bar `#2B2824` with the label in Courier Prime uppercase `#9C9184`, body `#23211E`, text `#E8DFD2` 15.5px/1.7, offset shadow `4px 4px 0 rgba(0,0,0,.15)`, Prism inks only: prompt and errors in `#E08A5E`/`#DE8B62`, good states in `#C9CFA4`. No window dots, no paper, no ruled lines, no hand-drawn border. Daniel rejected paper/torn-note and generic dark-terminal looks for prints: the print must be indistinguishable from a code block on the page.

1. Save the real output to a `.txt` with prompt lines starting with `$ `.
2. `python3 scripts/terminal.py out.txt out.html --label "bash · kind-ckad"`
3. `scripts/capture.sh out.html out.png` (2x, cropped to content).

See `examples/k8s-architecture.json` for the reference diagram (kubectl → control plane → node → pods).
