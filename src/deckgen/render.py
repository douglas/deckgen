"""Render a deck spec (YAML) into a self-contained HTML deck using the shared shell."""

import json
import re
from collections.abc import Callable, Iterator
from html import escape
from importlib import resources
from typing import Any

from ._types import Slide, Spec
from .diagrams import DIAGRAMS

SHELL = resources.files("deckgen") / "shell.html"
PLACEHOLDER = re.compile(r"\{\{(TITLE|BRAND|SUBTITLE|THEME|SLIDES|SPEC)\}\}")
# The themes in shell.html, in the order of its theme list.
THEMES = ("midnight", "editorial", "catppuccin")
HEALTH = {
    "on_track": ("ok", "On track"),
    "at_risk": ("risk", "At risk"),
    "off_track": ("off", "Off track"),
    "not_started": ("todo", "Not started"),
    "done": ("done", "Done"),
}
HEALTH_LEGEND = {
    "on_track": "",
    "at_risk": "needs a decision or a date",
    "off_track": "will miss the milestone without help",
    "not_started": "",
}


def md(text: object) -> str:
    """Escape, then allow **bold**, `code` and [label](url) inline."""
    out = escape(str(text))
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', out)


class Ctx:
    """Rendering state shared by the blocks: the spec, owner-tag classes and the slide counter.

    `base` is the spec path of what is being rendered (`slides/3/blocks/0/cards`), or None for generated
    slides. Edit mode uses the `data-src` paths from `src` to write browser edits back into the spec.
    """

    def __init__(self, spec: Spec) -> None:
        self.spec = spec
        self.teams: dict[str, str] = {
            t["name"]: f"t{i + 1}" for i, t in enumerate(spec.get("meta", {}).get("teams", []))
        }
        self.n = 0
        self.index = {id(s): n for n, s in enumerate(spec.get("slides", []))}
        self.base: str | None = None

    def src(self, *parts: object) -> str:
        """A `data-src` attribute for the spec field at `base/parts`, or nothing on generated slides."""
        if self.base is None:
            return ""
        return f' data-src="{escape("/".join([self.base, *map(str, parts)]))}"'

    def owner(self, name: str | None, src: str = "") -> str:
        if not name:
            return ""
        return f'<span class="owner {self.teams.get(name, "")}"{src}>{escape(name)}</span>'


def block_kpis(b: list[dict[str, Any]], ctx: Ctx) -> str:
    tiles = "".join(
        f'<div class="kpi"><div class="v"{ctx.src(i, "value")}>{md(k["value"])}</div>'
        f'<div class="k"{ctx.src(i, "label")}>{md(k["label"])}</div></div>'
        for i, k in enumerate(b)
    )
    return f'<div class="kpis" style="grid-template-columns: repeat({len(b)}, minmax(0, 340px))">{tiles}</div>'


def block_agenda(b: str, ctx: Ctx) -> str:
    def src(s: Slide) -> str:
        n = ctx.index.get(id(s))
        return "" if n is None else f' data-src="slides/{n}/agenda"'

    links = [
        f'<a data-jump="{escape(s["part"])}"{src(s)}>{escape(s.get("agenda", s["part"].title()))}</a>'
        for s in ctx.spec["slides"]
        if s.get("part") and s.get("layout") != "title"
    ]
    return f'<div class="agenda">{"".join(links)}</div>'


def block_cards(b: dict[str, Any], ctx: Ctx) -> str:
    cols = b.get("columns", min(4, len(b["cards"])))
    widths = b.get("widths") or " ".join(["1fr"] * cols)
    cards = []
    for n, c in enumerate(b["cards"]):
        body = f"<p{ctx.src('cards', n, 'text')}>{md(c['text'])}</p>" if c.get("text") else ""
        if c.get("items"):
            cls = ' class="wins"' if c.get("style") == "wins" else ""
            items = "".join(f"<li{ctx.src('cards', n, 'items', j)}>{md(i)}</li>" for j, i in enumerate(c["items"]))
            body += f"<ul{cls}>{items}</ul>"
        owner = ctx.owner(c.get("owner"), ctx.src("cards", n, "owner"))
        cards.append(f'<div class="card">{owner}<h3{ctx.src("cards", n, "title")}>{md(c["title"])}</h3>{body}</div>')
    cls = "g4" if b.get("glossary") else ""
    return (
        f'<div class="{cls}" style="display:grid;grid-template-columns:{escape(str(widths))};gap:16px;margin-top:20px;'
        f'font-size:{int(b.get("font_size", 16))}px">{"".join(cards)}</div>'
    )


def block_table(b: dict[str, Any], ctx: Ctx) -> str:
    head = "".join(
        f'<th style="width:{escape(str(c["width"]))}"{ctx.src("columns", i, "label")}>{md(c["label"])}</th>'
        if c.get("width")
        else f"<th{ctx.src('columns', i, 'label')}>{md(c['label'])}</th>"
        for i, c in enumerate(b["columns"])
    )
    rows = []
    for n, r in enumerate(b["rows"]):
        cells = []
        for i, v in enumerate(r):
            cls = ' class="muted"' if b["columns"][i].get("muted") else ""
            bold = b["columns"][i].get("bold")
            val = f"<b>{md(v)}</b>" if bold else md(v)
            cells.append(f"<td{cls}{ctx.src('rows', n, i)}{' data-bold' if bold else ''}>{val}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    cls = ' class="compact"' if b.get("compact", True) else ""
    return f'<table{cls} style="margin-top:14px"><tr>{head}</tr>{"".join(rows)}</table>'


def block_workstreams(b: list[dict[str, Any]], ctx: Ctx) -> str:
    head = (
        '<tr><th style="width:17%">Workstream</th><th style="width:11%">Owner</th><th style="width:10%">Health</th>'
        '<th style="width:22%">Done</th><th style="width:24%">Next</th><th>Waiting on</th></tr>'
    )
    rows = []
    for n, w in enumerate(b):
        cls, label = HEALTH[w["health"]]
        rows.append(
            f"<tr><td{ctx.src(n, 'name')} data-bold><b>{md(w['name'])}</b></td><td{ctx.src(n, 'owner')}>{md(w['owner'])}</td>"
            f'<td><span class="st {cls}">{label}</span></td><td{ctx.src(n, "done")}>{md(w.get("done", ""))}</td>'
            f"<td{ctx.src(n, 'next')}>{md(w.get('next', ''))}</td>"
            f'<td class="muted"{ctx.src(n, "waiting_on")}>{md(w.get("waiting_on", ""))}</td></tr>'
        )
    legend = "".join(
        f'<span><span class="st {HEALTH[k][0]}">{HEALTH[k][1]}</span> {escape(t)}</span>'
        for k, t in HEALTH_LEGEND.items()
    )
    return f'<table class="compact" style="margin-top:14px">{head}{"".join(rows)}</table><div class="legend">{legend}</div>'


def block_diagram(b: dict[str, Any], ctx: Ctx) -> str:
    if b.get("type") not in DIAGRAMS:
        raise ValueError(f"unknown diagram type {b.get('type')!r}")
    svg = DIAGRAMS[b["type"]](b, f"d{ctx.n}")
    # Diagram labels carry paths relative to the diagram; this wrapper holds the diagram's own path.
    base = f' data-src-base="{escape(ctx.base)}"' if ctx.base is not None else ""
    return (
        f'<div style="width:100%;overflow-x:auto;margin-top:4px"{base}>'
        f'<div style="min-width:1000px;max-width:{int(b.get("max_width", 1100))}px">'
        f"{svg}</div></div>"
    )


def block_callout(b: str | dict[str, Any], ctx: Ctx) -> str:
    tone = " warn" if isinstance(b, dict) and b.get("tone") == "warn" else ""
    text = b["text"] if isinstance(b, dict) else b
    src = ctx.src("text") if isinstance(b, dict) else ctx.src()
    return f'<div class="callout{tone}"{src}>{md(text)}</div>'


def block_changes(b: list[str], ctx: Ctx) -> str:
    items = "".join(f"<li>{c}</li>" for c in b)
    return f'<div class="card changes" style="margin-top:20px"><ul>{items}</ul></div>'


BLOCKS: dict[str, Callable[[Any, Ctx], str]] = {
    "kpis": block_kpis,
    "agenda": block_agenda,
    "cards": block_cards,
    "table": block_table,
    "workstreams": block_workstreams,
    "diagram": block_diagram,
    "callout": block_callout,
    "changes": block_changes,
}


def slide(s: Slide, ctx: Ctx) -> str:
    ctx.n += 1
    n = ctx.index.get(id(s))
    path = None if n is None else f"slides/{n}"
    ctx.base = path
    title = s.get("layout") == "title"
    attrs = f' data-part="{escape(s["part"])}"' if s.get("part") else ""
    out = [
        f'<section class="slide{" title-slide" if title else ""}" data-section="main"{attrs}>',
        f'  <div class="kicker"{ctx.src("kicker")}>{md(s.get("kicker", ""))}</div>',
    ]
    out.append(
        f"  <h1{ctx.src('title')}>{md(s['title'])}</h1>"
        if title
        else f"  <h2{ctx.src('headline')}>{md(s['headline'])}</h2>"
    )
    if s.get("lede"):
        out.append(f'  <p class="lede"{ctx.src("lede")}>{md(s["lede"])}</p>')
    notes = ctx.src("notes")
    for k, block in enumerate(s.get("blocks", [])):
        ((kind, body),) = block.items()
        if kind not in BLOCKS:
            raise ValueError(f"unknown block {kind!r}")
        ctx.base = None if path is None else f"{path}/blocks/{k}/{kind}"
        out.append("  " + BLOCKS[kind](body, ctx))
    if s.get("notes"):
        out.append(f'  <aside class="notes"{notes}>{md(s["notes"])}</aside>')
    out.append("</section>\n")
    return "\n".join(out)


def what_changed(prev: Spec, cur: Spec) -> list[str]:
    """Compare two specs and describe the changes a returning reader cares about."""
    changes = []
    old = {w["name"]: w for w in _workstreams(prev)}
    for w in _workstreams(cur):
        o = old.get(w["name"])
        if o and o["health"] != w["health"]:
            reason = f": {md(w['reason'])}" if w.get("reason") else ""
            changes.append(
                f'<b>{md(w["name"])}</b> moved from <span class="was">{HEALTH[o["health"]][1]}</span> to '
                f"<b>{HEALTH[w['health']][1]}</b>{reason}"
            )
        elif not o:
            changes.append(f"New workstream: <b>{md(w['name'])}</b> ({HEALTH[w['health']][1]})")
    prev_blockers, cur_blockers = set(_blockers(prev)), set(_blockers(cur))
    changes += [f"Resolved: <b>{md(b)}</b>" for b in sorted(prev_blockers - cur_blockers)]
    changes += [f"New blocker: <b>{md(b)}</b>" for b in sorted(cur_blockers - prev_blockers)]
    for d in cur.get("decisions_made", []):
        changes.append(f"Decided: <b>{md(d['what'])}</b>, by {md(d['by'])}")
    return changes or ["No status changes since the last update."]


def _workstreams(spec: Spec) -> Iterator[dict[str, Any]]:
    for s in spec.get("slides", []):
        for b in s.get("blocks", []):
            if "workstreams" in b:
                yield from b["workstreams"]


def _blockers(spec: Spec) -> Iterator[str]:
    for s in spec.get("slides", []):
        if s.get("part") == "blockers":
            for b in s.get("blocks", []):
                if "table" in b:
                    yield from (r[0] for r in b["table"]["rows"])


def render(spec: Spec, previous: Spec | None = None, theme: str = "midnight") -> str:
    """The finished HTML page. With `previous`, a generated \"What changed\" slide follows the title.

    `theme` is what the deck opens in unless the URL or the viewer's last pick says otherwise.
    """
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r}; use one of {', '.join(THEMES)}")
    ctx = Ctx(spec)
    slides = list(spec["slides"])
    if previous is not None:
        changes = {
            "kicker": "What changed",
            "headline": spec.get("meta", {}).get("changes_headline", "Since the last update."),
            "part": "changes",
            "agenda": "What changed",
            "blocks": [{"changes": what_changed(previous, spec)}],
        }
        slides.insert(1, changes)
        ctx.spec = {**spec, "slides": slides}
    body = "<!-- ================= MAIN DECK ================= -->\n\n" + "".join(slide(s, ctx) for s in slides)
    meta = spec["meta"]
    shell = SHELL.read_text(encoding="utf-8")
    values = {
        "TITLE": escape(meta["title"]),
        "BRAND": escape(meta["brand"]),
        "SUBTITLE": escape(meta["subtitle"]),
        "THEME": theme,
        "SLIDES": body,
        # The spec without its comments, so edit mode can save an updated YAML next to the deck.
        # Escaping "<" keeps the JSON from closing its <script> early; JSON.parse reads it back unchanged.
        "SPEC": json.dumps(spec, ensure_ascii=False, default=str).replace("<", "\\u003c"),
    }
    # One pass, so a value that happens to contain a placeholder is never expanded.
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], shell)
