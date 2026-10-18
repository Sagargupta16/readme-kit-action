"""Live numbers for the stats card, read from the GitHub REST API at render time."""

from __future__ import annotations

import json
import os
import urllib.parse

from readme_kit import fetch

API = "https://api.github.com/"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_REPO_PAGES = 10  # 100 repositories a page, so stars counts up to 1,000 of them
METRICS = ("repos", "followers", "stars", "merged-prs", "upstream-merged-prs")


class Client:
    """Reads one user's public numbers; every API path is fetched at most once."""

    def __init__(self, user: str, token: str | None = None) -> None:
        self.user = urllib.parse.quote(user, safe="")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.cache: dict[str, object] = {}

    @classmethod
    def from_env(cls, user: str) -> Client:
        """A client that uses $GITHUB_TOKEN when it is set, as it is for the action."""
        return cls(user, os.environ.get("GITHUB_TOKEN") or None)

    def get(self, path: str) -> object:
        if path not in self.cache:
            raw = fetch.fetch_bytes(API + path, API, MAX_JSON_BYTES, self.headers)
            try:
                self.cache[path] = json.loads(raw)
            except ValueError as exc:
                raise fetch.FetchError(f"{API}{path} did not return JSON") from exc
        return self.cache[path]

    def number(self, path: str, field: str) -> int:
        data = self.get(path)
        value = data.get(field) if isinstance(data, dict) else None
        if not isinstance(value, int) or isinstance(value, bool):
            raise fetch.FetchError(f"{API}{path} has no number in {field!r}")
        return value

    def merged_prs(self, *qualifiers: str) -> int:
        query = " ".join(("type:pr", "is:merged", f"author:{self.user}", *qualifiers))
        params = urllib.parse.urlencode({"q": query, "per_page": 1})
        return self.number(f"search/issues?{params}", "total_count")

    def stars(self) -> int:
        """Stars on the repositories the user owns, forks left out."""
        total = 0
        for page in range(1, MAX_REPO_PAGES + 1):
            repos = self.get(
                f"users/{self.user}/repos?type=owner&per_page=100&page={page}"
            )
            if not isinstance(repos, list):
                raise fetch.FetchError(
                    f"the repository list for {self.user} is not a list"
                )
            total += sum(
                repo.get("stargazers_count") or 0
                for repo in repos
                if isinstance(repo, dict) and not repo.get("fork")
            )
            if len(repos) < 100:
                break
        return total

    def metric(self, name: str) -> int:
        match name:
            case "repos":
                return self.number(f"users/{self.user}", "public_repos")
            case "followers":
                return self.number(f"users/{self.user}", "followers")
            case "stars":
                return self.stars()
            case "merged-prs":
                return self.merged_prs()
            case "upstream-merged-prs":
                return self.merged_prs(f"-user:{self.user}")
        raise ValueError(f"unknown metric {name!r}")
