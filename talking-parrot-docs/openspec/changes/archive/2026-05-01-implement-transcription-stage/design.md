## Context

Stage 3 of the pipeline is `TranscriptionStage`. After `ChunkingStage` it receives `ctx.chunks: list[Chunk]` (each with `start_ms`, `end_ms`, `source_segments`) and must populate `ctx.transcription_results: list[TranscriptionResult]` so that `AlignmentStage` (next change) has input.

Existing foundation already in the codebase:
- `models/transcription.py` defines frozen `TranscriptionResult(chunk_index, start_ms, end_ms, text, language, model_used, metrics, aligned_tokens=None)` and `TranscriptionMetrics(avg_logprob, compression_ratio, no_speech_prob, repetition_ratio)`.
- `config/models.py` defines `TranscribingStep(condition, backend, model, language=None)` and `PipelineConfig.transcribing: list[TranscribingStep]`. `ConfigLoader` already enforces `transcribing[0].condition == "true"` and non-empty list.
- `expression/condition.py` provides `ConditionEvaluator`, an AST-whitelist evaluator with `evaluate(expression: str, variables: dict) -> Any`.
- `stages/base.py` provides the `PipelineStage` ABC; `VADStage` / `ChunkingStage` are existing references for the multi-backend + evaluator pattern.
- Audio bytes are 16 kHz mono PCM throughout the pipeline. `ctx.media_info` carries the source audio path and `duration_ms`.
- `pyproject.toml` declares `faster-whisper>=1.0` and `mlx-whisper>=0.4` under separate optional-dependency extras (`faster-whisper`, `mlx`). At runtime, neither, one, or both may be installed depending on the install profile.

ADR-0001 (`docs/`) already prescribes a Factory + Interface pattern (no `if sys.platform` inside the stage). ADR-0002 prescribes `ConditionEvaluator` driving the cascade with each step running at most once.

## Goals / Non-Goals

**Goals:**
- Define `TranscriptionBackend` interface and a slice of audio data contract (PCM bytes + sample_rate + chunk window).
- Implement `FasterWhisperBackend` and `MLXWhisperBackend`, each emitting the same `TranscriptionResult` shape.
- Implement `TranscriptionBackendFactory.create(name: str) -> TranscriptionBackend` that selects the correct backend by name and refuses to construct one whose optional dependency is missing or whose required platform is mismatched.
- Implement `TranscriptionStage` driving the cascade: for each `Chunk`, evaluate `TranscribingStep.condition` against the latest `TranscriptionMetrics`, and if the condition holds run that step's backend/model. The result of the last successfully evaluated-and-executed step is the chunk's final `TranscriptionResult`.
- Compute `TranscriptionMetrics` (`avg_logprob`, `compression_ratio`, `no_speech_prob`, `repetition_ratio`) consistently across both backends so that conditions are portable.
- Produce one `TranscriptionResult` per `Chunk`, in input order, with `chunk_index` matching `Chunk.index`.

**Non-Goals:**
- Word- or token-level alignment (`aligned_tokens` is left `None` here; `AlignmentStage` populates it later).
- Streaming / partial results.
- Implementing model download progress, custom caching, or quantisation choices beyond library defaults.
- Cross-chunk context passing (overlap_ms is already deferred at the chunking layer).
- Adding new operators or variables to `ConditionEvaluator`.
- Concurrency: chunks transcribe sequentially in this change. Parallelism is a future optimisation.

## Decisions

### Backend interface accepts a Chunk plus the source audio path

`TranscriptionBackend.transcribe(audio_path: Path, chunk: Chunk, model: str, language: str | None) -> TranscriptionResult`. The backend is responsible for decoding the audio slice for `[chunk.start_ms, chunk.end_ms]`. We pass the path, not raw bytes, because both `faster_whisper.WhisperModel.transcribe` and `mlx_whisper.transcribe` accept either a path or a numpy array, and reading per-chunk lets each backend decide whether to slice via `ffmpeg` (`faster_whisper`'s default) or via numpy load (`mlx_whisper`).

`TranscriptionBackend` is an `abc.ABC` with abstract `name: str` property and `transcribe(...)`. Models are lazy-loaded and cached on the backend instance, keyed by `model` name, so cascading from `base` to `large-v3` does not re-instantiate `base` if revisited (irrelevant in current cascade since each step runs at most once, but cheap to add and protects future use).

**Alternatives considered:**
- Returning raw provider output and translating in the stage: rejected; metric translation is backend-specific (e.g., `faster_whisper` exposes `avg_logprob` per segment vs. mlx-whisper exposing per-token logprobs). Keeping the translation in the backend keeps the stage pure.
- Passing PCM bytes only: rejected; both libraries are happiest with file paths and handle ffmpeg-based slicing internally.

### FasterWhisperBackend wraps faster_whisper.WhisperModel

`FasterWhisperBackend` lazy-imports `faster_whisper` on first `transcribe()` call and raises `ImportError("Install with: uv add 'talking-parrot[faster-whisper]'")` if the optional dep is missing. It instantiates `WhisperModel(model_size_or_path=model)` with library defaults for `device` and `compute_type`. For each chunk it calls `model.transcribe(audio_path, language=language, clip_timestamps=[chunk.start_ms / 1000, chunk.end_ms / 1000])` and consumes the segment iterator. `name` returns `"faster-whisper"`.

The metrics map as follows:
- `avg_logprob`: weighted mean of segment `avg_logprob` values, weighted by segment duration.
- `compression_ratio`: weighted mean of segment `compression_ratio`.
- `no_speech_prob`: maximum of segment `no_speech_prob` values across the chunk (so any silence-heavy segment surfaces).
- `repetition_ratio`: computed locally as `1 - (unique_token_count / total_token_count)` over the joined text tokenised on whitespace; this avoids depending on any provider-specific repetition signal.

Concatenated `text` is the stripped join of segment texts. `model_used` is the requested `model` string, `language` is the segment-detected language (preferring the provider's `info.language` from `model.transcribe`'s second return value).

**Alternatives considered:**
- Calling `model.transcribe` once on the full audio and slicing post-hoc: rejected; the chunk boundary is the point at which we want metrics, so per-chunk invocation is correct.
- Computing `repetition_ratio` from token logprobs: rejected; not portable to MLX.

### MLXWhisperBackend wraps mlx_whisper.transcribe

`MLXWhisperBackend` lazy-imports `mlx_whisper` on first `transcribe()` call, raising `ImportError("Install with: uv add 'talking-parrot[mlx]'")` if absent. It additionally enforces `sys.platform == "darwin" and platform.machine() == "arm64"` at construction time and raises `RuntimeError("MLXWhisperBackend requires Apple Silicon macOS")` otherwise.

For each chunk it loads the requested chunk window into a numpy float32 array via `librosa`/`audio_io` helpers (already used by `audio-io` capability) — sliced from `[chunk.start_ms, chunk.end_ms]` in the source — and calls `mlx_whisper.transcribe(audio_array, path_or_hf_repo=model, language=language)`. The return value's `segments` field is iterated to compute the same four metrics using the same rules as the faster-whisper backend (weighted-mean for `avg_logprob` and `compression_ratio`, max for `no_speech_prob`, locally-computed `repetition_ratio`).

`name` returns `"mlx-whisper"`. Model name strings (e.g., `"large-v3"`) are passed through verbatim; mapping to a Hugging Face repo (e.g., `"mlx-community/whisper-large-v3"`) is the user's responsibility via the `model` field in YAML.

**Alternatives considered:**
- Auto-rewriting bare names like `"large-v3"` into `"mlx-community/whisper-large-v3"`: rejected; magical translation hides config and conflicts with user-pinned forks.
- Reading bytes from the file and decoding per backend: rejected; the project's `audio-io` already provides a centralised loader.

### TranscriptionBackendFactory selects by name and platform

`TranscriptionBackendFactory.create(backend_name: str) -> TranscriptionBackend` accepts the literal string from `TranscribingStep.backend` (`"faster-whisper"` or `"mlx-whisper"`). The factory does not consult `sys.platform` itself for the explicit case — the user's YAML choice wins. However:
- If the YAML omits the backend entirely (which is currently invalid per `pipeline-config`), behaviour is unaffected.
- A separate `TranscriptionBackendFactory.default_for_platform() -> str` returns `"mlx-whisper"` when `sys.platform == "darwin" and platform.machine() == "arm64"`, else `"faster-whisper"`. Callers may use this when constructing default config templates.
- The `TRANSCRIPTION_BACKEND` env var, if set, overrides whatever name is passed in. This is a CI / debugging escape hatch.
- Unknown backend names raise `ValueError(f"Unknown transcription backend: {name}")`.

The factory caches backend instances by (backend_name, model) across the stage's lifecycle so cascade steps that share a backend reuse the same loaded model (relevant when two steps target different model sizes via the same backend — each model is lazy-loaded on first call and cached thereafter).

**Alternatives considered:**
- Putting the factory in `transcription/__init__.py` as a function: rejected; a class with explicit `create` and `default_for_platform` is clearer, easier to mock in tests, and matches ADR-0001's "Factory" terminology.
- Auto-detecting backend by import availability: rejected; surprises the user when both extras are installed.

### TranscriptionStage cascade evaluation

`TranscriptionStage(factory: TranscriptionBackendFactory, evaluator: ConditionEvaluator)`. `process()` returns `ctx` unchanged if `ctx.chunks` is empty (logs DEBUG once and exits). Otherwise, for each `Chunk` in `ctx.chunks`:

1. Initialise `latest_result: TranscriptionResult | None = None` and `latest_metrics: dict[str, Any] = {}`.
2. For each `step` in `ctx.config.transcribing` (in declared order):
   a. Evaluate `evaluator.evaluate(step.condition, latest_metrics)`. The first step's condition is the literal `"true"` (already enforced by `ConfigLoader`) so it always passes; subsequent steps may reference `avg_logprob`, `compression_ratio`, `no_speech_prob`, `repetition_ratio`.
   b. If the result is `False`, stop the cascade for this chunk (the previous step's result is the final answer).
   c. If `True`, look up `backend = factory.create(step.backend)`, call `backend.transcribe(media_path, chunk, step.model, step.language or ctx.config.expected_language)`, replace `latest_result` with the returned `TranscriptionResult`, and update `latest_metrics` from `latest_result.metrics`.
3. After the loop, append `latest_result` to the accumulator (it is never `None` because step 0 always runs).

Each step thus executes at most once per chunk. The cascade explicitly never re-runs a step. Edge case: if a later step's condition is `True` but its backend raises (e.g., MLX on Linux), the stage logs WARN and keeps the previous step's result. This bounded fallback prevents one bad config line from killing a long batch.

**Alternatives considered:**
- Propagating backend exceptions: rejected for the cascade-fallback case; the prior step's result is a valid (if lower-quality) transcription. Hard exceptions only surface when step 0 fails, since there is no fallback.
- Re-checking earlier conditions: rejected; the cascade is monotonic (heavier-and-heavier model) by convention. ADR-0002 codifies "each step at most once".

### Variables exposed to ConditionEvaluator

The variable dict passed to `ConditionEvaluator.evaluate()` for step `N>0` contains exactly:
- `avg_logprob: float`
- `compression_ratio: float`
- `no_speech_prob: float`
- `repetition_ratio: float`

For step 0 the dict is empty. Since the first condition is always the literal `"true"`, this is fine.

This contract is documented in the `transcription-stage` spec so that users can write portable conditions.

### Per-chunk audio decoding shared via audio-io

To keep both backends honest and testable, decoding of the chunk window uses the existing `audio-io` capability's helpers (path → int16 PCM bytes → float32 numpy). `FasterWhisperBackend` mostly bypasses this because passing a path with `clip_timestamps` is more efficient, but it remains an option for tests. `MLXWhisperBackend` uses it directly. This avoids reinvented audio-loading code in two places.

## Risks / Trade-offs

- [Risk] `clip_timestamps` precision in `faster_whisper.WhisperModel.transcribe` may shift segment boundaries by tens of ms. → Mitigation: `Chunk.start_ms`/`end_ms` is the authoritative window; the resulting `TranscriptionResult.start_ms`/`end_ms` are taken from the chunk, not from segment timestamps. Internal segment timestamps are still used for metric weighting.
- [Risk] Optional dependencies (`faster-whisper`, `mlx-whisper`) may both be missing. → Mitigation: backend constructors raise actionable `ImportError` messages naming the install extra. The factory does not import either package at module load; imports happen on first `transcribe()` call.
- [Risk] Repetition ratio is computed from whitespace tokenisation, which is unfriendly to Japanese (no whitespace). → Mitigation: documented limitation; users running Japanese pipelines should not write conditions referencing `repetition_ratio`. A future change can add language-aware tokenisation. Listed as an explicit caveat in the `transcription-stage` spec.
- [Risk] `mlx_whisper` model names are HF repos, not bare strings; users mis-configuring will hit a download error. → Mitigation: clear error path — `mlx_whisper.transcribe` raises a recognisable error that the backend re-raises unchanged. We do not silently rewrite names.
- [Risk] Cascade fallback on backend failure may mask systemic environment problems. → Mitigation: WARN log includes step index, backend name, model, and exception type; step 0 failures are not caught and propagate normally.
