"""Downloads are refused off https or off the allowlist before any connection is opened."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Self

import pytest
from conftest import ICON_SVG, PNG

from readme_kit import fetch


class FakeResponse:
    def __init__(self, body: bytes, url: str) -> None:
        self.body = body
        self.url = url

    def read(self, n: int = -1) -> bytes:
        return self.body if n < 0 else self.body[:n]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def serve(
    monkeypatch: pytest.MonkeyPatch, body: bytes, final_url: str | None = None
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        assert timeout > 0
        return FakeResponse(body, final_url or request.full_url)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


@pytest.mark.parametrize(
    "url",
    ["http://example.com/logo.png", "file:///etc/passwd", "ftp://example.com/logo.png"],
)
def test_logo_urls_must_be_https(url):
    # the autouse no_network fixture turns any connection attempt into an AssertionError
    with pytest.raises(fetch.FetchError, match="refusing"):
        fetch.logo_data_uri(url)


def test_icons_only_come_from_simple_icons_on_jsdelivr():
    with pytest.raises(fetch.FetchError, match="refusing"):
        fetch.fetch_bytes(
            "https://example.com/icons/github.svg", fetch.ICON_PREFIX, 1024
        )


def test_redirect_off_https_is_refused(monkeypatch):
    serve(monkeypatch, PNG, final_url="http://example.com/logo.png")

    with pytest.raises(fetch.FetchError, match="redirected off https"):
        fetch.logo_data_uri("https://example.com/logo.png")


def test_oversized_logo_is_refused(monkeypatch):
    serve(monkeypatch, PNG + b"\x00" * fetch.MAX_LOGO_BYTES)

    with pytest.raises(fetch.FetchError, match="larger than 256 KB"):
        fetch.logo_data_uri("https://example.com/logo.png")


def test_non_image_logo_is_refused(monkeypatch):
    serve(monkeypatch, b"<html><body>not found</body></html>")

    with pytest.raises(fetch.FetchError, match="not a PNG"):
        fetch.logo_data_uri("https://example.com/logo.png")


def test_logo_becomes_a_data_uri(monkeypatch):
    serve(monkeypatch, PNG)

    assert fetch.logo_data_uri("https://example.com/logo.png").startswith(
        "data:image/png;base64,iVBORw0KGgo"
    )


@pytest.mark.parametrize(
    ("raw", "mime"),
    [
        (b"\xff\xd8\xff\xe0rest", "image/jpeg"),
        (b"GIF89a....", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (
            b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>',
            "image/svg+xml",
        ),
        (b"%PDF-1.7", None),
    ],
)
def test_image_type_sniffs_the_bytes(raw, mime):
    assert fetch.image_type(raw) == mime


def test_simple_icon_returns_its_path_data(monkeypatch):
    serve(monkeypatch, ICON_SVG)

    assert fetch.simple_icon("github") == "M1 1h22v22H1z"


def test_network_errors_become_fetch_errors(monkeypatch):
    def down(request: urllib.request.Request, timeout: float) -> None:
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", down)

    with pytest.raises(fetch.FetchError, match="no route to host"):
        fetch.simple_icon("github")
