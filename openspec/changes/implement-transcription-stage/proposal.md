## Why

Stage 3 of the pipeline (`TranscriptionStage`) is the missing link between `ChunkingStage` (which now produces `Chunk` objects) and downstream alignment / post-processing stages. Without it, `ctx.transcription_results` stays empty and the pipeline cannot produce subtitles. The configuration layer already declares `transcribing[]` with a cascade of `TranscribingStep` entries (`condition`, `backend`, `model`, `language`), but no runtime stage exists to honour it. We also need cross-platform Whisper backend support: `faster-whisper` for Windows/Linux and `mlx-whisper` for Apple Silicon macOS.

## What Changes

- Introduce a new `transcription/` subpackage with an abstract `TranscriptionBackend` interface and `TranscriptionBackendFactory` for platform-based selection.
- Implement `FasterWhisperBackend` wrapping `faster_whisper.WhisperModel` (Windows/Linux default, also available on macOS when MLX is unavailable).
- Implement `MLXWhisperBackend` wrapping `mlx_whisper.transcribe` (default on Apple Silicon macOS).
- Implement `TranscriptionStage` that iterates `ctx.chunks`, evaluates each `TranscribingStep.condition` against accumulated `TranscriptionMetrics` using `ConditionEvaluator`, and re-runs transcription with progressively heavier models (cascade upgrade) until either a step's condition rejects further upgrade or the cascade is exhausted.
- The factory selects the backend at construction time using (1) `TRANSCRIPTION_BACKEND` env var override, then (2) `sys.platform` + Apple Silicon detection. It raises a clear error when the selected backend's optional dependency is not installed.
- Each chunk produces exactly one final `TranscriptionResult` (the result of the last successfully-evaluated step) appended to `ctx.transcription_results`.

## Non-Goals

- Implementing alignment, post-processing, or subtitle export (separate changes per `TODOs.md`).
- Streaming / online transcription — batch only.
- Model downloading or caching infrastructure beyond what `faster_whisper` / `mlx_whisper` already provide internally.
- GPU configuration knobs (device, compute_type) beyond reasonable defaults — backends accept their library defaults.
- A Linux/Windows `MLXWhisperBackend` fallback or a macOS-only `FasterWhisperBackend` warning beyond the factory's platform check.
- Adding new condition operators to `ConditionEvaluator` — the existing operator whitelist is sufficient.
- Re-running a step with `condition: "true"` after the first invocation; each cascade step executes at most once.

## Capabilities

### New Capabilities

- `transcription-backend`: Abstract `TranscriptionBackend` interface and request/response contract for transcribing a single chunk.
- `faster-whisper-backend`: `FasterWhisperBackend` — wraps `faster_whisper.WhisperModel` to transcribe PCM audio and emit `TranscriptionResult` with `TranscriptionMetrics`.
- `mlx-whisper-backend`: `MLXWhisperBackend` — wraps `mlx_whisper.transcribe` for Apple Silicon macOS, emitting the same `TranscriptionResult` shape.
- `transcription-backend-factory`: Platform-aware factory that selects between `FasterWhisperBackend` and `MLXWhisperBackend` based on `TRANSCRIPTION_BACKEND` env var and `sys.platform` / `platform.machine()`.
- `transcription-stage`: `TranscriptionStage` that drives the cascade evaluation across `transcribing[]` steps using `ConditionEvaluator` and produces one `TranscriptionResult` per `Chunk`.

### Modified Capabilities

(none)

## Impact

- Affected specs: `transcription-backend` (new), `faster-whisper-backend` (new), `mlx-whisper-backend` (new), `transcription-backend-factory` (new), `transcription-stage` (new)
- Affected code:
  - New: src/talking_parrot/transcription/__init__.py
  - New: src/talking_parrot/transcription/backend.py
  - New: src/talking_parrot/transcription/faster_whisper_backend.py
  - New: src/talking_parrot/transcription/mlx_whisper_backend.py
  - New: src/talking_parrot/transcription/factory.py
  - New: src/talking_parrot/stages/transcription_stage.py
  - New: tests/unit/transcription/__init__.py
  - New: tests/unit/transcription/test_backend.py
  - New: tests/unit/transcription/test_faster_whisper_backend.py
  - New: tests/unit/transcription/test_mlx_whisper_backend.py
  - New: tests/unit/transcription/test_factory.py
  - New: tests/unit/stages/test_transcription_stage.py
  - Modified: src/talking_parrot/stages/__init__.py
