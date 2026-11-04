# deckgen: agent guide

deckgen turns a YAML spec into one self-contained HTML slide deck. Its only network request is web fonts from Google Fonts. Decks have three themes (Midnight, Editorial and Catppuccin), each in light and dark, plus search, keyboard navigation, speaker notes and browser edit mode. deckgen also exports PDFs and contact-sheet snapshots.

Authors, human or agent, write content. deckgen owns layout, diagrams, themes and export.

This repo is only the tool. Specs live in the user's own decks repo. Ask the user where it is if you don't know.

## Where to look

| To | Read |
|---|---|
| Write or fix a spec: every field, block, diagram, check and fit budget | `docs/spec.md` |
| Use deckgen as an agent, or set up the skills | `docs/agents.md`, `skills/deckgen/SKILL.md` |
| Change deckgen: architecture, edit-mode paths, adding blocks, diagrams and themes, releases | `DEVELOPMENT.md` |
| See a working example of any field | `examples/showcase.yaml` (each slide's notes name the features it shows) |

## Rules

- **Open source, AGPL v3 or later** (`LICENSE`), at `github.com/douglas/deckgen`. Keep third-party credits in `THIRD_PARTY_NOTICES.md`. Don't publish to a package index unless the user asks.
- **Specs are the source of truth.** Never hand-edit generated HTML or add per-deck CSS. Layout fixes belong in `src/deckgen/`; make them deliberately and say so.
- **Keep the guardrails in `check.py`:** owners, takeaway headlines, no email addresses, no unanswered ask markers, theme contrast, and the shape checks (known blocks and diagram types, lengths in style fields, blueprint cells per stage). `render` must never crash on a spec that passed `check`. Relaxing one needs the user's agreement.
- **Keep it dependency-light:** at runtime, the standard library plus PyYAML. Chromium and ImageMagick are optional external commands, used for PDF and snapshots only. Dev tools (ruff, mypy) live in the `dev` dependency group, pinned by `uv.lock`.
- **Keep it simple.** This is a small tool for developers and agents; don't build for rare corner cases. Add a block or diagram only when most decks would use it.
- **Decks may hold private material.** Never copy a user's spec, deck or snapshot into this repo, its tests or its examples.

## Layout

| Path | What it is |
|---|---|
| `src/deckgen/cli.py` | CLI (`check`, `render`, `pdf`, `snap`, `--version`), the `Config` dataclass, PDF export and snapshots |
| `src/deckgen/render.py` | Slides and blocks; `BLOCKS` maps a block name to its renderer |
| `src/deckgen/diagrams.py` | `DIAGRAMS`: `architecture`, `sequence`, `chain`, `blueprint`; and `Canvas`, the SVG helper they share |
| `src/deckgen/check.py` | Guardrails, shape checks and the theme contrast check |
| `src/deckgen/shell.html` | Page template: themes, edit mode, search, navigation, print styles. Read with `importlib.resources` |
| `src/deckgen/_types.py`, `__init__.py`, `__main__.py` | Spec type aliases; `__version__` (the single source of the version); `python -m deckgen` |
| `bin/deckgen`, `bin/export-pdf` | Run from a checkout without installing; `export-pdf` also exports any HTML deck |
| `bin/install-skills` | Links `skills/` into `.agents/skills` and `.claude/skills` for Claude Code, Codex, OpenCode and Pi |
| `skills/deckgen/`, `skills/alignment-deck/` | Agent skills. Their `spec.md` and `examples` are links to `docs/spec.md` and `examples/` |
| `examples/` | `guide.yaml` (an introduction to deckgen, and the reference example for tests), `showcase.yaml` with `showcase-previous.yaml` (every block and diagram, and "What changed"), `template.yaml` (fails `check` until its questions are answered) |
| `docs/` | `spec.md` (spec reference) and `agents.md` (agents and skills) |
| `tests/` | `unittest` tests: rendering, checks, CLI, config, and the examples in the README and `docs/spec.md` |
| `pyproject.toml`, `uv.lock` | Packaging, ruff and mypy config, and the pinned `dev` dependency group |
| `.github/workflows/ci.yml` | The checks on Python 3.11 and 3.15 |
| `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` | AGPL v3 text; how to report bugs and send changes; how to report a vulnerability |
| `THIRD_PARTY_NOTICES.md` | Credit and MIT notice for diagram-design, whose design language the diagrams follow |

## Commands

```
deckgen check  SPEC [--previous PREV]   # structure, owners, wording, privacy, contrast
deckgen render SPEC [--previous PREV] [-o OUT] [--force]   # writes meta.output (or OUT); refuses while checks fail
deckgen pdf    SPEC [--previous PREV]   # HTML, then a PDF next to it, in the config's theme (light)
deckgen snap   SPEC [--previous PREV] [--themes midnight/light midnight/dark] [--dir DIR]   # one contact sheet per theme
bin/export-pdf DECK.html [theme] [mode] # PDF of any deck
```

- **Config:** `~/.config/deckgen/config.toml` (or `$XDG_CONFIG_HOME/deckgen/config.toml`, or `$DECKGEN_CONFIG`) with `output_dir`, `snap_dir`, `chrome` and `theme`. The user's config file may be a dotfile symlink: edit its source, not the link.
- **Output and exit codes:** results (file paths) go to stdout, and diagnostics to stderr. Exit codes: 0 success, 1 failed checks, 2 a problem such as a missing file, invalid YAML or a missing browser, printed as one `deckgen: …` line.
- **Snapshots:** each slide at 1440×900, tiled three across at 732×462. Crop tile *n* (1-based) at `x = ((n-1) % 3) * 732`, `y = ((n-1) // 3) * 462`: `magick sheet.png -crop 732x462+X+Y slide.png`.

## Before committing

```
uv run ruff format . && uv run ruff check .
uv run mypy
uv run python -W error::ResourceWarning -m unittest discover -s tests
deckgen render examples/showcase.yaml --previous examples/showcase-previous.yaml
deckgen snap   examples/showcase.yaml --previous examples/showcase-previous.yaml --themes midnight/light midnight/dark
```

All three checks must pass. Don't silence a rule inline; if one genuinely doesn't fit, change `pyproject.toml` with a comment saying why, and tell the user. Look at every slide your change touches. For changes that shouldn't alter output, render the examples before and after, and diff the HTML.

A new block or diagram needs a renderer, a shape check, a YAML example in `docs/spec.md` and a use in `examples/showcase.yaml`; tests enforce the last two. `DEVELOPMENT.md` has the steps.

**Releases:** bump `__version__` in `src/deckgen/__init__.py` and move the notes in `CHANGELOG.md`. Don't tag or push unless the user asks.
