# vad-backend Specification

## Purpose

TBD - created by archiving change 'implement-vad-stage'. Update Purpose after archive.

## Requirements

### Requirement: VADBackend interface defines the contract for all VAD backends

The system SHALL define a `VADBackend` abstract base class with two abstract members:
- `name: str` (read-only property) — unique identifier for the backend, used as the formula variable prefix
- `analyze(audio_data: bytes, sample_rate: int) -> List[RawVadFrame]` — analyses the full audio and returns per-frame speech probabilities

All concrete VAD backends SHALL inherit from `VADBackend` and implement both members.

#### Scenario: Backend returns per-frame probabilities for non-silent audio

- **WHEN** `analyze()` is called with PCM audio containing speech
- **THEN** it returns a non-empty `List[RawVadFrame]` where each frame has `time_ms >= 0` and `prob` in `[0.0, 1.0]`

#### Scenario: Backend returns frames in chronological order

- **WHEN** `analyze()` is called with any audio
- **THEN** the returned frames are sorted by ascending `time_ms`


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

---
### Requirement: RawVadFrame is an immutable value object

The system SHALL provide a `RawVadFrame` frozen dataclass with:
- `time_ms: int` — start time of the frame in milliseconds
- `prob: float` — speech probability in range `[0.0, 1.0]`

#### Scenario: RawVadFrame cannot be mutated after construction

- **WHEN** a `RawVadFrame` is constructed
- **THEN** attempting to assign to any field raises `FrozenInstanceError`

##### Example: valid frame construction

| time_ms | prob | Valid? |
|---------|------|--------|
| 0       | 0.0  | Yes    |
| 160     | 0.95 | Yes    |
| 320     | 1.0  | Yes    |

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