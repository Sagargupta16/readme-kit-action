# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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
