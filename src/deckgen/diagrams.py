"""Data-driven diagrams in the diagram-design editorial grammar.

Every diagram is laid out from structured data (no hand-placed coordinates) and styled only through the
deck's `.dd` CSS classes, so it follows the active theme. Four layouts: architecture (zones on a grid),
sequence (lifelines), chain (a left-to-right dependency chain with inputs below) and blueprint (stages by layers).
"""

from collections.abc import Callable
from html import escape
from typing import Any

from ._types import Node

LEGEND_KINDS = ("accent", "link", "muted", "return", "blocked", "focal", "decision")


def src(*parts: object) -> str:
    """A `data-src` attribute: the spec path of a label, relative to the diagram (edit mode saves through it)."""
    return f' data-src="{escape("/".join(map(str, parts)))}"'


class Canvas:
    """Collects SVG markup for one diagram, and which legend kinds it used."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.parts: list[str] = []
        self.kinds: list[str] = []

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def used(self, kind: str | None) -> None:
        if kind and kind not in self.kinds:
            self.kinds.append(kind)

    def marker(self, kind: str) -> str:
        return f"url(#{self.prefix}-{ {'accent': 'arrow-accent', 'link': 'arrow-link'}.get(kind, 'arrow') })"

    def node(self, x: float, y: float, w: float, h: float, n: Node, *, path: str) -> None:
        kind = n.get("kind", "")
        self.used({"focal": "focal", "decision": "decision"}.get(kind))
        self.add(f'<rect class="mask" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
        self.add(f'<rect class="node {escape(kind)}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
        if n.get("tag"):
            tw = round(len(n["tag"]) * 5.2 + 12)
            self.add(f'<rect class="tag" x="{x + 8}" y="{y + 7}" width="{tw}" height="12" rx="2"/>')
            self.add(
                f'<text class="tagt" x="{x + 8 + tw / 2:.0f}" y="{y + 15.5}" text-anchor="middle"{src(path, "tag")}>{escape(n["tag"])}</text>'
            )
        self.add(
            f'<text class="name" x="{x + w / 2:.0f}" y="{y + h / 2 + 4:.0f}" text-anchor="middle"{src(path, "name")}>{escape(n["name"])}</text>'
        )
        if n.get("sub"):
            self.add(
                f'<text class="sub" x="{x + w / 2:.0f}" y="{y + h / 2 + 19:.0f}" text-anchor="middle"{src(path, "sub")}>{escape(n["sub"])}</text>'
            )

    def label(self, cx: float, y: float, text: str, path: str, cls: str = "") -> None:
        w = round(len(text) * 5.3 + 12)
        self.add(f'<rect class="lbl-bg" x="{cx - w / 2:.0f}" y="{y}" width="{w}" height="12" rx="2"/>')
        self.add(
            f'<text class="lbl {cls}" x="{cx:.0f}" y="{y + 9}" text-anchor="middle"{src(path)}>{escape(text)}</text>'
        )

    def side_label(self, x: float, cy: float, text: str, path: str, cls: str = "") -> None:
        w = round(len(text) * 5.3 + 12)
        self.add(f'<rect class="lbl-bg" x="{x}" y="{cy - 6:.0f}" width="{w}" height="12" rx="2"/>')
        self.add(f'<text class="lbl {cls}" x="{x + 6}" y="{cy + 3:.0f}"{src(path)}>{escape(text)}</text>')

    def legend(self, y: float, x0: float, x1: float, labels: dict[str, str]) -> int:
        items = [k for k in LEGEND_KINDS if k in self.kinds and labels.get(k)]
        if not items:
            return 0
        self.add(f'<line class="rule" x1="{x0}" y1="{y - 12}" x2="{x1}" y2="{y - 12}"/>')
        self.add(f'<text class="zl" x="{x0}" y="{y + 12}">LEGEND</text>')
        x, cy = x0 + 100, y + 9
        for kind in items:
            if kind in ("focal", "decision"):
                self.add(f'<rect class="node {kind}" x="{x}" y="{cy - 8}" width="30" height="16" rx="4"/>')
            elif kind == "blocked":
                self.add(
                    f'<line class="arrow blocked" x1="{x}" y1="{cy}" x2="{x + 26}" y2="{cy}"/>'
                    f'<line class="blocked-end" x1="{x + 28}" y1="{cy - 7}" x2="{x + 28}" y2="{cy + 7}"/>'
                )
            else:
                cls = {"accent": "arrow accent", "link": "arrow link", "return": "arrow ret"}.get(kind, "arrow")
                self.add(
                    f'<line class="{cls}" x1="{x}" y1="{cy}" x2="{x + 30}" y2="{cy}" marker-end="{self.marker(kind)}"/>'
                )
            text = labels[kind]
            self.add(f'<text class="lbl" x="{x + 40}" y="{cy + 3}"{src("legend", kind)}>{escape(text)}</text>')
            x += 40 + round(len(text) * 5.6) + 48
        return 48

    def svg(self, width: float, height: float, title: str, desc: str, top: float = 0) -> str:
        p = self.prefix
        defs = (
            "<defs>"
            f'<marker id="{p}-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon class="m-muted" points="0 0, 8 3, 0 6"/></marker>'
            f'<marker id="{p}-arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon class="m-accent" points="0 0, 8 3, 0 6"/></marker>'
            f'<marker id="{p}-arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon class="m-link" points="0 0, 8 3, 0 6"/></marker>'
            "</defs>"
        )
        return (
            f'<svg class="dd" viewBox="0 {top} {width} {height - top}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-labelledby="{p}-title {p}-desc"><title id="{p}-title">{escape(title)}</title>'
            f'<desc id="{p}-desc">{escape(desc)}</desc>{defs}'
            f'<rect class="paper" x="0" y="{top}" width="{width}" height="{height - top}"/>'
            + "\n".join(self.parts)
            + "</svg>"
        )


def architecture(spec: dict[str, Any], prefix: str) -> str:
    """Zones on a grid. Nodes take `col`/`row`; zones list their node ids; edges route orthogonally."""
    W, H, GAP, X0 = 196, 60, 96, 16
    ROW_Y = {0: 96, 1: 236, 2: 372, 3: 508}
    c = Canvas(prefix)
    nodes: dict[str, Node] = {}
    for i, n in enumerate(spec["nodes"]):
        w = n.get("width", W)
        x = X0 + n["col"] * (W + GAP) + (W - w)
        y = ROW_Y[n["row"]] + (8 if n.get("kind") == "focal" else 0)
        nodes[n["id"]] = {
            **n,
            "x": x,
            "y": y,
            "w": w,
            "h": H - (8 if n.get("kind") == "focal" else 0),
            "path": f"nodes/{i}",
        }
    width = X0 * 2 + (max(n["col"] for n in spec["nodes"]) + 1) * (W + GAP) - GAP + 16
    zones: dict[str, tuple[float, float, float, float]] = {}
    for zi, z in enumerate(spec.get("zones", [])):
        member = [nodes[i] for i in z["nodes"]]
        x0, y0 = min(m["x"] for m in member) - 20, min(m["y"] for m in member) - 32
        x1, y1 = (
            max(m["x"] + m["w"] for m in member) + 20,
            max(m["y"] + m["h"] for m in member) + 32 + z.get("extra_bottom", 0),
        )
        zones[z["id"]] = (x0, y0, x1, y1)
        lw = round(len(z["label"]) * 5.0 + 16)
        c.add(f'<rect class="zone" x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="8"/>')
        c.add(f'<rect class="zl-bg" x="{(x0 + x1) / 2 - lw / 2:.0f}" y="{y0 - 6}" width="{lw}" height="12" rx="2"/>')
        c.add(
            f'<text class="zl" x="{(x0 + x1) / 2:.0f}" y="{y0 + 3}" text-anchor="middle"{src("zones", zi, "label")}>{escape(z["label"])}</text>'
        )
    bottom = max([n["y"] + n["h"] for n in nodes.values()] + [z[3] for z in zones.values()])
    for ei, e in enumerate(spec.get("edges", [])):
        kind = e.get("kind", "muted")
        cls = {"accent": "arrow accent", "link": "arrow link", "return": "arrow ret"}.get(kind, "arrow")
        a = nodes[e["from"]]
        lbl_cls = "accent" if kind == "accent" else ""
        if kind == "blocked":
            zx0, *_ = zones[e["to_zone"]]
            x, y_run = a["x"] + 64, a["y"] + a["h"] + 52
            c.add(
                f'<path class="arrow blocked" d="M{x},{a["y"] + a["h"]} V{y_run - 8} Q{x},{y_run} {x + 8},{y_run} H{zx0 - 4}"/>'
            )
            c.add(f'<line class="blocked-end" x1="{zx0 - 2}" y1="{y_run - 10}" x2="{zx0 - 2}" y2="{y_run + 10}"/>')
            if e.get("label"):
                c.label((x + zx0) / 2 + 20, y_run - 22, e["label"], f"edges/{ei}/label")
            c.used("blocked")
            bottom = max(bottom, y_run + 16)
            continue
        b = nodes[e["to"]]
        c.used(kind)
        if a["row"] == b["row"]:
            ay = a["y"] + a["h"] / 2
            c.add(
                f'<line class="{cls}" x1="{a["x"] + a["w"]}" y1="{ay:.0f}" x2="{b["x"] - 2}" y2="{ay:.0f}" marker-end="{c.marker(kind)}"/>'
            )
            if e.get("label"):
                c.label((a["x"] + a["w"] + b["x"]) / 2, ay - 22, e["label"], f"edges/{ei}/label", lbl_cls)
        elif a["col"] == b["col"]:
            cx = a["x"] + a["w"] / 2
            if b["y"] > a["y"]:
                y1, y2 = a["y"] + a["h"], b["y"] - 2
            else:  # the target sits above: leave the top edge, enter the bottom
                y1, y2 = a["y"], b["y"] + b["h"] + 2
            c.add(
                f'<line class="{cls}" x1="{cx:.0f}" y1="{y1}" x2="{cx:.0f}" y2="{y2}" marker-end="{c.marker(kind)}"/>'
            )
            if e.get("label"):
                c.side_label(cx + 8, (y1 + y2) / 2, e["label"], f"edges/{ei}/label", lbl_cls)
        else:  # leave the right edge, turn once, enter the top or bottom of the target
            ay, bx = a["y"] + a["h"] / 2, b["x"] + b["w"] / 2
            down = b["y"] > a["y"]
            by = b["y"] - 2 if down else b["y"] + b["h"] + 2
            sgn = 1 if down else -1
            c.add(
                f'<path class="{cls}" d="M{a["x"] + a["w"]},{ay:.0f} H{bx - 8:.0f} Q{bx:.0f},{ay:.0f} {bx:.0f},{ay + 8 * sgn:.0f} V{by}" marker-end="{c.marker(kind)}"/>'
            )
            if e.get("label"):
                c.side_label(bx + 8, (ay + by) / 2, e["label"], f"edges/{ei}/label", lbl_cls)
    for n in nodes.values():
        c.node(n["x"], n["y"], n["w"], n["h"], n, path=n["path"])
    extra = c.legend(bottom + 40, X0, width - X0, spec.get("legend", {}))
    return c.svg(width, bottom + 40 + extra + 12, spec["title"], spec["desc"], top=44)


def sequence(spec: dict[str, Any], prefix: str) -> str:
    """Lifelines in a row; messages flow down. `self` messages loop on one lifeline."""
    actors = spec["actors"]
    width = spec.get("width", 1040)
    step = (width - 2 * 128) / max(1, len(actors) - 1)
    X = {a["id"]: 128 + i * step for i, a in enumerate(actors)}
    c = Canvas(prefix)
    y = 108
    rows: list[tuple[int, int, dict[str, Any]]] = []
    touch: dict[str, list[int]] = {}
    for mi, m in enumerate(spec["messages"]):
        ids = [m["self"]] if m.get("self") else [m["from"], m["to"]]
        rows.append((y, mi, m))
        for i in ids:
            touch.setdefault(i, [y, y])
            touch[i][1] = y + (24 if m.get("self") else 0)
        y += 40 if not m.get("self") else 48
    top, bot = 80, y
    first = actors[0]["id"]
    for a in actors:
        c.add(f'<line class="life" x1="{X[a["id"]]:.0f}" y1="{top}" x2="{X[a["id"]]:.0f}" y2="{bot}"/>')
    for i, (y0, y1) in touch.items():
        if i != first:
            c.add(f'<rect class="act" x="{X[i] - 4:.0f}" y="{y0 - 4}" width="8" height="{y1 - y0 + 8}"/>')
    for y0, mi, m in rows:
        kind = m.get("kind", "muted")
        lbl_cls = "accent" if kind == "accent" else ""
        if m.get("self"):
            x = X[m["self"]]
            c.add(
                f'<path class="arrow" d="M{x + 4:.0f},{y0} H{x + 36:.0f} Q{x + 44:.0f},{y0} {x + 44:.0f},{y0 + 8} V{y0 + 16} '
                f'Q{x + 44:.0f},{y0 + 24} {x + 36:.0f},{y0 + 24} H{x + 6:.0f}" marker-end="{c.marker("muted")}"/>'
            )
            c.side_label(x + 52, y0 + 12, m["label"], f"messages/{mi}/label")
            c.used("muted")
            continue
        a, b = X[m["from"]], X[m["to"]]
        cls = {"accent": "arrow accent", "link": "arrow link", "return": "arrow ret"}.get(kind, "arrow")
        d = 1 if b > a else -1
        c.add(
            f'<line class="{cls}" x1="{a + 4 * d:.0f}" y1="{y0}" x2="{b - 6 * d:.0f}" y2="{y0}" marker-end="{c.marker(kind)}"/>'
        )
        c.label((a + b) / 2, y0 - 20, m["label"], f"messages/{mi}/label", lbl_cls)
        c.used(kind)
    for ai, a in enumerate(actors):
        w = a.get("width", 176)
        c.node(round(X[a["id"]] - w / 2), 20, w, 56, a, path=f"actors/{ai}")
    extra = c.legend(bot + 32, 16, width - 16, spec.get("legend", {}))
    return c.svg(width, bot + 32 + extra + 12, spec["title"], spec["desc"])


def chain(spec: dict[str, Any], prefix: str) -> str:
    """Left-to-right dependency chain; `inputs` sit under a step and feed into it from below."""
    steps = spec["steps"]
    W, Y, H, GAP = 152, 64, 64, 28
    xs = [16 + i * (W + GAP) for i in range(len(steps))]
    width = xs[-1] + W + 16
    c = Canvas(prefix)
    for i in range(len(steps) - 1):
        c.add(
            f'<line class="arrow" x1="{xs[i] + W}" y1="{Y + 32}" x2="{xs[i + 1] - 2}" y2="{Y + 32}" marker-end="{c.marker("muted")}"/>'
        )
    c.used("muted")
    inputs = spec.get("inputs", [])
    for inp in inputs:
        cx = xs[inp["under"]] + W / 2
        c.add(
            f'<line class="arrow" x1="{cx:.0f}" y1="200" x2="{cx:.0f}" y2="{Y + H + 2}" marker-end="{c.marker("muted")}"/>'
        )
    for si, (x, s) in enumerate(zip(xs, steps, strict=True)):
        c.node(x, Y, W, H, s, path=f"steps/{si}")
    for ii, inp in enumerate(inputs):
        c.node(xs[inp["under"]], 200, W, 56, inp, path=f"inputs/{ii}")
    bottom = 256 if inputs else Y + H
    extra = c.legend(bottom + 44, 16, width - 16, spec.get("legend", {}))
    return c.svg(width, bottom + 44 + extra + 12, spec["title"], spec["desc"])


BLUEPRINT_LAYERS = ("customer", "frontstage", "backstage", "support")


def blueprint(spec: dict[str, Any], prefix: str) -> str:
    """Service blueprint: stages as columns, layers as rows, a line of visibility under the frontstage.

    Each layer lists one cell per stage (`name`, optional `sub`, `tag` and `focal`); `—` marks an empty cell.
    Optional: `persona` ({eyebrow, name}) labels the flow in the header margin, `grid` sizes the canvas for more
    columns than stages (so stacked blueprints line up), `row_height` sets the cell height, and no `legend` omits it.
    """
    stages, layers = spec["stages"], spec["layers"]
    order = [(li, layer) for kind in BLUEPRINT_LAYERS for li, layer in enumerate(layers) if layer["kind"] == kind]
    L, G = spec.get("margin", 112), 12
    W = spec.get("column", 176)
    width = L + spec.get("grid", len(stages)) * (W + G) - G + 16
    xs = [L + i * (W + G) for i in range(len(stages))]
    c = Canvas(prefix)
    if spec.get("persona"):
        c.add(
            f'<text class="zl" x="{L - 12}" y="34" text-anchor="end"{src("persona", "eyebrow")}>{escape(spec["persona"].get("eyebrow", ""))}</text>'
        )
        c.add(
            f'<text class="name" x="{L - 12}" y="52" text-anchor="end"{src("persona", "name")}>{escape(spec["persona"]["name"])}</text>'
        )
    for si, (x, s) in enumerate(zip(xs, stages, strict=True)):
        c.add(f'<rect class="stage-hd" x="{x}" y="20" width="{W}" height="40" data-stage="{escape(s["id"])}"/>')
        c.add(
            f'<text class="zl" x="{x + W / 2:.0f}" y="34" text-anchor="middle"{src("stages", si, "eyebrow")}>{escape(s.get("eyebrow", ""))}</text>'
        )
        c.add(
            f'<text class="name" x="{x + W / 2:.0f}" y="52" text-anchor="middle"{src("stages", si, "name")}>{escape(s["name"])}</text>'
        )
    y, H = 72, spec.get("row_height", 60)
    for i, (li, layer) in enumerate(order):
        kind = layer["kind"]
        if i:
            prev = order[i - 1][1]["kind"]
            role = (
                "visibility"
                if prev == "frontstage" and kind == "backstage"
                else ("interaction" if prev == "customer" else "internal-interaction")
            )
            cls = "vis" if role == "visibility" else "hair"
            c.add(f'<line class="{cls}" x1="{L - 8}" y1="{y + 4}" x2="{xs[-1] + W}" y2="{y + 4}" data-role="{role}"/>')
            y += 8
        c.add(
            f'<text class="zl" x="{L - 12}" y="{y + H / 2 - 2:.0f}" text-anchor="end"{src("layers", li, "label")}>{escape(layer["label"])}</text>'
        )
        if layer.get("sublabel"):
            c.add(
                f'<text class="sub" x="{L - 12}" y="{y + H / 2 + 11:.0f}" text-anchor="end"{src("layers", li, "sublabel")}>{escape(layer["sublabel"])}</text>'
            )
        c.add(f'<g data-layer="{kind}">')
        for ci, (x, s, raw) in enumerate(zip(xs, stages, layer["cells"], strict=True)):
            cell = {"name": raw} if isinstance(raw, str) else raw
            cpath = f"layers/{li}/cells/{ci}"
            focal = cell.get("focal")
            c.used("focal" if focal else None)
            fill = "focal" if focal else ("back" if kind in ("backstage", "support") else "front")
            empty = cell["name"] in ("—", "Not applicable")
            focal_attr = ' data-focal="true"' if focal else ""
            c.add(
                f'<rect class="cell {fill}{" empty" if empty else ""}" x="{x}" y="{y}" width="{W}" height="{H}" rx="4" '
                f'data-stage="{escape(s["id"])}" data-name="{escape(cell["name"])}"{focal_attr}/>'
            )
            if cell.get("tag"):
                tw = round(len(cell["tag"]) * 5.2 + 12)
                c.add(f'<rect class="tag" x="{x + 6}" y="{y + 6}" width="{tw}" height="12" rx="2"/>')
                c.add(
                    f'<text class="tagt" x="{x + 6 + tw / 2:.0f}" y="{y + 14.5}" text-anchor="middle"{src(cpath, "tag")}>{escape(cell["tag"])}</text>'
                )
            ty = y + H / 2 + (8 if cell.get("tag") else 4) - (6 if cell.get("sub") else 0)
            name_cls = "cname accent" if focal else ("cname muted" if empty else "cname")
            c.add(
                f'<text class="{name_cls}" x="{x + W / 2:.0f}" y="{ty:.0f}" text-anchor="middle"{src(cpath if isinstance(raw, str) else f"{cpath}/name")}>{escape(cell["name"])}</text>'
            )
            if cell.get("sub"):
                c.add(
                    f'<text class="sub" x="{x + W / 2:.0f}" y="{ty + 14:.0f}" text-anchor="middle"{src(cpath, "sub")}>{escape(cell["sub"])}</text>'
                )
        c.add("</g>")
        y += H
    labels = spec.get("legend", {})
    if not labels:
        return c.svg(width, y + 12, spec["title"], spec["desc"])
    c.add(f'<line class="rule" x1="16" y1="{y + 28}" x2="{width - 16}" y2="{y + 28}"/>')
    c.add(f'<text class="zl" x="16" y="{y + 52}">LEGEND</text>')
    x, cy = 116, y + 49
    for key, sample in (("visibility", "vis"), ("backstage", "back"), ("focal", "focal")):
        if not labels.get(key):
            continue
        if sample == "vis":
            c.add(f'<line class="vis" x1="{x}" y1="{cy}" x2="{x + 30}" y2="{cy}"/>')
        else:
            c.add(f'<rect class="cell {sample}" x="{x}" y="{cy - 8}" width="30" height="16" rx="4"/>')
        c.add(f'<text class="lbl" x="{x + 40}" y="{cy + 3}"{src("legend", key)}>{escape(labels[key])}</text>')
        x += 40 + round(len(labels[key]) * 5.6) + 48
    return c.svg(width, y + 72, spec["title"], spec["desc"])


DIAGRAMS: dict[str, Callable[[dict[str, Any], str], str]] = {
    "architecture": architecture,
    "sequence": sequence,
    "chain": chain,
    "blueprint": blueprint,
}
