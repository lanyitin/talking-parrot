## Summary

Snap split-cue timestamps to nearby VAD silence so that "split" subtitles change at speech pauses, not mid-word.

## Motivation

The `japanese-aware-cue-split` change (archived 2026-05-08) made the **text** split point grammar-aware via `SplitBoundaryPolicy`, but `CharacterBoundarySplitProcessor` and `TimeBasedSplitProcessor` still place the **time** split at the linear position `start_ms + (i + 1) * duration / n`. After the text snaps to a grammatical boundary, the time stays in the middle, so a viewer sees the subtitle change while the speaker is still mid-utterance. Manual review of `test-samples/sample1` (recorded in `docs/TODOs.md`) confirmed this is the dominant remaining "feels off" case for Japanese output.

VAD silences (gaps between consecutive `VadSegment`s in `PipelineContext.vad_segments`) already mark exactly where the speaker is not talking. We can use them to nudge each split's `slice_end_ms` toward the nearest silence within a small window, with a clean fallback to today's linear value.

## Proposed Solution

Introduce a new `SplitTimePolicy` protocol parallel to the existing `SplitBoundaryPolicy`:

```python
def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int
```

Two implementations:

1. **`LinearSplitTimePolicy`** — returns `candidate_ms` unchanged. Default for non-VAD pipelines and for backwards compatibility (i.e., the existing tests that assert linear timestamps continue to pass when this policy is selected).
2. **`VadAlignedSplitTimePolicy`** — constructed with a list of silence intervals `[(silence_start_ms, silence_end_ms), ...]` and a `search_radius_ms`. `adjust` finds the silence whose midpoint is closest to `candidate_ms` within `[candidate_ms - search_radius_ms, candidate_ms + search_radius_ms]`, clamped to `(cue_start_ms, cue_end_ms)`. Returns the silence midpoint when found; otherwise returns `candidate_ms`.

Wire it through:

- Both `CharacterBoundarySplitProcessor` and `TimeBasedSplitProcessor` gain a second constructor argument `time_policy: SplitTimePolicy | None = None` (defaults to `LinearSplitTimePolicy()`); they call `time_policy.adjust(candidate_ms, sub.start_ms, sub.end_ms)` once per inner slice boundary, then use the returned value for both the previous slice's `end_ms` and the next slice's `start_ms` (preserving time-span continuity).
- `DefaultGranularityAwareProcessorFactory._build_time_policy(ctx)` derives silence intervals from `ctx.vad_segments` (gaps between consecutive segments, plus a leading/trailing implicit silence outside the speech region) and constructs `VadAlignedSplitTimePolicy` when `ctx.vad_segments` is non-empty AND `ctx.config.post_processing` enables the feature; otherwise returns `LinearSplitTimePolicy()`. Applied to both the CHARACTER and time-based-fallback (`granularity is None`) branches. NOT applied to the WORD branch (English/word-aligned processor already uses token timestamps and is out of scope).
- Add config field `PostProcessingConfig.split_time_snap_radius_ms: int = 250` (range `[0, 2000]`, validated). `0` disables snapping (equivalent to selecting `LinearSplitTimePolicy`).

## Non-Goals

- Re-aligning **non-split** cue timestamps to VAD. Only timestamps produced by the split processors are affected.
- Re-aligning the **text** split point. That remains the job of `SplitBoundaryPolicy` (the existing `japanese-aware-cue-split` work).
- Snapping for the WORD-boundary path. `WordBoundarySplitProcessor` uses aligned-token timestamps and does not perform linear interpolation; it is out of scope.
- Introducing new VAD detection. The change consumes existing `ctx.vad_segments` produced by `VADStage`.
- Per-language overrides. The behaviour applies whenever VAD silences exist and snap is enabled in config; expected_language is not consulted.

## Alternatives Considered

- **Adjust slice timestamps inside each processor without a policy object.** Rejected because it would couple the processors to `vad_segments`, breaking the dependency boundary established by `SplitBoundaryPolicy`. Using a parallel `SplitTimePolicy` keeps the two snap concerns (text vs. time) independent and testable in isolation.
- **Re-run a windowed silence detector at split time.** Rejected — the VAD pass has already produced silence intervals; re-detecting would duplicate work and introduce a new dependency on the audio buffer at post-processing time.
- **Snap to the closest silence boundary edge instead of midpoint.** Rejected because subtitle changes feel most natural at the centre of a pause rather than its leading edge; midpoint also tolerates short silences symmetrically.

## Impact

- Affected specs:
  - Modified: `character-boundary-processors`, `time-based-processors`, `granularity-aware-processor-factory`, `pipeline-config`
  - New: `split-time-policy`
- Affected code:
  - New: `src/talking_parrot/post_processing/split_time_policy.py`
  - Modified: `src/talking_parrot/post_processing/character_boundary.py`, `src/talking_parrot/post_processing/time_based.py`, `src/talking_parrot/post_processing/factory.py`, `src/talking_parrot/config/models.py`
- Affected tests:
  - New: `tests/unit/post_processing/test_split_time_policy.py`
  - Modified: `tests/unit/post_processing/test_character_boundary.py`, `tests/unit/post_processing/test_time_based.py`, `tests/unit/post_processing/test_factory.py`, `tests/unit/config/test_models.py`
