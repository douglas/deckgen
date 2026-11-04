"""Shared type aliases. Specs are plain YAML data, so they stay dicts; these names say which dict is which."""

from typing import Any

Spec = dict[str, Any]
"""A whole deck spec: `meta`, `slides` and optional `decisions_made`."""
Slide = dict[str, Any]
Node = dict[str, Any]
"""One diagram element: a node, actor, step or stage."""
