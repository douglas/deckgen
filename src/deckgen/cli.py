"""deckgen: render, check and export slide decks from YAML specs.

  deckgen render SPEC [-o OUT] [--previous PREV]   write the HTML deck (adds "What changed" with --previous)
  deckgen check SPEC [--previous PREV]             validate content and theme contrast
  deckgen pdf SPEC [--previous PREV]               render, then export a PDF next to the HTML
  deckgen snap SPEC [--themes ...] [--dir DIR]     screenshot every slide per theme into a contact sheet

Settings: ~/.config/deckgen/config.toml (or $DECKGEN_CONFIG), keys output_dir, snap_dir, chrome and theme.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import yaml

from . import __version__
from ._types import Spec
from .check import check_contrast, check_spec
from .render import THEMES, render

CHROME_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")


class DeckgenError(Exception):
    """A problem the user can fix: printed as one line, exit status 2."""


def config_path() -> Path:
    """$DECKGEN_CONFIG, else $XDG_CONFIG_HOME/deckgen/config.toml, else ~/.config/deckgen/config.toml."""
    if os.environ.get("DECKGEN_CONFIG"):
        return Path(os.environ["DECKGEN_CONFIG"]).expanduser()
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "deckgen" / "config.toml"


@dataclass(frozen=True)
class Config:
    """Settings from the config file. A missing file means the defaults."""

    output_dir: Path
    snap_dir: Path
    chrome: str | None = None
    theme: str = "midnight"

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        path = path or config_path()
        data: dict[str, object] = {}
        if path.exists():
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as e:
                raise DeckgenError(f"{path}: {e}") from e
        theme = str(data.get("theme", "midnight"))
        if theme not in THEMES:
            raise DeckgenError(f"{path}: unknown theme {theme!r}; use one of {', '.join(THEMES)}")
        return cls(
            output_dir=Path(str(data.get("output_dir", Path.cwd()))).expanduser().resolve(),
            snap_dir=Path(str(data.get("snap_dir", tempfile.gettempdir()))).expanduser(),
            chrome=str(data["chrome"]) if data.get("chrome") else None,
            theme=theme,
        )

    def browser(self) -> str:
        """The Chromium-family browser to drive: $DECKGEN_CHROME, the config's `chrome`, else the first on PATH."""
        wanted = os.environ.get("DECKGEN_CHROME") or self.chrome
        for name in [wanted] if wanted else CHROME_NAMES:
            found = shutil.which(str(Path(name).expanduser()))
            if found:
                return found
        raise DeckgenError(
            f"no Chromium-family browser found (tried {wanted or ', '.join(CHROME_NAMES)}); "
            "set DECKGEN_CHROME or `chrome` in the config"
        )


def load(path: str | Path) -> Spec:
    """Read a spec, turning file and YAML problems into one-line errors."""
    try:
        spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise DeckgenError(f"{path}: {e.strerror}") from e
    except yaml.YAMLError as e:
        raise DeckgenError(f"{path}: invalid YAML: {e}") from e
    if not isinstance(spec, dict) or not isinstance(spec.get("meta"), dict):
        raise DeckgenError(f"{path}: a spec is a mapping with `meta` and `slides`")
    return spec


def out_path(spec_path: str | Path, out: str | None, cfg: Config, spec: Spec | None = None) -> Path:
    """`-o`, else an absolute `meta.output`, else `meta.output` (or `<spec name>.html`) under the output dir."""
    if out:
        return Path(out).resolve()
    meta = (spec or load(spec_path))["meta"]
    name = Path(meta.get("output") or Path(spec_path).with_suffix(".html").name).expanduser()
    return name if name.is_absolute() else cfg.output_dir / name


TIMEOUT = 120  # seconds; headless Chromium occasionally hangs instead of exiting


def run(cmd: Sequence[str | Path]) -> None:
    """Run a helper program; on failure, raise with the last line of its own error output."""
    try:
        subprocess.run([str(c) for c in cmd], check=True, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise DeckgenError(f"{Path(cmd[0]).name} did not finish within {TIMEOUT} seconds") from e
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip().splitlines()
        raise DeckgenError(
            f"{Path(cmd[0]).name} failed: {detail[-1] if detail else f'exit status {e.returncode}'}"
        ) from e


def deck_url(path: Path, theme: str, mode: str, slide: int | None = None) -> str:
    return f"{path.resolve().as_uri()}?theme={theme}&mode={mode}" + (f"#{slide}" if slide else "")


def export_pdf(path: Path, cfg: Config, theme: str | None = None, mode: str = "light") -> Path:
    """One PDF page per slide, next to the HTML (same as bin/export-pdf), in the config's theme by default."""
    out = path.with_suffix(".pdf")
    run(
        [
            cfg.browser(),
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=8000",
            f"--print-to-pdf={out}",
            deck_url(path, theme or cfg.theme, mode),
        ]
    )
    return out


def report(spec: Spec, prev: Spec | None) -> int:
    """Print the check results to stderr; 1 if there are errors."""
    errors, warnings = check_spec(spec, prev)
    errors += check_contrast()
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
    return 1 if errors else 0


def cmd_check(args: argparse.Namespace, _cfg: Config) -> int:
    return report(load(args.spec), load(args.previous) if args.previous else None)


def render_deck(args: argparse.Namespace, cfg: Config) -> Path | None:
    """Check, then write the HTML deck and print its path; None if the checks failed without --force."""
    spec = load(args.spec)
    prev = load(args.previous) if args.previous else None
    if report(spec, prev) and not args.force:
        print("not rendered: fix the errors above or pass --force", file=sys.stderr)
        return None
    path = out_path(args.spec, args.out, cfg, spec)
    try:
        html = render(spec, prev, cfg.theme)
    except (KeyError, ValueError, TypeError) as e:
        raise DeckgenError(f"{args.spec}: cannot render ({e}); run `deckgen check` for details") from e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(path)
    return path


def cmd_render(args: argparse.Namespace, cfg: Config) -> int:
    return 0 if render_deck(args, cfg) else 1


def cmd_pdf(args: argparse.Namespace, cfg: Config) -> int:
    path = render_deck(args, cfg)
    if path is None:
        return 1
    print(export_pdf(path, cfg))
    return 0


def cmd_snap(args: argparse.Namespace, cfg: Config) -> int:
    spec = load(args.spec)
    path = out_path(args.spec, args.out, cfg, spec)
    if not path.exists():
        raise DeckgenError(f"{path} does not exist; run `deckgen render` first")
    magick = shutil.which("magick")
    if not magick:
        raise DeckgenError("contact sheets need ImageMagick 7 (`magick`) on PATH")
    browser = cfg.browser()
    count = len(spec["slides"]) + (1 if args.previous else 0)
    snap_dir = Path(args.dir).expanduser() if args.dir else cfg.snap_dir
    snap_dir.mkdir(parents=True, exist_ok=True)
    sheets = []
    with tempfile.TemporaryDirectory(prefix="deckgen-") as tmp:
        for combo in args.themes or [f"{cfg.theme}/light", f"{cfg.theme}/dark"]:
            theme, _, mode = combo.partition("/")
            mode = mode or "light"
            shots = []
            for n in range(1, count + 1):
                shot = Path(tmp) / f"{theme}-{mode}-{n:02}.png"
                run(
                    [
                        browser,
                        "--headless",
                        "--disable-gpu",
                        "--window-size=1440,900",
                        f"--screenshot={shot}",
                        deck_url(path, theme, mode, n),
                    ]
                )
                shots.append(shot)
            sheet = snap_dir / f"{path.stem}-{theme}-{mode}.png"
            run([magick, "montage", *shots, "-tile", "3x", "-geometry", "720x450+6+6", "-background", "#888", sheet])
            sheets.append(sheet)
    print("\n".join(map(str, sheets)))
    return 0


COMMANDS: dict[str, Callable[[argparse.Namespace, Config], int]] = {
    "render": cmd_render,
    "check": cmd_check,
    "pdf": cmd_pdf,
    "snap": cmd_snap,
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="deckgen", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--version", action="version", version=f"deckgen {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in COMMANDS:
        s = sub.add_parser(name)
        s.add_argument("spec")
        s.add_argument("--previous", help="the previous update's spec, for 'What changed' and health-change checks")
        s.add_argument("-o", "--out")
        s.add_argument("--force", action="store_true", help="render even if checks fail")
        if name == "snap":
            s.add_argument("--themes", nargs="+", help="theme/mode pairs (default: the config's theme, light and dark)")
            s.add_argument(
                "--dir",
                default=None,
                help="where contact sheets go (default: snap_dir from the config, else the temp dir)",
            )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return COMMANDS[args.cmd](args, Config.load())
    except DeckgenError as e:
        print(f"deckgen: {e}", file=sys.stderr)
        return 2
