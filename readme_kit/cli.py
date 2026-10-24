"""Command line and GitHub Action entry: check the profile, render every card, write the files."""

from __future__ import annotations

import argparse
import itertools
import os
import sys
import urllib.parse
from html import escape
from pathlib import Path

from readme_kit import config, publish
from readme_kit.cards import Card, render_all

DEFAULT_MESSAGE = "chore: render readme cards"


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
    where = (
        "the images load from the output branch."
        if base.startswith("https://")
        else "paths are relative to the repository root."
    )
    return (
        "# readme-kit snippet\n\n"
        "Markup for every card, in profile order. Copy what you need into your README; "
        f"{where}\n\n"
        f"```html\n{body}\n```\n"
    )


def confined(name: str, value: str) -> Path:
    """Resolve a path flag, refusing one that lands outside the working directory."""
    base = Path.cwd().resolve()
    path = Path(value).resolve()
    if not path.is_relative_to(base):
        raise ValueError(
            f"{name} {value} is outside the working directory {base}; "
            "readme-kit only reads and writes inside the directory it runs in"
        )
    return path


def src_base(output_dir: str) -> str:
    """Where snippet.md points: output-dir relative to the repository root (the working directory)."""
    path = Path(output_dir)
    if not path.is_absolute():
        return output_dir
    return path.resolve().relative_to(Path.cwd().resolve()).as_posix()


def raw_base(repository: str, branch: str) -> str:
    """The raw.githubusercontent.com folder a README links to for files on another branch."""
    return f"https://raw.githubusercontent.com/{repository}/{urllib.parse.quote(branch, safe='/')}"


def env_flag(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if value in ("", "false"):
        return False
    if value == "true":
        return True
    raise ValueError(f"{name} must be true or false, got {os.environ[name]!r}")


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
    parser.add_argument(
        "--commit",
        action="store_true",
        help="commit output-dir on the checked-out branch and push it (default: $COMMIT)",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("BRANCH") or None,
        help="instead, make the cards the only commit of this branch and force-push it; "
        "implies --commit (default: $BRANCH)",
    )
    parser.add_argument(
        "--commit-message",
        default=os.environ.get("COMMIT_MESSAGE") or DEFAULT_MESSAGE,
        help=f"message for that commit (default: $COMMIT_MESSAGE, then {DEFAULT_MESSAGE!r})",
    )
    args = parser.parse_args(argv)
    try:
        commit = args.commit or env_flag("COMMIT") or args.branch is not None
    except ValueError as exc:
        report("error", str(exc))
        return 1
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if args.branch and "/" not in repository:
        report(
            "error",
            "branch needs $GITHUB_REPOSITORY (owner/repo) to write the image URLs in snippet.md; "
            "Actions sets it, set it yourself to run locally",
        )
        return 1
    try:
        profile_path = confined("config", args.config)
        out = confined("output-dir", args.output_dir)
    except ValueError as exc:
        report("error", str(exc))
        return 1
    path = Path(args.config)
    try:
        profile = config.load(profile_path)
    except config.ConfigError as exc:
        for problem in exc.problems:
            report("error", f"{path}: {problem}")
        return 1
    cards = render_all(profile, lambda message: report("warning", message))
    out.mkdir(parents=True, exist_ok=True)
    for card in cards:
        (out / card.name).write_text(card.svg + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {card.name}")
    base = (
        raw_base(repository, args.branch) if args.branch else src_base(args.output_dir)
    )
    (out / "snippet.md").write_text(
        snippet(cards, base), encoding="utf-8", newline="\n"
    )
    written = len(cards) + 1
    print(f"{written} files written to {Path(args.output_dir)}")
    set_output("files", str(written))
    if not commit:
        set_output("committed", "false")
        return 0
    return _publish(
        out, [card.name for card in cards], args.branch, args.commit_message
    )


def _publish(out: Path, card_names: list[str], branch: str | None, message: str) -> int:
    """Commit the written files here, or to branch when one is set, and report the result."""
    try:
        if branch:
            names = card_names + ["snippet.md"]
            sha = publish.commit_to_branch(out, names, branch, message)
        else:
            sha = publish.commit_here(out, message)
    except publish.PublishError as exc:
        report("error", str(exc))
        set_output("committed", "false")
        return 1
    print(f"committed {sha}" if sha else "the cards did not change, nothing to commit")
    set_output("committed", "true" if sha else "false")
    return 0
