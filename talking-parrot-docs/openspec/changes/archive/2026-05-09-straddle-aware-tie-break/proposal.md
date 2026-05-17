## Why

`vad-grammar-sanity-gate` (archived 2026-05-08) wired `JapaneseSplitBoundaryPolicy.adjust` into the VAD-driven cue split path so morpheme-internal cuts get re-snapped to a valid grammar boundary. A regression remained on `test-samples/sample1` cue 10 (manual review 2026-05-09): the VAD silence midpoint at `46368 ms` lands inside the `「す」` token (`46020–46540 ms`) of `「覚えています 卒業後は…」`, producing `char_idx_vad = 41` (cuts mid-`「ます」`). The sanity gate's small-radius `adjust` call finds two equidistant valid neighbours — `i=40` (between `「い」「ま」`) and `i=42` (between `「す」「 」`). The current spec rule "ties SHALL be broken by preferring the smaller index for determinism" (`split-boundary-policy/spec.md` step 3) picks `i=40`, which strands `「ます」` as a leading-final at the start of cue 10:

```
cue 9: ...覚えてい
cue 10: ます 卒業後は大学院にも進みまして…
```

The polite-form ending should trail the previous cue, not lead the next one. Smaller-on-tie is a reasonable default when the candidate is invalidated by Leading-particle / Leading-final / Mid-katakana / Mid-digit, but when the candidate is invalidated specifically by Mid-no-split-unit the unit straddles the cut and the two tied neighbours sit on opposite sides of that unit. Picking the smaller side puts the unit at the start of the next cue (the very pattern Mid-no-split-unit was added to prevent).

## What Changes

- Refine the tie-break rule for `JapaneseSplitBoundaryPolicy.adjust`: when `candidate_index` is straddled by a configured Mid-no-split-unit, prefer the LARGER tied index so the unit trails the previous cue. In all other cases (no straddle), keep the existing smaller-on-tie default.
- Extract a private `_straddles_no_split_unit(text, index)` helper used by both the new tie-break branch and the existing `is_valid` Mid-no-split-unit check (so the two cannot disagree).
- Update `docs/openspec/specs/split-boundary-policy/spec.md` step 3 to describe the conditional tie-break and add a Scenario covering the straddle case.

## Non-Goals

- Changing tie-break direction for the other invalidating rules (Mid-katakana, Mid-digit, Leading-particle, Leading-final). Those are not always symmetric around `candidate_index` and the existing smaller-on-tie behaviour stays correct for them.
- Expanding the `japanese_split_no_split_units` list (compound-word / kanji-dictionary protection from `docs/TODOs.md` is a separate, deferred change).
- Touching `SplitTimePolicy`, `VadAlignedSplitTimePolicy`, or `CharacterBoundarySplitProcessor`. The fix is local to `JapaneseSplitBoundaryPolicy.adjust`; the sanity-gate plumbing from `vad-grammar-sanity-gate` already routes through `adjust` and gets the new behaviour for free.
- Adding a config flag to toggle the new tie-break. The straddle-aware branch is strictly better for the affected case and a strict no-op when no unit straddles the candidate.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `split-boundary-policy`: `JapaneseSplitBoundaryPolicy.adjust` tie-break becomes conditional on whether `candidate_index` is straddled by a configured no-split unit. The smaller-on-tie default is preserved for all non-straddle cases.

## Impact

- Affected specs: `split-boundary-policy`
- Affected code:
  - Modified:
    - src/talking_parrot/post_processing/japanese.py
  - New: (none)
  - Removed: (none)
- Affected tests:
  - Modified:
    - tests/unit/post_processing/test_japanese.py (added two regression cases; existing cases unchanged)
- Logging: no changes.
- Configuration: no new fields. Existing `japanese_split_no_split_units` drives the straddle detection.
- Manual verification: re-running `talking-parrot` against `test-samples/sample1` confirms cue 10 now reads `卒業後は大学院にも進みまして…` (no leading `「ます」`); the previous cue absorbs `「覚えています」` whole.
