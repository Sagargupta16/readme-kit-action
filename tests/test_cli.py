"""main() writes every card plus snippet.md and reports the count as the files output."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from readme_kit import cli
from readme_kit.cards import Card

PROFILE = """\
hero:
  name: Ada Lovelace
headers:
  - title: Projects
    subtitle: what I built
buttons:
  - label: GitHub
    icon: github
    url: https://github.com/ada
projects:
  - title: Engine
    description: The first program. It computed Bernoulli numbers.
    url: https://example.com/engine
"""


def test_main_writes_cards_snippet_and_files_output(tmp_path, monkeypatch, downloads):
    profile = tmp_path / "profile.yml"
    profile.write_text(PROFILE, encoding="utf-8")
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    out = tmp_path / "cards"

    assert cli.main(["--config", str(profile), "--output-dir", str(out)]) == 0

    assert sorted(path.name for path in out.iterdir()) == [
        "button-github.svg",
        "header-projects-dark.svg",
        "header-projects-light.svg",
        "hero.svg",
        "project-engine.svg",
        "snippet.md",
    ]
    for svg in out.glob("*.svg"):
        ET.parse(svg)
    assert output.read_text(encoding="utf-8") == "files=6\n"
    snippet = (out / "snippet.md").read_text(encoding="utf-8")
    assert '<source media="(prefers-color-scheme: light)"' in snippet
    assert "header-projects-light.svg" in snippet
    assert '<a href="https://github.com/ada"><img src=' in snippet
    assert 'alt="Engine: The first program"' in snippet


def test_snippet_escapes_attributes_but_keeps_apostrophes():
    card = Card(
        "hero.svg",
        "<svg/>",
        'Ada "The" <Countess> O\'Brien',
        href="https://x.dev/?a=1&b=2",
    )

    text = cli.snippet([card], "out")

    assert (
        '<a href="https://x.dev/?a=1&amp;b=2"><img src="out/hero.svg" width="100%" '
        'alt="Ada &quot;The&quot; &lt;Countess&gt; O\'Brien" /></a>'
    ) in text


def test_env_vars_choose_the_paths(tmp_path, monkeypatch, downloads):
    profile = tmp_path / "profile.yml"
    profile.write_text(PROFILE, encoding="utf-8")
    monkeypatch.setenv("CONFIG_PATH", str(profile))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "from-env"))
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    assert cli.main([]) == 0

    assert (tmp_path / "from-env" / "hero.svg").is_file()


def test_config_errors_exit_1_as_annotations_under_actions(
    tmp_path, monkeypatch, capsys
):
    profile = tmp_path / "profile.yml"
    profile.write_text("hero:\n  kicker: hi\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    assert (
        cli.main(["--config", str(profile), "--output-dir", str(tmp_path / "out")]) == 1
    )

    assert f"::error::{profile}: hero.name: required" in capsys.readouterr().out
    assert not (tmp_path / "out").exists()


def test_config_errors_go_to_stderr_locally(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    assert cli.main(["--config", str(tmp_path / "missing.yml")]) == 1

    assert "error: " in capsys.readouterr().err
