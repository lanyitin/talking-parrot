## ADDED Requirements

### Requirement: TranscribingStep.backend is optional with platform-aware default

`TranscribingStep.backend` SHALL be an optional field. YAML that omits `backend:` from any transcribing step MUST be accepted by `ConfigLoader.load()` without raising `pydantic.ValidationError`.

When `backend` is omitted (or explicitly `null`) for a step, `ConfigLoader.load()` SHALL resolve the field to the value returned by `TranscriptionBackendFactory.default_for_platform()` before returning the `PipelineConfig`. After loading, every `TranscribingStep.backend` in the returned config MUST be a non-empty `str` so that downstream consumers (e.g., `TranscriptionStage`, `TranscriptionBackendFactory.create`) continue to receive a concrete backend name.

When `backend` is provided as a non-empty string, `ConfigLoader.load()` MUST preserve that explicit value unchanged. The platform default MUST NOT override an explicit value.

The runtime `TRANSCRIPTION_BACKEND` environment variable continues to be honoured by `TranscriptionBackendFactory.create()` and is out of scope for this loader-level resolution.

#### Scenario: Omitted backend resolves to platform default

- **WHEN** YAML defines a transcribing step with `condition: "true"`, no `backend:` key, and `model: large-v3`
- **THEN** `ConfigLoader.load()` MUST return a `PipelineConfig` whose corresponding `transcribing[i].backend` equals `TranscriptionBackendFactory.default_for_platform()`

##### Example: platform resolution table

| `sys.platform` | `platform.machine()` | Resolved `transcribing[0].backend` |
| -------------- | -------------------- | ---------------------------------- |
| `darwin`       | `arm64`              | `mlx-whisper`                      |
| `darwin`       | `x86_64`             | `faster-whisper`                   |
| `linux`        | `x86_64`             | `faster-whisper`                   |
| `win32`        | `AMD64`              | `faster-whisper`                   |

#### Scenario: Explicit backend value preserved

- **WHEN** YAML defines a transcribing step with explicit `backend: faster-whisper` while running on Apple Silicon macOS
- **THEN** `ConfigLoader.load()` MUST return a `PipelineConfig` whose `transcribing[i].backend` equals `"faster-whisper"` (the platform default MUST NOT override the explicit value)

#### Scenario: Null backend resolves to platform default

- **WHEN** YAML defines a transcribing step with `backend: null`
- **THEN** `ConfigLoader.load()` MUST treat the field as omitted and resolve it to `TranscriptionBackendFactory.default_for_platform()`

#### Scenario: Mixed cascade with one omitted backend

- **WHEN** YAML defines two transcribing steps where step 0 omits `backend:` and step 1 specifies `backend: whisper`
- **THEN** `ConfigLoader.load()` MUST resolve step 0 to `TranscriptionBackendFactory.default_for_platform()` and MUST preserve step 1 as `"whisper"` (which `TranscriptionBackendFactory.create()` may later reject at runtime if unknown — that validation is unchanged by this requirement)
