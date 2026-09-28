# daniel-diagram

Agent skill that draws diagrams in the DanielSite house style, rendered to PNG at the width the reader sees. The default `pencil` style draws boxes, zones and arrows in coloured pencil and graphite with hard shadows, pill titles and stamped labels; the older `sketch` style (plain rough.js) stays for existing specs. Both use the `tokens.css` paper palette and Karla / Courier Prime / Zilla Slab. A lint checks every spec before it renders; a capture script refuses to write a PNG whose fonts fell back or whose page did not finish drawing.

`SKILL.md` is the instruction set the agents follow; start there.

## Layout

```
SKILL.md                 the skill: workflow, size, palette, typography, spec format, budget, lint, taste gate
references/grammars.md   architecture, flow, sequence, state, nesting, comparison
references/terminal.md   terminal output rendered as the site's code block
scripts/render.py        spec.json -> lint -> rough.js HTML, pencil or sketch (--bake writes a .excalidraw preview)
scripts/capture.sh       HTML -> 2x PNG with Chrome headless
scripts/terminal.py      terminal output .txt -> HTML for capture.sh
examples/                reference specs, also the renderer's regression set
assets/fonts/            the site's woff2 files, used only to measure text
```

## Use

```bash
python3 scripts/render.py examples/k8s-architecture.json            # check only
python3 scripts/render.py examples/k8s-architecture.json out.html   # check, then render
scripts/capture.sh out.html out.png                                 # 1320px PNG for a 660px article column
```

Needs Python 3 with `fontTools` and `brotli` (text measurement; it falls back to estimates without them), Pillow, and Google Chrome (`CHROME=/path` to point elsewhere). The rendered page loads rough.js and the fonts from the network.

## Install

This directory is the canonical copy at `~/.codex/skills/daniel-diagram/`, which Codex loads directly. Claude Code loads `~/.claude/skills/daniel-diagram/SKILL.md`, a pointer with the same frontmatter whose body tells the agent to read this directory's `SKILL.md`. Edit only this copy.

## Credits

Several rules are adapted from [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT). Karla, Courier Prime and Zilla Slab are licensed under the SIL Open Font License 1.1.
