"""Shared fixtures: the repo root on sys.path, no network, canned downloads."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from readme_kit import fetch

ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>'
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Serve a tiny icon for simple-icons URLs and a PNG for anything else; record each URL."""
    seen: list[str] = []

    def fake(url: str, _allowed: str, _limit: int) -> bytes:
        seen.append(url)
        return ICON_SVG if url.startswith(fetch.ICON_PREFIX) else PNG

    monkeypatch.setattr(fetch, "fetch_bytes", fake)
    return seen


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every download fails, as it would with the CDN down."""

    def fail(url: str, _allowed: str, _limit: int) -> bytes:
        raise fetch.FetchError(f"{url} is unreachable")

    monkeypatch.setattr(fetch, "fetch_bytes", fail)
