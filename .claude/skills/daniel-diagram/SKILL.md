---
name: daniel-diagram
description: Draw diagrams in Daniel's house style — Excalidraw-like hand-drawn boxes and arrows, DanielSite palette (tokens.css) and fonts (Karla, Courier Prime, Zilla Slab), checked by a lint and rendered to PNG at the width it is read. Use whenever Daniel asks for a diagram, architecture drawing, flow, sequence or request diagram, state machine, "desenha isso", or a print of terminal output for a blog post, README, or study notes.
---

# Daniel diagram

Canonical copy: `~/.codex/skills/daniel-diagram/` (shared by Codex and Claude Code; Claude's `~/.claude/skills/daniel-diagram` points here). Edit only this copy.

Two looks, same geometry and lint (`"style"` in the spec):

- **`pencil` — the default (approved 28/09/2026).** Blockframe composition drawn in coloured pencil: graphite outlines, a hard graphite shadow under every box and zone, the role colour laid in as pencil hatching over a paper base, zone and group titles as pills straddling the border, the `sub` line in a small pill inside its box, arrow labels in pills and the accent arrow's label as a tilted stamp, on a dotted paper ground. Daniel rejected the plain rough.js render for looking flat ("tá bem feio"); this is the replacement.
- **`sketch` — legacy.** The earlier plain rough.js strokes, kept so old specs can re-render unchanged. Don't start new diagrams in it.

Both use rough.js with the DanielSite paper palette and fonts. Output is a PNG for `wwwroot/img/posts/` or a repo `img/` folder, drawn at the width it will be read so its text matches the page. Terminal output has its own workflow: `references/terminal.md`.

## Before drawing

- **Would a paragraph or a three-column table say it?** Then don't draw. One box is a sentence; a list is a list.
- **Deleting is the best edit.** Two boxes that always travel together are one box. An arrow whose relation the layout already shows goes. The diagram is done when nothing more can be removed.
- **Pick one grammar** — architecture, flow, sequence, state, nesting, comparison — and read its section in `references/grammars.md`.
- **State the plan in one line** before writing the spec: grammar, size, what gets cut. Daniel redirects there, not after the render. Ask only if the subject itself is ambiguous.

## Workflow

1. Write the spec (format below) as JSON in the scratchpad.
2. `python3 ~/.codex/skills/daniel-diagram/scripts/render.py spec.json out.html [--bake out.excalidraw]` checks, then renders. Fix every FAIL; keep a WARN only for a reason you can say. Without `out.html` it only checks.
3. `~/.codex/skills/daniel-diagram/scripts/capture.sh out.html out.png` — Chrome headless at 2x. It refuses to write the PNG if the fonts fell back or the page did not finish drawing. It saves a 256-colour PNG whenever that stays faithful (PSNR ≥ 40 dB): the pencil grain is noise PNG can't compress, and the palette brings a 660px diagram from ~940 KB to ~120–250 KB with no visible change.
4. **Look at the PNG yourself** (read the image) against the taste gate below before anyone else sees it. The lint knows geometry, not meaning.
5. **Show Daniel the PNG before placing it** (`open`). He decides; then copy the PNG, the `.json` spec and the `.html` to the destination — for a post, `wwwroot/img/posts/<name>.png` plus `docs/design/posts/<slug>/`.
6. For a post, write the alt text in each edition: one sentence about what the diagram says, not which shapes it has, read as a native speaker would.

Do not use the `diagram-design` skill or excalidraw.com for the final render; what was worth taking from diagram-design is already here.

## Size: draw at the width it is read

| `size` | canvas | use |
|---|---|---|
| `article` (default) | 660px exact → 1320px PNG, shown 1:1 | DanielSite post (the article column) |
| `readme` | 880px exact | GitHub README |
| `fit` | content + 24px on each side | study notes; warns when it would shrink in the article column |
| `video` | 660×371 exact (16:9) | a diagram that daniel-video animates; fills the video frame, and the post shows it 1:1 |

Content must fit the canvas minus 24px each side (612px for `article`), or the lint fails. Narrow the layout, split it or cut — never shrink the type. A 2351px PNG squeezed into the 660px column rendered 14px text at 8px; that shipped once.

## Palette (DanielSite `wwwroot/css/tokens.css`)

| role | use | fill | stroke | text |
|---|---|---|---|---|
| `zone-warm` | outer scope (cluster, control plane, a Docker host) | `#F7EDDA` | `#79513C` | `#79513C` |
| `zone-light` | inner scope (node, service boundary) | `#FDF7EA` | `#3F6472` | `#3F6472` |
| `group` | grouping inside a zone (pod, module) | `#A8AE8B` @ 75% | `#555E3C` | `#26211C` |
| `component` | boxes that do work | `#C9D6DC` | `#3F6472` | `#26211C` |
| `focal` | the 1–3 things the reader must look at | `#EFCDB4` | `#C85A32` | `#8F3D22` |
| `external` | outside your system (third-party API, the caller); dashed | `#FBF4E6` | `#79513C` | `#51463C` |
| `start` | the first state or step: a solid dot | `#26211C` | `#26211C` | – |
| `end` | a terminal state: a ring with a solid centre | `#FBF4E6` | `#26211C` | – |
| arrows | ink 2px; `accent` = terracotta for the one main path | – | `#51463C` / `#C85A32` | `#51463C` |

- Terracotta is an accent, not a category: one or two focal boxes (three at most) and one accent path. Something outside your system is `external`, not focal.
- Zones nest warm → light and draw lighter (1.5px, calmer) than the boxes inside them.
- In `pencil` the same roles draw as paper base + pencil hatch + graphite outline: `component` #DCE4E8 hatched #46708D, `focal` #F3E7D0 hatched #C85A32, `group` #EEDFC7 hatched #66704B; zones are paper cards (#F7EDDA warm, #FFF9F1 light) whose title pill takes #EFCDB4 / #C9D6DC (groups #A8AE8B). Arrows are graphite #26211C, the accent path terracotta. The hard shadows (6px boxes, 8px zones) fall into the 24px page margin and don't count against the width.
- An explicit `backgroundColor` / `strokeColor` must be a tokens.css colour; the lint rejects anything else. The roles above are the diagram palette; reach past them only for a reason the post names.

## Typography

| what | face | spec key |
|---|---|---|
| a name — concept, component, role | Karla 600, 16px | `label` |
| anything you could type in a terminal or in code | Courier Prime, 16px | `code` |
| technical second line | Courier Prime 13.5px, lighter ink | `sub` |
| zone and group titles | Zilla Slab 600, 20 / 17px (a `code` title stays Courier) | container `label` |
| arrow labels, frame operators | Courier Prime 13px uppercase, tracked (`code` keeps its case) | arrow `label` / `code` |
| margin note | Zilla Slab italic 17px, terracotta-700 | `callout` |

In `pencil` the same faces run heavier, as Daniel asked on 28/09/2026 ("bold mais forte"): Karla 800 for names, Courier Prime Bold for `code`, `sub`, arrow labels and tiles, Zilla Slab 700 for zone and group titles; callouts stay Zilla italic 400. The lint measures the bold cuts too. Free text keeps a `fontWeight` its spec sets.

**Words on the drawing** follow `humanizer` and keep only the spine of `eli5`: a label is a name or identifier a person would say out loud, never a slogan, a staged contrast or a caption ("Node = ride", "It does not reserve a seat" are post text, not labels). Each term sits on the piece it names. An analogy only when there is no plain word, one per diagram, an adult one, and in the post's own words. The explanation lives in the post, written with `daniel-writing`.

"Chat use case" is a `label`; `AskChatUseCase.Ask` is `code`. Nothing below 13px. Every face is self-hosted by the site with latin-ext, so Maltese renders; no other face goes in a diagram.

**No sentences in the image.** The PNG ships unchanged in all five editions, so its text is limited to identifiers and technical terms the editions keep in English (the post's alt texts are the test: if they keep the word, the image may). Titles, explanations and captions go in the post. The lint warns above four words.

## Spec format (an Excalidraw-compatible subset)

```json
{"type":"excalidraw","version":2,"source":"daniel-diagram","size":"article","style":"pencil",
 "title":"How kubectl reaches a container","alt":"kubectl talks to the API server, …",
 "elements":[
  {"type":"rectangle","id":"cp","x":24,"y":112,"width":612,"height":240,"role":"zone-warm","label":"Control plane"},
  {"type":"rectangle","id":"kubectl","cx":328,"y":24,"role":"focal","code":"kubectl"},
  {"type":"rectangle","id":"api","cx":328,"y":156,"role":"component","label":"API server"},
  {"type":"cylinder","id":"etcd","x":60,"y":264,"width":128,"role":"component","code":"etcd"},
  {"type":"arrow","id":"a1","from":"kubectl","to":"api","label":"https"},
  {"type":"arrow","id":"a2","from":"api","to":"etcd"},
  {"type":"callout","id":"n1","x":424,"y":168,"text":"only etcd client","to":"api"}
 ]}
```

`title` and `alt` become the SVG's `<title>` and `<desc>`; `alt` is also the English alt text.

**Shapes** — `rectangle`, `cylinder` (where data lives), `diamond` (a decision), `ellipse`:
- `label` / `code` / `sub` put the text inside, centred; `width` / `height` default to the text plus padding. Place with `x` or `cx`, `y` or `cy`; explicit values stay on the 4px grid.
- `role` from the palette; `pill: true` for whoever starts things (a person, a client); `dashed: true` for optional or outside (automatic on `external`).
- A container's `label` (or `code`) is its title, top-left; `titleAt: "right"` when arrows come in on the left. Leave about 44px above the first child.

**Arrows**:
- `from` / `to` name shapes and the renderer routes with right angles: top/bottom ports whenever there is vertical room, sides otherwise. Arrows leaving the same side share a trunk (a fork), arrows entering the same side get separate entry points, and an arrow into a container enters straight.
- Overrides: `fromSide` / `toSide` (`top|bottom|left|right`; the same side on both makes a U around), `mid` (where the elbow runs), `fromAt` / `toAt` (0–1 along the edge).
- `label` (words, shown uppercase) or `code` (an identifier, as written). Labels get a paper mask, 6px off the line and slid off zone borders; move one with `labelSide`, `labelSegment` or `labelAt` (0–1).
- `accent: true` for the one main path; `step: n` for a numbered marker the post can cite ("in step 3…"); `dashed: true` for async, optional or a response.
- `points` with `x`, `y` is a manual right-angle polyline, for sequences and whatever the router can't do; `head: false` drops the arrowhead (lifelines).
- A crossing gets an automatic hop on the dashed (or later) arrow. Prefer a layout without one.

**Tiles** — `{"type":"tiles","id","x","y","cols","items":["v1", {"code":"v2","role":"focal"}], "code":"web-green"}`: a grid of small same-size tiles for replicas, pods or shards, the thing a box can't show (9 × v1 + 1 × v2 *is* the canary). `size` (44) and `gap` (10) are optional; each item is a code string (role `component`) or `{code, role}`. An optional `code` / `label` names the grid above it (the Deployment). Arrows aim at the grid, not the name. The whole grid counts as one box in the budget; tile text must fit a tile.

**Other elements**:
- `callout` — `x`, `y`, `text` and `to` (a shape id) or `at` `[x, y]`: a margin note on a dashed leader. Two at most, never over a box, and still no sentences.
- `frame` — `x`, `y`, `width`, `height`, `op` (`alt|opt|loop`), `guard`; for `alt` also `split` (y of the dashed divider) and `guard2`.
- top-level `legend` — `[{"line":"solid|dashed|accent","text":"…"}, {"box":"<role>","text":"…"}]`, a strip under the diagram. Only when a colour or a dash carries meaning no label states.
- `text` — free text (`x`, `y`, `text`, `fontSize`, `font`: `sans|mono`, `anchor`, optional `fontWeight`, kept as given in pencil). Rarely needed: text belongs in its box.

The renderer fixes the paint order (containers, arrows, boxes, labels, text, callouts), so element order no longer matters. Excalidraw ignores the extra keys; `--bake` writes every drawn element (frames, legend, steps and callouts included; paper masks and hop bumps left out) as a plain `.excalidraw` to preview with the `excalidraw` MCP (`create_view`).

## Budget

≤10 boxes, ≤12 arrows, ≤4 zones and groups, ≤3 focal, ≤2 callouts, ≤6 steps. Over budget, cut in this order and stop as soon as it fits:

1. decoration — notes, a second title, anything that is neither a component nor a relation;
2. duplicates — three identical workers become one box named for the set;
3. leaf clusters — a group whose children are all leaves becomes the group;
4. dead ends that don't change the story — a log sink, an archive;
5. cross-cutting infrastructure — logging, metrics, secrets, CI — unless it is the subject;
6. still over: split into an overview and one detail diagram.

## What the lint checks

- **FAIL**: a malformed element (missing `id` or required keys, an unknown type, side, anchor or legend role, a fraction outside 0–1, a `labelSegment` the arrow doesn't have, a frame `split` outside the frame) — reported, never a traceback; content wider than the size; text that doesn't fit its box; two boxes overlapping; an arrow behind a box it neither starts nor ends at, or through its own end box; an arrow under a zone title; a label on a box; two texts colliding, free text included; a diagonal manual segment; a colour outside tokens.css; an unknown role.
- **WARN**: over budget; off the 4px grid; a box across a zone border; free text over a box that has its own text; a label on a zone border or touching another arrow; an arrow running along a zone border; a jog of a few px (align the centres); two arrows sharing a stroke; an arrow crossing a zone it neither starts nor ends in; more than four words anywhere, legend and guards included; a manual end touching nothing.
- **In the page**: fonts that fell back, a script error, or a screenshot of the wrong size stop `capture.sh`, which also deletes the old PNG first so a failed capture can't pass for a new one. Terminal prints go through the same font gate. `CHROME=/path` points it at another browser.

## Taste gate (look at the PNG)

- Could a box, an arrow or a label go? Delete it.
- Is terracotta on the one thing that matters, with one accent path at most?
- Can the eye follow the main path without backtracking?
- Is every label a name or an identifier, and every identifier spelled exactly as in the code?
- Is the space even: zones hugging their children, siblings aligned, no empty quadrant?
- Would the alt text alone tell a reader what the picture says?

## Anti-patterns

- Everything in Courier, or everything in Karla: the split between names and identifiers carries meaning.
- Terracotta as "important too", or as a category.
- A diagram drawn wide and left for the browser to shrink.
- Unlabelled arrows whose meaning isn't obvious; labels on arrows whose meaning is.
- Sentences baked into the PNG, so English prose ships in the pt/it/fr/mt editions.
- Crossings that a different layout avoids.
- A zone around a single box.

Rules partly adapted from [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT). Examples: `examples/k8s-architecture.json` (nesting), `ai-meter.json` (routing, accent path with steps, cylinders, externals), `sequence-jwt.json`, `state-pod.json`.
