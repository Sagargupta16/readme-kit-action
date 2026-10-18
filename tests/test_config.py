"""Config validation names the bad key and reports every problem in one pass."""

from __future__ import annotations

import datetime

import pytest

from readme_kit import config


def problems(raw: object) -> list[str]:
    with pytest.raises(config.ConfigError) as info:
        config.validate(raw)
    return info.value.problems


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"hero": {}}, "hero.name: required"),
        (
            {"hero": {"name": "Ada", "taglines": "one line"}},
            "hero.taglines: expected a list, got text",
        ),
        (
            {"hero": {"name": "Ada", "tagline": ["x"]}},
            "hero.tagline: unknown key, did you mean 'taglines'?",
        ),
        ({"heros": {"name": "Ada"}}, "heros: unknown key, did you mean 'hero'?"),
        (
            {"hero": {"name": True}},
            (
                "hero.name: expected text, got true; YAML reads yes, no, on and off as "
                "booleans, so quote the value"
            ),
        ),
        (
            {
                "hero": {
                    "name": "Ada",
                    "constellation": {"hub": "MCP", "nodes": ["KUBERNETES"]},
                }
            },
            "hero.constellation.nodes[0]: 'KUBERNETES' is 10 characters, the limit is 5",
        ),
        (
            {"theme": {"accent": "blue"}, "divider": True},
            "theme.accent: 'blue' is not a 6-digit hex color like '#60a5fa'",
        ),
        (
            {"stats": [{"value": 1, "label": "x", "color": "red"}]},
            "stats[0].color: 'red' is not one of accent, sky, green, amber",
        ),
        (
            {"tiles": {"items": [{"name": "X", "logo": "http://example.com/x.png"}]}},
            "tiles.items[0].logo: 'http://example.com/x.png' must be a URL starting with https://",
        ),
        (
            {"buttons": [{"label": "Mail", "url": "javascript:alert(1)"}]},
            "buttons[0].url: 'javascript:alert(1)' must be a URL starting with https:// or mailto:",
        ),
        (
            {"buttons": [{"label": "In", "icon": "Linked In"}]},
            "buttons[0].icon: 'Linked In' is not a simple-icons slug such as 'linkedin'",
        ),
        (
            {"timeline": {"milestones": [{"year": 2024, "title": "Now"}]}},
            "timeline.milestones: needs at least 2 entries, got 1",
        ),
        (
            {"terminal": {"commands": []}},
            "terminal.commands: needs at least 1 entry, got 0",
        ),
        (
            {"projects": [{"title": "A", "description": "x", "live": "yes please"}]},
            "projects[0].live: expected true or false, got text",
        ),
        ({"divider": "yes please"}, "divider: expected true, got text"),
        (
            {
                "projects": [
                    {"title": "Kalchar", "description": "a"},
                    {"title": "kalchar!", "description": "b"},
                ]
            },
            (
                "projects[1]: file name 'kalchar' is already used by projects[0]; "
                "set a different projects[1].key"
            ),
        ),
        (
            {"headers": [{"title": "!!!"}]},
            (
                "headers[0].title: '!!!' has no letters or digits to name a file after; "
                "set headers[0].key"
            ),
        ),
        (
            {"theme": {"accent": "#34d399"}},
            (
                "no cards to render; add at least one of: hero, terminal, headers, divider, "
                "footer, timeline, tiles, panels, stats, buttons, projects"
            ),
        ),
    ],
)
def test_bad_config_names_the_key(raw, expected):
    assert expected in problems(raw)


def test_every_problem_is_reported_at_once():
    found = problems(
        {"hero": {"taglines": 3}, "stats": [{"value": "1"}], "footer": {"lines": []}}
    )

    assert found == [
        "hero.name: required",
        "hero.taglines: expected a list, got a number",
        "stats[0].label: required",
        "footer.lines: needs at least 1 entry, got 0",
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "the file is empty"),
        (["hero"], "expected a mapping of sections at the top level, got a list"),
    ],
)
def test_top_level_must_be_a_mapping(raw, expected):
    assert problems(raw) == [expected]


def test_numbers_and_dates_become_text():
    profile = config.validate(
        {
            "stats": [{"value": 11, "label": "merged"}],
            "timeline": {
                "milestones": [
                    {"year": 2021, "title": "a"},
                    {"year": datetime.date(2024, 8, 1), "title": "b"},
                ]
            },
        }
    )

    assert profile["stats"][0]["value"] == "11"
    assert profile["timeline"]["milestones"][1]["year"] == "2024-08-01"


def test_sections_set_to_false_or_left_empty_are_skipped():
    profile = config.validate(
        {"hero": {"name": "Ada"}, "divider": False, "footer": None}
    )

    assert list(profile) == ["hero"]


def test_file_keys_default_to_a_slug_of_the_title():
    profile = config.validate(
        {"projects": [{"title": "Ledger Sync", "description": "x"}]}
    )

    assert profile["projects"][0]["key"] == "ledger-sync"


def test_invalid_yaml_reports_the_line(tmp_path):
    path = tmp_path / "profile.yml"
    path.write_text("hero:\n  name: Ada\n    kicker: hi\n", encoding="utf-8")

    with pytest.raises(config.ConfigError) as info:
        config.load(path)

    assert info.value.problems[0].startswith("not valid YAML at line 3")


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(config.ConfigError) as info:
        config.load(tmp_path / "nope.yml")

    assert info.value.problems == ["file not found"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"stats": [{"label": "stars"}]}, "stats[0]: set value, github, or both"),
        (
            {"stats": [{"github": "starz", "label": "stars"}]},
            (
                "stats[0].github: 'starz' is not one of repos, followers, stars, "
                "merged-prs, upstream-merged-prs"
            ),
        ),
        (
            {"github": {"user": "two words"}, "hero": {"name": "Ada"}},
            "github.user: 'two words' is not a GitHub username like 'octocat'",
        ),
    ],
)
def test_live_stats_are_checked(raw, expected):
    assert problems(raw) == [expected]


def test_github_alone_renders_nothing():
    assert problems({"github": {"user": "ada"}}) == [
        (
            "no cards to render; add at least one of: hero, terminal, headers, divider, "
            "footer, timeline, tiles, panels, stats, buttons, projects"
        )
    ]
