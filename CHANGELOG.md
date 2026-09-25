# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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
