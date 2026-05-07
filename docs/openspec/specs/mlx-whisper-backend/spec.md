# mlx-whisper-backend Specification

## Purpose

TBD - created by archiving change 'implement-transcription-stage'. Update Purpose after archive.

## Requirements

### Requirement: MLXWhisperBackend wraps mlx_whisper.transcribe

The system SHALL provide `MLXWhisperBackend(TranscriptionBackend)` whose `name` property returns the literal string `"mlx-whisper"` and whose `transcribe()` method drives `mlx_whisper.transcribe`.

The backend SHALL lazy-import `mlx_whisper` on the first `transcribe()` call. If the import fails, the backend MUST raise `ImportError` whose message names the install extra `talking-parrot[mlx]`.

#### Scenario: Missing optional dependency raises actionable error

- **WHEN** `MLXWhisperBackend.transcribe()` is called and `mlx_whisper` is not importable
- **THEN** the call MUST raise `ImportError` whose message contains the substring `talking-parrot[mlx]`


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
### Requirement: MLXWhisperBackend enforces Apple Silicon macOS at construction

`MLXWhisperBackend.__init__` SHALL inspect `sys.platform` and `platform.machine()`. If `sys.platform != "darwin"` OR `platform.machine() != "arm64"`, the constructor MUST raise `RuntimeError` whose message contains the substring `Apple Silicon macOS`.

#### Scenario: Linux instantiation rejected

- **GIVEN** `sys.platform` is patched to `"linux"`
- **WHEN** `MLXWhisperBackend()` is invoked
- **THEN** the call MUST raise `RuntimeError` containing `"Apple Silicon macOS"`

#### Scenario: Intel macOS instantiation rejected

- **GIVEN** `sys.platform == "darwin"` and `platform.machine()` is patched to `"x86_64"`
- **WHEN** `MLXWhisperBackend()` is invoked
- **THEN** the call MUST raise `RuntimeError` containing `"Apple Silicon macOS"`


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
### Requirement: MLXWhisperBackend decodes chunk window via audio-io

`MLXWhisperBackend.transcribe()` SHALL load the source audio file, extract the float32 sample window covering `[chunk.start_ms, chunk.end_ms]` using the project's `audio-io` helpers, and pass that numpy array to `mlx_whisper.transcribe(audio_array, path_or_hf_repo=model, language=language)`.

The backend SHALL pass the supplied `model` string verbatim to `path_or_hf_repo` without rewriting (so e.g. `"large-v3"` is forwarded as-is and any HF-repo translation is the caller's responsibility).

#### Scenario: Chunk window forwarded as numpy array

- **GIVEN** a chunk with `start_ms=2000`, `end_ms=4000` and a mocked `mlx_whisper.transcribe`
- **WHEN** `transcribe()` is called
- **THEN** `mlx_whisper.transcribe` MUST be called with a numpy array whose length equals `(4000 - 2000) * sample_rate / 1000` samples
- **AND** the `path_or_hf_repo` keyword MUST equal the `model` argument unchanged


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
### Requirement: MLXWhisperBackend assembles TranscriptionResult per the backend contract

`MLXWhisperBackend.transcribe()` SHALL iterate the `segments` field of the value returned by `mlx_whisper.transcribe` and emit one `TranscriptionResult` per element, in iteration order, satisfying the segment-level rules declared in `transcription-backend`.

For each segment dict:

- The result's `text` SHALL equal the segment's `text` after `str.strip()` (no cross-segment joining).
- The result's `metrics` SHALL be populated with the segment's raw `avg_logprob`, `compression_ratio`, `no_speech_prob`, plus a locally-computed `repetition_ratio` derived from the segment's stripped text.
- The result's `start_ms` and `end_ms` SHALL be `chunk.start_ms + int(round(segment["start"] * 1000))` and `chunk.start_ms + int(round(segment["end"] * 1000))` respectively.

The backend SHALL set every result's `language` to the `language` field of the returned dict when present, otherwise to the supplied `language` argument.

#### Scenario: Library-provided language surfaced on each result

- **GIVEN** `mlx_whisper.transcribe(...)` returns a dict with `language="en"` and three segments
- **WHEN** `transcribe()` is called with `language=None`
- **THEN** every element of the returned list MUST have `language == "en"`

#### Scenario: One result per segment dict

- **GIVEN** the returned dict contains two segments with texts `" hello"`, `" world "`
- **WHEN** `MLXWhisperBackend.transcribe()` runs
- **THEN** the returned list MUST have length 2 with `result[0].text == "hello"` and `result[1].text == "world"`

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