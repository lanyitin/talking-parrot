## Context

Stages 1–5 of the pipeline are implemented and produce a `PipelineContext` whose `subtitles: list[Subtitle]` field holds the final cue stream after `PostProcessingStage`. `Subtitle` is a `frozen=True` dataclass with fields `(index: int, start_ms: int, end_ms: int, text: str)`. `pipeline-overview.md` and `pipeline-module-interfaces.md` already pin the `SubtitleExporter` interface (`format_name`, `file_extension`, `export(subtitles, output_path) -> None`) and the two concrete classes (`SRTExporter`, `WebVTTExporter`). What those documents do NOT pin is (a) the exact byte-level serialization rules each exporter follows, (b) the factory's input validation surface, (c) how `ExportConfig` should attach to `PipelineConfig`, and (d) the order of operations in `cli.py` once both `ProjectFileWriter` and an exporter are present. This document fills those gaps.

`ProjectFileWriter` already lives at `src/talking_parrot/io/project_writer.py`, so the existing `io/` package is the correct home for the new `subtitle_export/` subpackage. The CLI currently runs `PipelineOrchestrator([])` (empty stage list) and then writes the project file — Stage wiring has been deferred until every stage existed. With Stage 5 done, that wait is over.

## Goals / Non-Goals

**Goals:**

- Define byte-exact serialization rules so two implementers would produce identical files for the same input.
- Define a single `SubtitleExporter` interface that both concrete exporters implement identically, so the factory and the CLI can select between them via duck-typed substitution.
- Define `ExportConfig` so that existing YAML configs (which omit `export`) continue to load — the field is optional with no default.
- Wire the CLI end-to-end so `talking-parrot --config X --output project.json input.mp4` produces both the project JSON and (when `export` is configured) the subtitle file in one run.
- Honor a "no opt-in, no side effect" rule: when `cfg.export is None`, no subtitle file is written and no warning is emitted.

**Non-Goals:**

- Streaming / chunked export. Both exporters buffer the full string and write once.
- Format autodetection from `output_path` extension. `format` is explicit in config; `output_path` is taken as-is and NOT validated against `file_extension`.
- BOM, alternate encodings, or charset negotiation. UTF-8 with no BOM, full stop.
- Cue styling, positioning, voices, regions, or any WebVTT/SRT extension feature.
- Adding a `subtitle-export` Stage to the orchestrator. The exporter runs in `cli.py` after `orchestrator.run`, because exporting is an output concern (parallel to `ProjectFileWriter`), not a transformation that the next Stage depends on.

## Decisions

### D1. Timecode formatting is per-format, not shared

Rejected alternative: a single `_format_timecode(ms)` helper used by both exporters. Reason: SRT uses `HH:MM:SS,mmm` (comma decimal); WebVTT uses `HH:MM:SS.mmm` (period decimal). Sharing a helper would force a `separator` argument that immediately leaks the format-specific knowledge it was meant to hide. Each exporter owns its own private `_format_timecode` method.

Decision: both methods compute hours / minutes / seconds / millis from `ms` via integer division (`hours = ms // 3_600_000`, etc.) and produce zero-padded segments. Inputs are non-negative `int` (already guaranteed by `Subtitle.start_ms / end_ms` upstream); no negative-value handling.

### D2. SRT serialization rules

For each `Subtitle s` in input order:

```
{s.index}
{HH:MM:SS,mmm of s.start_ms} --> {HH:MM:SS,mmm of s.end_ms}
{s.text}
                                          ← blank line between cues
```

The file ends with a single trailing `\n` after the last cue's text — i.e. the last cue's text line is terminated, but there is no extra blank line at EOF. Line endings are `\n` (LF), never `\r\n`. The text field is written verbatim — no escaping, no whitespace trimming. If `s.text` already contains internal `\n`, those line breaks are preserved (multi-line cues are valid SRT).

Empty input (`subtitles == []`) writes a zero-byte file. Rationale: the SRT specification is silent on empty files, and `srt`-parsing libraries accept zero bytes as "no cues". Emitting a placeholder header would be wrong because SRT has none.

### D3. WebVTT serialization rules

The file MUST begin with the literal four-byte sequence `WEBVTT\n\n` (header + blank line). For each `Subtitle s`:

```
{HH:MM:SS.mmm of s.start_ms} --> {HH:MM:SS.mmm of s.end_ms}
{s.text}
                                          ← blank line between cues
```

No per-cue index is written (WebVTT does not require one and we are not assigning cue identifiers). The file ends with a single trailing `\n` after the last cue's text. Line endings are `\n`.

Empty input writes exactly `"WEBVTT\n\n"` and stops. Rationale: the W3C WebVTT spec mandates the header even when no cues follow; a zero-byte file is invalid.

### D4. `SubtitleExporter` is an ABC, not a Protocol

Rejected alternative: a `typing.Protocol` with `format_name`, `file_extension`, and `export`. Reason: the rest of the project (alignment, transcription, VAD, post-processing) standardizes on `abc.ABC` for backend-style contracts; introducing a `Protocol` here would be inconsistent.

Decision: `SubtitleExporter(abc.ABC)` declares two abstract `@property` methods (`format_name`, `file_extension`) and one abstract method (`export`). Concrete classes override the properties with simple string returns and implement `export`. Direct instantiation of the ABC raises `TypeError` (Python's default behavior for abstract classes).

### D5. `SubtitleExporterFactory.create(format_name)` is a class method

Rejected alternative: a free function `make_exporter(name)`. Reason: the project's other factories (`AlignmentBackendFactory`, `TranscriptionBackendFactory`) are classes with a `create` method; consistency.

Decision: `class SubtitleExporterFactory` exposes `@classmethod create(cls, format_name: str) -> SubtitleExporter`. Mapping is a class-level `dict[str, type[SubtitleExporter]]` so the OCP closure point is a single edit. Unknown format raises `ValueError` whose message contains the offending input.

### D6. `ExportConfig` placement on `PipelineConfig`

`ExportConfig` is added at module level next to `PostProcessingConfig` in `src/talking_parrot/config/models.py`:

```python
class ExportConfig(BaseModel):
    model_config = {"extra": "forbid"}

    format: Literal["srt", "webvtt"]
    output_path: str

    @field_validator("output_path")
    @classmethod
    def output_path_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("output_path must be non-empty")
        return v
```

`PipelineConfig` gains `export: Optional[ExportConfig] = None`. The default `None` preserves backwards compatibility with all existing YAML files. `model_config = {"extra": "forbid"}` on `PipelineConfig` already means a typo like `exprt:` raises a clear validation error.

### D7. CLI wiring sequence

In `cli.py`, after `cfg = ConfigLoader.load(args.config)` and before any pipeline run, the CLI builds the stage list explicitly using the existing factory / backend constructors. Order:

1. `VadStage` — only if `cfg.vad is not None`.
2. `ChunkingStage` — only if `cfg.chunking is not None`.
3. `TranscriptionStage` — always (transcribing is required by `PipelineConfig`).
4. `AlignmentStage` — only if `cfg.align is not None`.
5. `PostProcessingStage` — always (Stage 5 has its own internal disabled-path; constructing it is cheap and keeps the stage list uniform).

The orchestrator is then invoked with this list. After it returns, the CLI:

6. Always writes the `ProjectFile` JSON (existing behavior).
7. If `cfg.export is not None`, calls `SubtitleExporterFactory.create(cfg.export.format).export(ctx.subtitles, cfg.export.output_path)`.

Step 6 runs even when step 7 raises — i.e. exporting is best-effort and never blocks the project-file output. Rationale: the `ProjectFile` is the recoverable artifact; if the exporter dies on disk-full, the user can re-run export from the JSON without re-running the whole pipeline.

### D8. Exporters write atomically — write-then-rename

To avoid leaving a half-written subtitle file on partial failure (e.g. `KeyboardInterrupt` mid-write), each exporter writes to `output_path + ".tmp"` first, `flush()`/`fsync()`, then `os.replace(tmp, output_path)`. Rejected alternative: write directly to `output_path`. Reason: pipeline runs are long; an interrupt during the final write would leave callers consuming a truncated `.srt` and not realize it.

### D9. The exporter is NOT a Stage

Rejected alternative: introduce a `SubtitleExportStage` and add it to the orchestrator's stage list. Reason: a Stage's contract is `process(ctx) -> ctx` — pure transformation. An exporter has a side effect (file I/O) and produces no new context state. Modeling it as a Stage would either (a) require `ctx` to gain a `subtitle_output_paths` field that nothing else reads, or (b) lie about purity. Keeping it parallel to `ProjectFileWriter` (called directly by `cli.py`) preserves the orchestrator's semantic discipline.

### D10. Factory rejects unknown formats with the exact value in the message

`SubtitleExporterFactory.create("ssa")` raises `ValueError("SubtitleExporterFactory: unsupported format 'ssa'. Supported: ['srt', 'webvtt'].")`. The message includes both the offending value and the supported set so a misconfigured YAML produces an actionable error at startup, not a silent fallback.

## Risks / Trade-offs

- **D2's "verbatim text" rule** means that `Subtitle.text` containing a stray `-->` substring would produce an SRT file that some parsers reject (the `-->` is also the timecode separator). Mitigation: Stage 5 already does not insert `-->`, and upstream transcription/alignment models do not produce it. If this surfaces in regression tests, escape `-->` to `→` in a follow-up change rather than adding general escaping logic now.
- **D3's empty-WebVTT rule** writes a 9-byte file. Some downstream players may treat a header-only file as malformed; this is a spec-conformant edge case. If users complain, we can revisit (but the current behavior is correct per W3C).
- **D7's "always include `PostProcessingStage`" rule** creates an extra factory-instantiation cost on every run. The cost is negligible (one ABC subclass + a list of two `[Merge, Split]` instances), and uniform stage construction simplifies testing. Trade-off accepted.
- **D8's atomic-rename** depends on `output_path` and `output_path + ".tmp"` being on the same filesystem. On Windows this is the same volume; on POSIX it is the same mount point. If a user configures `output_path` across mounts (rare), the `os.replace` falls back to copy-and-delete, which is still atomic from the reader's perspective on POSIX. Acceptable risk.
- **D9's "not a Stage" rule** means orchestrator integration tests for the export path live in CLI tests, not stage tests. This forces the new `tests/unit/cli/test_cli_wiring.py` to exist; without it the wiring is uncovered. Mitigated by including that file in this change.
- **D5's `dict`-based factory map** is closed at import time. Adding a third format requires editing both the map and the `ExportConfig` `Literal` — two edits, but they are co-located and any mismatch is caught immediately by the `ValueError` in `create`.
