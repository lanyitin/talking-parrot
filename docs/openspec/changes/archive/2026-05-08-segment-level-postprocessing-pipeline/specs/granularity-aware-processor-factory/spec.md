## MODIFIED Requirements

### Requirement: Factory returns word-boundary group for WORD granularity

When `create(AlignmentGranularity.WORD, ctx)` is called, the factory SHALL return a list whose order is:

1. `DedupSubtitleProcessor` (always present; reads `dedup_*` fields from `ctx.config.post_processing`).
2. `WordBoundaryMergeProcessor`.
3. `WordBoundarySplitProcessor`.
4. `JapaneseFillerProcessor` (present only when `ctx.config.expected_language == "ja"`).
5. `JapaneseRepetitionProcessor` (present only when `ctx.config.expected_language == "ja"`).

For non-Japanese languages the returned list has length 3 (`[Dedup, Merge, Split]`); for Japanese it has length 5.

#### Scenario: WORD with non-Japanese language returns dedup + merge + split

- **GIVEN** `ctx.config.expected_language == "en"`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the result length MUST equal 3
- **AND** `isinstance(result[0], DedupSubtitleProcessor)` MUST be true
- **AND** `isinstance(result[1], WordBoundaryMergeProcessor)` MUST be true
- **AND** `isinstance(result[2], WordBoundarySplitProcessor)` MUST be true

#### Scenario: WORD with Japanese appends filler + repetition processors

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the result length MUST equal 5
- **AND** `isinstance(result[3], JapaneseFillerProcessor)` MUST be true
- **AND** `isinstance(result[4], JapaneseRepetitionProcessor)` MUST be true

### Requirement: Factory returns character-boundary group for CHARACTER granularity

When `create(AlignmentGranularity.CHARACTER, ctx)` is called, the factory SHALL return a list whose order is:

1. `DedupSubtitleProcessor` (always present).
2. `CharacterBoundaryMergeProcessor`.
3. `CharacterBoundarySplitProcessor`.
4. `JapaneseFillerProcessor` (present only when `ctx.config.expected_language == "ja"`).
5. `JapaneseRepetitionProcessor` (present only when `ctx.config.expected_language == "ja"`).

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

### Requirement: Factory returns time-based group for None

When `create(None, ctx)` is called, the factory SHALL return a list whose order is:

1. `DedupSubtitleProcessor` (always present).
2. `TimeBasedMergeProcessor`.
3. `TimeBasedSplitProcessor`.
4. `JapaneseFillerProcessor` (present only when `ctx.config.expected_language == "ja"`).
5. `JapaneseRepetitionProcessor` (present only when `ctx.config.expected_language == "ja"`).

#### Scenario: None returns time-based fallback with dedup prefix

- **WHEN** `factory.create(None, ctx)` with `ctx.config.expected_language == "en"` is called
- **THEN** the result length MUST equal 3
- **AND** `isinstance(result[0], DedupSubtitleProcessor)` MUST be true
- **AND** `isinstance(result[1], TimeBasedMergeProcessor)` MUST be true
- **AND** `isinstance(result[2], TimeBasedSplitProcessor)` MUST be true
