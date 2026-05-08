## MODIFIED Requirements

### Requirement: Factory returns character-boundary group for CHARACTER granularity

When `create(AlignmentGranularity.CHARACTER, ctx)` is called, the factory SHALL return a list whose order is:

1. `DedupSubtitleProcessor` (always present).
2. `CharacterBoundaryMergeProcessor`.
3. `CharacterBoundarySplitProcessor`.
4. `JapaneseFillerProcessor` (present only when `ctx.config.expected_language == "ja"`).
5. `JapaneseRepetitionProcessor` (present only when `ctx.config.expected_language == "ja"`).

The `CharacterBoundarySplitProcessor` instance SHALL be constructed with:

- `policy` keyword: the result of `_build_policy(ctx)` (unchanged).
- `time_policy` keyword: the result of `_build_time_policy(ctx)` (unchanged).
- `token_map_by_index` keyword: the result of `_build_token_map(ctx.transcription_results)` (same helper already used for the WORD path).

#### Scenario: CHARACTER with Japanese returns full pipeline

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the result length MUST equal 5
- **AND** `isinstance(result[0], DedupSubtitleProcessor)` MUST be true
- **AND** `isinstance(result[1], CharacterBoundaryMergeProcessor)` MUST be true
- **AND** `isinstance(result[2], CharacterBoundarySplitProcessor)` MUST be true
- **AND** `isinstance(result[3], JapaneseFillerProcessor)` MUST be true
- **AND** `isinstance(result[4], JapaneseRepetitionProcessor)` MUST be true

#### Scenario: CHARACTER with non-Japanese omits Japanese processors

- **GIVEN** `ctx.config.expected_language == "zh"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the result length MUST equal 3 with no `JapaneseFillerProcessor` or `JapaneseRepetitionProcessor` instance present

#### Scenario: CHARACTER path injects token map into CharacterBoundarySplitProcessor

- **GIVEN** `ctx.transcription_results` of length 2 with non-empty `aligned_tokens`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the `CharacterBoundarySplitProcessor` instance at `result[2]` MUST have `token_map_by_index` with keys `{1, 2}`
