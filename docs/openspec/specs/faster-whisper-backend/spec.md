# faster-whisper-backend Specification

## Purpose

TBD - created by archiving change 'implement-transcription-stage'. Update Purpose after archive.

## Requirements

### Requirement: FasterWhisperBackend wraps faster_whisper.WhisperModel

The system SHALL provide `FasterWhisperBackend(TranscriptionBackend)` whose `name` property returns the literal string `"faster-whisper"` and whose `transcribe()` method drives `faster_whisper.WhisperModel.transcribe`.

The backend SHALL lazy-import `faster_whisper` on the first `transcribe()` call. If the import fails, the backend MUST raise `ImportError` whose message names the install extra `talking-parrot[faster-whisper]`.

The backend SHALL lazy-instantiate one `WhisperModel(model_size_or_path=model)` per distinct `model` argument and cache it on the instance. Library defaults SHALL be used for `device` and `compute_type`.

#### Scenario: Missing optional dependency raises actionable error

- **WHEN** `FasterWhisperBackend.transcribe()` is called and `faster_whisper` is not importable
- **THEN** the call MUST raise `ImportError` whose message contains the substring `talking-parrot[faster-whisper]`

#### Scenario: Models cached per name

- **GIVEN** `faster_whisper.WhisperModel` is mocked
- **WHEN** `transcribe()` is called twice with `model="base"` and once with `model="large-v3"`
- **THEN** `WhisperModel` MUST have been constructed exactly twice — once with `"base"` and once with `"large-v3"`


<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->

---
### Requirement: FasterWhisperBackend uses clip_timestamps for chunk window

`FasterWhisperBackend.transcribe()` SHALL pass the chunk window to the library via `clip_timestamps=[chunk.start_ms / 1000, chunk.end_ms / 1000]` and SHALL pass `language=language` (which may be `None`, in which case the library auto-detects).

#### Scenario: Chunk window passed to library

- **GIVEN** a chunk with `start_ms=5000`, `end_ms=15000` and a mocked `WhisperModel`
- **WHEN** the backend calls `model.transcribe()`
- **THEN** the `clip_timestamps` keyword argument MUST equal `[5.0, 15.0]`


<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->

---
### Requirement: FasterWhisperBackend assembles TranscriptionResult per the backend contract

`FasterWhisperBackend.transcribe()` SHALL consume the segment iterator returned by `WhisperModel.transcribe` and emit one `TranscriptionResult` per yielded segment, in iteration order, satisfying the segment-level rules declared in `transcription-backend`.

For each yielded segment:

- The result's `text` SHALL equal the segment's `text` after `str.strip()` (no cross-segment joining).
- The result's `metrics` SHALL be populated with the segment's raw `avg_logprob`, `compression_ratio`, `no_speech_prob`, plus a locally-computed `repetition_ratio` derived from the segment's stripped text.
- The result's `start_ms` and `end_ms` SHALL be `chunk.start_ms + int(round(segment.start * 1000))` and `chunk.start_ms + int(round(segment.end * 1000))` respectively.

The backend SHALL set every result's `language` to the value from the `info` object returned by `WhisperModel.transcribe` (the second return value), preferring it over the supplied `language` argument so that auto-detection is preserved when `language=None`.

#### Scenario: Auto-detected language surfaced on each result

- **GIVEN** `model.transcribe(...)` returns `(segments, info)` where `info.language == "ja"` and the iterator yields three segments
- **WHEN** `transcribe()` is called with `language=None`
- **THEN** every element of the returned list MUST have `language == "ja"`

#### Scenario: One result per yielded segment

- **GIVEN** the iterator yields two segments with texts `" hello"`, `" world "`
- **WHEN** `FasterWhisperBackend.transcribe()` runs
- **THEN** the returned list MUST have length 2 with `result[0].text == "hello"` and `result[1].text == "world"`

##### Example: empty-iterator return

- **GIVEN** `WhisperModel.transcribe` yields zero segments for the chunk
- **WHEN** `transcribe()` returns
- **THEN** the returned list MUST equal `[]`

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