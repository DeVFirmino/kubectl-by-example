# Terminal prints

Command output goes in a print that mirrors the site's article code block (`.article-code` in `paper.css`): bar `#2B2824` with the label in Courier Prime uppercase `#9C9184`, body `#23211E`, text `#E8DFD2` 15.5px/1.7, offset shadow `4px 4px 0 rgba(0,0,0,.15)`, Prism inks only: prompt and errors in `#E08A5E`/`#DE8B62`, good states in `#C9CFA4`. No window dots, no paper, no ruled lines, no hand-drawn border. Daniel rejected paper/torn-note and generic dark-terminal looks for prints: the print must be indistinguishable from a code block on the page.

1. Save the real output to a `.txt` with prompt lines starting with `$ `. Trim columns the text never discusses (e.g. the always-`<none>` NOMINATED NODE / READINESS GATES) so a table fits in ~85 characters.
2. `python3 ~/.codex/skills/daniel-diagram/scripts/terminal.py out.txt out.html --label "bash · kind-ckad"` — renders at the 660px article column width with Courier Prime 12px, so the PNG is never scaled down on the page (a 2400px-wide print shrinks to unreadable 6px text next to 15.5px code blocks; that happened once).
3. `scripts/capture.sh out.html out.png` (2x, cropped to content).
