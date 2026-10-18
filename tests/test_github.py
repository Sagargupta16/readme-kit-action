"""Live stats read the GitHub API through fetch_bytes, and fall back instead of failing."""

from __future__ import annotations

import json
import urllib.parse

import pytest

from readme_kit import cards, config, fetch, github

USER = {"login": "ada", "public_repos": 3, "followers": 1234}
REPOS = [
    {"name": "engine", "stargazers_count": 1200, "fork": False},
    {"name": "notes", "stargazers_count": 5, "fork": False},
    {"name": "someone-elses", "stargazers_count": 90000, "fork": True},
]


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, str]]]:
    """Answer api.github.com like GitHub would for user ada; record each URL and its headers."""
    seen: list[tuple[str, dict[str, str]]] = []

    def fake(url: str, allowed: str, _limit: int, headers=None) -> bytes:
        assert allowed == github.API
        seen.append((url, headers or {}))
        path = url.removeprefix(github.API)
        if path == "users/ada":
            body: object = USER
        elif path.startswith("users/ada/repos?"):
            body = REPOS if "page=1" in path else []
        elif path.startswith("search/issues?"):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["q"][0]
            body = {"total_count": 7 if "-user:ada" in query else 40}
        else:
            raise fetch.FetchError(f"HTTP Error 404 for {path}")
        return json.dumps(body).encode()

    monkeypatch.setattr(fetch, "fetch_bytes", fake)
    return seen


def stats(*metrics: str, **extra: object) -> dict:
    return config.validate(
        {
            "stats": [{"github": m, "label": m} for m in metrics],
            **extra,
        }
    )


@pytest.mark.parametrize(
    ("metric", "value"),
    [
        ("repos", 3),
        ("followers", 1234),
        ("stars", 1205),  # forks left out
        ("merged-prs", 40),
        ("upstream-merged-prs", 7),
    ],
)
def test_each_metric(api, metric, value):
    assert github.Client("ada").metric(metric) == value


def test_every_metric_is_handled(api):
    for metric in github.METRICS:
        assert isinstance(github.Client("ada").metric(metric), int)


def test_upstream_query_leaves_out_the_users_own_repos(api):
    github.Client("ada").metric("upstream-merged-prs")

    query = urllib.parse.parse_qs(urllib.parse.urlsplit(api[0][0]).query)["q"][0]
    assert query == "type:pr is:merged author:ada -user:ada"


def test_values_are_formatted_and_each_path_fetched_once(api, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    profile = stats("followers", "repos", "followers", github={"user": "ada"})

    [card] = cards.render_all(profile, pytest.fail)

    assert card.alt == "Stats: 1,234 followers; 3 repos; 1,234 followers"
    assert [url for url, _ in api] == [github.API + "users/ada"]


def test_token_is_sent_only_when_set(api, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    cards.render_all(stats("repos", github={"user": "ada"}), pytest.fail)
    monkeypatch.delenv("GITHUB_TOKEN")
    cards.render_all(stats("followers", github={"user": "ada"}), pytest.fail)

    assert api[0][1]["Authorization"] == "Bearer t0ken"
    assert "Authorization" not in api[1][1]


def test_user_defaults_to_the_repository_owner(api, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "ada")

    [card] = cards.render_all(stats("repos"), pytest.fail)

    assert card.alt == "Stats: 3 repos"


def test_a_failed_read_falls_back_to_value_then_na(monkeypatch):
    def down(url: str, *_args: object) -> bytes:
        raise fetch.FetchError("HTTP Error 403: rate limit exceeded")

    monkeypatch.setattr(fetch, "fetch_bytes", down)
    warnings: list[str] = []
    profile = config.validate(
        {
            "github": {"user": "ada"},
            "stats": [
                {"github": "stars", "value": "1k+", "label": "stars"},
                {"github": "followers", "label": "followers"},
                {"value": "6", "label": "certs"},
            ],
        }
    )

    [card] = cards.render_all(profile, warnings.append)

    assert card.alt == "Stats: 1k+ stars; n/a followers; 6 certs"
    assert warnings == [
        (
            "stats[0].github: stars not read (HTTP Error 403: rate limit exceeded); "
            "showing '1k+' instead"
        ),
        (
            "stats[1].github: followers not read (HTTP Error 403: rate limit exceeded); "
            "showing 'n/a' instead"
        ),
    ]


def test_no_user_anywhere_warns_once(monkeypatch, api):
    monkeypatch.delenv("GITHUB_REPOSITORY_OWNER", raising=False)
    warnings: list[str] = []

    [card] = cards.render_all(stats("repos", "stars"), warnings.append)

    assert card.alt == "Stats: n/a repos; n/a stars"
    assert len(warnings) == 1
    assert warnings[0].startswith("stats: no GitHub user")
    assert api == []


def test_non_json_answer_is_a_fetch_error(monkeypatch):
    monkeypatch.setattr(fetch, "fetch_bytes", lambda *_args: b"<html>")
    client = github.Client("ada")

    with pytest.raises(fetch.FetchError, match="did not return JSON"):
        client.metric("repos")


def test_api_requests_only_go_to_api_github_com():
    with pytest.raises(fetch.FetchError, match="refusing"):
        fetch.fetch_bytes("https://evil.example/users/ada", github.API, 1024)
