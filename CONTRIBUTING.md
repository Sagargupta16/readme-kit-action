# Contributing to readme-kit-action

This repo is a composite GitHub Action that turns one `profile.yml` into a matching set of self-hosted, animated SVG cards for a GitHub profile README, plus a `snippet.md` with the markup. Bug reports, fixes, doc corrections and new options or card types that come with tests are welcome.

## Setup

The runtime is the Python standard library plus PyYAML 6.0.3. Locally everything runs through `uv`/`uvx`; CI uses pip with the same pins.

## Before you open a PR

CI (`.github/workflows/ci.yml`) runs three jobs on every push to `main` and every pull request:

- `lint`: `pip install --only-binary :all: ruff==0.17.1`, then `ruff check .` on Python 3.13
- `test`: `pip install --only-binary :all: pytest==9.1.1 pyyaml==6.0.3`, then `pytest -v` on Python 3.12, 3.13 and 3.14
- `action`: runs `action.yml` from the checkout on `profile.example.yml` with live downloads into `ci-out/`, then asserts the `files` output equals the SVGs on disk plus `snippet.md`, every SVG parses, every button has its icon, a tile logo was inlined, and `ci-out/` holds the same card names as `examples/`

Run the first two locally:

```bash
uv run --no-project --with pytest==9.1.1 --with pyyaml==6.0.3 pytest -v
uvx ruff@0.17.1 check .
```

After changing a card or `profile.example.yml`, re-render the gallery (this needs network for icons and logos) and commit the result:

```bash
uv run --no-project --with pyyaml==6.0.3 python readme_kit.py --config profile.example.yml --output-dir examples
```

The tests and the CI job compare only file names, so a color or layout change with a stale `examples/` passes both. Re-render anyway.

## Conventions

- Tests live in `tests/`. `tests/conftest.py` blocks `urllib.request.urlopen` for every test and provides `downloads` and `offline` fixtures, so tests never touch the network.
- `tests/test_cards.py` has one parametrized case per card type, and `test_every_card_type_has_a_case` fails when a card type has none.
- `SECTIONS` in `readme_kit/config.py` is the whole profile schema. A new key goes there first.
- A new card type touches: `SECTIONS`, a renderer in `readme_kit/cards.py`, a `case` in `render_all`, a `CASES` entry in `tests/test_cards.py`, `profile.example.yml`, a re-render of `examples/`, and the README gallery and Profile reference table.
- Composite outputs need `id: render` on the step that writes `$GITHUB_OUTPUT` and the `value:` mapping in `action.yml`.
- Runtime stays standard library plus PyYAML. `action.yml` installs nothing else, so any other import breaks every consumer.
- The PyYAML pin appears in `action.yml`, `ci.yml`, `README.md` and `CLAUDE.md`. Bump all of them together. Renovate does not read `run:` lines, so the `ruff` and `pytest` pins are bumped by hand too.
- Every profile string goes through `config.clean` at validation and `html.escape` at interpolation. Keep both.
- Download only through `fetch.fetch_bytes`, which checks the allowlist, refuses a redirect off https, and caps the size.
- Never import from `readme_kit.py`. It shares its name with the `readme_kit/` package on purpose, and only calls `readme_kit.cli.main`.
- No literal en or em dash characters in source or docs. `config.py` builds them with `chr()` where it must match one.
- There is no ruff config on purpose: the tree passes ruff's full default ruleset.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`).
- `CHANGELOG.md` follows Keep a Changelog and Semantic Versioning. Add your entry under a concrete next version, for example `## [1.0.1] - YYYY-MM-DD`.

## Security issues

Do not report vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md).

## License

This project is released under the MIT License (see [LICENSE](LICENSE)). By contributing, you agree that your contributions are licensed under it.
