"""The only network code: simple-icons paths for buttons and logos for tiles, https only."""

from __future__ import annotations

import base64
import http.client
import re
import urllib.request

ICON_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg"
ICON_PREFIX = "https://cdn.jsdelivr.net/npm/simple-icons@"
MAX_ICON_BYTES = 64 * 1024
MAX_LOGO_BYTES = 256 * 1024
USER_AGENT = "readme-kit-action (+https://github.com/Sagargupta16/readme-kit-action)"
PATH_RE = re.compile(r'<path d="([^"]+)"')
SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


class FetchError(Exception):
    """A download was refused or failed; the card is drawn without it."""


def fetch_bytes(
    url: str, allowed: str, limit: int, headers: dict[str, str] | None = None
) -> bytes:
    """Return the body of url, refusing anything off the allowlist, off https, or over limit bytes.

    headers are sent to url only: urllib drops unredirected headers on a redirect, so a
    token never follows one to another host.
    """
    if not url.startswith(allowed):
        raise FetchError(f"refusing {url}: only {allowed} URLs are fetched")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for name, value in (headers or {}).items():
        request.add_unredirected_header(name, value)
    try:
        # the scheme and host were checked against the allowlist above
        with urllib.request.urlopen(request, timeout=20) as resp:  # nosec B310
            if not resp.url.startswith("https://"):
                raise FetchError(f"{url} redirected off https to {resp.url}")
            body = resp.read(limit + 1)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise FetchError(str(exc) or type(exc).__name__) from exc
    if len(body) > limit:
        raise FetchError(f"{url} is larger than {limit // 1024} KB")
    return body


def simple_icon(slug: str) -> str:
    """Return the path data of one simple-icons icon, drawn on a 24x24 viewBox."""
    raw = fetch_bytes(ICON_URL.format(slug=slug), ICON_PREFIX, MAX_ICON_BYTES)
    match = PATH_RE.search(raw.decode("utf-8", "replace"))
    if match is None:
        raise FetchError(f"no <path> in simple-icons {slug}.svg")
    return match.group(1)


def image_type(raw: bytes) -> str | None:
    """Return the MIME type of a PNG, JPEG, GIF, WebP or SVG image, or None."""
    for magic, mime in SIGNATURES:
        if raw.startswith(magic):
            return mime
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    head = raw[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith((b"<svg", b"<?xml", b"<!--")) and b"<svg" in raw.lower():
        return "image/svg+xml"
    return None


def logo_data_uri(url: str) -> str:
    """Fetch a tile logo and return it as a data URI, so the card needs no network to show."""
    raw = fetch_bytes(url, "https://", MAX_LOGO_BYTES)
    mime = image_type(raw)
    if mime is None:
        raise FetchError(f"{url} is not a PNG, JPEG, GIF, WebP or SVG image")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
