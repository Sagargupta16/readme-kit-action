"""Load profile.yml and check it against the card schema, naming every bad key."""

from __future__ import annotations

import datetime
import difflib
import re
from pathlib import Path

import yaml

from readme_kit.github import METRICS
from readme_kit.svg import COLOR_NAMES

KEY_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SLUG_RE = re.compile(r"[a-z0-9]+")
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
USER_RE = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}")
EN_DASH, EM_DASH = chr(0x2013), chr(0x2014)
# XML 1.0 forbids these even as character references, so they must never reach an SVG
INVALID_XML = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f"
    + f"{chr(0xD800)}-{chr(0xDFFF)}{chr(0xFFFE)}{chr(0xFFFF)}]"
)


class ConfigError(Exception):
    """The profile does not match the schema; problems lists every bad key found."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def clean(text: str) -> str:
    """Return text with en and em dashes turned into hyphens and XML-invalid characters dropped."""
    return INVALID_XML.sub("", text.replace(EN_DASH, "-").replace(EM_DASH, "-"))


def describe(value: object) -> str:
    """Name what YAML produced, for error messages."""
    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        return "a mapping"
    if isinstance(value, list):
        return "a list"
    return type(value).__name__


def entries(n: int) -> str:
    return f"{n} entry" if n == 1 else f"{n} entries"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def unknown(path: str, key: object, allowed: dict[str, Spec]) -> str:
    where = f"{path}.{key}" if path else str(key)
    close = difflib.get_close_matches(str(key), list(allowed), n=1)
    hint = (
        f"did you mean {close[0]!r}?"
        if close
        else "expected one of: " + ", ".join(allowed)
    )
    return f"{where}: unknown key, {hint}"


class Spec:
    """One node of the schema: checks a value, records problems, returns the clean value."""

    required = False

    def empty(self) -> object:
        """Value used when an optional key is missing."""
        return None

    def check(self, value: object, path: str, errors: list[str]) -> object:
        raise NotImplementedError


class Text(Spec):
    def __init__(
        self,
        *,
        required: bool = False,
        max_len: int | None = None,
        pattern: re.Pattern[str] | None = None,
        expect: str = "",
    ) -> None:
        self.required = required
        self.max_len = max_len
        self.pattern = pattern
        self.expect = expect

    def check(self, value: object, path: str, errors: list[str]) -> str | None:
        if isinstance(value, bool):
            errors.append(
                f"{path}: expected text, got {describe(value)}; YAML reads yes, no, on and off "
                "as booleans, so quote the value"
            )
            return None
        if isinstance(value, (int, float, datetime.date)):
            value = str(value)
        if not isinstance(value, str):
            errors.append(f"{path}: expected text, got {describe(value)}")
            return None
        text = clean(value)
        if self.required and not text.strip():
            errors.append(f"{path}: must not be empty")
        elif self.max_len is not None and len(text) > self.max_len:
            errors.append(
                f"{path}: {text!r} is {len(text)} characters, the limit is {self.max_len}"
            )
        elif self.pattern is not None and not self.pattern.fullmatch(text):
            errors.append(f"{path}: {text!r} is not {self.expect}")
        return text


class Url(Text):
    def __init__(self, schemes: tuple[str, ...], *, required: bool = False) -> None:
        super().__init__(required=required)
        self.schemes = schemes

    def check(self, value: object, path: str, errors: list[str]) -> str | None:
        text = super().check(value, path, errors)
        if text and (
            not text.startswith(self.schemes) or any(c.isspace() for c in text)
        ):
            errors.append(
                f"{path}: {text!r} must be a URL starting with {' or '.join(self.schemes)}"
            )
        return text


class Choice(Text):
    def __init__(self, choices: tuple[str, ...]) -> None:
        super().__init__()
        self.choices = choices

    def check(self, value: object, path: str, errors: list[str]) -> str | None:
        text = super().check(value, path, errors)
        if text is not None and text not in self.choices:
            errors.append(f"{path}: {text!r} is not one of {', '.join(self.choices)}")
        return text


class Flag(Spec):
    def empty(self) -> bool:
        return False

    def check(self, value: object, path: str, errors: list[str]) -> bool:
        if not isinstance(value, bool):
            errors.append(f"{path}: expected true or false, got {describe(value)}")
            return False
        return value


class Toggle(Spec):
    """A card with no options: `true` renders it."""

    def check(self, value: object, path: str, errors: list[str]) -> bool | None:
        if value is True or value == {}:
            return True
        errors.append(f"{path}: expected true, got {describe(value)}")
        return None


class ListOf(Spec):
    def __init__(
        self,
        item: Spec,
        *,
        required: bool = False,
        min_items: int = 0,
        max_items: int | None = None,
    ) -> None:
        self.item = item
        self.required = required
        self.min_items = min_items
        self.max_items = max_items

    def empty(self) -> list:
        return []

    def check(self, value: object, path: str, errors: list[str]) -> list:
        if not isinstance(value, list):
            errors.append(f"{path}: expected a list, got {describe(value)}")
            return []
        if len(value) < self.min_items:
            errors.append(
                f"{path}: needs at least {entries(self.min_items)}, got {len(value)}"
            )
        if self.max_items is not None and len(value) > self.max_items:
            errors.append(
                f"{path}: takes at most {entries(self.max_items)}, got {len(value)}"
            )
        return [self.item.check(v, f"{path}[{i}]", errors) for i, v in enumerate(value)]


class Fields(Spec):
    def __init__(self, fields: dict[str, Spec], *, required: bool = False) -> None:
        self.fields = fields
        self.required = required

    def check(self, value: object, path: str, errors: list[str]) -> dict | None:
        if not isinstance(value, dict):
            errors.append(f"{path}: expected a mapping, got {describe(value)}")
            return None
        errors.extend(
            unknown(path, key, self.fields) for key in value if key not in self.fields
        )
        out = {}
        for key, spec in self.fields.items():
            sub = f"{path}.{key}"
            if value.get(key) is None:
                if spec.required:
                    errors.append(f"{sub}: required")
                out[key] = spec.empty()
            else:
                out[key] = spec.check(value[key], sub, errors)
        return out


class Stat(Fields):
    """A stats entry: a typed value, a live GitHub number, or both (the value is then the fallback)."""

    def check(self, value: object, path: str, errors: list[str]) -> dict | None:
        out = super().check(value, path, errors)
        if out is not None and not out["value"] and out["github"] is None:
            errors.append(f"{path}: set value, github, or both")
        return out


COLOR = Choice(COLOR_NAMES)
KEY = Text(
    pattern=KEY_RE,
    expect="a file name key: lowercase letters, digits and single hyphens, like 'ledger-sync'",
)
NODE = Text(required=True, max_len=5)

SECTIONS: dict[str, Spec] = {
    "theme": Fields(
        {"accent": Text(pattern=HEX_RE, expect="a 6-digit hex color like '#60a5fa'")}
    ),
    "github": Fields(
        {"user": Text(pattern=USER_RE, expect="a GitHub username like 'octocat'")}
    ),
    "hero": Fields(
        {
            "name": Text(required=True),
            "kicker": Text(),
            "role": Text(),
            "taglines": ListOf(Text(required=True), max_items=12),
            "status": Text(),
            "location": Text(),
            "constellation": Fields({"hub": NODE, "nodes": ListOf(NODE, max_items=5)}),
        }
    ),
    "terminal": Fields(
        {
            "prompt": Text(),
            "title": Text(),
            "commands": ListOf(
                Fields(
                    {
                        "command": Text(required=True),
                        "output": ListOf(Text()),
                        "color": COLOR,
                    }
                ),
                required=True,
                min_items=1,
            ),
        }
    ),
    "headers": ListOf(
        Fields({"title": Text(required=True), "subtitle": Text(), "key": KEY}),
        min_items=1,
    ),
    "divider": Toggle(),
    "footer": Fields(
        {
            "kicker": Text(),
            "lines": ListOf(
                Text(required=True), required=True, min_items=1, max_items=12
            ),
        }
    ),
    "timeline": Fields(
        {
            "title": Text(),
            "milestones": ListOf(
                Fields(
                    {
                        "year": Text(required=True),
                        "title": Text(required=True),
                        "subtitle": Text(),
                        "tag": Text(),
                    }
                ),
                required=True,
                min_items=2,
                max_items=6,
            ),
            "expand": Fields(
                {
                    "title": Text(),
                    "items": ListOf(
                        Fields(
                            {
                                "when": Text(required=True),
                                "title": Text(required=True),
                                "subtitle": Text(),
                            }
                        ),
                        required=True,
                        min_items=1,
                        max_items=6,
                    ),
                }
            ),
        }
    ),
    "tiles": Fields(
        {
            "title": Text(),
            "items": ListOf(
                Fields(
                    {
                        "name": Text(required=True),
                        "subtitle": Text(),
                        "logo": Url(("https://",)),
                    }
                ),
                required=True,
                min_items=1,
                max_items=6,
            ),
        }
    ),
    "panels": Fields(
        {
            "title": Text(),
            "items": ListOf(
                Fields(
                    {
                        "title": Text(required=True),
                        "color": COLOR,
                        "entries": ListOf(
                            Fields({"text": Text(required=True), "year": Text()}),
                            required=True,
                            min_items=1,
                        ),
                    }
                ),
                required=True,
                min_items=1,
                max_items=4,
            ),
        }
    ),
    "stats": ListOf(
        Stat(
            {
                "value": Text(),
                "github": Choice(METRICS),
                "label": Text(required=True),
                "color": COLOR,
            }
        ),
        min_items=1,
    ),
    "buttons": ListOf(
        Fields(
            {
                "label": Text(required=True),
                "icon": Text(
                    pattern=SLUG_RE, expect="a simple-icons slug such as 'linkedin'"
                ),
                "url": Url(("https://", "mailto:")),
                "key": KEY,
            }
        ),
        min_items=1,
    ),
    "projects": ListOf(
        Fields(
            {
                "title": Text(required=True),
                "date": Text(),
                "description": Text(required=True),
                "tech": ListOf(Text(required=True)),
                "live": Flag(),
                "url": Url(("https://",)),
                "key": KEY,
            }
        ),
        min_items=1,
    ),
}
# sections that configure the others and write no file
SETTINGS = ("theme", "github")
CARDS = [name for name in SECTIONS if name not in SETTINGS]
# sections that write one file per entry, and the field their file name comes from
KEYED = {"headers": "title", "buttons": "label", "projects": "title"}


def _resolve_keys(config: dict, errors: list[str]) -> None:
    """Give every header, button and project a unique file name key."""
    for section, source in KEYED.items():
        seen: dict[str, int] = {}
        for i, item in enumerate(config.get(section) or []):
            key = item["key"] or slugify(item[source])
            if not key:
                errors.append(
                    f"{section}[{i}].{source}: {item[source]!r} has no letters or digits to name "
                    f"a file after; set {section}[{i}].key"
                )
            elif key in seen:
                errors.append(
                    f"{section}[{i}]: file name {key!r} is already used by {section}[{seen[key]}]; "
                    f"set a different {section}[{i}].key"
                )
            else:
                seen[key] = i
            item["key"] = key


def validate(raw: object) -> dict:
    """Return the checked profile: present sections only, in file order, defaults filled in."""
    if raw is None:
        raise ConfigError(["the file is empty"])
    if not isinstance(raw, dict):
        raise ConfigError(
            [f"expected a mapping of sections at the top level, got {describe(raw)}"]
        )
    errors: list[str] = []
    config = {}
    for key, value in raw.items():
        if key not in SECTIONS:
            errors.append(unknown("", key, SECTIONS))
        elif value is not None and value is not False:
            config[key] = SECTIONS[key].check(value, key, errors)
    if not errors and not any(name in config for name in CARDS):
        errors.append("no cards to render; add at least one of: " + ", ".join(CARDS))
    if not errors:
        _resolve_keys(config, errors)
    if errors:
        raise ConfigError(errors)
    return config


def load(path: Path) -> dict:
    """Read, parse and validate a profile file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError(["file not found"]) from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError([f"cannot read the file ({exc})"]) from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        reason = getattr(exc, "problem", None) or " ".join(str(exc).split())
        raise ConfigError([f"not valid YAML{where}: {reason}"]) from exc
    return validate(raw)
