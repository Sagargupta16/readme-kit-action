"""Palette and the SVG building blocks the cards share."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from html import escape

WIDTH = 840

# Warm near-black, one blue family (swappable through theme.accent), green only
# for live or current, sky and amber as the two secondary accents.
BG = "#0b1012"
CARD = "#0f171c"
BLUE = "#2563eb"
BLUE_LIGHT = "#60a5fa"
SKY = "#38bdf8"
GREEN = "#22c55e"
AMBER = "#f59e0b"
MONO = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
SANS = "'Segoe UI',Inter,-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
SVG_CLOSE = "</svg>"
COLOR_NAMES = ("accent", "sky", "green", "amber")


@dataclass(frozen=True)
class Palette:
    """The two accent shades every card draws with: light for ink, deep for fills."""

    accent: str = BLUE_LIGHT
    deep: str = BLUE

    @classmethod
    def from_accent(cls, accent: str | None) -> Palette:
        """Return the default blue pair, or a pair derived from one #rrggbb accent."""
        if accent is None or accent.lower() == BLUE_LIGHT:
            return cls()
        r, g, b = (int(accent[i : i + 2], 16) / 255 for i in (1, 3, 5))
        hue, light, sat = colorsys.rgb_to_hls(r, g, b)
        # same step as BLUE_LIGHT to BLUE: darker and a little less saturated
        deep = colorsys.hls_to_rgb(hue, max(light - 0.15, 0.0), sat * 0.9)
        return cls(accent.lower(), "#" + "".join(f"{round(c * 255):02x}" for c in deep))

    def color(self, name: str) -> str:
        """Return the hex value of one of COLOR_NAMES."""
        return {"accent": self.accent, "sky": SKY, "green": GREEN, "amber": AMBER}[name]


def svg_open(w: float, h: float, label: str) -> str:
    """Open a self-contained SVG that screen readers announce as one image."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}">'
    )


def wrap(text: str, width: int) -> list[str]:
    """Split text into lines of at most width characters, breaking between words."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + ([cur] if cur else [])


def summary(text: str, limit: int = 118) -> str:
    """Return the first sentence of text, cut at a word boundary."""
    first = text.split(". ", 1)[0].rstrip(".")
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def chips(items: list[str], x: float, y: float, max_w: float, color: str) -> str:
    """Return pill chips on one line, dropping whatever does not fit in max_w."""
    out: list[str] = []
    cx = x
    for item in items:
        w = 12 + len(item) * 6.2
        if cx + w > x + max_w:
            break
        out.append(
            f'<rect x="{cx:.1f}" y="{y}" width="{w:.1f}" height="20" rx="10" fill="{color}14" stroke="{color}55"/>'
            f'<text class="m" x="{cx + w / 2:.1f}" y="{y + 13.5}" text-anchor="middle" fill="{color}" '
            f'font-size="9">{escape(item)}</text>'
        )
        cx += w + 6
    return "".join(out)


def rotating(
    lines: list[str],
    x: float,
    y: float,
    cls: str,
    size: int,
    color: str,
    anchor: str | None = None,
    slot: float = 3.0,
) -> str:
    """Lines that take turns: each fades in, holds for its slot, and fades out."""
    n = len(lines)
    dur = slot * n
    align = f' text-anchor="{anchor}"' if anchor else ""
    out = []
    for i, text in enumerate(lines):
        a = i / n
        b = a + 0.04
        c = a + 1 / n - 0.04
        d = a + 1 / n
        times = sorted({0.0, round(a, 3), round(b, 3), round(c, 3), round(d, 3), 1.0})
        values = ["1" if round(b, 3) <= t <= round(c, 3) else "0" for t in times]
        out.append(
            f'<text{align} class="{cls}" x="{x}" y="{y}" fill="{color}" font-size="{size}" opacity="0">{escape(text)}'
            f'<animate attributeName="opacity" values="{";".join(values)}" '
            f'keyTimes="{";".join(f"{t:g}" for t in times)}" dur="{dur}s" repeatCount="indefinite"/></text>'
        )
    return "".join(out)


def typed_line(
    idx: int,
    x: int,
    y: int,
    text: str,
    begin: float,
    color: str,
    char_w: float = 8.4,
    cps: float = 38,
) -> tuple[str, float]:
    """A line that types itself out character by character, then holds."""
    n = len(text)
    dur = max(n / cps, 0.2)
    widths = ";".join(f"{i * char_w:.1f}" for i in range(n + 1))
    clip = (
        f'<clipPath id="t{idx}"><rect x="{x}" y="{y - 14}" width="0" height="20">'
        f'<animate attributeName="width" values="{widths}" dur="{dur:.2f}s" begin="{begin:.2f}s" '
        f'calcMode="discrete" fill="freeze"/></rect></clipPath>'
    )
    line = f'<text x="{x}" y="{y}" fill="{color}" clip-path="url(#t{idx})">{escape(text)}</text>'
    return clip + line, begin + dur


def shown_line(x: int, y: int, text: str, begin: float, color: str) -> str:
    """An output line: appears whole once its command has finished typing."""
    return (
        f'<text x="{x}" y="{y}" fill="{color}" opacity="0">{escape(text)}'
        f'<set attributeName="opacity" to="1" begin="{begin:.2f}s" fill="freeze"/></text>'
    )


def rail(x1: float, x2: float, y: float, begin: float, dur: float, pal: Palette) -> str:
    """A horizontal track that draws itself from left to right."""
    length = x2 - x1
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="rgba(255,255,255,0.10)" stroke-width="2"/>'
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{pal.deep}" stroke-width="2" '
        f'stroke-dasharray="{length}" stroke-dashoffset="{length}">'
        f'<animate attributeName="stroke-dashoffset" from="{length}" to="0" dur="{dur}s" '
        f'begin="{begin:.2f}s" fill="freeze"/></line>'
    )


def node(x: float, y: float, at: float, color: str, ring: bool = False) -> str:
    """A timeline stop that lights up when the rail reaches it; ring marks the current one."""
    out = ""
    if ring:
        out += (
            f'<circle class="now" cx="{x}" cy="{y}" r="7" fill="none" stroke="{color}" stroke-width="1.5" opacity="0">'
            f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/></circle>'
        )
    return out + (
        f'<circle cx="{x}" cy="{y}" r="6" fill="{BG}" stroke="{color}" stroke-width="2" opacity="0.25">'
        f'<animate attributeName="opacity" to="1" begin="{at:.2f}s" dur="0.3s" fill="freeze"/></circle>'
        f'<circle cx="{x}" cy="{y}" r="2.6" fill="{color}" opacity="0">'
        f'<animate attributeName="opacity" to="1" begin="{at:.2f}s" dur="0.3s" fill="freeze"/></circle>'
    )


def fade_group(at: float, body: str) -> str:
    """Wrap body in a group that fades in at `at` seconds."""
    return (
        f'<g opacity="0"><animate attributeName="opacity" to="1" begin="{at:.2f}s" dur="0.4s" fill="freeze"/>'
        f"{body}</g>"
    )
