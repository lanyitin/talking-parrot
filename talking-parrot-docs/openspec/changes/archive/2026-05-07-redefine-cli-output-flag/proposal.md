## Why

Today, `talking-parrot --output <path>` writes the **project JSON** (recoverable state) while the **subtitle file** (the user-facing artifact) is silently controlled by `cfg.export.output_path` in YAML. Users running `talking-parrot --config c.yaml --output sample1.srt input.mp3` reasonably expect `sample1.srt` to be the SRT file, not the project JSON. The current behavior is surprising, undocumented in the flag's help text, and recently caused a confusing `FileNotFoundError` when the YAML-configured `output/` directory did not exist.

## What Changes

- **BREAKING**: `--output <path>` SHALL refer to the **subtitle output path** when `cfg.export` is set. It overrides `cfg.export.output_path`.
- Add a new `--project-json <path>` flag for the recoverable JSON file. When omitted, the path SHALL be derived from the subtitle output path by replacing the extension with `.json` (e.g. `sample1.srt` → `sample1.json`). When `cfg.export` is `None`, `--project-json` (or `--output` as a fallback) SHALL be required.
- When `cfg.export` is `None`, `--output` SHALL be treated as the project-JSON path (preserves the only useful interpretation in that mode and keeps single-flag invocations working).
- Update `--output` help text to describe the new semantics and document `--project-json`.
- The CLI SHALL fail fast with a clear error when `--output` is given a subtitle extension but `cfg.export` is `None`, or when extensions disagree with `cfg.export.format`.

## Non-Goals

- Auto-detecting subtitle format from the `--output` extension (format still comes from `cfg.export.format`; mismatch is an error, not silent coercion).
- Deprecation shim that preserves the old `--output = project JSON` behavior. The tool is pre-1.0 (`v0.1.0`); a clean break is preferred over a flag-renaming alias that would have to be removed later.
- Changing `cfg.export.output_path` semantics — the YAML field remains the default when `--output` is not given.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `pipeline-end-to-end-wiring`: CLI argument semantics for `--output` and the new `--project-json` flag, including the derivation rule and the validation behavior when `cfg.export` is absent.

## Impact

- Affected specs: `pipeline-end-to-end-wiring` (delta).
- Affected code:
  - Modified: `src/talking_parrot/cli.py`
  - Modified: `tests/test_cli.py` (if present) or new CLI tests covering the new flag semantics.
- User-visible: invocations that previously passed `--output project.json` continue to work only when `cfg.export` is `None`; invocations with `cfg.export` set now treat `--output` as the subtitle path. Users with both must update their command lines.
