"""Smoke tests: the examples render, the guardrails fire, and the config resolves output.

Run with: python3 -m unittest discover -s tests
"""

import contextlib
import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import yaml

from deckgen import cli
from deckgen.check import check_contrast, check_spec
from deckgen.diagrams import DIAGRAMS
from deckgen.render import BLOCKS, render

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "examples" / "guide.yaml"


def example(name: str) -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load((ROOT / "examples" / name).read_text(encoding="utf-8"))
    return spec


class RenderTest(unittest.TestCase):
    def test_guide_renders_every_slide(self) -> None:
        spec = example("guide.yaml")
        html = render(spec)
        self.assertIn("<!DOCTYPE html>".lower(), html[:200].lower())
        self.assertEqual(html.count('class="slide'), len(spec["slides"]))

    def test_guide_passes_the_checks(self) -> None:
        errors, warnings = check_spec(example("guide.yaml"))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_themes_meet_contrast(self) -> None:
        self.assertEqual(check_contrast(), [])


class ShowcaseTest(unittest.TestCase):
    """examples/showcase.yaml uses every block and diagram type; its previous edition drives "What changed"."""

    def test_the_showcase_uses_every_block_and_diagram(self) -> None:
        spec = example("showcase.yaml")
        blocks = {kind for s in spec["slides"] for b in s.get("blocks", []) for kind in b}
        diagrams = {b["diagram"]["type"] for s in spec["slides"] for b in s.get("blocks", []) if "diagram" in b}
        self.assertEqual(blocks, set(BLOCKS) - {"changes"})
        self.assertEqual(diagrams, set(DIAGRAMS))

    def test_the_showcase_passes_the_checks_against_its_previous_edition(self) -> None:
        errors, warnings = check_spec(example("showcase.yaml"), example("showcase-previous.yaml"))
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(check_spec(example("showcase-previous.yaml")), ([], []))

    def test_what_changed_reports_health_moves_blockers_and_decisions(self) -> None:
        html = render(example("showcase.yaml"), example("showcase-previous.yaml"))
        for expected in (
            "<b>Ingest</b> moved from",
            "Resolved: <b>Queue migration</b>",
            "New blocker: <b>Click-log privacy review</b>",
            "New workstream: <b>Cut-over</b>",
            "Decided:",
        ):
            self.assertIn(expected, html)

    def test_edit_mode_can_map_every_editable_field_back_to_the_spec(self) -> None:
        spec = example("showcase.yaml")
        page = render(spec, example("showcase-previous.yaml"))
        embedded = re.search(r'<script type="application/json" id="deckgen-spec">(.*?)</script>', page, re.S)
        assert embedded is not None
        self.assertEqual(json.loads(embedded.group(1)), json.loads(json.dumps(spec, default=str)))
        paths = re.findall(r' data-src="([^"]+)"', page)
        bases = re.findall(r' data-src-base="([^"]+)"', page)
        self.assertTrue(all(p.startswith("slides/") for p in bases))
        self.assertGreater(len(paths), 100)
        for path in paths:
            # Diagram labels are relative to their diagram; resolve them against every diagram in the deck
            candidates = [path] if path.startswith("slides/") else [f"{b}/{path}" for b in bases]
            self.assertTrue(any(self.resolves(spec, c) for c in candidates), path)

    @staticmethod
    def resolves(spec: Any, path: str) -> bool:
        """The parent of the field exists, so edit mode can set it (an empty kicker has no value yet)."""
        *keys, last = path.split("/")
        node = spec
        for k in keys:
            try:
                node = node[int(k)] if isinstance(node, list) else node[k]
            except (KeyError, IndexError, ValueError, TypeError):
                return False
        return (isinstance(node, list) and last.isdigit() and int(last) < len(node)) or isinstance(node, dict)


class ReadmeTest(unittest.TestCase):
    def test_the_readme_example_passes_the_checks_and_renders(self) -> None:
        match = re.search(r"```yaml\n(meta:.*?)```", (ROOT / "README.md").read_text(encoding="utf-8"), re.S)
        assert match
        spec = yaml.safe_load(match.group(1))
        errors, _ = check_spec(spec)
        self.assertEqual(errors, [])
        self.assertIn("Payments migration", render(spec))

    def test_the_spec_reference_examples_pass_the_checks_and_render(self) -> None:
        text = (ROOT / "docs" / "spec.md").read_text(encoding="utf-8")
        snippets = re.findall(
            r"```yaml\n(- (?:kpis|agenda|cards|table|workstreams|callout|diagram):.*?)```", text, re.S
        )
        self.assertGreaterEqual(len(snippets), 10)
        spec = example("guide.yaml")
        spec["slides"] = spec["slides"][:1] + [
            {"headline": f"Example {n}.", "blocks": yaml.safe_load(s)} for n, s in enumerate(snippets)
        ]
        self.assertEqual(check_spec(spec), ([], []))
        self.assertEqual(render(spec).count('class="slide'), len(snippets) + 1)


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = example("guide.yaml")

    def test_template_is_blocked_until_its_questions_are_answered(self) -> None:
        errors, _ = check_spec(example("template.yaml"))
        self.assertTrue(any("TODO(ask)" in e for e in errors))

    def test_email_addresses_are_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["slides"][1]["notes"] = "Ask someone@example.com"
        errors, _ = check_spec(spec)
        self.assertTrue(any("email" in e for e in errors))

    def test_label_headlines_warn(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["slides"][1]["headline"] = "What it is"
        _, warnings = check_spec(spec)
        self.assertTrue(any("takeaway" in w for w in warnings))

    def test_unknown_diagram_endpoints_are_errors(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["slides"][2]["blocks"][0]["diagram"]["inputs"] = []
        spec["slides"][2]["blocks"][0]["diagram"]["edges"] = [{"from": "nowhere", "to": "nobody"}]
        spec["slides"][2]["blocks"][0]["diagram"]["nodes"] = [{"id": "a"}]
        errors, _ = check_spec(spec)
        self.assertTrue(any("unknown node" in e for e in errors))


class ShapeCheckTest(unittest.TestCase):
    """Malformed specs are reported by check_spec instead of crashing render."""

    def errors_for(self, block: dict[str, Any]) -> list[str]:
        spec = example("guide.yaml")
        spec["slides"][1]["blocks"] = [block]
        return check_spec(spec)[0]

    def test_unknown_block(self) -> None:
        self.assertTrue(any("unknown block 'slidez'" in e for e in self.errors_for({"slidez": []})))

    def test_block_with_two_keys(self) -> None:
        self.assertTrue(any("exactly one key" in e for e in self.errors_for({"callout": "a", "table": {}})))

    def test_unknown_diagram_type(self) -> None:
        errors = self.errors_for({"diagram": {"type": "pie", "title": "t", "desc": "d"}})
        self.assertTrue(any("unknown diagram type 'pie'" in e for e in errors))

    def test_style_values_must_be_lengths(self) -> None:
        errors = self.errors_for({"cards": {"widths": '1fr" onload="x', "cards": [{"title": "a"}]}})
        self.assertTrue(any("widths" in e for e in errors))

    def test_a_table_without_columns_is_an_error_not_a_crash(self) -> None:
        self.assertTrue(any("needs `columns`" in e for e in self.errors_for({"table": {"rows": [["a"]]}})))
        errors = self.errors_for({"table": {"columns": [{"width": "30%"}], "rows": [["a"]]}})
        self.assertTrue(any("needs a `label`" in e for e in errors))

    def test_a_non_string_headline_is_checked_not_a_crash(self) -> None:
        spec = example("guide.yaml")
        spec["slides"][1]["headline"] = 2026
        self.assertTrue(any("takeaway" in w for w in check_spec(spec)[1]))

    def test_blueprint_cells_must_match_stages(self) -> None:
        diagram = {
            "type": "blueprint",
            "title": "t",
            "desc": "d",
            "stages": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
            "layers": [{"kind": "customer", "label": "DOES", "cells": ["only one"]}],
        }
        self.assertTrue(any("1 cells for 2 stages" in e for e in self.errors_for({"diagram": diagram})))


class DiagramTest(unittest.TestCase):
    def test_architecture_routes_upward_turning_and_blocked_edges(self) -> None:
        diagram = {
            "title": "t",
            "desc": "d",
            "nodes": [
                {"id": "a", "name": "A", "col": 0, "row": 1},
                {"id": "b", "name": "B", "col": 0, "row": 0},
                {"id": "c", "name": "C", "col": 1, "row": 0},
                {"id": "d", "name": "D", "col": 2, "row": 2},
            ],
            "zones": [{"id": "z", "label": "LATER", "nodes": ["d"]}],
            "edges": [
                {"from": "a", "to": "b", "label": "up"},
                {"from": "a", "to": "c", "kind": "link", "label": "turn"},
                {"from": "a", "to_zone": "z", "kind": "blocked", "label": "not yet"},
            ],
            "legend": {"link": "EXTERNAL", "blocked": "BLOCKED"},
        }
        svg = DIAGRAMS["architecture"](diagram, "d1")
        self.assertEqual(svg.count('class="arrow blocked"'), 2)  # the edge and its legend sample
        for label in ("up", "turn", "not yet", "EXTERNAL", "BLOCKED"):
            self.assertIn(f">{label}</text>", svg)


class SafetyTest(unittest.TestCase):
    def test_a_title_containing_a_placeholder_is_not_expanded(self) -> None:
        spec = example("guide.yaml")
        spec["meta"]["title"] = "{{SLIDES}}"
        html = render(spec)
        self.assertIn("<title>{{SLIDES}}</title>", html)
        self.assertEqual(html.count('class="slide'), len(spec["slides"]))


class CliTest(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_render_prints_only_the_path_on_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "guide.html"
            code, out, err = self.run_cli("render", str(GUIDE), "-o", str(target))
            self.assertEqual((code, out.strip()), (0, str(target)))
            self.assertIn("0 error(s)", err)

    def test_render_refuses_while_checks_fail_unless_forced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec, target = Path(tmp) / "spec.yaml", Path(tmp) / "deck.html"
            draft = example("guide.yaml")
            draft["slides"][1]["notes"] = "TODO(ask): who owns this?"
            spec.write_text(yaml.safe_dump(draft), encoding="utf-8")
            code, out, err = self.run_cli("render", str(spec), "-o", str(target))
            self.assertEqual((code, out, target.exists()), (1, "", False))
            self.assertIn("not rendered", err)
            code, _, _ = self.run_cli("render", str(spec), "-o", str(target), "--force")
            self.assertEqual((code, target.exists()), (0, True))

    def offline(self, tmp: str) -> contextlib.AbstractContextManager[object]:
        """No user config, and the Python interpreter standing in for the browser, so nothing real is launched."""
        env = {"DECKGEN_CONFIG": str(Path(tmp) / "none.toml"), "DECKGEN_CHROME": sys.executable}
        return mock.patch.dict(os.environ, env)

    def test_pdf_renders_then_prints_to_pdf_next_to_the_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.offline(tmp), mock.patch.object(cli, "run") as run:
            target = Path(tmp) / "guide.html"
            code, out, _ = self.run_cli("pdf", str(GUIDE), "-o", str(target))
            self.assertEqual(code, 0)
            self.assertEqual(out.split(), [str(target), str(target.with_suffix(".pdf"))])
            cmd = run.call_args.args[0]
            self.assertIn(f"--print-to-pdf={target.with_suffix('.pdf')}", cmd)
            self.assertTrue(cmd[-1].endswith("guide.html?theme=midnight&mode=light"))

    def test_snap_shoots_every_slide_and_tiles_one_sheet_per_theme(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            self.offline(tmp),
            mock.patch.object(cli, "run") as run,
            mock.patch("shutil.which", side_effect=lambda name: name),
        ):
            target = Path(tmp) / "guide.html"
            target.write_text("<html></html>", encoding="utf-8")
            code, out, _ = self.run_cli(
                "snap", str(GUIDE), "-o", str(target), "--dir", tmp, "--themes", "midnight/dark"
            )
            self.assertEqual(code, 0)
            self.assertEqual(out.split(), [str(Path(tmp) / "guide-midnight-dark.png")])
            slides = len(example("guide.yaml")["slides"])
            self.assertEqual(run.call_count, slides + 1)  # one screenshot per slide, then the montage
            self.assertTrue(run.call_args_list[0].args[0][-1].endswith("?theme=midnight&mode=dark#1"))
            self.assertEqual(run.call_args.args[0][:2], ["magick", "montage"])

    def test_a_missing_spec_is_one_line_and_exit_2(self) -> None:
        code, out, err = self.run_cli("check", "/nonexistent/spec.yaml")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("deckgen: /nonexistent/spec.yaml"))

    def test_invalid_yaml_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.yaml"
            bad.write_text("meta: [unclosed\n", encoding="utf-8")
            code, _, err = self.run_cli("check", str(bad))
        self.assertEqual(code, 2)
        self.assertIn("invalid YAML", err)

    def test_a_missing_browser_is_explained(self) -> None:
        config = cli.Config.load(Path("/nonexistent/config.toml"))
        with (
            mock.patch.dict(os.environ, {"DECKGEN_CHROME": "/nonexistent/browser"}),
            self.assertRaises(cli.DeckgenError),
        ):
            config.browser()

    def test_a_hung_browser_is_one_line(self) -> None:
        hung = subprocess.TimeoutExpired("chromium", cli.TIMEOUT)
        with mock.patch.object(subprocess, "run", side_effect=hung), self.assertRaises(cli.DeckgenError) as caught:
            cli.run(["/usr/bin/chromium", "--headless"])
        self.assertIn("did not finish", str(caught.exception))


class ConfigTest(unittest.TestCase):
    def test_relative_output_resolves_against_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(f'output_dir = "{tmp}"\nchrome = "my-chrome"\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"DECKGEN_CONFIG": str(cfg)}):
                config = cli.Config.load()
            self.assertEqual(config.chrome, "my-chrome")
            self.assertEqual(cli.out_path(GUIDE, None, config), Path(tmp).resolve() / "out" / "deckgen_guide.html")

    def test_without_a_config_output_resolves_against_the_current_directory(self) -> None:
        config = cli.Config.load(Path("/nonexistent/config.toml"))
        self.assertEqual(cli.out_path(GUIDE, None, config), Path.cwd() / "out" / "deckgen_guide.html")

    def test_out_flag_wins(self) -> None:
        config = cli.Config.load(Path("/nonexistent/config.toml"))
        self.assertEqual(cli.out_path("ignored.yaml", "x/deck.html", config), Path("x/deck.html").resolve())

    def test_theme_sets_the_default_and_rejects_unknown_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text('theme = "catppuccin"\n', encoding="utf-8")
            self.assertEqual(cli.Config.load(cfg).theme, "catppuccin")
            cfg.write_text('theme = "neon"\n', encoding="utf-8")
            with self.assertRaises(cli.DeckgenError):
                cli.Config.load(cfg)
        html = render(example("guide.yaml"), theme="catppuccin")
        self.assertIn('<html lang="en" data-theme="catppuccin"', html)
        self.assertIn(": 'catppuccin';", html)
        self.assertEqual(cli.Config.load(Path("/nonexistent/config.toml")).theme, "midnight")

    def test_a_broken_config_is_one_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text("output_dir = [unclosed\n", encoding="utf-8")
            with self.assertRaises(cli.DeckgenError):
                cli.Config.load(cfg)


if __name__ == "__main__":
    unittest.main()
