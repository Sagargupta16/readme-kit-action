"""readme-kit entry point: python readme_kit.py [--config profile.yml] [--output-dir assets/readme-kit].

The readme_kit/ package next to this file holds the code; a package wins over a
same-named module on import, so `import readme_kit` always resolves to it.
"""

from readme_kit.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
