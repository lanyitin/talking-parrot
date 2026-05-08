## Summary

Make cue splitting grammar-aware for Japanese so long cues split on natural Japanese boundaries (between bunsetsu, before particles, after sentence-final auxiliaries) instead of mid-word, mid-katakana, mid-number, or mid-auxiliary.

## Motivation

End-to-end verification of archived change `2026-05-08-segment-level-postprocessing-pipeline` against the ground-truth script (see `test-samples/sample1/`) found six cues split at unreadable boundaries:

- `専攻しておりまし / た` (splits the auxiliary `まし` from sentence-final `た`)
- `印象深 / いのは` (splits the i-adjective stem from its inflection `い`)
- `持つよ / うになり` (splits `よう` mid-mora and orphans the particle `に`)
- `携わったプロジェクトの中で、特に印象深 / いのは`
- `日本料理にも挑戦し / ていて`
- `日本語の勉強を通じて、日本の文化や考え方にも興味を持つよ / うになり`

The current `CharacterBoundarySplitProcessor` and `TimeBasedSplitProcessor` choose the split index by linear interpolation `round(slice_end_ms / cue_duration_ms * len(text))`, which is language-blind. For English the WordBoundarySplit path already snaps to word boundaries via `AlignedToken` data. Japanese cues use the character-level alignment path and have no equivalent snap step, so splits land inside morphemes.

## Proposed Solution

Introduce a `SplitBoundaryPolicy` abstraction that decides the actual character index at which to slice a cue. The split processors call the policy with `(text, candidate_index, slice_window)` and the policy returns the adjusted index.

1. Add `SplitBoundaryPolicy` protocol in `src/talking_parrot/post_processing/split_policy.py` with one method: `adjust(text: str, candidate_index: int, search_radius: int) -> int`.
2. Add `LinearSplitBoundaryPolicy` (default — returns `candidate_index` unchanged) so existing behaviour is preserved for non-Japanese.
3. Add `JapaneseSplitBoundaryPolicy` (in `src/talking_parrot/post_processing/japanese.py`) that searches `[candidate_index - radius, candidate_index + radius]` and returns the nearest valid boundary, ranked by distance from the candidate. A boundary `i` is invalid if any of these hold:
   - `text[i-1:i+1]` falls inside a katakana run (both sides are katakana `゠-ヿ`).
   - `text[i-1:i+1]` falls inside a digit run (both sides match `[0-9０-９]`).
   - `text[i-1:i+1]` falls inside a sequence in the configured "no-split unit" list — defaults: `ます`, `ません`, `まし`, `です`, `でし`, `だっ`, `った`, `ない`, `なかっ`, `たい`, `よう`, `そう`, `という`, `について`.
   - `text[i:]` starts with a particle in the configured "no-leading-particle" list — defaults: `て`, `で`, `に`, `を`, `が`, `は`, `も`, `と`, `から`, `まで`, `より`, `へ`, `や`, `か`, `の`, `ね`, `よ`.
   - `text[i:]` starts with a sentence-final character in the configured "no-leading-final" list — defaults: `た`, `だ`, `る`, `い` when preceded by a hiragana/kanji (avoids stranding a single inflection char).

   If no valid boundary is found in the window, return `candidate_index` unchanged (current behaviour).

4. Modify `CharacterBoundarySplitProcessor` and `TimeBasedSplitProcessor` to accept a `SplitBoundaryPolicy` (constructor-injected, defaulting to `LinearSplitBoundaryPolicy`) and call `policy.adjust(...)` after computing the linear index. `WordBoundarySplitProcessor` is unchanged because it already snaps via `AlignedToken`.
5. Update `DefaultGranularityAwareProcessorFactory.create()` to inject `JapaneseSplitBoundaryPolicy` into the relevant split processors when `ctx.config.expected_language == "ja"`, and `LinearSplitBoundaryPolicy` otherwise.
6. Add `PostProcessingConfig` fields (all optional, with defaults so existing configs keep working):
   - `japanese_split_search_radius: int = 4` (chars; clamped to `[0, 20]`)
   - `japanese_split_no_split_units: list[str]` (default list above)
   - `japanese_split_no_leading_particles: list[str]` (default list above)
   - `japanese_split_no_leading_finals: list[str]` (default list above)

## Non-Goals

- Full morphological analysis (no MeCab / SudachiPy / fugashi dependency). Rule-based with character-class heuristics only — no new third-party dep.
- Tuning English / other-language split behaviour. Non-Japanese paths get `LinearSplitBoundaryPolicy` and behave exactly as today.
- Changing merge processors. Only split processors gain the policy.
- Re-splitting an already-split cue. Boundary policy runs once per split, on the original linearly-interpolated candidate.
- Changing `WordBoundarySplitProcessor` (it already uses `AlignedToken` boundaries).

## Alternatives Considered

- **Add fugashi/MeCab for true bunsetsu detection.** Rejected: introduces a heavy native dependency for a cosmetic improvement; existing rule-based audio2subtitle parity does not require it.
- **Append a separate `JapaneseSplitFixupProcessor` after the split step.** Rejected: post-hoc detection of "which adjacent cue pair came from a single split" is brittle; deciding at the split site is cleaner and keeps the original-text invariant intact.
- **Extend `JapaneseRepetitionProcessor` / `JapaneseFillerProcessor`.** Rejected: those operate on text content, not on cue boundaries — different concern.

## Impact

- Affected specs:
  - Modified: `character-boundary-processors`, `time-based-processors`, `granularity-aware-processor-factory`, `pipeline-config`
  - New: `split-boundary-policy`
- Affected code:
  - New:
    - `src/talking_parrot/post_processing/split_policy.py`
    - `tests/unit/post_processing/test_split_policy.py`
  - Modified:
    - `src/talking_parrot/post_processing/character_boundary.py`
    - `src/talking_parrot/post_processing/time_based.py`
    - `src/talking_parrot/post_processing/japanese.py`
    - `src/talking_parrot/post_processing/factory.py`
    - `src/talking_parrot/config/models.py`
    - `tests/unit/post_processing/test_character_boundary.py`
    - `tests/unit/post_processing/test_time_based.py`
    - `tests/unit/post_processing/test_japanese.py`
    - `tests/unit/post_processing/test_factory.py`
    - `tests/unit/config/test_models.py`
  - Removed: (none)
