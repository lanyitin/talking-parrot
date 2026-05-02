## 1. ExportConfig & PipelineConfig

- [x] 1.1 Add `ExportConfig` model in `src/talking_parrot/config/models.py` covering **ExportConfig declares format and output_path** (`format: Literal["srt", "webvtt"]`, `output_path: str`, `extra="forbid"`, `output_path_must_be_non_empty` validator) per **D6. `ExportConfig` placement on `PipelineConfig`**
- [x] 1.2 Add `export: Optional[ExportConfig] = None` field to `PipelineConfig` covering **PipelineConfig gains an optional export field**
- [x] 1.3 Write tests in `tests/unit/config/test_export_config.py` covering ExportConfig defaults, format Literal validation, empty `output_path` rejection, `extra="forbid"`, and PipelineConfig round-trip with and without `export`

## 2. SubtitleExporter ABC (TDD)

- [x] 2.1 Write failing tests in `tests/unit/io/subtitle_export/test_base.py` for **SubtitleExporter abstract base class** (direct `SubtitleExporter()` raises `TypeError`; minimal `_FakeExporter` subclass is constructible)
- [x] 2.2 Write failing tests for **SubtitleExporter writes UTF-8 with no BOM** (first byte of output file is not `0xEF`; non-ASCII text round-trips through `decode("utf-8")`) — exercised against a minimal concrete subclass
- [x] 2.3 Write failing tests for **SubtitleExporter writes atomically** per **D8. Exporters write atomically — write-then-rename** (patch the write step to raise after `.tmp` is created; assert `output_path` does not exist or is unchanged)
- [x] 2.4 Write failing tests for **SubtitleExporter handles empty subtitle input** (`exporter.export([], path)` returns `None` without raising and `path` exists)
- [x] 2.5 Implement `SubtitleExporter` ABC in `src/talking_parrot/io/subtitle_export/base.py` per **D4. `SubtitleExporter` is an ABC, not a Protocol** — `format_name` / `file_extension` abstract properties, abstract `export(subtitles, output_path)` method, and a shared `_atomic_write_text(path, text)` helper that performs the `.tmp` + `os.replace` dance

## 3. SRTExporter (TDD)

- [x] 3.1 Write failing tests in `tests/unit/io/subtitle_export/test_srt.py` for **SRTExporter exposes format_name and file_extension** (`"srt"` / `".srt"`)
- [x] 3.2 Write failing tests for **SRTExporter serializes cues using SubRip syntax** per **D2. SRT serialization rules** — including the exact two-cue byte string, multi-line text preservation, and hour-spanning timecode formatting per **D1. Timecode formatting is per-format, not shared**
- [x] 3.3 Write failing test for **SRTExporter emits a zero-byte file for empty input**
- [x] 3.4 Implement `SRTExporter` in `src/talking_parrot/io/subtitle_export/srt.py` (private `_format_timecode` using `,` separator, body builder, atomic write via base helper)

## 4. WebVTTExporter (TDD)

- [x] 4.1 Write failing tests in `tests/unit/io/subtitle_export/test_webvtt.py` for **WebVTTExporter exposes format_name and file_extension** (`"webvtt"` / `".vtt"`)
- [x] 4.2 Write failing tests for **WebVTTExporter writes the WEBVTT header followed by cues** per **D3. WebVTT serialization rules** — including the exact two-cue byte string with `WEBVTT\n\n` prefix and period decimal separator per **D1. Timecode formatting is per-format, not shared**
- [x] 4.3 Write failing test for **WebVTTExporter emits header-only file for empty input** (file content is exactly `"WEBVTT\n\n"`, 9 bytes)
- [x] 4.4 Implement `WebVTTExporter` in `src/talking_parrot/io/subtitle_export/webvtt.py` (private `_format_timecode` using `.` separator)

## 5. SubtitleExporterFactory (TDD)

- [x] 5.1 Write failing tests in `tests/unit/io/subtitle_export/test_factory.py` for **SubtitleExporterFactory.create returns the matching exporter** (covers both `"srt"` and `"webvtt"` mappings) per **D5. `SubtitleExporterFactory.create(format_name)` is a class method**
- [x] 5.2 Write failing test for **SubtitleExporterFactory rejects unknown formats** asserting the `ValueError` message contains the offending name and supported list per **D10. Factory rejects unknown formats with the exact value in the message**
- [x] 5.3 Write failing test for **SubtitleExporterFactory returns a fresh instance per call** (`a is not b` for two `create("srt")` calls)
- [x] 5.4 Implement `SubtitleExporterFactory` in `src/talking_parrot/io/subtitle_export/factory.py` with class-level `_REGISTRY: dict[str, type[SubtitleExporter]]` and `@classmethod create` raising `ValueError` for unknown keys
- [x] 5.5 Re-export `SubtitleExporter`, `SRTExporter`, `WebVTTExporter`, `SubtitleExporterFactory` from `src/talking_parrot/io/subtitle_export/__init__.py`

## 6. CLI End-to-End Wiring (TDD)

- [x] 6.1 Refactor `cli.main` so the stage-list construction is a separate testable helper `_build_stages(cfg)` returning `list[PipelineStage]`
- [x] 6.2 Write failing tests in `tests/unit/cli/test_cli_wiring.py` for **cli.py builds the full five-stage pipeline** (transcribing-only config produces `[TranscriptionStage, PostProcessingStage]`; full config produces all five stages in order)
- [x] 6.3 Write failing test for **cli.py invokes the subtitle exporter when export is configured** — patch `PipelineOrchestrator.run` to return a context with one subtitle, run `cli.main`, assert the SRT file exists with expected content AND the project-file JSON exists
- [x] 6.4 Write failing test for the second scenario of the same requirement: when the patched exporter raises `IOError`, the project-file JSON is still written before the exception propagates per **D7. CLI wiring sequence** (project-file write before export call) and **D9. The exporter is NOT a Stage**
- [x] 6.5 Write failing test for **cli.py is silent when export is not configured** (no subtitle file created, no warning emitted, project-file JSON written as before) covering **D9**
- [x] 6.6 Write failing test for **The exporter is not registered as a pipeline Stage** asserting no element of `_build_stages(cfg)` is a `SubtitleExporter` instance even when `cfg.export is not None`
- [x] 6.7 Implement the wiring in `cli.main`: call `_build_stages(cfg)`, run the orchestrator, write the `ProjectFile` JSON, then if `cfg.export is not None` call `SubtitleExporterFactory.create(cfg.export.format).export(ctx.subtitles, cfg.export.output_path)`

## 7. Verification

- [x] 7.1 Run `uv run pytest tests/unit/io/subtitle_export tests/unit/config/test_export_config.py tests/unit/cli` and ensure 100% pass
- [x] 7.2 Run `uv run ruff check .` and `uv run ruff format --check .` with zero errors
- [x] 7.3 Run full `uv run pytest` to confirm no regressions in upstream stages or existing CLI tests
