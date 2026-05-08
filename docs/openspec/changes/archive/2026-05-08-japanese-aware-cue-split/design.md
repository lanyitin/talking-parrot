## Context

The current post-processing pipeline ships three split processors (`WordBoundarySplitProcessor`, `CharacterBoundarySplitProcessor`, `TimeBasedSplitProcessor`). The character-boundary and time-based variants pick the slice point by linear interpolation:

```
char_idx_i = round(slice_end_ms_i / cue_duration_ms * len(text))
```

For Japanese this lands inside morphemes because the alignment backend produces character-level (not word-level) tokens, so the factory wires the character-boundary path. End-to-end verification on a real Japanese sample (archived change `2026-05-08-segment-level-postprocessing-pipeline`) found six cues split mid-morpheme.

`audio2subtitle` does not solve this either — it is the reason the user filed this follow-up. There is no third-party Japanese segmenter currently in the dependency tree, and adding one is rejected (see Decision 4).

## Goals

- Long Japanese cues split at boundaries that do not orphan a particle, isolate a single inflection character, or break inside a katakana word / number / common auxiliary.
- Zero behaviour change for non-Japanese pipelines.
- No new third-party dependency.

## Non-Goals

- Full bunsetsu / morphological analysis.
- Modifying merge processors.
- Adjusting `WordBoundarySplitProcessor` (English path; already snaps via `AlignedToken`).
- Re-splitting cues that have already been split.

## Decisions

### Decision 1: Introduce a `SplitBoundaryPolicy` abstraction injected into split processors

A small protocol with one method `adjust(text: str, candidate_index: int, search_radius: int) -> int` is added. Split processors compute the linear candidate index as today, then call `policy.adjust(...)` to allow language-specific snapping. Default is `LinearSplitBoundaryPolicy` which returns the candidate unchanged.

**Why over inlining the snap logic in the processor:** keeps language-specific knowledge out of `character_boundary.py` / `time_based.py`, which are language-agnostic by spec. The policy lives in `japanese.py` next to the other Japanese rules.

**Alternatives considered:**

- Inline an `if config.language == "ja": ...` branch inside each split processor. Rejected: scatters Japanese rules across multiple files; harder to test in isolation.
- Append a `JapaneseSplitFixupProcessor` after splitting. Rejected: detecting "which adjacent cue pair came from one split" requires reconstructing the original cue, which is brittle once timestamps and indices have been rewritten.

### Decision 2: Snap by searching a bounded character window with rule-based validity

`JapaneseSplitBoundaryPolicy.adjust` searches indices in `[candidate - radius, candidate + radius]` (clamped to `[1, len(text) - 1]`), filters out invalid indices, and returns the valid index closest to `candidate`. Ties are broken in favour of the smaller (earlier) index for determinism.

A boundary `i` is INVALID if any of:

1. Both `text[i-1]` and `text[i]` are katakana (`U+30A0`-`U+30FF` or `U+31F0`-`U+31FF`).
2. Both `text[i-1]` and `text[i]` are digits (`[0-9]` or `[０-９]`).
3. The substring `text[i-k:i+m]` (for any `k+m ≤ len(unit), k ≥ 1, m ≥ 1`) equals a configured no-split unit (e.g., `text[i-1:i+1] == "まし"`).
4. `text[i:]` starts with a configured no-leading-particle (e.g., `に`, `を`).
5. `text[i:]` starts with a configured no-leading-final char AND `text[i-1]` is hiragana or kanji (avoids `印象深 / い`).

If no valid index exists in the window, return `candidate` unchanged.

**Why a 4-char default radius:** the six observed bad splits all have a valid boundary within ±3 chars; +1 buffer for safety. The radius is configurable.

**Why character-class checks instead of a dictionary:** the failure modes observed (mid-katakana, mid-number, mid-auxiliary, orphan particle, orphan inflection) are all detectable from local 2-char context; a curated unit list (~14 entries) covers the auxiliary cases. A real morphological analyser is overkill for the failure modes seen.

### Decision 3: Wire the policy via the factory based on `expected_language`

`DefaultGranularityAwareProcessorFactory.create()` reads `ctx.config.expected_language` and passes either `JapaneseSplitBoundaryPolicy(config=ctx.config.post_processing)` or `LinearSplitBoundaryPolicy()` into the split processor constructors. Language matching is exact-string `"ja"` (consistent with `granularity-aware-processor-factory` spec for the existing Japanese processors).

**Why the factory not the processor:** keeps processors language-blind; concentrates language routing in one place that already does it for `JapaneseFillerProcessor` / `JapaneseRepetitionProcessor`.

### Decision 4: Rule-based, no new dependency

Rejected adding `fugashi`, `mecab-python3`, or `sudachipy`. Reasons:

- All three require a native dictionary install (UniDic / IPAdic) — heavy and platform-fragile.
- The failure modes are local (2-char window suffices); a parser is not necessary.
- `audio2subtitle` parity does not require it.

If future failures show this rule set is insufficient, this decision can be revisited as a follow-up change.

### Decision 5: Defaults for the configurable lists are populated, not empty

`PostProcessingConfig` ships with non-empty defaults for `japanese_split_no_split_units`, `japanese_split_no_leading_particles`, `japanese_split_no_leading_finals`. Reason: an empty list is operationally indistinguishable from "policy disabled" and would silently regress the user's reason for opening this change. Users opting out can set `japanese_split_search_radius = 0`.

## Risks / Trade-offs

- **[Risk] Snap window too small** → mitigation: configurable `japanese_split_search_radius`; default 4 is empirically grounded but increasable.
- **[Risk] Snap moves split far from time-target, distorting cue duration** → mitigation: radius is bounded (≤20 chars by validator); for typical Japanese speech ~10 chars/sec the worst-case shift is ≤2s, accepted.
- **[Risk] Edge case: text shorter than radius on both sides** → mitigation: window is clamped to `[1, len(text) - 1]`; if no valid index exists, fall back to original candidate (current behaviour).
- **[Risk] Rule list may miss a future failure mode** → mitigation: lists are config-overridable without a code change; new entries can be added incrementally.

## Migration Plan

Backwards-compatible:

- Default policy for non-Japanese is `LinearSplitBoundaryPolicy` → identical output.
- New `PostProcessingConfig` fields all have defaults → existing config files load without change.
- The split processor constructor adds an optional kwarg `policy: SplitBoundaryPolicy | None = None`; `None` resolves to `LinearSplitBoundaryPolicy()`. Existing direct instantiations in tests keep working.

No rollback needed beyond reverting the change.

## Open Questions

None.
