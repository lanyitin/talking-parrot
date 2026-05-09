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
- `backend: str` — identifier of the producing backend; for real backends this MUST equal the backend's `name` attribute (e.g., `"silero_vad"`, `"ten_vad"`); the literal string `"composite"` is reserved for the unified composite timeline emitted by `VADStage`; the literal string `"unknown"` is reserved for frames loaded from legacy `.tp` files that predate this field.

All three fields are required at construction. `backend` MUST be a non-empty string.

#### Scenario: RawVadFrame cannot be mutated after construction

- **WHEN** a `RawVadFrame` is constructed with `time_ms=0, prob=0.5, backend="silero_vad"`
- **THEN** attempting to assign to any field raises `FrozenInstanceError`

#### Scenario: RawVadFrame requires a backend tag at construction

- **WHEN** code constructs `RawVadFrame(time_ms=0, prob=0.5)` without supplying `backend`
- **THEN** the call raises `TypeError`

##### Example: valid frame construction

| time_ms | prob | backend       | Valid? |
|---------|------|---------------|--------|
| 0       | 0.0  | "silero_vad"  | Yes    |
| 160     | 0.95 | "ten_vad"     | Yes    |
| 320     | 1.0  | "composite"   | Yes    |
| 480     | 0.5  | "unknown"     | Yes    |
| 0       | 0.5  | ""            | No (empty backend) |

<!-- @trace
source: vad-frames-per-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/cli.py
  - src/talking_parrot/models/context.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - src/talking_parrot/gui/__init__.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - src/talking_parrot/gui/static/index.html
  - src/talking_parrot/gui/cli.py
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/gui/api.py
  - tests/unit/shared/__init__.py
  - docs/TODOs.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/shared/__init__.py
tests:
  - tests/unit/gui/test_cli.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/gui/test_api.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/gui/test_dependency_direction.py
  - tests/unit/shared/test_public_api.py
-->