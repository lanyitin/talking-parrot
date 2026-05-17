## 1. CLI argument parsing

- [x] 1.1 In `src/talking_parrot/cli.py`, replace the existing `--output` argparse definition so it is no longer marked `required=True` and update its help text to describe extension-aware semantics: subtitle path when `cfg.export` is set, project-JSON path otherwise. Implements the "cli.py accepts --output and --project-json with extension-aware semantics" requirement.
- [x] 1.2 Add a new `--project-json <path>` argparse flag (optional) to `cli.main` with help text describing the derivation rule (replace the resolved subtitle path's extension with `.json`).

## 2. Path resolution and validation

- [x] 2.1 Implement a small helper inside `cli.py` (e.g. `_resolve_output_paths(cfg, args)`) that returns a `(subtitle_path | None, project_json_path)` tuple following the rules in the "cli.py accepts --output and --project-json with extension-aware semantics" requirement, including the path-resolution table.
- [x] 2.2 In the helper, raise `SystemExit` (via `parser.error(...)`) with a clear message when `cfg.export is None` and `--output` is omitted.
- [x] 2.3 In the helper, raise `SystemExit` when `cfg.export is not None` and the resolved subtitle extension does not match `cfg.export.format` (`srt` ↔ `.srt`, `webvtt` ↔ `.vtt`); the format is NOT inferred from the extension.

## 3. Wire resolved paths into the pipeline

- [x] 3.1 [P] Update `cli.main` so `ProjectFileWriter.write(project_file, <resolved project_json_path>)` uses the resolved JSON path returned by the helper. Keep the "write project file before exporter" ordering required by the unchanged D7 ordering note in the "cli.py invokes the subtitle exporter when export is configured" requirement.
- [x] 3.2 [P] Update `cli.main` so `exporter.export(ctx.subtitles, <resolved subtitle_path>)` uses the resolved subtitle path (override) instead of `cfg.export.output_path`, fulfilling the "cli.py invokes the subtitle exporter when export is configured" requirement.
- [x] 3.3 Verify (by inspection) that when `cfg.export is None` no subtitle exporter is instantiated and no warning is emitted, preserving the "cli.py is silent when export is not configured" requirement.

## 4. Tests

- [x] 4.1 [P] Add a CLI test in `tests/unit/cli/test_cli_wiring.py` (or a new sibling file) covering: `--output` with export configured writes the subtitle to the CLI path and derives the JSON path with `.json` extension.
- [x] 4.2 [P] Add a CLI test covering: `--output` plus `--project-json` writes both files at the supplied paths.
- [x] 4.3 [P] Add a CLI test covering: `cfg.export is None` requires `--output`; supplying it writes the project JSON only and creates no subtitle file ("cli.py is silent when export is not configured").
- [x] 4.4 [P] Add a CLI test covering: extension/format mismatch (`--output sample.vtt` with `format=srt`) exits non-zero before the pipeline runs, and no files are written.
- [x] 4.5 [P] Add a CLI test covering: with `--output` supplied, `cfg.export.output_path` from YAML is NOT written ("cli.py invokes the subtitle exporter when export is configured" override scenario).

## 5. Docs

- [x] 5.1 Update `config.example.yaml` and any README/usage docs that show `--output` to reflect the new semantics. If `docs/TODOs.md` lists this as an item, mark it.
- [x] 5.2 Verify `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .` all pass.
