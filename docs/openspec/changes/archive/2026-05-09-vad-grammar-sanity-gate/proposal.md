## Why

VAD-driven cue split (introduced by `vad-driven-cue-split`) bypasses the grammar sanity check that `JapaneseSplitBoundaryPolicy` was designed to enforce. When a VAD silence midpoint falls inside a Japanese auxiliary or verb conjugation, aligned tokens faithfully map the millisecond timestamp to a morpheme-internal `char_idx`, producing observably wrong cuts (e.g., `専攻しておりまし／た`, `覚えていま／す` from `test-samples/sample1`, 2026-05-08 manual review). The grammar layer must be reintroduced as a sanity gate without surrendering VAD as the primary signal. Design rationale and worked examples live in `docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md`.

## What Changes

- Promote `JapaneseSplitBoundaryPolicy._is_valid` into a public `is_valid(text, index) -> bool` method on the `SplitBoundaryPolicy` protocol. `LinearSplitBoundaryPolicy.is_valid` always returns `True` (preserves LSP for non-Japanese pipelines).
- Refactor `CharacterBoundarySplitProcessor` to use a three-stage decision after deriving `char_idx_vad` from `SplitTimePolicy.adjust` + aligned tokens:
  1. If `boundary_policy.is_valid(text, char_idx_vad)` → use `char_idx_vad` (happy path, no log).
  2. Else call `boundary_policy.adjust(text, char_idx_vad, vad_grammar_search_radius)` to snap to the nearest valid boundary in a small radius. If snap succeeds, log INFO `grammar_snap`.
  3. Else fall back to the linear midpoint as candidate, call `boundary_policy.adjust` with the existing larger fallback radius, and log INFO `grammar_fallback`.
- Add `PostProcessingConfig.vad_grammar_search_radius: int = 2` (validated `>= 0`).
- Emit structured INFO logs for paths 2 and 3 with fields: `cue_id`, `char_idx_vad`, `char_idx_final`, `fallback_reason` (`grammar_snap` | `grammar_fallback`).

## Non-Goals

- Expanding `JapaneseSplitBoundaryPolicy.is_valid` rules (compound-word / kanji-dictionary protection from `docs/TODOs.md`) — deliberately deferred. This change only wires the sanity gate; rule expansion is a separate change that will benefit automatically once this lands.
- Refactoring `WordBoundarySplitProcessor` or `TimeBasedSplitProcessor` — only the character-boundary processor uses VAD-driven char_idx derivation today.
- Changing `SplitTimePolicy` or `VadAlignedSplitTimePolicy` behavior — VAD silence selection logic is unchanged.
- Replacing the existing `_is_valid` rule set with a morphological analyzer — out of scope per ADR-0003 decision 4 (rule-based, no new dependency).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `split-boundary-policy`: Protocol gains a public `is_valid(text, index) -> bool` method. `LinearSplitBoundaryPolicy` and `JapaneseSplitBoundaryPolicy` implementations expose it.
- `character-boundary-processors`: `CharacterBoundarySplitProcessor` adopts the valid → snap → fallback three-stage decision and emits structured INFO logs for the snap / fallback branches.
- `pipeline-config`: `PostProcessingConfig` gains `vad_grammar_search_radius: int = 2` with validation `>= 0`.

## Impact

- Affected specs: `split-boundary-policy`, `character-boundary-processors`, `pipeline-config`
- Affected code:
  - Modified:
    - src/talking_parrot/post_processing/split_policy.py
    - src/talking_parrot/post_processing/japanese.py
    - src/talking_parrot/post_processing/character_boundary.py
    - src/talking_parrot/config/models.py
  - New: (none)
  - Removed: (none)
- Affected tests:
  - Modified:
    - tests/unit/post_processing/test_split_policy.py
    - tests/unit/post_processing/test_japanese.py
    - tests/unit/post_processing/test_character_boundary.py
    - tests/unit/config/test_models.py
- Logging: new INFO log events `grammar_snap` and `grammar_fallback` from `character_boundary.py`. No log schema changes elsewhere.
- Configuration: new YAML field `post_processing.vad_grammar_search_radius` (defaults to `2`); existing configs without the field continue to work unchanged.
