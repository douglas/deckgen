# deckgen

[![CI](https://github.com/douglas/deckgen/actions/workflows/ci.yml/badge.svg)](https://github.com/douglas/deckgen/actions/workflows/ci.yml)

**Write a deck as a YAML spec; get one self-contained HTML file back.**

deckgen renders slide decks from structured specs. You describe what each slide says: a takeaway headline, cards, tables, status by workstream, and diagrams given as data. deckgen handles layout, themes, navigation and export. Before rendering anything, it checks the spec: every slide states a takeaway, everything has an owner, and nothing leaks an email address or leaves a question unanswered.

It was built for project alignment and architecture decks written by people and AI agents together, where a fixed structure and hard checks matter more than free-form design.

> **Status:** 0.1, the first release. Free software under the [GNU AGPL v3 or later](LICENSE).

## Install

deckgen needs Python 3.11 or later. [uv](https://docs.astral.sh/uv/) installs it as a command, and downloads a suitable Python if your system doesn't have one. `check` and `render` need nothing else. `pdf` and `snap` drive a headless Chromium-family browser (Chromium or Google Chrome), and `snap` builds contact sheets with ImageMagick 7 (`magick`).

### macOS

These steps use [Homebrew](https://brew.sh), on macOS 13 (Ventura) or later.

1. **Install uv, ImageMagick and Google Chrome:**

   ```
   brew install uv imagemagick
   brew install --cask google-chrome   # skip if Chrome is already in /Applications
   ```

2. **Install deckgen:**

   ```
   uv tool install git+https://github.com/douglas/deckgen@v0.1.0
   uv tool update-shell                # puts ~/.local/bin on your PATH; open a new terminal after
   deckgen --version
   ```

3. **Point deckgen at Chrome.** Apps in `/Applications` aren't on your `PATH`, so deckgen can't find Chrome by name. Create `~/.config/deckgen/config.toml`:

   ```toml
   chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   ```

   Other Chromium-family browsers work the same way, such as Brave (`/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`). For `bin/export-pdf`, set `DECKGEN_CHROME` to the path instead.

4. **Try it** on the introduction deck:

   ```
   git clone https://github.com/douglas/deckgen ~/src/deckgen && cd ~/src/deckgen
   deckgen render examples/guide.yaml -o /tmp/guide.html && open /tmp/guide.html
   deckgen snap   examples/guide.yaml -o /tmp/guide.html --dir /tmp --themes midnight/light
   deckgen pdf    examples/guide.yaml -o /tmp/guide.html && open /tmp/guide.pdf
   ```

   If macOS asks whether Chrome may run, allow it.

### Arch Linux and Omarchy

[Omarchy](https://omarchy.org) is built on Arch Linux, so the steps are the same. It already comes with Chromium.

1. **Install uv, Chromium and ImageMagick** from the official repositories:

   ```
   sudo pacman -S --needed uv chromium imagemagick
   ```

   Arch's `imagemagick` is version 7, with `magick`. deckgen looks for `chromium`, `chromium-browser`, `google-chrome`, `google-chrome-stable` and `chrome` on your `PATH`, in that order. For another browser, such as Brave, set `chrome = "brave"` in the config.

2. **Install deckgen:**

   ```
   uv tool install git+https://github.com/douglas/deckgen@v0.1.0
   uv tool update-shell                # puts ~/.local/bin on your PATH; open a new terminal after
   deckgen --version
   ```

3. **Try it** on the introduction deck:

   ```
   git clone https://github.com/douglas/deckgen ~/src/deckgen && cd ~/src/deckgen
   deckgen render examples/guide.yaml -o /tmp/guide.html && xdg-open /tmp/guide.html
   deckgen snap   examples/guide.yaml -o /tmp/guide.html --dir /tmp --themes midnight/light
   deckgen pdf    examples/guide.yaml -o /tmp/guide.html && xdg-open /tmp/guide.pdf
   ```

   Headless Chromium needs no display, so `pdf` and `snap` also work over SSH, and on Wayland sessions such as Omarchy's Hyprland.

### Other systems

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then `uv tool install git+https://github.com/douglas/deckgen@v0.1.0` (or `pipx install` the same URL). Add a Chromium-family browser and ImageMagick 7 for `pdf` and `snap`, and set `chrome` in the config if the browser isn't on your `PATH`.

### Updating and removing

```
uv tool install --force git+https://github.com/douglas/deckgen@<tag>   # move to another release
uv tool uninstall deckgen
```

Your config and decks stay where they are. To work on deckgen itself, run `uv tool install --editable .` in a clone, so `deckgen` follows your edits; `bin/deckgen` runs a clone without installing. To let your coding agent write decks, see [Agents](#agents).

### Troubleshooting

| Message or symptom | Fix |
|---|---|
| `deckgen: command not found` | Run `uv tool update-shell` and open a new terminal, or add `~/.local/bin` to your `PATH`. |
| `no Chromium-family browser found` | Install Chromium or Chrome. On macOS, set `chrome` in the config to the full path inside the `.app` (step 3). |
| `contact sheets need ImageMagick 7` | macOS: `brew install imagemagick`. Arch: `sudo pacman -S imagemagick`. ImageMagick 6 has no `magick` command. |
| `… did not finish within 120 seconds` | Check that the browser starts headless at all, for example `chromium --headless --dump-dom about:blank`, and close stuck instances. |
| PDFs or snapshots use fallback fonts | Decks load their fonts from Google Fonts and fall back to system fonts offline. Export with a network connection for the intended look. |
| `… does not exist; run deckgen render first` | `snap` screenshots the HTML that `render` last wrote. Render first, with the same `-o` if you used one. |
| `bin/install-skills`: `realpath: command not found` | macOS before 13 has no `realpath`: update macOS, or `brew install coreutils`. |

## Quick start

```
cp examples/template.yaml ~/decks/specs/my-project/update-1.yaml
$EDITOR ~/decks/specs/my-project/update-1.yaml      # answer every TODO(ask)
deckgen check  ~/decks/specs/my-project/update-1.yaml
deckgen render ~/decks/specs/my-project/update-1.yaml   # → out/<name>.html
deckgen snap   ~/decks/specs/my-project/update-1.yaml   # contact sheets, to review every slide
deckgen pdf    ~/decks/specs/my-project/update-1.yaml   # → out/<name>.pdf
```

Three example decks come with deckgen:

- **`examples/guide.yaml`:** an introduction to deckgen, as a deck. Start here.
- **`examples/showcase.yaml`:** a fictional project deck that uses every block and diagram type. Render it with `--previous examples/showcase-previous.yaml` to see a generated "What changed" slide.
- **`examples/template.yaml`:** an annotated starting point for a project alignment deck. It fails `check` until its questions are answered.

## A spec at a glance

```yaml
meta:
  title: "Payments migration"
  brand: Payments
  subtitle: Project alignment · Update 1
  output: out/payments_update1.html
  teams: [{ name: Platform }, { name: Billing }]

slides:
  - layout: title
    part: intro
    title: Payments migration
    lede: Moving card payments to the new processor by March.
    blocks:
      - kpis: [{ value: "6 weeks", label: "to cut-over" }]
      - agenda: auto

  - part: status
    kicker: Status
    headline: The migration is on track; the refund flow is the one risk.
    blocks:
      - workstreams:
          - { name: Card payments, owner: Platform, health: on_track, done: "Sandbox live", next: "Shadow traffic" }
          - { name: Refunds, owner: Billing, health: at_risk, next: "Pick an approach", waiting_on: "Processor API" }
      - callout: "Decide the refund approach this week to keep March."
    notes: "Speaker notes go here."
```

The [spec reference](docs/spec.md) documents every field, block and diagram, the checks, and how to make slides fit.

## Features

- **One HTML file per deck.** Its only network request is web fonts, with system fonts as the offline fallback.
- **Keyboard shortcuts:** arrows or space to move, a number then Enter to jump, `/` search, `G` slide overview, `N` speaker notes, `T` theme, `M` light or dark, `P` print, `E` edit, `D` a diagnostics panel for viewers that restyle the deck.
- **Three themes,** each in light and dark: Midnight, Editorial and Catppuccin. Pick one in the deck, by URL (`?theme=editorial&mode=dark`) or in the config. All text meets 4.5:1 contrast.
- **Edit mode** for text fixes in the browser. Save writes the deck and, next to it, `<deck>.yaml` with your edits, so `deckgen render` can regenerate it. Comments from the original spec aren't kept.
- **Blocks:** `kpis`, `agenda`, `cards` (including glossaries with owner tags), `table`, `workstreams` (status with health), `callout` and `diagram`.
- **Diagrams drawn from data,** with no coordinates or CSS, in the theme's colors: `architecture` (zones of boxes on a grid), `sequence` (actors and messages), `chain` (dependencies, with inputs) and `blueprint` (user journeys across stages and layers).
- **Checks that block rendering:** missing owners, email addresses, unanswered `TODO(ask)` markers, health changes without a reason, and malformed specs. Label-style headlines and glossary terms without an owner are warnings.
- **Update editions:** `--previous` generates a "What changed" slide from health moves, resolved and new blockers, and decisions made.
- **PDF export and contact sheets,** through a headless Chromium-family browser.

## Commands

| Command | What it does |
|---|---|
| `deckgen check SPEC [--previous PREV]` | Validates structure, owners, wording, privacy and theme contrast |
| `deckgen render SPEC [--previous PREV] [-o OUT] [--force]` | Writes the HTML deck; refuses while checks fail unless `--force` |
| `deckgen pdf SPEC [--previous PREV]` | Renders, then exports a PDF next to the HTML |
| `deckgen snap SPEC [--previous PREV] [--themes midnight/light midnight/dark] [--dir DIR]` | One contact sheet per theme (default: the config's theme, light and dark), each slide at 1440×900 |
| `deckgen --version` | Prints the version |
| `bin/export-pdf DECK.html [theme] [mode]` | PDF of any HTML deck |

File paths go to stdout and diagnostics to stderr. Exit codes are 0 for success, 1 for failed checks, and 2 for problems such as a missing file, invalid YAML or a missing browser.

## Configuration

`~/.config/deckgen/config.toml` (or `$XDG_CONFIG_HOME/deckgen/config.toml`, or `$DECKGEN_CONFIG`):

```toml
output_dir = "~/decks"            # where a relative meta.output resolves (default: the current directory)
snap_dir   = "~/decks/out/snap"   # where contact sheets go without --dir (default: the temp directory)
chrome     = "chromium"           # browser for pdf and snap (default: the first Chromium-family browser on PATH)
theme      = "catppuccin"         # theme decks open in, and pdf and snap use (default: midnight)
```

`$DECKGEN_CHROME` overrides `chrome`. A `?theme=` in the URL, or the viewer's last pick in that browser, wins over `theme`. `-o` and absolute `meta.output` paths always win.

Keep specs in their own repo, such as `~/decks`, and point `output_dir` at it. Then you can run deckgen from any directory.

## Agents

deckgen ships skills for Claude Code, Codex, OpenCode and Pi:

- **`deckgen`:** write, update, check, render and review any deck. Agents pick it up when you ask for a deck.
- **`alignment-deck`:** draft an alignment or status deck from issues, PRs and notes, and its update editions. Invoke it by name.

Link them from a clone; the links point into it, so `git pull` there updates them:

```
~/src/deckgen/bin/install-skills            # for your user
~/src/deckgen/bin/install-skills ~/decks    # for one repo
```

[docs/agents.md](docs/agents.md) covers installing the skills in each harness, what to put in your decks repo's `AGENTS.md`, and how agents should work with deckgen.

## Docs

| Doc | For |
|---|---|
| [docs/spec.md](docs/spec.md) | Writing specs: every field, block, diagram and check |
| [docs/agents.md](docs/agents.md) | Setting up and working with coding agents |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Changing deckgen: architecture, adding blocks, diagrams and themes, releases |
| [AGENTS.md](AGENTS.md) | Rules for agents working in this repo (also `CLAUDE.md`) |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Reporting bugs and sending changes |

## Acknowledgements

Diagrams follow the editorial design language of [diagram-design](https://github.com/cathrynlavery/diagram-design) by Cathryn Lavery (MIT): hairline boxes, tags, focal and external kinds, and restrained arrows. deckgen doesn't need it installed; it redraws that grammar from spec data in the deck's own themes. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

deckgen is free software: you can redistribute it and modify it under the terms of the [GNU Affero General Public License](LICENSE), version 3 or (at your option) any later version. Decks you make with deckgen are yours; the license covers deckgen itself.
