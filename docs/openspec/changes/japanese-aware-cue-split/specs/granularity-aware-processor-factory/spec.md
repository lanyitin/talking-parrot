## ADDED Requirements

### Requirement: Factory injects SplitBoundaryPolicy into split processors based on language

`DefaultGranularityAwareProcessorFactory.create(granularity, ctx)` SHALL construct a `SplitBoundaryPolicy` instance and pass it to `CharacterBoundarySplitProcessor` (when `granularity == AlignmentGranularity.CHARACTER`) and to `TimeBasedSplitProcessor` (when `granularity is None`).

The chosen policy SHALL be:

- `JapaneseSplitBoundaryPolicy(ctx.config.post_processing)` when `ctx.config.expected_language == "ja"`.
- `LinearSplitBoundaryPolicy()` for all other language values, including `None` and the empty string.

`WordBoundarySplitProcessor` SHALL NOT receive a `SplitBoundaryPolicy` (it already snaps via `AlignedToken` data). The factory SHALL NOT pass any policy keyword to the word-boundary path.

The language match SHALL be exact-string `"ja"` (case-sensitive), consistent with the existing `Factory returns word-boundary group for WORD granularity`, `Factory returns character-boundary group for CHARACTER granularity`, and `Factory returns time-based group for None` requirements.

#### Scenario: CHARACTER + Japanese injects JapaneseSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a policy of type `JapaneseSplitBoundaryPolicy`

#### Scenario: CHARACTER + non-Japanese injects LinearSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "en"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a policy of type `LinearSplitBoundaryPolicy`

#### Scenario: None granularity + Japanese injects JapaneseSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the returned list's `TimeBasedSplitProcessor` instance MUST hold a policy of type `JapaneseSplitBoundaryPolicy`

#### Scenario: WORD granularity does not receive a SplitBoundaryPolicy

- **GIVEN** any `ctx`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the returned list's `WordBoundarySplitProcessor` constructor MUST NOT have been called with any `policy` keyword argument

