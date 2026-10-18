# CLAUDE.md

> This file stacks on top of the workspace root at `C:\Code\GitHub\`:
> - Root [`CLAUDE.md`](../../CLAUDE.md) -- voice, rules, routing map, references, skills, slash commands, conventions.
> - Root [`MEMORY.md`](../../MEMORY.md) -- live facts across repos.
> - Root [`STATUS.md`](../../STATUS.md) -- live PR/CI/security dashboard.
> - [`.claude/resources/`](../../.claude/resources/README.md) -- deep reference for collaboration, workflow, git, OSS, debugging, voice.
>
> Read those first. The guidance below only adds **repo-specific context** -- it does not override anything in the root.

## Project

Composite GitHub Action that turns one `profile.yml` into a matching set of self-hosted animated SVG cards for a GitHub profile README (hero, terminal, section headers, divider, footer, timeline, tiles, panels, stats, buttons, project cards), plus `snippet.md` with the README markup for every card.

The designs were extracted on 2026-09-25 from `brand/Sagargupta16/scripts/render-svgs.py`. Published as `Sagargupta16/readme-kit-action`: release v1.0.0 (2026-09-25), a moving `v1` tag, and a live Marketplace listing at https://github.com/marketplace/actions/readme-kit. Sagar's profile still renders its cards with render-svgs.py.

## Stack

- **Language**: Python 3.13 in the action (tests cover 3.12 to 3.14), standard library plus PyYAML
- **Framework**: GitHub Actions composite action (`action.yml`)
- **Database**: none
- **Package manager**: none for consumers (`action.yml` pip-installs the pinned PyYAML wheel); `uv` locally
- **Deploy target**: consumed via `uses:` in other repos' workflows; releases are git tags

## Run

```
uv run --no-project --with pyyaml==6.0.3 python readme_kit.py --config profile.example.yml --output-dir examples
```

The action passes its inputs as `CONFIG_PATH` and `OUTPUT_DIR`; the flags override them. Defaults are `profile.yml` and `assets/readme-kit`. Icons and logos are fetched live, so this needs network.

## Test

```
uv run --no-project --with pytest==9.1.1 --with pyyaml==6.0.3 pytest -v
uvx ruff@0.17.1 check .
```

- `tests/conftest.py` puts the repo root on `sys.path`, blocks `urllib.request.urlopen` for every test (autouse), and offers `downloads` / `offline` fixtures that replace `fetch.fetch_bytes` with canned bytes or a failure.
- `tests/test_cards.py` has one parametrized case per card type (XML validity plus escaping of `< > & "`); `test_every_card_type_has_a_case` fails when a card type is added without one.
- `.github/workflows/ci.yml`: `lint` (ruff, 3.13), `test` (3.12/3.13/3.14), and `action`, the only job that loads `action.yml`. It runs `uses: ./` on `profile.example.yml` with live downloads and asserts `files` == SVGs on disk + 1, every SVG parses, every button has its icon, a tile logo was inlined, and `ci-out/` holds the same card names as `examples/`.
- `ruff==0.17.1`, `pytest==9.1.1` and `pyyaml==6.0.3` are pinned inline in `run:` lines, which Renovate does not read. Bump by hand.
- No ruff config on purpose: the tree passes ruff 0.17's full default set (407 rules; 0.16 had 413), the same no-config approach as credly-badge-readme-action.

## Entry points

- `action.yml` -- inputs `config` and `output-dir` become env `CONFIG_PATH` and `OUTPUT_DIR`; output `files` maps to `steps.render.outputs.files`
- `readme_kit.py` -- the script the action runs; only imports `readme_kit.cli.main`
- `readme_kit/cli.py` -- arguments, load, render, write every card and `snippet.md`, append `files=N` to `$GITHUB_OUTPUT`

## Key files

- `readme_kit/config.py` -- `SECTIONS` is the whole schema; validation, text cleaning, file-key resolution
- `readme_kit/cards.py` -- one renderer per card type and the `render_all` dispatch
- `readme_kit/svg.py` -- palette (`Palette`, with the `theme.accent` derivation) and shared SVG primitives
- `readme_kit/fetch.py` -- the only network code: allowlist, https-only, size caps, image sniffing
- `profile.example.yml` -- every key documented, filled with Sagar's real data; renders `examples/`
- `examples/` -- the committed gallery the README shows

## Gotchas

- `readme_kit.py` and the `readme_kit/` package share a name on purpose: action.yml runs `readme_kit.py`. A package directory wins over a same-named module on the same `sys.path` entry, so `import readme_kit` always gets the package (checked on 2026-09-25). Never import from `readme_kit.py`.
- Re-render `examples/` whenever a card or `profile.example.yml` changes. The unit test and the CI job only compare file names, so a color or layout change with stale examples passes both.
- Validated sections are complete dicts: `Fields.check` fills every missing optional key (`None`, `[]` for lists, `False` for flags), so renderers index `cfg["key"]` directly. A new key goes into `SECTIONS` first.
- Adding a card type touches: `SECTIONS`, a renderer in `cards.py`, a `case` in `render_all`, a `CASES` entry in `tests/test_cards.py`, `profile.example.yml`, a re-render of `examples/`, and the README gallery and reference table.
- Composite outputs need both the `id: render` on the step that writes `$GITHUB_OUTPUT` and the `value:` mapping in `action.yml`; either one missing makes `files` an empty string.
- `:all:` followed by a space is a YAML mapping error: quote the whole `run:` value (ci.yml) or use a block scalar (action.yml).
- ruff 0.17 defaults include BLE001 (no `except Exception`) and ISC004 (implicit string concatenation inside a list literal must be parenthesized). Most SVG fragments here are parenthesized for that reason.
- The user-level dash hook blocks any write containing a literal en or em dash, including source that has to match one. `config.py` builds them with `chr(0x2013)` and `chr(0x2014)`; an escape sequence in a string literal also passes, a literal character never does.
- Fed the same data, 26 of 33 cards matched render-svgs.py byte for byte on 2026-09-25. The rest differ only in `aria-label`, inlined logo bytes (render-svgs downsizes logos with Pillow) and a position-based shine delay. Diff against `brand/Sagargupta16/assets/svg/` when porting a design change either way.
- simple-icons is fetched at `@latest`, so a slug removed upstream becomes a warning and an icon-less button, not a failed run.
- The footer and divider are transparent; the footer's light text only reads on GitHub's dark theme (documented under Scope in the README).

## Repo-specific rules

- Runtime stays standard library plus PyYAML. `action.yml` installs nothing else, so any other import breaks every consumer.
- The PyYAML pin appears in `action.yml`, `ci.yml`, the README and this file. Bump all of them together.
- Every profile string goes through `config.clean` at validation and `html.escape` at interpolation. Keep both.
- Download only through `fetch.fetch_bytes`, which checks the allowlist before `urlopen`, refuses a redirect off https, and caps the size.

## Usage

- In a workflow: `uses: Sagargupta16/readme-kit-action@v1` with optional `config` and `output-dir`; the consumer's workflow commits `output-dir` itself (README Quick start).
- Standalone: `python readme_kit.py --config profile.yml --output-dir out` (needs PyYAML).

## Config

- Config file: `profile.yml`, YAML, read with `yaml.safe_load`.
- Schema: `SECTIONS` in `readme_kit/config.py`; documented in `profile.example.yml` and the README's Profile reference table.
