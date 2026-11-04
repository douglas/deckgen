# Spec reference

A deck is one YAML file: `meta`, an optional `decisions_made`, and a list of `slides`. Each slide has a headline and a list of blocks. This page lists every field. For working examples, copy from `examples/showcase.yaml`, which uses every block and diagram type; its slide notes name the features each slide shows.

## Contents

- [The spec](#the-spec)
- [Slides](#slides)
- [Inline text and YAML quoting](#inline-text-and-yaml-quoting)
- [Blocks](#blocks)
- [Diagrams](#diagrams)
- [Update editions](#update-editions)
- [Checks](#checks)
- [Making slides fit](#making-slides-fit)
- [Writing well](#writing-well)

## The spec

```yaml
meta:
  title: Payments migration             # required
  brand: Payments                       # required: shown in the deck's top bar
  subtitle: Project alignment · Update 1   # required
  output: out/payments_update1.html     # optional; default <spec name>.html
  teams: [{ name: Platform }, { name: Billing }]   # optional; the order sets owner-tag colors
  changes_headline: Since the last update.         # optional, for "What changed"
decisions_made:                         # optional, for update editions
  - { what: Ship refunds behind a flag, by: Billing }
slides: [ … ]
```

- **`output`** resolves against `output_dir` from the config, or against the current directory without one. An absolute path and `deckgen render -o OUT` always win.
- **`teams`** are the names used in `owner` fields. A team that isn't listed still works but gets no color.

## Slides

```yaml
- layout: title            # the first slide only
  part: intro
  title: Payments migration
  lede: Moving card payments to the new processor by March.
  blocks: [ … ]

- part: status             # starts a section and an agenda entry
  agenda: Status           # the agenda label; default the part name, capitalized
  kicker: Status · Workstreams
  headline: The migration is on track; the refund flow is the one risk.
  blocks: [ … ]
  notes: "Speaker notes: detail, sources, caveats."
```

| Field | Meaning |
|---|---|
| `layout: title` | The title slide. It takes `title` and `lede` instead of `headline`. |
| `part` | Starts a section. Every slide with a `part` (except the title slide) gets an agenda entry that jumps to it. |
| `agenda` | The agenda label for the part. |
| `kicker` | A short label above the headline, such as `Status · Workstreams`. |
| `headline` | Required on every slide except the title slide. A full sentence that states the takeaway; the check warns if it doesn't end in `.`, `?` or `!`. |
| `blocks` | The slide's content: a list, each item a mapping with exactly one key, the block name. |
| `notes` | Speaker notes, shown with `N`. Put sources and caveats here. |

## Inline text and YAML quoting

- **Inline text** in every text field supports `**bold**`, `` `code` `` and `[label](https://url)`. Everything else is escaped, so HTML in a spec shows as text.
- **Quote a YAML string** if it contains `: ` or `#`, or starts with a backtick or a quote. Inside a flow mapping (`{ … }`), also quote strings that contain `,` or `?`.
- **Values YAML reads as other types**, such as `2026`, `yes` or `no`, become text in the deck, but quote them when you mean text.

## Blocks

### `kpis`

Big numbers, usually on the title slide.

```yaml
- kpis:
    - { value: "6 weeks", label: "to cut-over" }
    - { value: "3 teams", label: "Platform · Billing · Data" }
```

### `agenda`

```yaml
- agenda: auto
```

Links to every part, in order. Use it on the title slide.

### `cards`

Comparisons, lists of points and glossaries.

```yaml
- cards:
    columns: 3                    # default: the number of cards, at most 4
    widths: 0.9fr 1.25fr 0.85fr   # optional CSS grid widths: fr, %, px, em or rem
    font_size: 15                 # default 16
    glossary: true                # owner tags on every card; the check warns on a missing owner
    cards:
      - title: Ledger             # required
        owner: Billing            # optional owner tag
        text: The record of every payment.   # a paragraph,
        items: ["Built in Q3", "Owned by Billing"]   # and/or a bullet list
        style: wins               # optional: check marks instead of bullets
```

### `table`

```yaml
- table:
    compact: true                 # default true: smaller type and padding
    columns:
      - { label: Blocker, width: 30%, bold: true }   # label is required; width is a CSS length
      - { label: Owner, width: 15% }
      - { label: Needed by, muted: true }            # muted: secondary text color
    rows:
      - ["Processor API access", Platform, "Feb 3"]
```

- **Every row needs one cell per column.**
- **A column labelled `Owner`** must be filled in on every row.

### `workstreams`

Status by area, with a health legend under the table.

```yaml
- workstreams:
    - name: Refunds               # required; "What changed" matches editions by name
      owner: Billing              # required
      health: at_risk             # required: on_track, at_risk, off_track, not_started or done
      done: Sandbox live
      next: Pick an approach
      waiting_on: Processor API
      reason: The processor moved its API date.   # required when health changed since --previous
```

### `callout`

The one thing to remember from the slide.

```yaml
- callout: "Decide the refund approach this week to keep March."
- callout: { text: "Refunds slip without a decision this week.", tone: warn }
```

### `diagram`

See [Diagrams](#diagrams).

## Diagrams

Diagrams are data: you list boxes, rows and arrows, and deckgen lays them out and draws them in the theme's colors. There are no coordinates or CSS.

Every diagram takes these fields:

| Field | Meaning |
|---|---|
| `type` | `architecture`, `sequence`, `chain` or `blueprint` |
| `title` | Required: a short name, read by screen readers |
| `desc` | Required: a sentence describing the diagram, read by screen readers |
| `max_width` | Optional, in pixels (default 1100). Diagrams never shrink below 1000 px |
| `legend` | Optional labels for the legend, keyed by kind. Only kinds the diagram uses are shown |

Boxes (nodes, actors, steps and inputs) share these fields: `name` (required), `tag` (a small label above the name, such as `API` or `EXT`), `sub` (a second line), and `kind`.

### `architecture`: zones of boxes on a grid

```yaml
- diagram:
    type: architecture
    title: Payments today
    desc: The checkout service calls the payments API, which writes to the ledger and calls the processor.
    nodes:
      - { id: checkout, tag: WEB, name: Checkout, col: 0, row: 0 }
      - { id: api, tag: API, name: Payments API, col: 1, row: 0, kind: focal }
      - { id: ledger, tag: DATA, name: Ledger, sub: Postgres, col: 1, row: 1, kind: store }
      - { id: proc, tag: EXT, name: Processor, col: 2, row: 0, kind: ext }
    zones:
      - { id: ours, label: OUR SYSTEMS, nodes: [checkout, api, ledger] }
    edges:
      - { from: checkout, to: api, kind: accent, label: charge }
      - { from: api, to: ledger }
      - { from: api, to: proc, kind: link, label: HTTPS }
    legend: { accent: THE CHARGE PATH, link: EXTERNAL CALL, focal: CHANGES IN THIS PROJECT }
```

- **Nodes:** `id`, `col` (0, 1, 2 and so on) and `row` (0–3 only) are required. `kind` is `ext`, `focal` or `store`. `width` is in pixels (default 196). Columns are 196 px wide with 96 px gaps.
- **Zones:** `id`, `label`, and `nodes` (the IDs inside it). A zone is drawn as the bounding box of its nodes, so never place a node from outside the zone within that box. `extra_bottom` adds space below.
- **Edges:** `from` and `to` (node IDs), `kind` (`accent`, `link`, `return` or `muted`, the default) and an optional `label`. Use `accent` for the one path the slide is about. A `blocked` edge takes `to_zone` instead of `to` and ends in a bar at the zone's edge.
- **Routing:** edges between boxes in the same row or column are straight. Others leave the right side and turn once into the top or bottom of the target.
- **Labels** wider than the gap between two boxes get clipped. Keep them to a word or two.

### `sequence`: actors and messages over time

```yaml
- diagram:
    type: sequence
    title: A refund, end to end
    desc: Support asks the payments API for a refund, which asks the processor and records the result.
    actors:
      - { id: support, tag: WEB, name: Support tool }
      - { id: api, tag: API, name: Payments API, kind: focal }
      - { id: proc, tag: EXT, name: Processor, kind: ext }
    messages:
      - { from: support, to: api, label: POST /refunds, kind: accent }
      - { from: api, to: proc, label: refund, kind: link }
      - { from: proc, to: api, label: "200 OK", kind: return }
      - { self: api, label: write ledger entry }
```

- **Actors:** `id` is required; `width` is in pixels (default 176). `width` on the diagram sets the canvas (default 1040).
- **Messages:** `from` and `to`, or `self` for a step on one lifeline; `label` is required; `kind` as for architecture edges.
- **Height:** each message adds about 40 px and each `self` message about 48 px. A sequence plus a callout fits at about 8 messages.

### `chain`: steps left to right, with inputs below

```yaml
- diagram:
    type: chain
    title: From contract to launch
    desc: Legal signs, then Platform integrates, then Billing migrates. Two inputs feed the integration.
    steps:
      - { tag: LEGAL, name: Contract signed }
      - { tag: PLATFORM, name: Integrate, kind: focal }
      - { tag: BILLING, name: Migrate }
    inputs:
      - { under: 1, tag: EXT, name: API credentials, kind: ext }
      - { under: 1, tag: ASK, name: Refund approach, kind: decision }
    legend: { focal: WE ARE HERE, decision: NEEDS A DECISION }
```

- **Steps:** `kind` is `focal`, `decision` or `ext`.
- **Inputs:** `under` is the index of the step they feed (from 0).

### `blueprint`: a journey across stages and layers

```yaml
- diagram:
    type: blueprint
    title: Asking for a refund
    desc: What the customer does and sees at each stage, and the systems behind it.
    persona: { eyebrow: CUSTOMER, name: Card holder }
    stages:
      - { id: ask, eyebrow: STAGE 1, name: Ask }
      - { id: wait, eyebrow: STAGE 2, name: Wait }
    layers:
      - { kind: customer, label: DOES, cells: ["Opens a ticket", "Checks email"] }
      - { kind: frontstage, label: SEES, cells: ["Support form", "Status email"] }
      - kind: backstage
        label: SYSTEMS
        cells: [{ name: Payments API, tag: API, focal: true }, "—"]
    legend: { visibility: LINE OF VISIBILITY, backstage: BEHIND THE SCENES, focal: CHANGES }
```

- **Stages:** `id` and `name` are required; `eyebrow` is a small label above.
- **Layers:** `kind` is `customer`, `frontstage`, `backstage` or `support`, drawn in that order. A line of visibility separates frontstage from backstage. `label` and `sublabel` sit in the left margin.
- **Cells:** exactly one per stage. A cell is a string, or `{ name, sub, tag, focal }`. `"—"` or `"Not applicable"` draws an empty cell.
- **Sizing:** `column` (default 176), `margin` (default 112), `row_height` (default 60), and `grid` (the number of columns to size the canvas for, so stacked blueprints line up).

## Update editions

`--previous PREV` compares the spec with its previous edition and inserts a generated "What changed" slide after the title slide:

- **Workstreams,** matched by `name`: health moves (quoting each `reason`, which the check requires) and new workstreams.
- **Blockers:** the first column of every `table` on slides with `part: blockers`, listed as resolved or new.
- **Decisions:** `decisions_made` from the current spec.

The slide's headline is `meta.changes_headline` (default "Since the last update."). See `examples/showcase.yaml` and `examples/showcase-previous.yaml`.

## Checks

`deckgen check` reports errors, which block `render`, and warnings, which are review comments. `render --force` renders anyway.

**Errors:**
- `meta.title`, `meta.brand` or `meta.subtitle` missing, no slides, or a slide without a headline (or title, on the title slide).
- Missing owners on workstreams and on table rows with an `Owner` column.
- An email address anywhere in the spec.
- An unanswered ask marker: the text `TODO(ask)` anywhere, even inside prose that only describes it. Describe it in words instead.
- A health change without a `reason`, with `--previous`.
- Malformed blocks: unknown block or diagram types, a block with more than one key, table rows that don't match the columns, table columns without a label, style values that aren't lengths, diagram edges to unknown nodes, architecture rows outside 0–3, chain inputs under missing steps, and blueprint layers whose cells don't match the stages.
- Theme text below 4.5:1 contrast. This only fails when deckgen's own themes change.

**Warnings:** headlines that read like labels, and glossary cards without an owner.

## Making slides fit

Every slide must fit a 1440×900 screen; overflow hides the bottom of a slide, usually its callout.

- **Look at every slide you changed:** `deckgen snap SPEC`, then read the contact sheet. Tile *n* (1-based) is 732×462 at `x = ((n-1) % 3) * 732`, `y = ((n-1) // 3) * 462`; crop one with `magick sheet.png -crop 732x462+X+Y slide.png`.
- **Budgets:** about 8 table rows with a callout; about 8 glossary cards at `columns: 4` and `font_size` 14–15; about 8 sequence messages with a callout.
- **`max_width` can't shrink a diagram below 1000 px.** To make one shorter, merge or remove messages or nodes.
- **Fix overflow with words:** shorten text, move detail into `notes`, or split the slide in two, each with its own takeaway. Never with CSS.

## Writing well

- **Write for everyone in the room.** Open with a plain "what it is" slide before any architecture. Give every diagram a one- or two-line plain-language callout.
- **Headlines state the takeaway as a full sentence.** Kickers are short labels.
- **Tag diagram boxes** with the system they belong to, such as `API`, `DATA` or `EXT`, and spell out abbreviations.
- **Give every glossary term, blocker and workstream an owning team.**
- **Facts come from sources,** such as code, PRs, issues and project docs, not memory. Put sources and caveats in `notes`.
- **Mark unknowns with an ask marker** and answer them before rendering.
- **Keep personal data out:** no emails, client names, credentials, or private text that hasn't been cleared.
