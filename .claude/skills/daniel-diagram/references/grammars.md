# Grammars

One diagram, one grammar. If two seem to fit, pick the one that matches the main axis of the story; the other becomes a second diagram.

## Architecture — components and what connects them

- Group by tier or trust boundary (caller → API → stores; public → private) with at most three zones.
- The main flow runs one way, top→down by default because the article column is narrow. Hold it.
- Stores are `cylinder`s, the caller is a `pill`, anything outside your system is `external`.
- One `accent` path with `step`s when the post walks through it; the rest stays ink.
- Label an arrow only when the relation isn't obvious (`OTLP :4317`, `CRI`), never `calls` or `uses`.
- Avoid: arrows in both directions when one is implied; every box focal; a zone around a single box.
- Example: `examples/ai-meter.json`.

## Flow — decision logic

- Top→down. Steps are rectangles, decisions `diamond`s with a question as `code` or `label`, the entry a `pill`, the end an `end` dot.
- A diamond has at most three exits and every exit is labelled (`yes` / `no`); by convention yes continues down, no leaves sideways.
- Accent either the happy path or the one decision that matters, never both.
- Avoid: colour standing in for node type (shape does that); a diamond with four exits — nest two.

## Sequence — who calls whom, in time order

- Actors in one row at the top, same `y` and height. Lifelines are manual lines from each actor's bottom: `{"type":"arrow","x":<cx>,"y":<actor bottom>,"points":[[0,0],[0,<length>]],"head":false,"dashed":true,"strokeColor":"#79513C"}`.
- An actor holding control gets an activation bar: a `component` rectangle 12px wide centred on the lifeline (`x = cx - 6`, so keep `cx` at 4n+2 for the grid).
- Messages are horizontal manual arrows from bar edge (or lifeline) to bar edge (or lifeline), at least 32px apart so each label clears the next line. Calls solid, responses `dashed`. Time only goes down — never an arrow pointing up.
- A self-call is a 32×32 U to the right of the bar: `"points":[[0,0],[32,0],[32,32],[0,32]]`, label on segment 1.
- Branches get one `frame`: `alt` with `split` and two guards, or `opt` / `loop` with one. At most one frame, two regions, no nesting; beyond that, draw the failure path as its own diagram.
- ≤5 lifelines, ≤12 messages. A `legend` of call/response is worth its strip here.
- Example: `examples/sequence-jwt.json`.

## State — what a thing can be, and what moves it

- States are rectangles named as the system spells them (`code`: `Pending`, `Running`). Start is an `ellipse` with `role: start`, 20×20; a terminal marker is `role: end`, 24×24.
- Every transition is labelled with its event (`label`) or condition (`code`: `exit 0`); an unlabelled transition is the whole diagram missing. The one exception is the arrow out of the start dot, which only says "begins here".
- "From any state" becomes one callout, not an arrow from every box. More transitions than twice the states means two machines.
- Focal on the state the reader must notice: the failure, or the goal.
- Example: `examples/state-pod.json`.

## Nesting — scope through containment

- Outer to inner: `zone-warm` → `zone-light` → `group`, with an even 20–36px inset. Three levels at most.
- Titles sit top-left (`titleAt: "right"` when arrows come in on the left); children start ~44px below the zone's top.
- Arrows between zones may start or end on the zone itself; the router enters it straight.
- Example: `examples/k8s-architecture.json`.

## Comparison — the same thing twice, differing in one respect

- Two or three rows with identical layout and x positions, so the eye reads across and sees only the difference (the taints lab: `no-wristband` → Pending, `blue-wristband` → Running).
- The difference is carried by one thing — the accent on the path that works, or the focal on the result that matters — plus the real status as the arrow's `code`.
- The explanation of why belongs in the post, not in a caption inside the image.
