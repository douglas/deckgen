# Developing deckgen

This guide is for anyone, human or agent, who wants to change deckgen itself: fix a layout, add a block, diagram or theme, or make a release. To use deckgen, start with the [README](README.md) and the [spec reference](docs/spec.md).

## Principles

- **Authors write content; deckgen owns presentation.** Specs never carry CSS, coordinates or HTML. If a deck needs a layout change, it belongs in `src/deckgen/` for every deck.
- **Checks guard rendering.** `render` must never crash on a spec that passed `check`. Every new field that could crash a renderer or inject markup needs a shape check.
- **Small and dependency-light.** At runtime: the standard library plus PyYAML. Chromium and ImageMagick are optional external commands. Add a block or diagram only when most decks would use it. There is no plugin system.
- **Simple over clever.** deckgen is a small tool for developers and agents. Don't build for corner cases nobody has hit.

## Setup

```
git clone https://github.com/douglas/deckgen && cd deckgen
uv sync                                    # Python and the dev tools (ruff, mypy), pinned by uv.lock
uv tool install --editable .               # a `deckgen` command that runs your checkout
```

`bin/deckgen` also runs the checkout without installing anything but PyYAML.

## Checks

All three must pass before a commit; CI runs them on Python 3.11 and 3.15.

```
uv run ruff format . && uv run ruff check .                            # formatting and lint
uv run mypy                                                            # strict type checks of src/ and tests/
uv run python -W error::ResourceWarning -m unittest discover -s tests  # tests
```

Don't silence a rule inline. If one genuinely doesn't fit, change `pyproject.toml` with a comment saying why.

## How it works

```
spec.yaml ─▶ cli.load ─▶ check.check_spec ─▶ render.render ─▶ shell.html ─▶ deck.html ─▶ Chromium ─▶ PDF, PNGs
                           (errors stop here)    (BLOCKS, DIAGRAMS)
```

| File | What it does |
|---|---|
| `src/deckgen/cli.py` | Commands, the `Config` dataclass, spec loading, output paths, PDF export and snapshots. `DeckgenError` is a problem the user can fix: printed as one line, exit status 2 |
| `src/deckgen/check.py` | `check_spec` returns `(errors, warnings)`; `_check_block` and `_check_diagram` are the shape checks; `check_contrast` reads the theme tokens from `shell.html` |
| `src/deckgen/render.py` | `render` builds every slide and fills the shell's placeholders. `BLOCKS` maps a block name to its renderer; `Ctx` carries state across blocks; `what_changed` builds the update slide |
| `src/deckgen/diagrams.py` | `DIAGRAMS` maps a type to a layout function. `Canvas` collects SVG markup, arrow markers and the legend |
| `src/deckgen/shell.html` | The page: theme tokens, styles, navigation, search, notes, edit mode, diagnostics and print styles |
| `src/deckgen/_types.py` | `Spec`, `Slide` and `Node`: plain YAML dicts, named for readability |
| `tests/test_deckgen.py` | Rendering, checks, the CLI and the config, mostly driven by the examples |

### Rendering

- **`render(spec, previous, theme)`** inserts the "What changed" slide when `previous` is given, renders each slide with `slide()`, then fills `{{TITLE}}`, `{{BRAND}}`, `{{SUBTITLE}}`, `{{THEME}}`, `{{SLIDES}}` and `{{SPEC}}` in the shell in one pass, so a value that contains a placeholder is never expanded.
- **`md(text)`** is the only path from spec text to HTML: it escapes everything, then allows `**bold**`, `` `code` `` and `http`/`https` links. Use it for every user-facing string, and `html.escape` for attribute values.
- **Style values** (widths and font sizes) reach inline `style` attributes, so the check only accepts lengths and integers for them.

### Edit mode and `data-src`

Edit mode saves browser edits back into the spec, so every editable element says which spec field it came from:

- **`ctx.src(*parts)`** returns a `data-src="slides/3/blocks/0/cards/cards/1/title"` attribute: `ctx.base` (the current block's path) plus `parts`. Generated slides have no base and get no attribute.
- **Diagrams** use `diagrams.src(*parts)`, relative to the diagram. `block_diagram` wraps the SVG in an element with `data-src-base`, which edit mode prepends.
- **The spec is embedded** as JSON in `<script id="deckgen-spec">`. Save applies the edited fields to it and writes `<deck>.yaml` next to the deck.

`ShowcaseTest.test_edit_mode_can_map_every_editable_field_back_to_the_spec` checks that every `data-src` in the showcase resolves to a field. Give every new editable element a `src`.

### Themes

Diagrams follow the design language of [diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT; see `THIRD_PARTY_NOTICES.md`). Keep new diagrams in that grammar: hairline boxes, small tags, one focal path, no shadows or gradients.

Each theme and mode is a `[data-theme="<name>"][data-mode="<mode>"]` block of CSS custom properties in `shell.html`. Blocks and diagrams use only those tokens and the `.dd` diagram classes, never raw colors, so everything follows the theme. `check_contrast` checks every text token against `--bg` and `--panel` at 4.5:1.

## Extending deckgen

### A new block

1. **Render it:** a typed `block_<name>(body, ctx) -> str` in `render.py`, registered in `BLOCKS`. Pass text through `md()`, and give every editable element `ctx.src(...)`.

   ```python
   def block_quote(b: dict[str, Any], ctx: Ctx) -> str:
       who = f"<cite{ctx.src('by')}>{md(b['by'])}</cite>" if b.get("by") else ""
       return f'<blockquote class="quote"><p{ctx.src("text")}>{md(b["text"])}</p>{who}</blockquote>'
   ```

2. **Check its shape** in `_check_block` in `check.py`, so a malformed block is an error, not a crash:

   ```python
   if kind == "quote" and not (isinstance(body, dict) and body.get("text")):
       errors.append("quote needs a `text`")
   ```

3. **Style it** in `shell.html` with theme tokens (`var(--ink)`, `var(--muted)` and so on).
4. **Document it** in `docs/spec.md`, under Blocks, with a YAML example. A test renders and checks every block example in that file.
5. **Use it** in `examples/showcase.yaml`, in a slide whose notes name it. A test checks that the showcase uses every block.
6. **Test** any guardrail you added, in `ShapeCheckTest`.

### A new diagram

1. **Lay it out:** a `(spec, prefix) -> str` function in `diagrams.py`, registered in `DIAGRAMS`. Compute positions from the data, draw through a `Canvas`, and use only the `.dd` CSS classes. Give labels `src(...)` paths relative to the diagram.
2. **Check it:** shape checks in `_check_diagram`, and an endpoint check if it has edges.
3. **Document it** in `docs/spec.md` with a YAML example, and **use it** in `examples/showcase.yaml`. A test checks that the showcase uses every diagram type.

### A new theme

Add a `[data-theme="<name>"][data-mode="light"]` and a `…[data-mode="dark"]` block to `shell.html`, an `<option>` in the theme list, the name in the allow-list in the theme script, and the name in `THEMES` in `render.py`. `check_contrast` must still pass.

### A new command or config key

Add it to `COMMANDS` or `Config` in `cli.py`, and document it in the README and in `AGENTS.md`. Results go to stdout and diagnostics to stderr; raise `DeckgenError` for problems the user can fix.

## Reviewing output

Tests catch crashes and broken checks, not ugly slides. Before committing a change that affects output:

```
deckgen render examples/showcase.yaml --previous examples/showcase-previous.yaml
deckgen snap   examples/showcase.yaml --previous examples/showcase-previous.yaml --themes midnight/light midnight/dark
```

Look at every slide your change touches, in light and dark. For a change that shouldn't alter output, render the examples (and your own decks) before and after, and diff the HTML.

## Style

- **Type every function,** with built-in generics and `X | None`. mypy runs in strict mode.
- **Prefer `pathlib`** for paths and `importlib.resources` for package files.
- **Keep diffs small.** Long SVG and HTML f-strings stay on one line; the formatter handles code.
- **Tests use `unittest`** and the examples. Never put a user's real spec, deck or snapshot in the repo, its tests or its examples: write a small fictional one.

## Releases

1. Bump `__version__` in `src/deckgen/__init__.py`; `pyproject.toml` reads it.
2. Move the Unreleased notes in `CHANGELOG.md` under the new version and date.
3. Run the checks, render and snap the examples, and look at them.
4. Commit, then tag `vX.Y.Z` and push the tag, when the release is agreed.

deckgen is licensed under the AGPL v3 or later (`LICENSE`); contributions are accepted under the same license. It isn't published to a package index yet.
