# Changelog

## 0.1.0 (unreleased)

First release.

### Rendering
- **One self-contained HTML deck per spec.** Its only network request is web fonts, with system fonts as the offline fallback.
- **In the deck:** keyboard navigation, search (`/`; up and down pick a result, Enter goes to it), a slide overview (`G`), speaker notes (`N`), print styles (`P`), and a diagnostics panel (`D`) for viewers without developer tools, such as Slack's file preview.
- **Themes:** Midnight (the default), Editorial and Catppuccin, each in light and dark, chosen in the deck, by URL (`?theme=editorial&mode=dark`) or by `theme` in the config. All text meets 4.5:1 contrast.
- **Edit mode (`E`)** for text fixes in the browser, with drafts kept locally. Save writes the deck and `<deck>.yaml` beside it, with every edited headline, card, table cell, note and diagram label written back to its field, so `deckgen render` can regenerate the deck. The YAML keeps no comments. In Chromium-family browsers, Save asks for a folder once per session; other browsers download both files.

### Content
- **Blocks:** `kpis`, `agenda`, `cards` (with glossary owner tags), `table`, `workstreams`, `callout`, `diagram`.
- **Diagrams drawn from data:** `architecture`, `sequence`, `chain`, `blueprint`. They follow the theme and carry a title and description for screen readers.
- **Update editions:** `--previous` generates a "What changed" slide from health moves, resolved and new blockers, and decisions made.

### Checks
- **Rendering is blocked by:**
  - missing owners on workstreams and table rows;
  - email addresses;
  - unanswered `TODO(ask)` markers;
  - health changes without a reason, in update editions;
  - theme contrast below 4.5:1;
  - malformed specs: unknown blocks or diagram types, diagram edges to unknown nodes, table rows that don't match the columns, table columns without a label, style values that aren't lengths, blueprint layers whose cells don't match the stages, chain inputs under missing steps, and architecture rows outside 0–3.
- **Warnings:** label-style headlines and glossary terms without an owner.
- **`render` never crashes on a spec that passed `check`;** malformed specs get an error, not a traceback.

### Commands and setup
- **Commands:** `check`, `render`, `pdf`, `snap` (contact sheets) and `--version`, plus `bin/export-pdf` for any HTML deck.
- **Config:** `~/.config/deckgen/config.toml` with `output_dir`, `snap_dir`, `chrome` and `theme`.
- **Errors:** one line on stderr and exit status 2 for problems such as missing files, invalid YAML, a missing browser, or a browser that hangs for more than 120 seconds.
- **Packaging:** Python 3.11 or later, installable with `uv tool install` or `pipx`. PyYAML is the only runtime dependency. CI runs the checks on Python 3.11 and 3.15.

### Docs, examples and agents
- **License:** GNU AGPL v3 or later. `CONTRIBUTING.md` covers bug reports and changes, and `SECURITY.md` private vulnerability reports.
- **Credits:** diagrams follow the design language of [diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT), credited in `THIRD_PARTY_NOTICES.md`.
- **Docs:** `README.md`, the spec reference in `docs/spec.md`, the agent guide in `docs/agents.md`, and `DEVELOPMENT.md` for extending deckgen.
- **Examples:** `examples/guide.yaml` (an introduction to deckgen), `examples/template.yaml` (a project alignment starting point), and `examples/showcase.yaml` with `showcase-previous.yaml` (every block and diagram type, and "What changed").
- **Agent skills** for Claude Code, Codex, OpenCode and Pi: `deckgen` (write and review any deck) and `alignment-deck` (alignment and status decks from issues, PRs and notes). `bin/install-skills` links them into each harness.
