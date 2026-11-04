"""Guardrails for decks: structure, ownership, wording, privacy and theme contrast."""

import re
from collections.abc import Iterator
from typing import Any

from ._types import Spec
from .diagrams import DIAGRAMS
from .render import BLOCKS, HEALTH, SHELL

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TODO = re.compile(r"TODO\(ask\)", re.I)
CSS_LENGTH = re.compile(r"^\d+(\.\d+)?(px|%|fr|em|rem)?$")
ARCHITECTURE_ROWS = range(4)


def _walk(node: object, path: str = "") -> Iterator[tuple[str, object]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, node


def check_spec(spec: Spec, previous: Spec | None = None) -> tuple[list[str], list[str]]:
    """Errors (which block rendering) and warnings (review comments) for a spec, against its previous edition."""
    errors: list[str] = []
    warnings: list[str] = []
    errors += [f"meta.{key} is required" for key in ("title", "brand", "subtitle") if not spec.get("meta", {}).get(key)]
    slides = spec.get("slides") or []
    if not slides:
        errors.append("slides is empty")
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            errors.append(f"slides[{i}]: must be a mapping")
            continue
        where = f"slides[{i}] ({s.get('part') or s.get('kicker', '?')})"
        if s.get("layout") == "title":
            if not s.get("title"):
                errors.append(f"{where}: title slide needs a title")
        elif not s.get("headline"):
            errors.append(f"{where}: headline is required")
        elif not str(s["headline"]).rstrip().endswith((".", "?", "!")):
            warnings.append(f"{where}: headline reads like a label; state the takeaway as a sentence")
        for b in s.get("blocks", []):
            if not isinstance(b, dict) or len(b) != 1:
                errors.append(f"{where}: each block must be a mapping with exactly one key, such as `- cards: …`")
                continue
            ((kind, body),) = b.items()
            if kind not in BLOCKS or kind == "changes":
                errors.append(
                    f"{where}: unknown block {kind!r}; use one of {', '.join(k for k in BLOCKS if k != 'changes')}"
                )
                continue
            if shape := _check_block(kind, body):
                errors += [f"{where}: {e}" for e in shape]
                continue
            if kind == "workstreams":
                for w in body:
                    if not w.get("owner"):
                        errors.append(f"{where}: workstream {w.get('name')!r} has no owner")
                    if w.get("health") not in HEALTH:
                        errors.append(
                            f"{where}: workstream {w.get('name')!r} health must be one of {', '.join(HEALTH)}"
                        )
            if kind == "cards" and body.get("glossary"):
                warnings += [
                    f"{where}: glossary term {c.get('title')!r} has no owning team"
                    for c in body["cards"]
                    if not c.get("owner")
                ]
            if kind == "table":
                cols = [str(c["label"]).lower() for c in body["columns"]]
                if "owner" in cols:
                    j = cols.index("owner")
                    for r in body["rows"]:
                        if len(r) <= j or not str(r[j]).strip():
                            errors.append(f"{where}: row {r[0]!r} has no owner")
                for r in body["rows"]:
                    if len(r) != len(cols):
                        errors.append(f"{where}: row {r[0]!r} has {len(r)} cells for {len(cols)} columns")
            if kind == "diagram":
                ids = {n["id"] for n in body.get("nodes", [])} | {a["id"] for a in body.get("actors", [])}
                for e in body.get("edges", []) + body.get("messages", []):
                    for end in ("from", "to", "self"):
                        if end in e and e[end] not in ids:
                            errors.append(f"{where}: diagram edge refers to unknown node {e[end]!r}")
    if previous is not None:
        old = {
            w["name"]: w["health"]
            for s in previous.get("slides", [])
            for b in s.get("blocks", [])
            if "workstreams" in b
            for w in b["workstreams"]
        }
        for s in slides:
            for b in s.get("blocks", []):
                for w in b.get("workstreams", []):
                    if w["name"] in old and old[w["name"]] != w["health"] and not w.get("reason"):
                        errors.append(f"workstream {w['name']!r} changed health without a reason")
    for path, value in _walk(spec):
        if isinstance(value, str):
            if EMAIL.search(value):
                errors.append(f"{path}: contains an email address; keep personal data out of decks")
            if TODO.search(value):
                errors.append(f"{path}: unanswered TODO(ask)")
    return errors, warnings


def _check_block(kind: str, body: Any) -> list[str]:
    """Shape errors that would otherwise crash rendering or inject markup through style values."""
    errors = []
    if kind in ("cards", "table", "diagram") and not isinstance(body, dict):
        return [f"{kind} must be a mapping"]
    if kind in ("kpis", "workstreams") and not isinstance(body, list):
        return [f"{kind} must be a list"]
    if kind == "cards":
        if not isinstance(body.get("cards"), list):
            errors.append("cards needs a `cards:` list")
        errors += [
            f"cards {key} must be a whole number"
            for key in ("columns", "font_size")
            if key in body and not isinstance(body[key], int)
        ]
        if "widths" in body and not all(CSS_LENGTH.match(w) for w in str(body["widths"]).split()):
            errors.append("cards widths must be space-separated lengths such as `1fr 2fr` or `30%`")
    if kind == "table":
        errors += [
            f"table column {c.get('label')!r} width must be a length such as `30%`"
            for c in body.get("columns", [])
            if "width" in c and not CSS_LENGTH.match(str(c["width"]))
        ]
        if not body.get("columns") or "rows" not in body:
            errors.append("table needs `columns` and `rows`")
        elif not all(isinstance(c, dict) and c.get("label") for c in body["columns"]):
            errors.append("every table column needs a `label`")
    if kind == "diagram":
        errors += _check_diagram(body)
    return errors


def _check_diagram(d: dict[str, Any]) -> list[str]:
    kind = d.get("type")
    if kind not in DIAGRAMS:
        return [f"unknown diagram type {kind!r}; use one of {', '.join(DIAGRAMS)}"]
    errors = [f"diagram needs a `{k}`" for k in ("title", "desc") if not d.get(k)]
    if "max_width" in d and not isinstance(d["max_width"], int):
        errors.append("diagram max_width must be a whole number of pixels")
    if kind == "architecture":
        ids = {n.get("id") for n in d.get("nodes", [])}
        errors += [
            f"architecture node {n.get('id')!r} needs a row from 0 to 3"
            for n in d.get("nodes", [])
            if n.get("row") not in ARCHITECTURE_ROWS
        ]
        errors += [
            f"zone {z.get('id')!r} lists unknown node {m!r}"
            for z in d.get("zones", [])
            for m in z.get("nodes", [])
            if m not in ids
        ]
        zone_ids = {z.get("id") for z in d.get("zones", [])}
        errors += [
            f"blocked edge points at unknown zone {e.get('to_zone')!r}"
            for e in d.get("edges", [])
            if e.get("kind") == "blocked" and e.get("to_zone") not in zone_ids
        ]
    if kind == "chain":
        steps = len(d.get("steps", []))
        errors += [
            f"chain input {inp.get('name')!r} is under step {inp.get('under')!r}, but steps run 0 to {steps - 1}"
            for inp in d.get("inputs", [])
            if not isinstance(inp.get("under"), int) or not 0 <= inp["under"] < steps
        ]
    if kind == "blueprint":
        stages = len(d.get("stages", []))
        errors += [
            f"blueprint layer {layer.get('label')!r} has {len(layer.get('cells', []))} cells for {stages} stages"
            for layer in d.get("layers", [])
            if len(layer.get("cells", [])) != stages
        ]
    return errors


def _lum(h: str) -> float:
    c = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _ratio(a: str, b: str) -> float:
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def check_contrast(css: str | None = None) -> list[str]:
    """Every text color against the page and card background, for every theme and mode in the shell."""
    css = SHELL.read_text(encoding="utf-8") if css is None else css
    tokens: dict[tuple[str, str], dict[str, str]] = {}
    for theme, mode, body in re.findall(r'\[data-theme="(\w+)"\]\[data-mode="(\w+)"\]\s*\{([^}]*)\}', css):
        tokens.setdefault((theme, mode), {}).update(dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", body)))
    return [
        f"{theme}/{mode}: --{fg} on --{bg} is {_ratio(t[fg], t[bg]):.2f}:1 (needs 4.5)"
        for (theme, mode), t in sorted(tokens.items())
        for fg in ("ink", "muted", "soft", "accent", "link", "green", "amber", "red", "violet")
        for bg in ("bg", "panel")
        if fg in t and bg in t and _ratio(t[fg], t[bg]) < 4.5
    ]
