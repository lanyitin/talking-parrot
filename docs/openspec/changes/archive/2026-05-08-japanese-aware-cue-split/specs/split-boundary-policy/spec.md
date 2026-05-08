## ADDED Requirements

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
3. From valid indices in `W`, return the one with smallest `abs(i - candidate_index)`. Ties SHALL be broken by preferring the smaller index for determinism.
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

