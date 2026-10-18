"""Commit the rendered files: on the checked-out branch, or as the only commit of an output branch."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
IDENTITY = {
    "GIT_AUTHOR_NAME": BOT_NAME,
    "GIT_AUTHOR_EMAIL": BOT_EMAIL,
    "GIT_COMMITTER_NAME": BOT_NAME,
    "GIT_COMMITTER_EMAIL": BOT_EMAIL,
}
# trailer on every output-branch commit; only a branch whose tip carries it is replaced
MARKER = "Generated-by: readme-kit"


class PublishError(Exception):
    """git refused, or the target is unsafe to write; the message says what to change."""


def git(
    *args: str, stdin: str | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run git in the current directory as github-actions[bot]."""
    proc = subprocess.run(
        ["git", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={**os.environ, **IDENTITY},
        check=False,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit code {proc.returncode}"
        raise PublishError(f"git {args[0]} failed: {detail}")
    return proc


def push(*args: str) -> None:
    try:
        git("push", "--quiet", *args)
    except PublishError as exc:
        raise PublishError(
            f"{exc}; the job needs `permissions: contents: write` to push"
        ) from exc


def current_branch() -> str | None:
    proc = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def commit_here(out: Path, message: str) -> str | None:
    """Commit out on the checked-out branch and push it. Returns the commit, or None if nothing changed."""
    if current_branch() is None:
        raise PublishError(
            "commit needs a checked-out branch, and HEAD is detached (pull_request runs check out "
            "a merge commit); run on push, schedule or workflow_dispatch, or set branch"
        )
    git("add", "--all", "--", str(out))
    if git("diff", "--cached", "--quiet", "--", str(out), check=False).returncode == 0:
        return None
    git("commit", "--quiet", "--message", message, "--", str(out))
    push("origin", "HEAD")
    return git("rev-parse", "HEAD").stdout.strip()


def commit_to_branch(
    out: Path, names: list[str], branch: str, message: str
) -> str | None:
    """Make names in out the whole tree of branch, as one parentless commit, and force-push it.

    Only a branch that is missing, or whose tip is a parentless commit carrying MARKER,
    is replaced, so a typo such as branch: main can never wipe real history. Returns the
    commit, or None when the branch already holds exactly these files.
    """
    git("check-ref-format", "--branch", branch)
    if branch == current_branch():
        raise PublishError(
            f"branch {branch!r} is the checked-out branch; name a separate output branch"
        )
    lines = []
    for name in names:
        blob = git("hash-object", "-w", "--", str(out / name)).stdout.strip()
        lines.append(f"100644 blob {blob}\t{name}\0")
    # NUL-terminated, so text mode cannot turn the line ends into CRLF on Windows
    tree = git("mktree", "-z", stdin="".join(lines)).stdout.strip()
    ref = f"refs/heads/{branch}"
    remote = git("ls-remote", "--exit-code", "origin", ref, check=False)
    if remote.returncode == 0:
        git("fetch", "--quiet", "--depth=1", "origin", ref)
        header, _, body = git("cat-file", "commit", "FETCH_HEAD").stdout.partition(
            "\n\n"
        )
        has_parent = any(line.startswith("parent ") for line in header.splitlines())
        if has_parent or MARKER not in body.splitlines():
            raise PublishError(
                f"branch {branch!r} was not written by readme-kit, which only replaces a "
                "branch it wrote; pick a new branch name"
            )
        if git("rev-parse", "FETCH_HEAD^{tree}").stdout.strip() == tree:
            return None
    elif remote.returncode != 2:  # 2 means the branch does not exist yet
        raise PublishError(
            f"git ls-remote failed: {(remote.stderr or remote.stdout).strip()}"
        )
    commit = git("commit-tree", tree, "-m", message, "-m", MARKER).stdout.strip()
    push("--force", "origin", f"{commit}:{ref}")
    return commit
