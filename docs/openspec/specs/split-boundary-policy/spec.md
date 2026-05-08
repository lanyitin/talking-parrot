# split-boundary-policy Specification

## Purpose

TBD - created by archiving change 'japanese-aware-cue-split'. Update Purpose after archive.

## Requirements

### Requirement: SplitBoundaryPolicy protocol defines the snap interface

The system SHALL provide a `SplitBoundaryPolicy` protocol (in `src/talking_parrot/post_processing/split_policy.py`) declaring a single method:

```python
def adjust(self, text: str, candidate_index: int, search_radius: int) -> int
```

`adjust` SHALL accept the cue text, the linearly-interpolated split index produced by the calling processor, and a search radius in characters. It SHALL return an integer in the closed interval `[1, len(text) - 1]`. Implementations MUST NOT mutate `text`. The protocol SHALL NOT be instantiable directly; it is a structural type used for dependency injection.

#### Scenario: Returned index is a valid slice point

- **GIVEN** any `SplitBoundaryPolicy` implementation, a non-empty `text` of length `n >= 2`, a `candidate_index` in `[1, n - 1]`, and `search_radius >= 0`
- **WHEN** `policy.adjust(text, candidate_index, search_radius)` is called
- **THEN** the returned integer MUST be in the closed interval `[1, n - 1]`


<!-- @trace
source: japanese-aware-cue-split
updated: 2026-05-08
code:
  - CLAUDE.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/japanese.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/post_processing/dedup.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/stages/transcription_stage.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
tests:
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/config/test_loader.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_dedup.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/post_processing/test_split_policy.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/post_processing/test_japanese.py
-->

---
### Requirement: LinearSplitBoundaryPolicy returns the candidate unchanged

The system SHALL provide a concrete `LinearSplitBoundaryPolicy` (in `src/talking_parrot/post_processing/split_policy.py`) whose `adjust(text, candidate_index, search_radius)` SHALL return `candidate_index` unmodified. This is the default policy used for non-Japanese pipelines and preserves the historical linear-interpolation split behaviour.

#### Scenario: Default policy is a no-op

- **GIVEN** `policy = LinearSplitBoundaryPolicy()` and `text = "abcdefgh"`, `candidate_index = 4`, `search_radius = 3`
- **WHEN** `policy.adjust(text, candidate_index, search_radius)` is called
- **THEN** the returned integer MUST equal `4`

##### Example: search radius is ignored

- **GIVEN** the same policy and any non-negative `search_radius`
- **WHEN** `adjust` is called with the same `text` and `candidate_index`
- **THEN** the returned value MUST equal `candidate_index`, regardless of `search_radius`


<!-- @trace
source: japanese-aware-cue-split
updated: 2026-05-08
code:
  - CLAUDE.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/japanese.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/post_processing/dedup.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/stages/transcription_stage.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
tests:
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/config/test_loader.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_dedup.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/post_processing/test_split_policy.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/post_processing/test_japanese.py
-->

---
### Requirement: JapaneseSplitBoundaryPolicy snaps to nearest valid grammar boundary

The system SHALL provide a concrete `JapaneseSplitBoundaryPolicy` (in `src/talking_parrot/post_processing/japanese.py`) constructed with a `PostProcessingConfig` instance from which it reads `japanese_split_no_split_units`, `japanese_split_no_leading_particles`, and `japanese_split_no_leading_finals`.

When `adjust(text, candidate_index, search_radius)` is called, the policy SHALL:

1. Build the candidate window `W = [max(1, candidate_index - search_radius), min(len(text) - 1, candidate_index + search_radius)]`. If `W` is empty, the policy SHALL return `candidate_index`.
2. For each integer `i` in `W` (including `candidate_index` itself), evaluate boundary validity. Index `i` is INVALID if any of these hold:
   - **Mid-katakana**: `text[i-1]` is katakana (`U+30A0`-`U+30FF` or `U+31F0`-`U+31FF`) AND `text[i]` is katakana.
   - **Mid-digit**: `text[i-1]` matches `[0-9０-９]` AND `text[i]` matches `[0-9０-９]`.
   - **Mid-no-split-unit**: there exists a configured no-split-unit string `u` and an offset `k` with `1 <= k <= len(u) - 1` such that `text[i-k:i-k+len(u)] == u`. (i.e., the cut would fall inside one of the configured units.)
   - **Leading-particle**: `text[i:]` starts with any configured no-leading-particle string.
   - **Leading-final**: `text[i:]` starts with any configured no-leading-final string AND `text[i-1]` is hiragana (`U+3040`-`U+309F`) or kanji (`U+4E00`-`U+9FFF`).
3. From valid indices in `W`, return the one with smallest `abs(i - candidate_index)`. Ties SHALL be broken deterministically as follows:
   - If `candidate_index` is straddled by any configured no-split unit (i.e., the Mid-no-split-unit rule fires at `candidate_index` for some unit `u`), the policy SHALL prefer the LARGER index. This snaps PAST the unit so it trails the previous cue rather than leading the next one (e.g., `「覚えています」` stays whole instead of producing `「覚えてい / ます…」`).
   - Otherwise the policy SHALL prefer the SMALLER index.
4. If no valid index exists in `W`, the policy SHALL return `candidate_index` unchanged.

If `search_radius == 0`, the only candidate in `W` is `candidate_index` itself; the policy SHALL apply step 2 and return `candidate_index` whether valid or not (operationally equivalent to the linear policy).

#### Scenario: Snap moves split off mid-auxiliary boundary

- **GIVEN** `text = "専攻しておりました"` (length 9), `candidate_index = 7` (which would split between `まし` and `た`), `search_radius = 3`, default config
- **WHEN** `JapaneseSplitBoundaryPolicy(config).adjust(text, 7, 3)` is called
- **THEN** the returned index MUST NOT equal `7`
- **AND** the returned index MUST be in `[4, 9]`
- **AND** the returned index MUST be one where `text[index-1:index+1]` is not `"まし"` and `text[index:]` does not start with `"た"` preceded by a hiragana (i.e., the `Leading-final` rule does not flag it)

#### Scenario: No valid boundary in window falls back to candidate

- **GIVEN** `text = "カタカナテスト"` (all katakana, length 7), `candidate_index = 3`, `search_radius = 2`
- **WHEN** `adjust` is called
- **THEN** every index in `[1, 5]` is invalid by the Mid-katakana rule
- **AND** the returned integer MUST equal `3`

#### Scenario: Search radius zero is a no-op

- **GIVEN** any `text`, any `candidate_index`, `search_radius = 0`, any config
- **WHEN** `adjust` is called
- **THEN** the returned integer MUST equal `candidate_index`

##### Example: leading-particle rule snaps before a particle

- **GIVEN** `text = "印象深いのは"` (length 6), `candidate_index = 3` (would split before `い`), `search_radius = 2`, default config (which forbids leading-final `い` after hiragana/kanji)
- **WHEN** `adjust(text, 3, 2)` is called
- **THEN** the returned index MUST NOT be `3`
- **AND** the returned index MUST be a valid boundary in `[1, 5]`

#### Scenario: Tie-break snaps PAST a straddling no-split unit

- **GIVEN** `text = "覚えています 卒業"` (length 9), `candidate_index = 5` (cuts inside `ます`, which is a configured no-split unit), `search_radius = 2`, default config
- **WHEN** `adjust(text, 5, 2)` is called
- **THEN** the candidate window is `[3, 7]` and the valid indices are `{4, 6, 7}`
- **AND** indices `4` and `6` are equidistant from `5` (distance `1`)
- **AND** because `candidate_index = 5` is straddled by the no-split unit `ます`, the returned index MUST equal `6` (the larger of the tied indices), so `「ます」` trails the previous cue instead of leading the next one

<!-- @trace
source: straddle-aware-tie-break
updated: 2026-05-09
code:
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/japanese.py
  - docs/architecture/index.md
  - src/talking_parrot/config/models.py
  - docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md
  - src/talking_parrot/post_processing/split_policy.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/config/test_loader.py
  - tests/unit/post_processing/test_split_policy.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/post_processing/test_character_boundary.py
-->

---
### Requirement: SplitBoundaryPolicy protocol declares public is_valid method

The `SplitBoundaryPolicy` protocol (in `src/talking_parrot/post_processing/split_policy.py`) SHALL declare an additional method:

```python
def is_valid(self, text: str, index: int) -> bool
```

`is_valid` SHALL accept the cue text and a candidate split index, and SHALL return `True` if the implementation considers `index` a valid (non-forbidden) cut point inside `text`, otherwise `False`. Implementations MUST be pure (no side effects) and MUST NOT mutate `text`. The method SHALL be safely callable for any integer `index` in `[1, len(text) - 1]`; behavior outside that range is unspecified and callers SHALL clamp the input first.

The protocol contract SHALL satisfy: for any implementation `P`, if `P.is_valid(text, i)` returns `True`, then `P.adjust(text, i, 0)` SHALL return `i`. (i.e., a valid index is a fixed point of `adjust` at radius 0.)

#### Scenario: Valid index is a fixed point of adjust at radius 0

- **GIVEN** any `SplitBoundaryPolicy` implementation `P`, a non-empty `text` of length `n >= 2`, and an index `i` in `[1, n - 1]`
- **WHEN** `P.is_valid(text, i)` returns `True`
- **THEN** `P.adjust(text, i, 0)` MUST return `i`

#### Scenario: is_valid is pure

- **GIVEN** any `SplitBoundaryPolicy` implementation `P` and inputs `text`, `i`
- **WHEN** `P.is_valid(text, i)` is called twice with identical arguments
- **THEN** both calls MUST return the same boolean value
- **AND** `text` MUST NOT be mutated


<!-- @trace
source: vad-grammar-sanity-gate
updated: 2026-05-09
code:
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/config/models.py
  - docs/architecture/index.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/japanese.py
  - docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md
tests:
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/config/test_loader.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/post_processing/test_split_policy.py
-->

---
### Requirement: LinearSplitBoundaryPolicy.is_valid always returns True

`LinearSplitBoundaryPolicy.is_valid(text, index)` SHALL return `True` for every input where `1 <= index <= len(text) - 1`. This preserves Liskov substitutability: the linear policy treats every in-range index as a valid cut point, matching its no-op `adjust` behavior.

#### Scenario: Linear policy considers any in-range index valid

- **GIVEN** `policy = LinearSplitBoundaryPolicy()` and `text = "abcdefgh"` (length 8)
- **WHEN** `policy.is_valid(text, i)` is called for every `i` in `[1, 7]`
- **THEN** every call MUST return `True`


<!-- @trace
source: vad-grammar-sanity-gate
updated: 2026-05-09
code:
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/config/models.py
  - docs/architecture/index.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/japanese.py
  - docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md
tests:
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/config/test_loader.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/post_processing/test_split_policy.py
-->

---
### Requirement: JapaneseSplitBoundaryPolicy.is_valid exposes the existing rule check

`JapaneseSplitBoundaryPolicy.is_valid(text, index)` SHALL return `False` if and only if `index` is INVALID under the rule set already defined for `JapaneseSplitBoundaryPolicy.adjust` (the union of Mid-katakana, Mid-digit, Mid-no-split-unit, Leading-particle, and Leading-final rules, evaluated against the policy's configured `japanese_split_no_split_units`, `japanese_split_no_leading_particles`, and `japanese_split_no_leading_finals`). Otherwise `is_valid` SHALL return `True`.

The implementation SHALL share its rule evaluation with `adjust` such that the two methods cannot disagree (e.g., by routing both through a single internal predicate).

#### Scenario: Mid-auxiliary index is invalid

- **GIVEN** `policy = JapaneseSplitBoundaryPolicy(default_config)` and `text = "専攻しておりました"` (length 9)
- **WHEN** `policy.is_valid(text, 8)` is called (would split between `まし` and `た`; `text[7]='し'` is hiragana and `text[8:]` starts with `た` which is a configured leading-final)
- **THEN** the return value MUST be `False`

#### Scenario: Boundary outside any forbidden rule is valid

- **GIVEN** the same `policy` and `text = "専攻しておりました"`
- **WHEN** `policy.is_valid(text, 2)` is called (boundary between `専攻` and `してお…`; no rule triggered)
- **THEN** the return value MUST be `True`

#### Scenario: is_valid agrees with adjust at radius 0

- **GIVEN** `policy = JapaneseSplitBoundaryPolicy(default_config)`, any `text`, any `index` in `[1, len(text) - 1]`
- **WHEN** `policy.is_valid(text, index)` returns `True`
- **THEN** `policy.adjust(text, index, 0)` MUST return `index`
- **AND** when `policy.is_valid(text, index)` returns `False`, `policy.adjust(text, index, 0)` MUST also return `index` (per existing radius-0 no-op rule), but the index remains semantically invalid

<!-- @trace
source: vad-grammar-sanity-gate
updated: 2026-05-09
code:
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/config/models.py
  - docs/architecture/index.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/japanese.py
  - docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md
tests:
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/config/test_loader.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/post_processing/test_split_policy.py
-->