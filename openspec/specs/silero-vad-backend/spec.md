# silero-vad-backend Specification

## Purpose

TBD - created by archiving change 'implement-vad-stage'. Update Purpose after archive.

## Requirements

### Requirement: SileroVADBackend wraps silero_vad and returns per-frame probabilities

The system SHALL provide `SileroVADBackend` implementing `VADBackend` with:
- `name` property returning `"silero_vad"`
- Constructor accepting `chunk_size: int = 512`
- `analyze()` splitting audio into chunks of `chunk_size` samples, calling the Silero model on each chunk, and returning one `RawVadFrame` per chunk

The Silero model SHALL be lazy-loaded via `silero_vad.load_silero_vad()` on the first `analyze()` call and cached for subsequent calls.

#### Scenario: analyze returns one frame per chunk

- **WHEN** `analyze()` is called with audio of N samples
- **THEN** it returns `floor(N / chunk_size)` frames

##### Example: frame count for common audio lengths

| audio samples | chunk_size | expected frame count |
|---------------|------------|----------------------|
| 512           | 512        | 1                    |
| 1024          | 512        | 2                    |
| 1500          | 512        | 2                    |
| 16000         | 512        | 31                   |

#### Scenario: frame time_ms matches chunk position

- **WHEN** `analyze()` is called with `chunk_size=512` and `sample_rate=16000`
- **THEN** the frame at index `i` has `time_ms = i * 512 / 16000 * 1000 = i * 32`

##### Example: time_ms for first four frames

| frame index | chunk_size | sample_rate | expected time_ms |
|-------------|------------|-------------|-----------------|
| 0           | 512        | 16000       | 0               |
| 1           | 512        | 16000       | 32              |
| 2           | 512        | 16000       | 64              |
| 3           | 512        | 16000       | 96              |

#### Scenario: prob reflects Silero model output

- **WHEN** the Silero model returns probability `0.72` for a chunk
- **THEN** the corresponding `RawVadFrame.prob` equals `0.72`

<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->