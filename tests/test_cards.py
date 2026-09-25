"""Every card type renders valid, self-contained SVG with config text escaped."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from readme_kit import cards, config
from readme_kit.svg import Palette

ROOT = Path(__file__).resolve().parent.parent
SVG_TAG = "{http://www.w3.org/2000/svg}svg"
NASTY = 'Tom & "Jerry" <b>'

# one minimal profile per card type, with NASTY in every text field it renders
CASES = {
    "hero": {
        "hero": {
            "name": NASTY,
            "kicker": NASTY,
            "role": NASTY,
            "taglines": [NASTY, "second"],
            "status": NASTY,
            "location": NASTY,
            "constellation": {"hub": "A&B", "nodes": ["<x>", '"q"']},
        }
    },
    "terminal": {
        "terminal": {
            "prompt": NASTY,
            "title": NASTY,
            "commands": [{"command": NASTY, "output": [NASTY], "color": "amber"}],
        }
    },
    "headers": {"headers": [{"title": NASTY, "subtitle": NASTY}]},
    "divider": {"divider": True},
    "footer": {"footer": {"kicker": NASTY, "lines": [NASTY, "second"]}},
    "timeline": {
        "timeline": {
            "title": NASTY,
            "milestones": [
                {"year": 2021, "title": NASTY, "subtitle": NASTY},
                {"year": "2024", "title": "Now", "tag": NASTY},
            ],
            "expand": {
                "title": NASTY,
                "items": [{"when": NASTY, "title": NASTY, "subtitle": NASTY}],
            },
        }
    },
    "tiles": {
        "tiles": {
            "title": NASTY,
            "items": [
                {
                    "name": NASTY,
                    "subtitle": NASTY,
                    "logo": "https://example.com/logo.png",
                },
                {"name": "State Street"},
            ],
        }
    },
    "panels": {
        "panels": {
            "title": NASTY,
            "items": [{"title": NASTY, "entries": [{"text": NASTY, "year": NASTY}]}],
        }
    },
    "stats": {"stats": [{"value": NASTY, "label": NASTY, "color": "green"}]},
    "buttons": {
        "buttons": [
            {"label": NASTY, "icon": "github", "url": "https://github.com/?a=1&b=2"}
        ]
    },
    "projects": {
        "projects": [
            {
                "title": NASTY,
                "date": NASTY,
                "description": NASTY,
                "tech": [NASTY],
                "live": True,
            }
        ]
    },
}


def parse(svg: str) -> ET.Element:
    root = ET.fromstring(svg)
    assert root.tag == SVG_TAG
    assert root.get("role") == "img"
    assert root.get("aria-label") is not None
    return root


def example_profile() -> dict:
    return yaml.safe_load((ROOT / "profile.example.yml").read_text(encoding="utf-8"))


def test_every_card_type_has_a_case():
    assert sorted(CASES) == sorted(config.CARDS)


@pytest.mark.parametrize("section", CASES)
def test_card_is_valid_xml_and_escapes_config_text(section, downloads):
    rendered = cards.render_all(config.validate(CASES[section]), pytest.fail)

    assert rendered
    for card in rendered:
        root = parse(card.svg)
        assert "<b>" not in card.svg
        assert "<B>" not in card.svg
        if section != "divider":
            text = "".join(root.itertext()) + root.get("aria-label")
            assert NASTY in text or NASTY.upper() in text


def test_missing_optional_sections_render_nothing(downloads):
    profile = config.validate(
        {"hero": {"name": "Ada"}, "terminal": None, "divider": False}
    )

    rendered = cards.render_all(profile, pytest.fail)

    assert [card.name for card in rendered] == ["hero.svg"]
    assert downloads == []


def test_missing_optional_parts_are_left_out_of_a_card():
    hero = config.validate({"hero": {"name": "Ada"}})["hero"]

    svg = cards.render_hero(hero, Palette()).svg

    assert "animateMotion" not in svg  # no constellation
    assert "#22c55e14" not in svg  # no status pill
    assert 'aria-label="Ada."' in svg


def test_timeline_without_expand_is_short():
    timeline = config.validate(
        {
            "timeline": {
                "milestones": [
                    {"year": 2020, "title": "a"},
                    {"year": 2024, "title": "b"},
                ]
            }
        }
    )["timeline"]

    root = parse(cards.render_timeline(timeline, Palette()).svg)

    assert root.get("height") == "160"


def test_default_palette_keeps_the_original_blues():
    svg = cards.render_header("01", "Experience", None, "dark", Palette())

    assert "#60a5fa" in svg
    assert "#2563eb" in svg


def test_accent_replaces_the_blue_family_on_every_card(downloads):
    raw = example_profile()
    raw["theme"] = {"accent": "#34D399"}

    rendered = cards.render_all(config.validate(raw), pytest.fail)

    for card in rendered:
        svg = card.svg.lower()
        assert "#60a5fa" not in svg, card.name
        assert "#2563eb" not in svg, card.name
        assert "#34d399" in svg, card.name


def test_en_and_em_dashes_become_hyphens():
    dashed = f"Open{chr(0x2013)}Source{chr(0x2014)}Work"
    profile = config.validate({"headers": [{"title": dashed, "subtitle": dashed}]})

    svg = cards.render_all(profile, pytest.fail)[0].svg

    assert chr(0x2013) not in svg
    assert chr(0x2014) not in svg
    assert "Open-Source-Work" in svg


def test_icons_and_logos_are_inlined(downloads):
    profile = config.validate(
        {
            "buttons": [{"label": "GitHub", "icon": "github"}],
            "tiles": {
                "items": [{"name": "AWS", "logo": "https://example.com/aws.png"}]
            },
        }
    )

    rendered = {card.name: card.svg for card in cards.render_all(profile, pytest.fail)}

    assert '<path d="M1 1h22v22H1z"' in rendered["button-github.svg"]
    assert 'href="data:image/png;base64,' in rendered["tiles.svg"]
    assert downloads == [
        "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/github.svg",
        "https://example.com/aws.png",
    ]


def test_failed_downloads_fall_back_and_name_the_key(offline):
    profile = config.validate(
        {
            "buttons": [{"label": "GitHub", "icon": "github"}],
            "tiles": {
                "items": [
                    {"name": "State Street", "logo": "https://example.com/ss.png"}
                ]
            },
        }
    )
    warnings: list[str] = []

    rendered = {
        card.name: card.svg for card in cards.render_all(profile, warnings.append)
    }

    assert "<path d=" not in rendered["button-github.svg"]
    assert 'text-anchor="middle"' in rendered["button-github.svg"]
    assert "<image" not in rendered["tiles.svg"]
    assert ">SS</text>" in rendered["tiles.svg"]
    assert [w.split(":")[0] for w in warnings] == [
        "buttons[0].icon",
        "tiles.items[0].logo",
    ]


def test_long_button_labels_widen_the_button():
    short = parse(cards.render_button("GitHub", None, 0, Palette()))
    long = parse(cards.render_button("HackerRank Profile", None, 0, Palette()))

    assert short.get("width") == "156"
    assert int(long.get("width")) > 156


def test_example_profile_renders_the_cards_in_examples(downloads):
    rendered = cards.render_all(config.load(ROOT / "profile.example.yml"), pytest.fail)

    for card in rendered:
        parse(card.svg)
    assert sorted(card.name for card in rendered) == sorted(
        path.name for path in (ROOT / "examples").glob("*.svg")
    )
