"""Measure readme-kit on profile.example.yml and print the README's numbers table.

    uv run --no-project --with pyyaml==6.0.3 python scripts/benchmark.py [--runs 50]

One live pass fetches every icon and logo and keeps the bytes. The timed passes then
replay those bytes, so the render time is the code's, not the network's.
"""

from __future__ import annotations

import argparse
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from readme_kit import config, fetch
from readme_kit.cards import render_all


def fail(message: str) -> None:
    raise SystemExit(f"benchmark needs every download to work: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()

    profile = config.load(ROOT / "profile.example.yml")
    live = fetch.fetch_bytes
    cache: dict[str, bytes] = {}

    def recording(url: str, *rest: object) -> bytes:
        cache[url] = live(url, *rest)
        return cache[url]

    fetch.fetch_bytes = recording
    start = time.perf_counter()
    cards = render_all(profile, fail)
    live_ms = (time.perf_counter() - start) * 1000

    fetch.fetch_bytes = lambda url, *_rest: cache[url]
    times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        render_all(profile, fail)
        times.append((time.perf_counter() - start) * 1000)

    sizes = sorted((len(card.svg.encode("utf-8")) + 1, card.name) for card in cards)
    total = sum(size for size, _ in sizes)
    rows = [
        ("Cards rendered from profile.example.yml", f"{len(cards)}"),
        ("Downloads (simple-icons glyphs and tile logos)", f"{len(cache)}"),
        ("First render, downloads included", f"{live_ms:,.0f} ms"),
        (
            f"Render with downloads cached, median of {args.runs}",
            f"{statistics.median(times):.1f} ms",
        ),
        ("All cards together", f"{total / 1024:.1f} KB"),
        ("Median card", f"{statistics.median(s for s, _ in sizes) / 1024:.1f} KB"),
        (f"Largest card ({sizes[-1][1]})", f"{sizes[-1][0] / 1024:.1f} KB"),
    ]
    print(
        f"Python {platform.python_version()} on {platform.system()} {platform.machine()}\n"
    )
    print("| Measure | Value |\n| --- | --- |")
    for name, value in rows:
        print(f"| {name} | {value} |")


if __name__ == "__main__":
    main()
