## Context

The post-processing stage runs after VAD, transcription, and alignment. Two of its split processors — `CharacterBoundarySplitProcessor` (used for Japanese / character-aligned languages) and `TimeBasedSplitProcessor` (the no-alignment fallback) — split any cue exceeding `config.split_max_duration_ms` into `n = ceil(duration / cap)` slices. For each slice they currently compute:

```
slice_end_ms = sub.start_ms + ((i + 1) * duration) // n
```

This linear interpolation places the boundary at a fixed fraction of cue duration regardless of where the speaker actually pauses. After `japanese-aware-cue-split` (archived 2026-05-08) made the **text** boundary grammar-aware, the misalignment between text and time became the dominant remaining "feels off" case observed during manual review of `test-samples/sample1` (recorded under the `Split 邊界後續優化` heading in `docs/TODOs.md`).

Relevant existing pieces:

- `PipelineContext.vad_segments: list[VadSegment]` (frozen dataclass with `start_ms`, `end_ms`, …) is already populated by `VADStage` and is available to the post-processing stage via the context passed to `DefaultGranularityAwareProcessorFactory.create(granularity, ctx)`.
- The factory already injects a `SplitBoundaryPolicy` into split processors (`japanese-aware-cue-split`'s parallel pattern). We will reuse that pattern for time policies.
- `PostProcessingConfig` already validates ranges for similar fields (`japanese_split_search_radius` is bounded `[0, 20]`).

## Goals / Non-Goals

**Goals:**

- Subtitle change-points in split-derived cues land at speech pauses when a nearby silence exists, eliminating the mid-utterance flicker observed in sample1.
- Snap is a clean no-op when the feature is disabled (radius = 0), no VAD silences exist, or no silence falls inside the search window. Existing test expectations for linear timestamps continue to hold under the default-radius-0 configuration.
- The added behaviour is observable per cue via DEBUG logs that report whether snapping occurred and by how many milliseconds.
- Time-span continuity is preserved: every adjacent slice pair's `prev.end_ms == next.start_ms`, and the outer cue's `[start_ms, end_ms]` window is unchanged.

**Non-Goals:**

- Re-snapping non-split cues (single-slice cues) — they do not call the time policy.
- Snapping the WORD-boundary path (`WordBoundarySplitProcessor` uses aligned token timestamps directly).
- Adjusting text indices — `SplitBoundaryPolicy` retains that responsibility.
- New VAD detection, audio re-decoding, or any work outside the existing `vad_segments` data.
- Asymmetric snapping (e.g., always toward the leading edge of silence). We snap to silence midpoint only.

## Decisions

### Decision 1: Introduce a `SplitTimePolicy` protocol parallel to `SplitBoundaryPolicy`

**Choice:** New module `src/talking_parrot/post_processing/split_time_policy.py` exporting:

```python
@runtime_checkable
class SplitTimePolicy(Protocol):
    def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int: ...

class LinearSplitTimePolicy:
    def adjust(self, candidate_ms, cue_start_ms, cue_end_ms): return candidate_ms

class VadAlignedSplitTimePolicy:
    def __init__(self, silences: Sequence[tuple[int, int]], search_radius_ms: int): ...
    def adjust(self, candidate_ms, cue_start_ms, cue_end_ms): ...
```

**Rationale:** Mirrors the existing `SplitBoundaryPolicy` design. Keeps text-snap and time-snap independent and individually testable. Default `LinearSplitTimePolicy` preserves historical behaviour.

**Alternative rejected:** Threading `vad_segments` directly into the processors. This would couple the processors to the silence shape and make unit testing require constructing fake VAD segments. The policy seam isolates that concern.

### Decision 2: Snap to silence midpoint, clamped to the open interval `(cue_start_ms, cue_end_ms)`

**Choice:** `VadAlignedSplitTimePolicy.adjust(candidate, cue_start, cue_end)` selects the silence interval whose midpoint is closest to `candidate` and lies inside `[candidate - radius_ms, candidate + radius_ms]` ∩ `(cue_start, cue_end)`. Returns that midpoint. If no silence midpoint is in range, returns `candidate` unchanged.

**Rationale:** Midpoint feels natural perceptually (the change happens during the quiet gap, not at its edge). Clamping to the open interval avoids producing a zero-duration slice (`prev.end_ms <= prev.start_ms`).

**Alternative rejected:** Snap to silence start. Subjectively the change appears too early (just as the speaker stops). Snap to silence end appears too late.

### Decision 3: Derive silence intervals from `vad_segments` gaps in the factory, not in the policy

**Choice:** `DefaultGranularityAwareProcessorFactory._build_time_policy(ctx)` walks `ctx.vad_segments` (sorted ascending by `start_ms`) and emits `silences = [(seg[i].end_ms, seg[i+1].start_ms) for i in range(len(seg)-1)]`. Filters out non-positive-length gaps. Constructs `VadAlignedSplitTimePolicy(silences, radius_ms)` only when `len(silences) > 0` AND `radius_ms > 0`; otherwise returns `LinearSplitTimePolicy()`.

**Rationale:** Keeps the policy a pure function of its constructor inputs (no knowledge of `VadSegment`). Centralises the "no VAD → no snap" decision in one place. Empty vad_segments (e.g., the disabled-VAD path or smoke test fixtures) deterministically falls back to linear.

**Alternative rejected:** Including the speech-region prefix and suffix as implicit silences. Out of scope — only inter-segment gaps are considered. If a future change wants leading/trailing silence, it can extend the factory without touching the policy.

### Decision 4: Slice continuity — a single adjusted boundary serves both adjacent slices

**Choice:** For `n` slices the processor computes `n - 1` candidate boundaries (`i = 1 .. n - 1`). For each candidate it calls `time_policy.adjust(candidate_ms, sub.start_ms, sub.end_ms)` once and stores the result in `boundaries[i]`. Slice `i`'s `start_ms = boundaries[i]`, slice `i`'s `end_ms = boundaries[i + 1]`, where `boundaries[0] = sub.start_ms` and `boundaries[n] = sub.end_ms`.

**Rationale:** Guarantees `prev.end_ms == next.start_ms` (continuity). Avoids the corruption-mode where each slice independently adjusts its own start and end and they disagree.

**Edge case:** If two adjusted boundaries collide (`boundaries[i] >= boundaries[i + 1]`), the slice is emitted with `end_ms = max(boundaries[i + 1], boundaries[i] + 1)` — a 1ms-minimum slice — and a DEBUG log is emitted. Pathological but possible if two text-snap collisions and one time-snap collision happen in the same cue. We choose 1ms-min over zero-duration to keep `Subtitle` invariant `start_ms < end_ms` intact.

### Decision 5: New config field `split_time_snap_radius_ms` with range validation

**Choice:** Add `PostProcessingConfig.split_time_snap_radius_ms: int = 250`, validated to `[0, 2000]`. `0` means "disabled" — the factory short-circuits to `LinearSplitTimePolicy()`. `250` is the default because typical Japanese VAD silences in our test corpus are 200–500 ms long and sit within ~150–300 ms of the linear midpoint of a long cue.

**Rationale:** A bounded integer matches the existing `japanese_split_search_radius` field's style. Upper bound `2000` prevents nonsensical configurations (a 2 s window would let any speech-bearing pause swallow the boundary). Defaulting to a non-zero value enables the feature out-of-the-box for new pipelines, since the historical "linear" behaviour is preserved for any pipeline that has no `vad_segments`.

**Compatibility note:** Existing unit tests that hand-construct cues without VAD context already get `LinearSplitTimePolicy()` (factory short-circuit when `vad_segments` is empty). Tests that exercise the processors directly without explicit `time_policy` get `LinearSplitTimePolicy()` from the constructor default. Therefore previously-asserted linear timestamp values continue to hold.

### Decision 6: Apply the time policy to CHARACTER and time-based-fallback paths only

**Choice:** `_build_time_policy(ctx)` is consulted by the factory's `CHARACTER` and `granularity is None` branches; the `WORD` branch is unchanged. The new constructor argument is added to both `CharacterBoundarySplitProcessor` and `TimeBasedSplitProcessor` but NOT to `WordBoundarySplitProcessor`.

**Rationale:** `WordBoundarySplitProcessor` already places boundaries at aligned-token timestamps, which are derived from the audio waveform — they are already silence-aware in the alignment-model sense. Adding a second layer would be redundant and could conflict with token boundaries.

## Risks / Trade-offs

- **Risk:** A long contiguous silence can pull two adjacent boundaries to the same midpoint when the cue is split into 3+ slices. → **Mitigation:** the collision branch in Decision 4 emits a 1 ms-minimum slice and logs at DEBUG level.
- **Risk:** Disabled VAD configurations would silently lose the snap behaviour. → **Mitigation:** acceptable. The feature is opportunistic; without VAD data, falling back to linear is correct.
- **Risk:** Snapping past the linear midpoint by hundreds of ms might leave the previous slice noticeably shorter or longer than its neighbour, harming perceived rhythm. → **Mitigation:** bounded `search_radius_ms` (default 250 ms, configurable up to 2000 ms). Users seeing too-aggressive snaps can lower the radius.
- **Trade-off:** We snap by midpoint rather than the silence's leading or trailing edge. This may feel slightly late in pauses with short trailing energy or slightly early in pauses with long ramp-down. We accept this in exchange for symmetry.

## Migration Plan

No data migration required. The feature activates automatically when:

1. The pipeline has produced non-empty `vad_segments` (true for all real-audio pipelines), AND
2. `PostProcessingConfig.split_time_snap_radius_ms > 0` (default `250`).

To opt out, set `split_time_snap_radius_ms: 0` in the pipeline config. Rollback is a single-config change.

## Open Questions

None at design time. Empirical tuning of the default radius (250 ms) is left to manual review of the next round of `test-samples/sample1` regression after implementation lands.
