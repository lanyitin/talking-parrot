<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development (SDD). Specs live in `docs/openspec/specs/`, change proposals in `docs/openspec/changes/`.

## When to use `/spectra-*` skills

| Situation | Skill |
|-----------|-------|
| Discussion needs structure before coding | `/spectra-discuss` |
| Planning, proposing, or designing a change | `/spectra-propose` |
| Tasks are ready to implement | `/spectra-apply` |
| There's an in-progress change to continue | `/spectra-ingest` |
| Questions about specs or how something works | `/spectra-ask` |
| Implementation is done | `/spectra-archive` |
| Committing only files related to a specific change | `/spectra-commit` |

## Workflow

```
discuss? → propose → apply ⇄ ingest → archive
```

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Enter plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked (temporarily moved out of `openspec/changes/`). Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra-apply` and `/spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->

# Project Conventions

## Documentation

- All documents must be placed inside the `docs/` directory.
- `docs/` is an Obsidian Vault — use `obsidian` related tools to interact with it.

## TODO Tracking

- `@docs/TODOs.md` is the current TODO list for tracking project items and progress.
- Any newly discovered TODO items must be added to this file.
- The user may also add items to this list at any time.

## Environment & Tooling

- **Runtime**: Python ≥ 3.13, managed via [uv](https://github.com/astral-sh/uv)
- **Package manager**: `uv` — do NOT use `pip`, `pip3`, or bare `python` / `python3` / `pytest`

### Command Conventions

All commands must be run through `uv`. Direct invocations are prohibited.

| Do NOT use | Use instead |
|---|---|
| `python script.py` | `uv run python script.py` |
| `python -m module` | `uv run python -m module` |
| `pytest` | `uv run pytest` |
| `pip install <pkg>` | `uv add <pkg>` |
| `pip uninstall <pkg>` | `uv remove <pkg>` |

## Development Workflow

### 1. Starting a new feature

```bash
git checkout -b feature/<short-description>
uv sync          # sync dependencies from lockfile
```

### 2. During development

```bash
uv run pytest --tb=short        # run tests (short traceback)
uv run ruff check .             # lint
uv run ruff format .            # format
```

### 3. Before every commit

All of the following must pass with zero errors:

```bash
uv run pytest                   # full test suite — 100% green
uv run ruff check .             # no lint errors
uv run ruff format --check .    # no unformatted files
```

## Code Style

- **Docstrings are mandatory** on every public module, class, and function/method. One-line docstrings are acceptable for simple cases. Never leave a public symbol without a docstring.
- Internal helpers (prefixed `_`) should have a docstring if the behaviour is non-obvious.

## Constraints & Prohibited Actions

- **Never** run `python`, `python3`, `pip`, or bare `pytest`; always go through `uv` / `uv run`.
- **Never** modify the `[build-system]` table in `pyproject.toml`.
- **Never** add a new dependency without explicit instruction.
- **Never** commit if any test is failing or any lint error exists.
- **Never** force-push to `main` or `develop`.

## TODOs

See @TODOs.md for more details.
