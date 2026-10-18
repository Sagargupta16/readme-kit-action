"""commit and branch run real git against a local bare remote, so no network is needed."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from readme_kit import publish

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A clone on main with one commit, pushed to a bare origin, as the working directory."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    run("init", "--quiet", "--bare", str(remote), cwd=tmp_path)
    run("init", "--quiet", "-b", "main", str(work), cwd=tmp_path)
    for key, value in (
        ("user.name", "Ada"),
        ("user.email", "ada@example.com"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
    ):
        run("config", key, value, cwd=work)
    (work / "profile.yml").write_text("hero:\n  name: Ada\n", encoding="utf-8")
    run("add", "profile.yml", cwd=work)
    run("commit", "--quiet", "-m", "init", cwd=work)
    run("remote", "add", "origin", str(remote), cwd=work)
    run("push", "--quiet", "origin", "main", cwd=work)
    monkeypatch.chdir(work)
    return work


def write_cards(work: Path, **files: str) -> tuple[Path, list[str]]:
    out = work / "assets" / "readme-kit"
    out.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (out / f"{name}.svg").write_text(body, encoding="utf-8", newline="\n")
    return out, [f"{name}.svg" for name in files]


def remote_log(work: Path, ref: str) -> list[str]:
    return run("log", "--format=%s|%an", f"origin/{ref}", cwd=work).splitlines()


def test_commit_here_commits_and_pushes_only_output_dir(repo):
    (repo / "profile.yml").write_text("hero:\n  name: Ada L\n", encoding="utf-8")
    run("add", "profile.yml", cwd=repo)  # staged, but not part of the cards commit
    out, _ = write_cards(repo, hero="<svg/>")

    sha = publish.commit_here(out, "chore: render readme cards")

    run("fetch", "--quiet", "origin", cwd=repo)
    assert sha == run("rev-parse", "origin/main", cwd=repo)
    assert remote_log(repo, "main") == [
        "chore: render readme cards|github-actions[bot]",
        "init|Ada",
    ]
    assert run("show", "--name-only", "--format=", sha, cwd=repo) == (
        "assets/readme-kit/hero.svg"
    )


def test_commit_here_skips_when_nothing_changed(repo):
    out, _ = write_cards(repo, hero="<svg/>")
    publish.commit_here(out, "first")

    assert publish.commit_here(out, "second") is None


def test_commit_here_refuses_a_detached_head(repo):
    run("checkout", "--quiet", "--detach", cwd=repo)
    out, _ = write_cards(repo, hero="<svg/>")

    with pytest.raises(publish.PublishError, match="HEAD is detached"):
        publish.commit_here(out, "x")


def test_branch_holds_exactly_the_cards_as_one_commit(repo):
    out, names = write_cards(repo, hero="<svg>1</svg>", stats="<svg/>")
    first = publish.commit_to_branch(out, names, "output", "render")

    out, names = write_cards(repo, hero="<svg>2</svg>")
    second = publish.commit_to_branch(out, names, "output", "render")

    run("fetch", "--quiet", "origin", cwd=repo)
    assert first != second
    assert second == run("rev-parse", "origin/output", cwd=repo)
    assert run("rev-list", "--count", "origin/output", cwd=repo) == "1"
    # stats.svg is gone: the branch is rebuilt from the cards of this run only
    assert run("ls-tree", "--name-only", "origin/output", cwd=repo) == "hero.svg"
    assert run("show", "origin/output:hero.svg", cwd=repo) == "<svg>2</svg>"
    assert run("rev-list", "--count", "origin/main", cwd=repo) == "1"
    assert run("log", "-1", "--format=%B", "origin/output", cwd=repo) == (
        f"render\n\n{publish.MARKER}"
    )


def test_branch_skips_when_the_tree_is_unchanged(repo):
    out, names = write_cards(repo, hero="<svg/>")
    publish.commit_to_branch(out, names, "output", "render")

    assert publish.commit_to_branch(out, names, "output", "render") is None


@pytest.mark.parametrize("extra_commits", [0, 1])
def test_branch_never_replaces_a_branch_it_did_not_write(repo, extra_commits):
    # main with a single commit is parentless too, so the marker is what protects it
    for i in range(extra_commits):
        run("commit", "--quiet", "--allow-empty", "-m", f"more {i}", cwd=repo)
        run("push", "--quiet", "origin", "main", cwd=repo)
    run("checkout", "--quiet", "-b", "feature", cwd=repo)
    out, names = write_cards(repo, hero="<svg/>")
    before = run("rev-parse", "origin/main", cwd=repo)

    with pytest.raises(publish.PublishError, match="was not written by readme-kit"):
        publish.commit_to_branch(out, names, "main", "render")

    run("fetch", "--quiet", "origin", cwd=repo)
    assert run("rev-parse", "origin/main", cwd=repo) == before


def test_branch_refuses_the_checked_out_branch(repo):
    out, names = write_cards(repo, hero="<svg/>")

    with pytest.raises(publish.PublishError, match="is the checked-out branch"):
        publish.commit_to_branch(out, names, "main", "render")


def test_branch_name_must_be_valid(repo):
    out, names = write_cards(repo, hero="<svg/>")

    with pytest.raises(publish.PublishError, match="check-ref-format"):
        publish.commit_to_branch(out, names, "bad..name", "render")


def test_push_failure_names_the_permission(repo):
    run("remote", "set-url", "origin", str(repo / "missing.git"), cwd=repo)
    out, _ = write_cards(repo, hero="<svg/>")

    with pytest.raises(publish.PublishError, match="contents: write"):
        publish.commit_here(out, "x")
