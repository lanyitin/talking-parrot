## Why

`TranscribingStep.backend` is currently a required string field, which forces every config author (and `config.example.yaml`) to hard-code either `faster-whisper` or `mlx-whisper`. This defeats the intent of `TranscriptionBackendFactory.default_for_platform()`, which already knows the right default per platform (Apple Silicon macOS → `mlx-whisper`, otherwise → `faster-whisper`). Users on Apple Silicon today end up running `faster-whisper` because the example config writes that literal — even though MLX would be the better default on their machine.

## What Changes

- Make `TranscribingStep.backend` optional in `PipelineConfig`. Omitting the field MUST be valid YAML and MUST NOT raise `pydantic.ValidationError`.
- When the field is omitted (or explicitly `null`), `ConfigLoader.load()` SHALL resolve it to `TranscriptionBackendFactory.default_for_platform()` so that downstream code (`TranscriptionStage`, factory cache) continues to see a concrete backend name.
- When the field is provided, behavior is unchanged — the explicit value wins over the platform default. The existing `TRANSCRIPTION_BACKEND` env-var override at factory level is unaffected and continues to take precedence at runtime.
- Update `config.example.yaml` to omit `backend:` from the fallback (`condition: "true"`) step, demonstrating the new platform-default behavior. The cascade step that requires a specific backend (e.g., `condition: "avg_logprob < -1.0"`) keeps its explicit `backend:`.

## Non-Goals

- Not changing the env var override semantics in `TranscriptionBackendFactory.create()`.
- Not introducing platform detection elsewhere (VAD, alignment, post-processing) — scope is limited to `transcribing[].backend`.
- Not changing `TranscribingStep.model` or `TranscribingStep.language` defaults.
- Not adding a way to express "platform default" inside cascade steps other than the first — the use case is the fallback default; later steps that opt into a different backend continue to write it explicitly.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `pipeline-config`: `TranscribingStep.backend` becomes optional; `ConfigLoader` resolves omitted values to the platform default at load time.

## Impact

- Affected specs: `pipeline-config`
- Affected code:
  - Modified: src/talking_parrot/config/models.py
  - Modified: src/talking_parrot/config/loader.py
  - Modified: config.example.yaml
  - Modified: tests/unit/config/test_models.py
  - Modified: tests/unit/config/test_loader.py
  - New: (none)
  - Removed: (none)
