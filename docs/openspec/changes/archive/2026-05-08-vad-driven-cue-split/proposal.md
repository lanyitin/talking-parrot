## Why

`CharacterBoundarySplitProcessor` currently decides where to cut an oversized cue by linearly interpolating a character index and then snapping that index to a grammatical boundary via `JapaneseSplitBoundaryPolicy` (text → time). This text-first approach is fragile: every new grammatical edge case requires another rule (Whac-A-Mole). VAD silence valleys are the more principled signal — where the speaker actually paused is the natural cut point. Flipping to a time → text strategy produces splits that are both acoustically grounded and grammatically safer, because the character index is derived from real token timestamps rather than estimated from linear proportions.

## What Changes

- `SplitTimePolicy` gains a `pick(cue_start_ms, cue_end_ms) -> int | None` method that returns the best silence midpoint strictly inside the cue window, or `None` when no qualifying silence exists. The existing `adjust` method is retained for the fallback path.
- `LinearSplitTimePolicy.pick` always returns `None`, preserving existing fallback semantics.
- `VadAlignedSplitTimePolicy.pick` selects the silence midpoint nearest the linear time midpoint within `(cue_start_ms, cue_end_ms)`.
- `CharacterBoundarySplitProcessor` accepts an optional `token_map_by_index: dict[int, list[AlignedToken]]` parameter (matching the WORD-path constructor pattern). When a qualifying silence midpoint is found via `pick()` AND aligned tokens are available for the cue, the processor derives the text cut by binary-searching `AlignedToken.start_ms` for the character index whose timestamp is nearest that midpoint. When `pick()` returns `None` or the token map is absent/empty for the cue, the processor falls back to `JapaneseSplitBoundaryPolicy` (or `LinearSplitBoundaryPolicy`) plus linear time.
- `DefaultGranularityAwareProcessorFactory` extends `_build_token_map` usage to cover the CHARACTER path, injecting `token_map_by_index` into `CharacterBoundarySplitProcessor`.
- The WORD path and the time-based fallback (`None` granularity) path are unchanged.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `character-boundary-processors`: `CharacterBoundarySplitProcessor` constructor gains `token_map_by_index` parameter; split decision now time → text when a VAD silence is found inside the cue window.
- `granularity-aware-processor-factory`: CHARACTER path now injects `token_map_by_index` into `CharacterBoundarySplitProcessor` (matching existing WORD-path pattern).
- `split-time-policy`: `SplitTimePolicy` protocol and both concrete classes gain a `pick(cue_start_ms, cue_end_ms) -> int | None` method.

## Impact

Modified source files:

- src/talking_parrot/post_processing/character_boundary.py
- src/talking_parrot/post_processing/factory.py
- src/talking_parrot/post_processing/split_time_policy.py

Modified test files:

- tests/unit/post_processing/test_character_boundary.py
- tests/unit/post_processing/test_factory.py
- tests/unit/post_processing/test_split_time_policy.py
