# alignment-stage Specification

## Purpose

TBD - created by archiving change 'implement-alignment-stage'. Update Purpose after archive.

## Requirements

### Requirement: AlignmentStage exposes name and constructor injection

The system SHALL provide `AlignmentStage(PipelineStage)` constructed with `(factory: AlignmentBackendFactory, audio_reader: AudioReader)`. Its `name` property SHALL return the literal string `"alignment"`. The stage MUST NOT mutate the input `PipelineContext`; it MUST return a new context via `dataclasses.replace`.

#### Scenario: Name property

- **GIVEN** an instantiated `AlignmentStage`
- **WHEN** `name` is read
- **THEN** the value MUST equal `"alignment"`


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: AlignmentStage disabled-path

When `ctx.config.align is None` OR `ctx.config.align.enabled is False`, `AlignmentStage.process(ctx)` SHALL return a new context with:
- `alignment_status = AlignmentStatus.DISABLED`
- `alignment_granularity = None`
- `alignment_results = []`
- `transcription_results` unchanged (each `aligned_tokens` stays as it was, including `None`)

The factory and audio reader MUST NOT be consulted in the disabled path.

#### Scenario: align config absent returns DISABLED

- **GIVEN** `ctx.config.align is None`
- **WHEN** `AlignmentStage.process(ctx)` is called
- **THEN** the returned context's `alignment_status` MUST equal `AlignmentStatus.DISABLED`
- **AND** `alignment_granularity` MUST be `None`
- **AND** `alignment_results` MUST equal `[]`

#### Scenario: align disabled flag returns DISABLED

- **GIVEN** `ctx.config.align.enabled == False`
- **WHEN** `AlignmentStage.process(ctx)` is called
- **THEN** the returned context's `alignment_status` MUST equal `AlignmentStatus.DISABLED`
- **AND** the factory's `create` method MUST NOT be invoked


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: AlignmentStage resolves a single backend per run

When alignment is enabled, `AlignmentStage.process(ctx)` SHALL:
1. Parse `granularity_pref = GranularityPreference(ctx.config.align.granularity.upper())`.
2. Resolve `backend = factory.create(ctx.config.expected_language, granularity_pref)` exactly once for the entire run (not per chunk).

If the factory raises `ValueError` for the language or granularity, the stage SHALL log a `WARNING` and return a new context with `alignment_status = AlignmentStatus.FAILED`, `alignment_granularity = None`, `alignment_results = []`, and `transcription_results` unchanged. The stage MUST NOT propagate the `ValueError`.

#### Scenario: Factory ValueError yields FAILED status

- **GIVEN** `ctx.config.expected_language = "fr"` and the factory raises `ValueError("No alignment backend for language: fr")`
- **WHEN** the stage runs
- **THEN** the returned context's `alignment_status` MUST equal `AlignmentStatus.FAILED`
- **AND** `alignment_granularity` MUST be `None`
- **AND** `alignment_results` MUST equal `[]`
- **AND** a `WARNING`-level log MUST have been emitted

#### Scenario: Granularity string parsed case-insensitively

- **GIVEN** `ctx.config.align.granularity = "auto"` (lowercase)
- **WHEN** the stage runs and resolves the preference
- **THEN** the factory MUST be called with `GranularityPreference.AUTO`


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: AlignmentStage aligns each chunk and shifts timestamps to absolute

For each `result` in `ctx.transcription_results`, the stage SHALL:
1. Read audio bytes via `audio_bytes = audio_reader.read(result.start_ms, result.end_ms)` (the segment's absolute time bounds, NOT the parent chunk's bounds).
2. Call `tokens = backend.align(audio_bytes, audio_reader.sample_rate, result.text)`.
3. Shift each returned token's `start_ms` and `end_ms` by adding `result.start_ms` (the backend returns audio-window-relative timestamps; the stage produces absolute timestamps).

The stage SHALL build the output list in the same order as `ctx.transcription_results`. `result.chunk_index` MAY still be used for diagnostic logging but MUST NOT be used to derive the audio range to read.

#### Scenario: Timestamps shifted by result start, not chunk start

- **GIVEN** a `TranscriptionResult` with `start_ms = 12_500`, `end_ms = 14_000` (its parent chunk has `start_ms=10_000, end_ms=20_000`) and a backend returning a single token with `start_ms=100, end_ms=500`
- **WHEN** the stage processes that result
- **THEN** the absolute token MUST have `start_ms = 12_600` and `end_ms = 13_000`
- **AND** the audio reader MUST have been called with `(12_500, 14_000)` (not `(10_000, 20_000)`)

#### Scenario: Multiple segments from one chunk aligned independently

- **GIVEN** two `TranscriptionResult` instances with the same `chunk_index` but `start_ms`/`end_ms` `(12_000, 13_000)` and `(13_500, 14_500)`
- **WHEN** the stage processes both
- **THEN** the audio reader MUST have been called twice with each segment's bounds, and each result's aligned tokens MUST be shifted by that result's `start_ms`


<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->

---
### Requirement: AlignmentStage applies bounded per-chunk fallback on backend exceptions

If `backend.align(...)` raises any exception while processing a single chunk, `AlignmentStage` SHALL:
1. Log a `WARNING` identifying the chunk index and exception type.
2. Treat that chunk's aligned tokens as `[]` (empty list).
3. Continue with the next chunk (no abort).

The whole-run `alignment_status` SHALL be `AlignmentStatus.SUCCESS` when at least one chunk produced a non-empty token list, and `AlignmentStatus.FAILED` when every chunk produced an empty token list (or when `ctx.transcription_results` is empty while alignment is enabled).

#### Scenario: One chunk fails, another succeeds → SUCCESS

- **GIVEN** two chunks where the backend raises `RuntimeError` for chunk 0 and returns a non-empty token list for chunk 1
- **WHEN** the stage runs
- **THEN** `alignment_status` MUST equal `AlignmentStatus.SUCCESS`
- **AND** `alignment_results[0].tokens` MUST equal `[]`
- **AND** `alignment_results[1].tokens` MUST be non-empty

#### Scenario: All chunks fail → FAILED

- **GIVEN** every chunk's backend call raises an exception
- **WHEN** the stage runs
- **THEN** `alignment_status` MUST equal `AlignmentStatus.FAILED`

#### Scenario: Empty transcription_results with alignment enabled → FAILED

- **GIVEN** `ctx.transcription_results == []` and alignment is enabled
- **WHEN** the stage runs
- **THEN** `alignment_status` MUST equal `AlignmentStatus.FAILED`
- **AND** `alignment_results` MUST equal `[]`


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: AlignmentStage writes aligned_tokens onto each TranscriptionResult

After successful alignment of a chunk, the stage SHALL emit a new `TranscriptionResult` (via `dataclasses.replace`) whose `aligned_tokens` is the absolute-timestamp `list[AlignedToken]` for that chunk. For chunks whose backend call raised, `aligned_tokens` SHALL be an empty list `[]`. The output `transcription_results` ordering MUST match the input ordering.

#### Scenario: aligned_tokens populated for every result

- **GIVEN** three transcription results and a backend that succeeds for all three chunks
- **WHEN** the stage runs
- **THEN** each `transcription_results[i].aligned_tokens` MUST be a non-empty list
- **AND** the output ordering MUST match input ordering


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: AlignmentStage records granularity from the backend

When alignment succeeds for at least one chunk (`alignment_status == SUCCESS`), the returned `ctx.alignment_granularity` SHALL equal `backend.granularity`. When `alignment_status` is `FAILED` or `DISABLED`, `alignment_granularity` MUST be `None`.

#### Scenario: SUCCESS records backend granularity

- **GIVEN** an English run that succeeds (`backend.granularity == AlignmentGranularity.WORD`)
- **WHEN** the stage runs
- **THEN** the returned `ctx.alignment_granularity` MUST equal `AlignmentGranularity.WORD`

#### Scenario: FAILED returns None granularity

- **GIVEN** a run where the factory raises `ValueError`
- **WHEN** the stage runs
- **THEN** the returned `ctx.alignment_granularity` MUST be `None`

<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->