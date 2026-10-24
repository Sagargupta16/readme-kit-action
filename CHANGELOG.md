# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.1.3] - 2026-10-24

### Security

- `config` and `output-dir` (and `--config`, `--output-dir`, `$CONFIG_PATH`,
  `$OUTPUT_DIR`) must now resolve inside the working directory, which on a runner is the
  checkout. A path that climbs out with `..`, an absolute path elsewhere, or a symlink that
  leads out fails the run with an error before any file is read or written. Before, the
  profile could be read from, and the cards written to, any folder the job could reach.
  This closes the four SonarCloud `pythonsecurity:S8707` path injection findings in
  `cli.py` and `config.py`. The default and relative paths work as before, and the inputs
  and outputs are unchanged.

### Changed

- An `output-dir` outside the working directory is now an error. In 1.1.0 it kept its
  path in `snippet.md` and got a warning. `commit` and a workflow that commits the cards
  itself always needed it inside the repository; only `branch` and local runs could write
  elsewhere.
- README: the How it works figure was re-rendered because its `cli.py` evidence lines
  moved. The figure itself is unchanged.

## [1.1.2] - 2026-10-24

### Changed

- README: redrew the "How it works" figure with orrery 0.12.0's 64 px icons (they were
  48 px). `docs/diagrams/pipeline.yaml` now uses the tightest spacing, which brings the
  figure from 1175 to 1110 px wide, so the README shows it a little larger. Every node,
  edge and evidence path is unchanged. Docs only; the action is unchanged.

## [1.1.1] - 2026-10-21

### Added

- README: an architecture figure at the top of "How it works", drawn with
  [orrery](https://github.com/Sagargupta16/orrery) from `docs/diagrams/pipeline.yaml`, in
  dark and light variants. It shows the push that triggers the workflow, validate (failing
  with error annotations), render, fetch from jsDelivr, logo hosts and api.github.com,
  write, and the opt-in commit back to the repository. Every node and edge names the file
  and line it comes from.

## [1.1.0] - 2026-10-18

### Added

- `commit` input: commits `output-dir` on the checked-out branch as `github-actions[bot]`
  and pushes it, only when a card changed. Quick start no longer needs a commit step.
- `branch` input: pushes the cards to an output branch as its only commit, force-pushed
  each run, so the main history gets no render commits and removed cards disappear. Only a
  branch that is missing or was written by readme-kit (a parentless commit with the
  `Generated-by: readme-kit` trailer) is replaced. `snippet.md` then links
  raw.githubusercontent.com URLs on that branch.
- `commit-message` input and `committed` output.
- Live GitHub stats: a `stats` entry can set `github:` to `repos`, `followers`, `stars`,
  `merged-prs` or `upstream-merged-prs` and gets the number from the GitHub REST API at
  render time. `value` becomes optional and is the fallback when the read fails. A new
  `github.user` profile key picks the user; it defaults to the repository owner.
- `token` input (default `github.token`), sent only to api.github.com and never across a
  redirect.
- `--commit`, `--branch` and `--commit-message` flags for local runs.
- `scripts/benchmark.py` and a Numbers section in the README with its measured output.
- Tests for live stats (canned API answers) and for commit and branch (real git against a
  bare repository in a temp folder). The CI `action` job runs both modes against a bare
  origin on the runner, with live stats.

### Fixed

- An absolute `output-dir` inside the working directory is now written as a relative path
  in `snippet.md`. Before, the image paths were absolute runner paths that never load in a
  README. An `output-dir` outside the working directory keeps its path and gets a warning.

## [1.0.1] - 2026-10-18

### Fixed

- A timeline `expand` rail with a single item now marks that item as current (green, with
  the ring), the same way the main rail marks its last milestone. Before, a one-item rail
  had no current item.
- The action no longer changes the Python on the consumer's `PATH`. `setup-python` runs
  with `update-environment: false` and the action calls that interpreter by its path, so
  steps after readme-kit keep the Python they set up themselves.

### Changed

- ruff pinned to 0.17.1 in CI and the docs (was 0.16.6). The tree passes its default
  ruleset unchanged.

### Added

- `SECURITY.md` and `CONTRIBUTING.md`.
- README: Marketplace, release and license badges, and a "How it works" section with the
  validate, fetch, render, write pipeline and the design decisions behind it.
- README: the Profile reference notes that hero `role` is alt text only and is not drawn.

## [1.0.0] - 2026-09-25

Initial release.

### Added

- Composite action that renders one `profile.yml` into self-hosted animated SVG cards,
  with `config` and `output-dir` inputs and a `files` output.
- Eleven card types, each rendered only when its section is present: hero, terminal,
  section headers (dark and light variants), divider, footer, timeline (with an optional
  second rail), tiles, panels, stats, buttons and project cards. The designs are ported
  unchanged from the cards on github.com/Sagargupta16.
- `theme.accent`, which replaces the blue family on every card and derives the deeper
  shade from it.
- `snippet.md` in `output-dir`: README markup for every card in profile order, with links
  from each button and project `url`.
- Profile validation that reports every problem in one pass, names the bad key, and
  suggests the closest known key for a typo.
- https-only downloads for simple-icons glyphs (cdn.jsdelivr.net) and tile logos, with
  logos capped at 256 KB and checked by their bytes. A failed download falls back to an
  icon-less button or a monogram tile and a warning, never a failed run.
- Every profile string is HTML-escaped, and en and em dashes become hyphens.
- PyYAML 6.0.3 installed as a pinned wheel; everything else is the standard library.
- `profile.example.yml` with every key documented, and `examples/` rendered from it.
- Tests with no network access, and CI running ruff, pytest on Python 3.12 to 3.14, and
  the action itself against the example profile.
