# transcription-backend-factory Specification

## Purpose

TBD - created by archiving change 'implement-transcription-stage'. Update Purpose after archive.

## Requirements

### Requirement: TranscriptionBackendFactory creates backends by name

The system SHALL provide `TranscriptionBackendFactory` with an instance method `create(backend_name: str) -> TranscriptionBackend` that returns a `FasterWhisperBackend` for `"faster-whisper"` and a `MLXWhisperBackend` for `"mlx-whisper"`.

For any other `backend_name`, the method MUST raise `ValueError` whose message contains the substring `Unknown transcription backend`.

The factory SHALL cache backend instances by `backend_name` on the factory instance, so repeated `create()` calls with the same name return the same `TranscriptionBackend` object.

#### Scenario: Known names produce correct backend types

- **WHEN** `factory.create("faster-whisper")` is called
- **THEN** the returned object MUST be an instance of `FasterWhisperBackend`

- **WHEN** `factory.create("mlx-whisper")` is called on Apple Silicon macOS
- **THEN** the returned object MUST be an instance of `MLXWhisperBackend`

#### Scenario: Unknown name rejected

- **WHEN** `factory.create("openai-whisper")` is called
- **THEN** the call MUST raise `ValueError` whose message contains `"Unknown transcription backend"`

#### Scenario: Repeated calls return the same instance

- **WHEN** `factory.create("faster-whisper")` is called twice
- **THEN** both calls MUST return the same object (verified via `is` identity)


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
### Requirement: TRANSCRIPTION_BACKEND env var overrides backend name

When the environment variable `TRANSCRIPTION_BACKEND` is set to a non-empty value, `TranscriptionBackendFactory.create()` SHALL ignore its `backend_name` argument and use the env var's value instead. Validation rules (unknown name → `ValueError`) apply equally to env-var values.

#### Scenario: Env var overrides argument

- **GIVEN** `TRANSCRIPTION_BACKEND="faster-whisper"` is set in the environment
- **WHEN** `factory.create("mlx-whisper")` is called
- **THEN** the returned object MUST be an instance of `FasterWhisperBackend`

#### Scenario: Empty env var ignored

- **GIVEN** `TRANSCRIPTION_BACKEND=""` is set in the environment
- **WHEN** `factory.create("faster-whisper")` is called
- **THEN** the returned object MUST be an instance of `FasterWhisperBackend` (the empty value MUST be ignored)


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
### Requirement: TranscriptionBackendFactory exposes platform default

`TranscriptionBackendFactory` SHALL provide a class- or static-method `default_for_platform() -> str` that returns `"mlx-whisper"` when `sys.platform == "darwin"` AND `platform.machine() == "arm64"`, and otherwise returns `"faster-whisper"`.

#### Scenario: Platform default selection

| sys.platform | platform.machine() | Expected return value |
|--------------|--------------------|-----------------------|
| `"darwin"`   | `"arm64"`          | `"mlx-whisper"`       |
| `"darwin"`   | `"x86_64"`         | `"faster-whisper"`    |
| `"linux"`    | `"x86_64"`         | `"faster-whisper"`    |
| `"win32"`    | `"AMD64"`          | `"faster-whisper"`    |

- **WHEN** `TranscriptionBackendFactory.default_for_platform()` is called under each row's patched values
- **THEN** the return value MUST equal the row's expected value

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