## Why

Stage 6 of the pipeline — the subtitle-export step — is the only part of the documented architecture that has no implementation. Stages 1–5 already exist and produce a populated `ctx.subtitles: list[Subtitle]`, and `pipeline-overview.md` / `pipeline-module-interfaces.md` already pin the `SubtitleExporter` interface plus its two concrete implementations (`SRTExporter`, `WebVTTExporter`). Without them, the CLI cannot write a `.srt` or `.vtt` file — only the `ProjectFile` JSON — so an end-user run of `talking-parrot` produces no subtitles. This change closes that gap and wires the full pipeline end-to-end.

## What Changes

- Add a new `subtitle_export` subsystem under `src/talking_parrot/io/subtitle_export/` containing the `SubtitleExporter` ABC, two concrete exporters (`SRTExporter`, `WebVTTExporter`), and the `SubtitleExporterFactory`.
- Add an `ExportConfig` model under `src/talking_parrot/config/models.py` carrying `format: Literal["srt", "webvtt"]` and `output_path: str`. Wire it into `PipelineConfig` as an optional `export` field so existing YAML configs that omit it still load.
- Wire the full pipeline in `src/talking_parrot/cli.py`: build the six stages (VAD → Chunking → Transcription → Alignment → PostProcessing) and run them through `PipelineOrchestrator`, then — when `cfg.export is not None` — instantiate the chosen exporter via `SubtitleExporterFactory` and call `exporter.export(ctx.subtitles, cfg.export.output_path)`.
- The disabled path (`cfg.export is None`) MUST short-circuit cleanly: write only the `ProjectFile`, no subtitle file, no warning. Existing CLI behavior is preserved for callers that have not opted into export yet.
- The exporters MUST handle the empty-subtitle case: writing a zero-cue file (valid empty SRT = empty file; valid empty WebVTT = `"WEBVTT\n\n"`).

## Non-Goals

- This change does NOT add new subtitle formats beyond SRT and WebVTT (e.g. `.ass`, `.lrc`). The factory's enumerated `format` field is the OCP closure point — adding a new exporter is a separate change.
- This change does NOT modify the upstream stages (Stages 1–5) or any backend; it only consumes `ctx.subtitles`.
- This change does NOT introduce streaming / incremental export. Both exporters write the full file in one pass.
- This change does NOT add styling, positioning, or speaker-label features to either format. SRT cues are `index\nstart --> end\ntext` triples; WebVTT cues are the equivalent without the leading index. No `STYLE`, no `NOTE`, no cue identifiers.
- This change does NOT address character-encoding negotiation. Both exporters write UTF-8 with no BOM.
- This change does NOT change `ProjectFileWriter` or the `ProjectFile` JSON schema.

## Capabilities

### New Capabilities

- `subtitle-exporter`: The `SubtitleExporter` ABC contract — `format_name: str` and `file_extension: str` read-only properties, and `export(subtitles: list[Subtitle], output_path: str) -> None` which serializes the cues and writes UTF-8 to disk.
- `srt-exporter`: `SRTExporter` implementing the SubRip format — 1-based cue index, `HH:MM:SS,mmm --> HH:MM:SS,mmm` timecode, blank-line cue separator, trailing newline at EOF.
- `webvtt-exporter`: `WebVTTExporter` implementing the WebVTT format per W3C — file MUST start with the literal `WEBVTT` header followed by a blank line, then cues use `HH:MM:SS.mmm --> HH:MM:SS.mmm` (period decimal separator, no per-cue index).
- `subtitle-exporter-factory`: `SubtitleExporterFactory.create(format_name: str) -> SubtitleExporter` mapping `"srt"` and `"webvtt"` to the matching exporter, raising `ValueError` for any other string.
- `export-config`: The `ExportConfig` Pydantic model and its integration into `PipelineConfig` as an optional `export` field. Adds the `format` / `output_path` validators (format ∈ {"srt", "webvtt"}, `output_path` non-empty).
- `pipeline-end-to-end-wiring`: The CLI wiring change — `cli.py` constructs all six stages, runs the orchestrator, and (only when `cfg.export is not None`) invokes the factory + exporter on `ctx.subtitles`. Preserves the existing `ProjectFile` write path.

### Modified Capabilities

(none — existing pipeline foundation, pipeline config, and pipeline data-model specs are referenced read-only)

## Impact

- Affected specs: six new capability specs listed above.
- Affected code:
  - New:
    - src/talking_parrot/io/subtitle_export/__init__.py
    - src/talking_parrot/io/subtitle_export/base.py
    - src/talking_parrot/io/subtitle_export/srt.py
    - src/talking_parrot/io/subtitle_export/webvtt.py
    - src/talking_parrot/io/subtitle_export/factory.py
    - tests/unit/io/subtitle_export/__init__.py
    - tests/unit/io/subtitle_export/test_base.py
    - tests/unit/io/subtitle_export/test_srt.py
    - tests/unit/io/subtitle_export/test_webvtt.py
    - tests/unit/io/subtitle_export/test_factory.py
    - tests/unit/config/test_export_config.py
    - tests/unit/cli/__init__.py
    - tests/unit/cli/test_cli_wiring.py
  - Modified:
    - src/talking_parrot/config/models.py (additive `ExportConfig` model + optional `export` field on `PipelineConfig`)
    - src/talking_parrot/cli.py (build six stages, run orchestrator, invoke exporter)
  - Removed: (none)
- Dependencies: no new third-party dependencies. Standard-library `pathlib` for path handling, stdlib `logging` for diagnostics.
