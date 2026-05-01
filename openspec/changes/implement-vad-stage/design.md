## Context

Stage 1 of the pipeline is `VADStage`. It receives a `PipelineContext` containing `media_info` and `config`, and must populate `ctx.vad_segments` before `ChunkingStage` can run. Without VAD, the entire pipeline stalls.

The current codebase has:
- `models/vad.py` — `VadSegment` with `confidence: float` (wrong; spec requires `ten_vad_prob`, `silero_vad_prob`, `composite_score`)
- `config/models.py` — `VadConfig` missing `formula` and `neg_threshold` fields
- `expression/formula.py` — `FormulaEvaluator` already implemented
- No `vad/` subpackage exists yet

All audio in the pipeline is 16 kHz mono PCM — this is a project-wide constraint that all stages rely on.

This change fixes the model/config mismatches and delivers the full VAD subsystem.

## Goals / Non-Goals

**Goals:**
- Define `VADBackend` interface and `RawVadFrame` model
- Implement `TenVADBackend` (wrapping the `ten-vad` package) and `SileroVADBackend` (wrapping `silero-vad`)
- Implement `VADStage` with hysteresis-based frame merging and `FormulaEvaluator` integration
- Fix `VadSegment` and `VadConfig` to match the architecture spec

**Non-Goals:**
- Training or fine-tuning VAD models
- Implementing `ChunkingStage` (separate change)
- Supporting more than two VAD backends in this change
- Streaming / online VAD (batch only)
- Audio resampling or channel conversion (upstream responsibility)

## Decisions

### Backend interface returns per-frame probabilities

`VADBackend.analyze()` returns `List[RawVadFrame]`, where each frame has `time_ms` (frame start in ms) and `prob` (speech probability 0.0–1.0). The frame rate is backend-specific. `VADStage` is responsible for aligning frames from multiple backends.

**Alternatives considered:**
- Return already-merged segments: rejected because it prevents `FormulaEvaluator` from combining raw probabilities across backends at frame granularity.

### TenVADBackend wraps `ten_vad.TenVad`

`TenVADBackend` splits the input PCM bytes into fixed-size chunks of `hop_size` samples (default 256 @ 16 kHz = 16 ms), calls `TenVad(hop_size, threshold).process(chunk)` for each chunk, and yields `RawVadFrame(time_ms=chunk_index * hop_size / sample_rate * 1000, prob=result.probability)`. The `threshold` parameter is passed at construction time and used only internally by the TEN library for its `.flag`; `VADStage` relies solely on `result.probability`.

The `ten_vad.TenVad` instance is lazy-initialised on first `analyze()` call and cached on the backend instance. `name` property returns `"ten_vad"`.

### SileroVADBackend wraps `silero_vad`

`SileroVADBackend` uses `silero_vad.load_silero_vad()` to load the ONNX model and calls the model on fixed-size chunks (512 samples @ 16 kHz = 32 ms). It yields `RawVadFrame(time_ms, prob)` per chunk. The model is lazy-loaded and cached. `name` property returns `"silero_vad"`.

**Alternatives considered:**
- Using `silero_vad.get_speech_timestamps()`: rejected because it returns merged segments and bypasses `FormulaEvaluator`.

### Frame alignment by nearest-neighbour with zero-fill

When multiple backends produce frames at different rates, `VADStage` aligns them using the union of all backend time points. For each time point, the probability from a given backend is the `prob` of its closest frame within a 50 ms tolerance window. If no frame falls within tolerance, the probability defaults to 0.0.

**Alternatives considered:**
- Linear interpolation: adds complexity for minimal gain; VAD decisions tolerate small temporal offsets.

### Backend name maps to formula variable via `{name}_prob`

Each `VADBackend.name` (e.g. `"ten_vad"`, `"silero_vad"`) maps to a formula variable named `{name}_prob`. `VADStage` builds the variable dict dynamically: `{f"{backend.name}_prob": aligned_prob for backend, aligned_prob in ...}`. This avoids hard-coding variable names in the stage.

### Hysteresis-based segment merging (two thresholds)

Frame merging uses a state machine:
- SILENCE → SPEECH when `composite_score >= activity_threshold`
- SPEECH → SILENCE when `composite_score < neg_threshold` (neg_threshold < activity_threshold)

Post-merge steps applied in order:
1. **Gap merging**: adjacent segments with silence gap < `min_silence_duration_ms` merge into one
2. **Short-segment filtering**: segments shorter than `min_speech_duration_ms` discarded
3. **Long-segment splitting**: segments longer than `max_speech_duration_ms` split at midpoint (hard cut)
4. **Speech padding**: each segment's `start_ms` shifted earlier and `end_ms` shifted later by `speech_pad_ms`, clamped to `[0, audio_duration_ms]`

`VadSegment.ten_vad_prob`, `silero_vad_prob`, and `composite_score` store the mean probability across the segment's frames for debugging and regression analysis.

### VadSegment model updated (breaking change within pre-release codebase)

The existing `confidence: float` field is removed and replaced with `ten_vad_prob: float`, `silero_vad_prob: float`, and `composite_score: float`. No migration is required (pre-release).

### VadConfig extended with `formula` and `neg_threshold`

`VadConfig` gains two new fields:
- `formula: str` — default `"(ten_vad_prob + silero_vad_prob) / 2"` (equal-weight average)
- `neg_threshold: float` — default `0.35`

## Risks / Trade-offs

- [Risk] Midpoint splitting of long segments may cut mid-word. → Mitigation: known limitation; users should tune `max_speech_duration_ms`. Same trade-off as `ChunkingStage` hard-cut.
