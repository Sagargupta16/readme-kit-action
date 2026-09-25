"""Command line and GitHub Action entry: check the profile, render every card, write the files."""

from __future__ import annotations

import argparse
import itertools
import os
import sys
from html import escape
from pathlib import Path

from readme_kit import config
from readme_kit.cards import Card, render_all


def report(level: str, message: str) -> None:
    """Print a problem as a GitHub annotation under Actions, or to stderr locally."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        text = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::{level}::{text}")
    else:
        print(f"{level}: {message}", file=sys.stderr)


def set_output(name: str, value: str) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with Path(target).open("a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def _attr(value: str) -> str:
    """Escape for a double-quoted HTML attribute, leaving apostrophes readable."""
    return escape(value, quote=False).replace('"', "&quot;")


def _img(src: str, card: Card, size: str) -> str:
    img = f'<img src="{_attr(src)}" {size} alt="{_attr(card.alt)}" />'
    return f'<a href="{_attr(card.href)}">{img}</a>' if card.href else img


FULL = 'width="100%"'


def snippet(cards: list[Card], src_dir: str) -> str:
    """Return README markup for every card, in profile order, as one fenced block."""
    base = src_dir.replace("\\", "/").rstrip("/")
    blocks = []
    for kind, group in itertools.groupby(cards, key=lambda card: card.kind):
        items = list(group)
        if kind == "header":
            for card in items:
                dark = f"{base}/{card.name}"
                light = dark.removesuffix("-dark.svg") + "-light.svg"
                blocks.append(
                    "<picture>\n"
                    f'  <source media="(prefers-color-scheme: dark)" srcset="{_attr(dark)}">\n'
                    f'  <source media="(prefers-color-scheme: light)" srcset="{_attr(light)}">\n'
                    f"  {_img(dark, card, FULL)}\n"
                    "</picture>"
                )
        elif kind in ("button", "project"):
            size = 'height="44"' if kind == "button" else 'width="49%"'
            row = "\n".join(_img(f"{base}/{card.name}", card, size) for card in items)
            blocks.append(f'<p align="center">\n{row}\n</p>')
        elif kind == "card":
            blocks += [_img(f"{base}/{card.name}", card, FULL) for card in items]
    body = "\n\n".join(blocks)
    return (
        "# readme-kit snippet\n\n"
        "Markup for every card, in profile order. Copy what you need into your README; "
        "paths are relative to the repository root.\n\n"
        f"```html\n{body}\n```\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="readme_kit.py",
        description="Render a matching set of animated SVG cards from one profile YAML file.",
    )
    parser.add_argument(
        "--config",
        default=os.environ.get("CONFIG_PATH") or "profile.yml",
        help="profile YAML file (default: $CONFIG_PATH, then profile.yml)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("OUTPUT_DIR") or "assets/readme-kit",
        help="directory the files are written to (default: $OUTPUT_DIR, then assets/readme-kit)",
    )
    args = parser.parse_args(argv)
    path = Path(args.config)
    try:
        profile = config.load(path)
    except config.ConfigError as exc:
        for problem in exc.problems:
            report("error", f"{path}: {problem}")
        return 1
    cards = render_all(profile, lambda message: report("warning", message))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for card in cards:
        (out / card.name).write_text(card.svg + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {card.name}")
    (out / "snippet.md").write_text(
        snippet(cards, args.output_dir), encoding="utf-8", newline="\n"
    )
    written = len(cards) + 1
    print(f"{written} files written to {out}")
    set_output("files", str(written))
    return 0
