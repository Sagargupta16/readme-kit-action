"""One renderer per card type. Each takes a checked config section and returns Cards."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from html import escape

from readme_kit import fetch, github
from readme_kit.svg import (
    BG,
    CARD,
    GREEN,
    MONO,
    SANS,
    SKY,
    SVG_CLOSE,
    WIDTH,
    Palette,
    chips,
    fade_group,
    node,
    rail,
    rotating,
    shown_line,
    summary,
    svg_open,
    typed_line,
    wrap,
)


@dataclass(frozen=True)
class Card:
    """One SVG file, plus what a README needs to show it."""

    name: str
    svg: str
    alt: str
    kind: str = "card"  # card, header, header-light, button or project
    href: str | None = None


# ---------------------------------------------------------------- hero

SATELLITES = ((620, 70), (730, 60), (790, 140), (690, 180), (590, 160))
HUB = (700, 118)
RING_LINKS = ((0, 1), (2, 3), (3, 4))


def _constellation(cfg: dict, pal: Palette) -> str:
    """Satellite nodes wired to a hub, with packets travelling in along every spoke."""
    labels = cfg["nodes"]
    points = [*SATELLITES[: len(labels)], HUB]
    names = [*labels, cfg["hub"]]
    hub = len(labels)
    spokes = [(i, hub) for i in range(len(labels))]
    links = spokes + [(a, b) for a, b in RING_LINKS if b < len(labels)]
    out = []
    for a, b in links:
        (x1, y1), (x2, y2) = points[a], points[b]
        out.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>'
        )
    for i, (a, b) in enumerate(spokes):
        (x1, y1), (x2, y2) = points[a], points[b]
        out.append(
            f'<circle r="2.6" fill="{SKY}"><animateMotion dur="2.4s" begin="{i * 0.45:.2f}s" '
            f'repeatCount="indefinite" path="M{x1} {y1} L{x2} {y2}"/></circle>'
        )
    for i, ((x, y), label) in enumerate(zip(points, names, strict=True)):
        is_hub = i == hub
        r = 22 if is_hub else 17
        stroke = f"{pal.deep}dd" if is_hub else "rgba(255,255,255,0.16)"
        fill = f"{pal.deep}26" if is_hub else CARD
        ink = pal.accent if is_hub else "rgba(255,255,255,0.7)"
        out.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.3">'
            f'<animate attributeName="r" values="{r};{r + 1.5};{r}" dur="3s" begin="{i * 0.4:.1f}s" '
            'repeatCount="indefinite"/></circle>'
            f'<text class="m" x="{x}" y="{y + 3.5}" text-anchor="middle" fill="{ink}" font-size="9" '
            f'style="letter-spacing:1px">{escape(label)}</text>'
        )
    return "".join(out)


def render_hero(cfg: dict, pal: Palette) -> Card:
    """Name, kicker, rotating taglines, status pill, location and a node constellation."""
    w, h = WIDTH, 250
    lead = cfg["role"] or (cfg["taglines"][0] if cfg["taglines"] else "")
    alt = ". ".join(part.rstrip(".") for part in (cfg["name"], lead) if part) + "."
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:2px}}"
            f".n{{font-family:{SANS};font-weight:800;letter-spacing:-1px}}"
            f".s{{font-family:{SANS};font-weight:600}}</style>"
        ),
        (
            '<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
            '<path d="M24 0H0V24" fill="none" stroke="rgba(255,255,255,0.035)" stroke-width="1"/></pattern>'
            '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e1a24"/>'
            f'<stop offset="0.7" stop-color="{BG}"/></linearGradient>'
            f'<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{SKY}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{SKY}" stop-opacity="0.10"/>'
            f'<stop offset="1" stop-color="{SKY}" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="card"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="18"/></clipPath></defs>'
        ),
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="url(#bg)" stroke="rgba(255,255,255,0.09)"/>',
        (
            f'<g clip-path="url(#card)"><rect width="{w}" height="{h}" fill="url(#grid)"/>'
            f'<rect x="-200" y="0" width="200" height="{h}" fill="url(#scan)">'
            '<animateTransform attributeName="transform" type="translate" values="0 0;1240 0" '
            'dur="7s" repeatCount="indefinite"/></rect></g>'
        ),
    ]
    if cfg["kicker"]:
        parts.append(
            f'<text class="m" x="44" y="62" fill="{pal.accent}" font-size="11">{escape(cfg["kicker"].upper())}</text>'
        )
    parts.append(
        f'<text class="n" x="40" y="118" fill="#f8fafc" font-size="58">{escape(cfg["name"])}</text>'
    )
    parts.append(rotating(cfg["taglines"], 44, 152, "s", 18, "rgba(255,255,255,0.78)"))
    x = 44
    if cfg["status"]:
        pill = 89 + 7 * len(cfg["status"])
        parts.append(
            f'<rect x="44" y="176" width="{pill}" height="28" rx="14" fill="{GREEN}14" stroke="{GREEN}55"/>'
            f'<circle cx="62" cy="190" r="4" fill="{GREEN}"><animate attributeName="opacity" '
            'values="1;0.35;1" dur="1.8s" repeatCount="indefinite"/></circle>'
            f'<text class="m" x="74" y="194" fill="{GREEN}" font-size="10" style="letter-spacing:1px">'
            f"{escape(cfg['status'].upper())}</text>"
        )
        x += pill + 16
    if cfg["location"]:
        parts.append(
            f'<text class="m" x="{x}" y="194" fill="rgba(255,255,255,0.45)" font-size="10" '
            f'style="letter-spacing:1px">{escape(cfg["location"].upper())}</text>'
        )
    if cfg["constellation"]:
        parts.append(_constellation(cfg["constellation"], pal))
    parts.append(SVG_CLOSE)
    return Card("hero.svg", "".join(parts), alt)


# ---------------------------------------------------------------- terminal


def _prompt(prompt: str, y: int, at: float) -> str:
    return (
        f'<text x="24" y="{y}" fill="{GREEN}" opacity="0">{escape(prompt)}'
        f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/></text>'
    )


def render_terminal(cfg: dict, pal: Palette) -> Card:
    """A terminal window that types each command, then shows its output."""
    prompt = (cfg["prompt"] or "$").rstrip() + " "
    commands = cfg["commands"]
    w = WIDTH
    h = 70 + sum(24 * len(c["output"]) + 34 for c in commands) + 24
    alt = "Terminal: " + ", ".join(c["command"] for c in commands)
    cmd_x = 24 + int(len(prompt) * 8.4)
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>text{{font-family:{MONO};font-size:14px}}"
            ".cur{animation:blink 1.05s steps(1) infinite}"
            "@keyframes blink{50%{opacity:0}}</style>"
        ),
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="rgba(255,255,255,0.10)"/>',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="36" rx="14" fill="{CARD}"/>',
        f'<rect x="0.5" y="24" width="{w - 1}" height="13" fill="{CARD}"/>',
        f'<line x1="0" y1="37" x2="{w}" y2="37" stroke="rgba(255,255,255,0.08)"/>',
    ]
    for i, cx in enumerate((24, 44, 64)):
        fill = GREEN if i == 2 else "rgba(255,255,255,0.22)"
        parts.append(f'<circle cx="{cx}" cy="19" r="5.5" fill="{fill}"/>')
    if cfg["title"]:
        parts.append(
            f'<text x="{w // 2}" y="24" text-anchor="middle" fill="rgba(255,255,255,0.45)" '
            f'style="font-size:12px">{escape(cfg["title"])}</text>'
        )
    y, t = 70, 0.6
    for idx, command in enumerate(commands):
        parts.append(_prompt(prompt, y, t))
        line, t = typed_line(idx, cmd_x, y, command["command"], t + 0.15, "#e5e7eb")
        parts.append(line)
        t += 0.25
        color = (
            pal.color(command["color"])
            if command["color"]
            else "rgba(255,255,255,0.72)"
        )
        for out in command["output"]:
            y += 24
            parts.append(shown_line(40, y, out, t, color))
            t += 0.12
        y += 34
        t += 0.45
    parts.append(_prompt(prompt, y, t))
    parts.append(
        f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
        f'<rect class="cur" x="{cmd_x}" y="{y - 13}" width="9" height="17" fill="{pal.accent}"/></g>'
    )
    parts.append(SVG_CLOSE)
    return Card("terminal.svg", "".join(parts), alt)


# ---------------------------------------------------------------- section headers, divider, footer


def render_header(
    num: str, title: str, sub: str | None, theme: str, pal: Palette
) -> str:
    """A numbered section header; the light variant swaps the ink for light-mode READMEs."""
    w, h = WIDTH, 64
    ink = "#f3f4f6" if theme == "dark" else "#0b1012"
    dim = "rgba(255,255,255,0.45)" if theme == "dark" else "rgba(11,16,18,0.55)"
    rule = "rgba(255,255,255,0.10)" if theme == "dark" else "rgba(11,16,18,0.12)"
    kicker = f"{num}  /  {sub.upper()}" if sub else num
    return "".join(
        [
            svg_open(w, h, title),
            (
                f'<defs><linearGradient id="sweep" x1="0" x2="1"><stop offset="0" stop-color="{SKY}" stop-opacity="0"/>'
                f'<stop offset="0.5" stop-color="{pal.accent}"/><stop offset="1" stop-color="{SKY}" stop-opacity="0"/>'
                "</linearGradient></defs>"
            ),
            f'<rect x="0" y="12" width="4" height="30" rx="2" fill="{pal.deep}"/>',
            (
                f'<text x="18" y="24" fill="{pal.accent}" font-family="{MONO}" font-size="11" font-weight="700" '
                f'letter-spacing="2">{escape(kicker)}</text>'
            ),
            (
                f'<text x="18" y="46" fill="{ink}" font-family="{SANS}" font-size="24" font-weight="700">'
                f"{escape(title)}</text>"
            ),
            f'<line x1="0" y1="{h - 4}" x2="{w}" y2="{h - 4}" stroke="{rule}" stroke-width="1"/>',
            (
                f'<rect x="-160" y="{h - 5}" width="160" height="2" fill="url(#sweep)">'
                '<animateTransform attributeName="transform" type="translate" values="0 0;1000 0" '
                'dur="4.5s" repeatCount="indefinite"/></rect>'
            ),
            f'<circle cx="{w - 8}" cy="30" r="3" fill="{dim}"/>',
            SVG_CLOSE,
        ]
    )


def render_headers(items: list[dict], pal: Palette) -> list[Card]:
    """A dark and a light header per entry, numbered 01, 02 and so on in file order."""
    cards = []
    for i, item in enumerate(items, start=1):
        for theme in ("dark", "light"):
            cards.append(
                Card(
                    f"header-{item['key']}-{theme}.svg",
                    render_header(
                        f"{i:02d}", item["title"], item["subtitle"], theme, pal
                    ),
                    item["title"],
                    kind="header" if theme == "dark" else "header-light",
                )
            )
    return cards


def render_divider(pal: Palette) -> Card:
    """A hairline with a pulse running along it."""
    w, h = WIDTH, 14
    svg = "".join(
        [
            svg_open(w, h, "divider"),
            (
                f'<defs><linearGradient id="pulse" x1="0" x2="1"><stop offset="0" stop-color="{pal.deep}" '
                f'stop-opacity="0"/><stop offset="0.5" stop-color="{pal.accent}"/>'
                f'<stop offset="1" stop-color="{pal.deep}" stop-opacity="0"/></linearGradient></defs>'
            ),
            f'<line x1="0" y1="7" x2="{w}" y2="7" stroke="rgba(127,127,127,0.28)" stroke-width="1"/>',
            f'<circle cx="{w / 2}" cy="7" r="2.5" fill="{pal.accent}"/>',
            (
                '<rect x="-220" y="6" width="220" height="2" fill="url(#pulse)">'
                '<animateTransform attributeName="transform" type="translate" values="0 0;1060 0" '
                'dur="3.6s" repeatCount="indefinite"/></rect>'
            ),
            SVG_CLOSE,
        ]
    )
    return Card("divider.svg", svg, "")


def render_footer(cfg: dict, pal: Palette) -> Card:
    """A kicker, rotating sign-off lines and a wave with a dot riding it."""
    w, h = WIDTH, 150
    wave = "M0 110 C 140 80, 280 140, 420 110 S 700 80, 840 110"
    alt = ". ".join(line.rstrip(".") for line in cfg["lines"]) + "."
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.s{{font-family:{SANS};font-weight:800}}"
            f".m{{font-family:{MONO};font-weight:700;letter-spacing:2px}}</style>"
        ),
    ]
    if cfg["kicker"]:
        parts.append(
            f'<text class="m" x="{w / 2}" y="34" text-anchor="middle" fill="{pal.accent}" font-size="10">'
            f"{escape(cfg['kicker'].upper())}</text>"
        )
    parts += [
        rotating(cfg["lines"], w / 2, 78, "s", 30, "#f3f4f6", anchor="middle"),
        f'<path d="{wave}" fill="none" stroke="rgba(127,127,127,0.25)" stroke-width="1.2"/>',
        (
            f'<path d="{wave}" fill="none" stroke="{pal.accent}" stroke-width="2" stroke-dasharray="120 900" '
            'stroke-linecap="round"><animate attributeName="stroke-dashoffset" values="1020;0" dur="4s" '
            'repeatCount="indefinite"/></path>'
        ),
        f'<circle r="3.5" fill="{SKY}"><animateMotion dur="4s" repeatCount="indefinite" path="{wave}"/></circle>',
        SVG_CLOSE,
    ]
    return Card("footer.svg", "".join(parts), alt)


# ---------------------------------------------------------------- timeline


def _expansion(cfg: dict, right: float, top_y: int, pal: Palette) -> list[str]:
    """The last milestone drops into a bracket over a second rail of dated sub-items."""
    open_at = 0.3 + 2.4 + 0.2
    sub_y, sub_left, sub_right, bracket_y = 250, 120, 720, 176
    drop = f"M{right} {top_y + 58} V{bracket_y} H{sub_left} M{right} {bracket_y} H{sub_right}"
    parts = [
        (
            f'<path d="{drop}" fill="none" stroke="{GREEN}88" stroke-width="1.4" stroke-dasharray="3 4" opacity="0">'
            f'<animate attributeName="opacity" to="1" begin="{open_at:.2f}s" dur="0.4s" fill="freeze"/></path>'
        )
    ]
    if cfg["title"]:
        parts.append(
            fade_group(
                open_at,
                f'<text class="m" x="{sub_left}" y="{bracket_y - 8}" fill="{GREEN}" font-size="9">'
                f"{escape(cfg['title'].upper())}</text>",
            )
        )
    sub_draw = 1.8
    parts.append(rail(sub_left, sub_right, sub_y, open_at + 0.3, sub_draw, pal))
    items = cfg["items"]
    sub_step = (sub_right - sub_left) / max(len(items) - 1, 1)
    sub_last = max(len(items) - 1, 1)
    for i, item in enumerate(items):
        x = sub_left + i * sub_step
        at = open_at + 0.3 + sub_draw * i / sub_last
        current = i == len(items) - 1
        color = GREEN if current else SKY
        parts.append(
            f'<line x1="{x}" y1="{bracket_y}" x2="{x}" y2="{sub_y - 8}" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>'
        )
        parts.append(node(x, sub_y, at, color, ring=current))
        body = (
            f'<text class="m" x="{x}" y="{sub_y - 16}" text-anchor="middle" fill="{color}" font-size="8.5">'
            f"{escape(item['when'].upper())}</text>"
            f'<text class="t" x="{x}" y="{sub_y + 28}" text-anchor="middle" fill="#f3f4f6" font-size="13">'
            f"{escape(item['title'])}</text>"
        )
        if item["subtitle"]:
            body += (
                f'<text class="m" x="{x}" y="{sub_y + 46}" text-anchor="middle" fill="rgba(255,255,255,0.5)" '
                f'font-size="8.5">{escape(item["subtitle"].upper())}</text>'
            )
        parts.append(fade_group(at, body))
    return parts


def render_timeline(cfg: dict, pal: Palette) -> Card:
    """A rail of milestones, oldest first; the last one can expand into a second rail."""
    milestones, expand = cfg["milestones"], cfg["expand"]
    w, h = WIDTH, 330 if expand else 160
    left, top_y = 96, 84
    right = 690 if expand else w - left
    step = (right - left) / (len(milestones) - 1)
    draw = 2.4
    alt = (
        (cfg["title"] or "Timeline")
        + ": "
        + ", ".join(f"{m['year']} {m['title']}" for m in milestones)
    )
    if expand:
        alt += (
            "; "
            + (expand["title"] or "then")
            + ": "
            + ", ".join(i["title"] for i in expand["items"])
        )
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1.4px}}"
            f".t{{font-family:{SANS};font-weight:700}}"
            ".now{animation:ring 2.2s ease-out infinite;transform-origin:center;transform-box:fill-box}"
            "@keyframes ring{0%{opacity:0.9;transform:scale(1)}100%{opacity:0;transform:scale(2.6)}}</style>"
        ),
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="rgba(255,255,255,0.08)"/>',
    ]
    if cfg["title"]:
        parts.append(
            f'<text class="m" x="24" y="30" fill="{pal.accent}" font-size="10">{escape(cfg["title"].upper())}</text>'
        )
    parts.append(rail(left, right, top_y, 0.3, draw, pal))
    last = len(milestones) - 1
    for i, m in enumerate(milestones):
        x = left + i * step
        at = 0.3 + draw * i / last
        current = i == last
        color = GREEN if current else pal.accent
        label = f"{m['year']}  {m['tag']}" if m["tag"] else m["year"]
        parts.append(node(x, top_y, at, color, ring=current))
        body = (
            f'<text class="m" x="{x}" y="{top_y - 22}" text-anchor="middle" fill="{color}" font-size="10">'
            f"{escape(label.upper())}</text>"
            f'<text class="t" x="{x}" y="{top_y + 30}" text-anchor="middle" fill="#f3f4f6" font-size="13">'
            f"{escape(m['title'])}</text>"
        )
        if m["subtitle"]:
            body += (
                f'<text class="m" x="{x}" y="{top_y + 49}" text-anchor="middle" fill="rgba(255,255,255,0.5)" '
                f'font-size="9">{escape(m["subtitle"].upper())}</text>'
            )
        parts.append(fade_group(at, body))
    if expand:
        parts += _expansion(expand, right, top_y, pal)
    parts.append(SVG_CLOSE)
    return Card("timeline.svg", "".join(parts), alt)


# ---------------------------------------------------------------- tiles


def _logo_tile(
    name: str, logo: str | None, x: float, y: float, size: int, pal: Palette
) -> str:
    """A logo when one was fetched, otherwise a two-letter monogram."""
    frame = (
        f'<rect x="{x:.1f}" y="{y}" width="{size}" height="{size}" rx="12" fill="#ffffff0f" '
        'stroke="rgba(255,255,255,0.12)"/>'
    )
    if logo:
        pad = 9
        return frame + (
            f'<image href="{escape(logo)}" x="{x + pad:.1f}" y="{y + pad}" width="{size - 2 * pad}" '
            f'height="{size - 2 * pad}"/>'
        )
    initials = "".join(word[0] for word in name.replace("-", " ").split()[:2]).upper()
    return frame + (
        f'<text class="t" x="{x + size / 2:.1f}" y="{y + size / 2 + 6}" text-anchor="middle" '
        f'fill="{pal.accent}" font-size="17">{escape(initials)}</text>'
    )


def render_tiles(cfg: dict, pal: Palette, logos: dict[str, str | None]) -> Card:
    """A row of tiles: logo or monogram, name, and a subtitle wrapped to two lines."""
    items = cfg["items"]
    w, h = WIDTH, 232
    gap, pad = 10, 16
    tw = (w - 2 * pad - (len(items) - 1) * gap) / len(items)
    wrap_at = round(tw / 7)
    alt = (
        (cfg["title"] or "Tiles")
        + ": "
        + "; ".join(
            ", ".join(p for p in (t["name"], t["subtitle"]) if p) for t in items
        )
    )
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1.2px}}"
            f".t{{font-family:{SANS};font-weight:800}}.s{{font-family:{SANS};font-weight:500}}</style>"
        ),
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="rgba(255,255,255,0.08)"/>',
    ]
    if cfg["title"]:
        parts.append(
            f'<text class="m" x="24" y="31" fill="{GREEN}" font-size="10">{escape(cfg["title"].upper())}</text>'
        )
    for i, tile in enumerate(items):
        x = pad + i * (tw + gap)
        cx = x + tw / 2
        begin = 0.15 + i * 0.12
        subtitle = "".join(
            f'<text class="s" x="{cx:.1f}" y="{168 + j * 16}" text-anchor="middle" fill="rgba(255,255,255,0.62)" '
            f'font-size="11.5">{escape(line)}</text>'
            for j, line in enumerate(wrap(tile["subtitle"] or "", wrap_at)[:2])
        )
        parts.append(
            f'<g opacity="0"><animate attributeName="opacity" to="1" begin="{begin:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" '
            f'begin="{begin:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<rect x="{x:.1f}" y="46" width="{tw:.1f}" height="{h - 62}" rx="12" fill="{CARD}" '
            'stroke="rgba(255,255,255,0.07)"/>'
            + _logo_tile(
                tile["name"], logos.get(tile["logo"] or ""), cx - 26, 62, 52, pal
            )
            + f'<text class="t" x="{cx:.1f}" y="146" text-anchor="middle" fill="#f3f4f6" font-size="14.5">'
            f"{escape(tile['name'])}</text>" + subtitle + "</g>"
        )
    parts.append(SVG_CLOSE)
    return Card("tiles.svg", "".join(parts), alt)


# ---------------------------------------------------------------- panels

PANEL_COLORS = ("sky", "accent", "green", "amber")


def _panel_height(entries: list[dict]) -> int:
    return 56 + sum(16 * len(wrap(e["text"], 50)[:3]) + 12 for e in entries) + 4


def _panel(
    label: str,
    entries: list[dict],
    box: tuple[float, float, float, float],
    accent: str,
    delay: float,
) -> str:
    x, y, pw, ph = box
    out = [
        (
            f'<g opacity="0"><animate attributeName="opacity" to="1" begin="{delay:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="12" fill="{CARD}" '
            'stroke="rgba(255,255,255,0.07)"/>'
            f'<rect x="{x:.1f}" y="{y + 16:.1f}" width="3" height="22" rx="1.5" fill="{accent}"/>'
            f'<text class="m" x="{x + 18:.1f}" y="{y + 31:.1f}" fill="{accent}" font-size="9.5">{escape(label)}</text>'
        )
    ]
    cy = y + 56
    for entry in entries:
        lines = wrap(entry["text"], 50)[:3]
        out.append(
            f'<circle cx="{x + 21:.1f}" cy="{cy - 4:.1f}" r="2.5" fill="{accent}"/>'
            f'<text class="m" x="{x + pw - 16:.1f}" y="{cy:.1f}" text-anchor="end" fill="rgba(255,255,255,0.4)" '
            f'font-size="8.5">{escape(entry["year"] or "")}</text>'
            + "".join(
                f'<text class="s" x="{x + 32:.1f}" y="{cy + j * 16:.1f}" fill="rgba(255,255,255,0.78)" '
                f'font-size="12">{escape(line)}</text>'
                for j, line in enumerate(lines)
            )
        )
        cy += 16 * len(lines) + 12
    out.append("</g>")
    return "".join(out)


def render_panels(cfg: dict, pal: Palette) -> Card:
    """Up to four titled lists in a 2x2 grid, each entry with its year on the right."""
    panels = cfg["items"]
    w, pad, gap = WIDTH, 16, 12
    pw = (w - 2 * pad - gap) / 2
    rows = [panels[i : i + 2] for i in range(0, len(panels), 2)]
    heights = [max(_panel_height(p["entries"]) for p in row) for row in rows]
    h = 44 + sum(heights) + gap * (len(rows) - 1) + pad
    alt = (
        (cfg["title"] or "Panels")
        + ": "
        + "; ".join(e["text"] for p in panels for e in p["entries"])
    )
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1.2px}}"
            f".s{{font-family:{SANS};font-weight:500}}</style>"
        ),
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="rgba(255,255,255,0.08)"/>',
    ]
    if cfg["title"]:
        parts.append(
            f'<text class="m" x="24" y="30" fill="{SKY}" font-size="10">{escape(cfg["title"].upper())}</text>'
        )
    y = 44.0
    for r, row in enumerate(rows):
        for c, panel in enumerate(row):
            i = r * 2 + c
            accent = pal.color(panel["color"] or PANEL_COLORS[i])
            box = (pad + c * (pw + gap), y, pw, heights[r])
            parts.append(
                _panel(
                    panel["title"].upper(),
                    panel["entries"],
                    box,
                    accent,
                    0.15 + i * 0.12,
                )
            )
        y += heights[r] + gap
    parts.append(SVG_CLOSE)
    return Card("panels.svg", "".join(parts), alt)


# ---------------------------------------------------------------- stat tiles


def render_stats(items: list[dict], pal: Palette) -> Card:
    """A four-column grid of big values with a label under each."""
    w = WIDTH
    cols, gap, pad, th = 4, 12, 16, 80
    tw = (w - 2 * pad - (cols - 1) * gap) / cols
    rows = (len(items) + cols - 1) // cols
    h = 2 * pad + rows * th + (rows - 1) * gap + 8
    alt = "Stats: " + "; ".join(f"{s['value']} {s['label']}" for s in items)
    parts = [
        svg_open(w, h, alt),
        (
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1.2px}}"
            f".v{{font-family:{SANS};font-weight:800}}</style>"
        ),
    ]
    for i, stat in enumerate(items):
        col, row = i % cols, i // cols
        x = pad + col * (tw + gap)
        y = pad + row * (th + gap)
        begin = 0.2 + i * 0.12
        parts.append(
            f'<g opacity="0"><animate attributeName="opacity" to="1" begin="{begin:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" '
            f'begin="{begin:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="12" fill="{CARD}" stroke="rgba(255,255,255,0.08)"/>'
            f'<rect x="{x}" y="{y + 18}" width="3" height="26" rx="1.5" fill="{pal.color(stat["color"] or "accent")}"/>'
            f'<text class="v" x="{x + 18}" y="{y + 42}" fill="#f3f4f6" font-size="26">{escape(stat["value"])}</text>'
            f'<text class="m" x="{x + 18}" y="{y + 64}" fill="rgba(255,255,255,0.5)" font-size="8.5">'
            f"{escape(stat['label'].upper())}</text></g>"
        )
    parts.append(SVG_CLOSE)
    return Card("stats.svg", "".join(parts), alt)


# ---------------------------------------------------------------- buttons


def render_button(label: str, icon_path: str | None, index: int, pal: Palette) -> str:
    """A pill button with a simple-icons glyph; wider than 156 only for long labels."""
    text = label.upper()
    w, h = max(156, 68 + 8 * len(text)), 44
    icon = (
        f'<svg x="16" y="12" width="20" height="20" viewBox="0 0 24 24">'
        f'<path d="{escape(icon_path)}" fill="rgba(255,255,255,0.9)"/></svg>'
        if icon_path
        else ""
    )
    anchor = 'x="48"' if icon_path else f'x="{w / 2}" text-anchor="middle"'
    return "".join(
        [
            svg_open(w, h, label),
            f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1.4px}}</style>",
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="22" fill="{CARD}" stroke="{pal.accent}66"/>',
            (
                f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="22" fill="{pal.deep}22" opacity="0">'
                f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;0.1;0.2;1" dur="5s" '
                f'begin="{index * 0.5:.1f}s" repeatCount="indefinite"/></rect>'
            ),
            icon,
            f'<text class="m" {anchor} y="27" fill="#f3f4f6" font-size="11">{escape(text)}</text>',
            SVG_CLOSE,
        ]
    )


def render_buttons(
    items: list[dict], pal: Palette, icons: dict[str, str | None]
) -> list[Card]:
    return [
        Card(
            f"button-{b['key']}.svg",
            render_button(b["label"], icons.get(b["icon"] or ""), i, pal),
            b["label"],
            kind="button",
            href=b["url"],
        )
        for i, b in enumerate(items)
    ]


# ---------------------------------------------------------------- project cards


def render_project(p: dict, index: int, pal: Palette) -> str:
    """Date, live or source status, title, a three-line summary and tech chips."""
    w, h = 410, 196
    lines = wrap(summary(p["description"]), 56)[:3]
    body = "".join(
        f'<text class="s" x="22" y="{86 + j * 18}" fill="rgba(255,255,255,0.68)" font-size="12.5">{escape(line)}</text>'
        for j, line in enumerate(lines)
    )
    status = (
        f'<circle cx="{w - 72}" cy="30" r="3.5" fill="{GREEN}"><animate attributeName="opacity" '
        'values="1;0.35;1" dur="1.8s" repeatCount="indefinite"/></circle>'
        f'<text class="m" x="{w - 62}" y="34" fill="{GREEN}" font-size="9">LIVE</text>'
        if p["live"]
        else f'<text class="m" x="{w - 22}" y="34" text-anchor="end" fill="rgba(255,255,255,0.4)" font-size="9">SOURCE</text>'
    )
    return "".join(
        [
            svg_open(w, h, f"{p['title']}: {summary(p['description'])}"),
            (
                f"<style>.m{{font-family:{MONO};font-weight:700;letter-spacing:1px}}"
                f".t{{font-family:{SANS};font-weight:800}}.s{{font-family:{SANS};font-weight:500}}</style>"
            ),
            (
                '<defs><linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                '<stop offset="0.5" stop-color="#fff" stop-opacity="0.06"/><stop offset="1" stop-color="#fff" '
                'stop-opacity="0"/></linearGradient>'
                f'<clipPath id="c"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16"/></clipPath></defs>'
            ),
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{CARD}" stroke="rgba(255,255,255,0.09)"/>',
            f'<rect x="0" y="22" width="3" height="28" rx="1.5" fill="{pal.accent}"/>',
            f'<text class="m" x="22" y="34" fill="{pal.accent}" font-size="9">{escape((p["date"] or "").upper())}</text>',
            status,
            f'<text class="t" x="22" y="62" fill="#f3f4f6" font-size="19">{escape(p["title"])}</text>',
            body,
            chips(p["tech"][:5], 22, h - 38, w - 44, SKY),
            (
                f'<g clip-path="url(#c)"><rect x="-140" y="0" width="120" height="{h}" fill="url(#shine)" '
                'transform="skewX(-18)"><animateTransform attributeName="transform" type="translate" '
                f'values="0 0;700 0" dur="6s" begin="{index * 0.7:.1f}s" repeatCount="indefinite" '
                'additive="sum"/></rect></g>'
            ),
            SVG_CLOSE,
        ]
    )


def render_projects(items: list[dict], pal: Palette) -> list[Card]:
    return [
        Card(
            f"project-{p['key']}.svg",
            render_project(p, i, pal),
            f"{p['title']}: {summary(p['description'])}",
            kind="project",
            href=p["url"],
        )
        for i, p in enumerate(items)
    ]


# ---------------------------------------------------------------- everything


def _icons(buttons: list[dict], warn: Callable[[str], None]) -> dict[str, str | None]:
    icons: dict[str, str | None] = {}
    for i, button in enumerate(buttons):
        slug = button["icon"]
        if slug and slug not in icons:
            try:
                icons[slug] = fetch.simple_icon(slug)
            except fetch.FetchError as exc:
                icons[slug] = None
                warn(
                    f"buttons[{i}].icon: simple-icons '{slug}' not fetched ({exc}); drawing the button without it"
                )
    return icons


def _logos(tiles: list[dict], warn: Callable[[str], None]) -> dict[str, str | None]:
    logos: dict[str, str | None] = {}
    for i, tile in enumerate(tiles):
        url = tile["logo"]
        if url and url not in logos:
            try:
                logos[url] = fetch.logo_data_uri(url)
            except fetch.FetchError as exc:
                logos[url] = None
                warn(
                    f"tiles.items[{i}].logo: not fetched ({exc}); drawing a monogram instead"
                )
    return logos


def _live_stats(
    stats: list[dict], user: str | None, warn: Callable[[str], None]
) -> list[dict]:
    """Fill in each stat that names a github metric; on failure keep its value, or n/a."""
    if not any(stat["github"] for stat in stats):
        return stats
    if not user:
        warn(
            "stats: no GitHub user to read numbers for; set github.user in the profile "
            "(the action defaults it to the repository owner)"
        )
    client = github.Client.from_env(user) if user else None
    live: dict[str, str | None] = {}
    out = []
    for i, stat in enumerate(stats):
        metric = stat["github"]
        if metric is None:
            out.append(stat)
            continue
        if metric not in live:
            live[metric] = _read_metric(client, metric, i, stat["value"], warn)
        out.append({**stat, "value": live[metric] or stat["value"] or "n/a"})
    return out


def _read_metric(
    client: github.Client | None,
    metric: str,
    i: int,
    fallback: str | None,
    warn: Callable[[str], None],
) -> str | None:
    """One live number, formatted with thousands separators, or None if it was not read."""
    if client is None:
        return None
    try:
        return f"{client.metric(metric):,}"
    except fetch.FetchError as exc:
        warn(
            f"stats[{i}].github: {metric} not read ({exc}); "
            f"showing {fallback or 'n/a'!r} instead"
        )
        return None


def render_all(config: dict, warn: Callable[[str], None]) -> list[Card]:
    """Render every section present in a checked profile, in file order."""
    pal = Palette.from_accent(
        config["theme"]["accent"] if config.get("theme") else None
    )
    icons = _icons(config.get("buttons") or [], warn)
    logos = _logos(config["tiles"]["items"] if config.get("tiles") else [], warn)
    user = (config.get("github") or {}).get("user") or os.environ.get(
        "GITHUB_REPOSITORY_OWNER"
    )
    cards: list[Card] = []
    for section, value in config.items():
        match section:
            case "hero":
                cards.append(render_hero(value, pal))
            case "terminal":
                cards.append(render_terminal(value, pal))
            case "headers":
                cards += render_headers(value, pal)
            case "divider":
                cards.append(render_divider(pal))
            case "footer":
                cards.append(render_footer(value, pal))
            case "timeline":
                cards.append(render_timeline(value, pal))
            case "tiles":
                cards.append(render_tiles(value, pal, logos))
            case "panels":
                cards.append(render_panels(value, pal))
            case "stats":
                cards.append(render_stats(_live_stats(value, user, warn), pal))
            case "buttons":
                cards += render_buttons(value, pal, icons)
            case "projects":
                cards += render_projects(value, pal)
    return cards
