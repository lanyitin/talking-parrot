## MODIFIED Requirements

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
