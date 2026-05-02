## ADDED Requirements

### Requirement: GranularityAwareProcessorFactory interface and concrete implementation

The system SHALL provide an abstract `GranularityAwareProcessorFactory` (in `src/talking_parrot/post_processing/factory.py`) declaring `create(granularity: AlignmentGranularity | None, ctx: PipelineContext) -> list[SubtitleProcessor]`. The system SHALL also provide a concrete implementation `DefaultGranularityAwareProcessorFactory` that returns ordered processor lists per the rules below. Direct instantiation of the abstract class MUST raise `TypeError`.

#### Scenario: Abstract base cannot be instantiated

- **WHEN** code calls `GranularityAwareProcessorFactory()` directly
- **THEN** Python MUST raise `TypeError`

---

### Requirement: Factory returns word-boundary group for WORD granularity

When `create(AlignmentGranularity.WORD, ctx)` is called, the factory SHALL return a list of length 2 whose first element is an instance of `WordBoundaryMergeProcessor` and whose second element is an instance of `WordBoundarySplitProcessor`, in that order.

#### Scenario: WORD returns merge then split

- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the result length MUST equal 2
- **AND** `isinstance(result[0], WordBoundaryMergeProcessor)` MUST be true
- **AND** `isinstance(result[1], WordBoundarySplitProcessor)` MUST be true

---

### Requirement: Factory returns character-boundary group for CHARACTER granularity

When `create(AlignmentGranularity.CHARACTER, ctx)` is called, the factory SHALL return a list of length 2 whose first element is an instance of `CharacterBoundaryMergeProcessor` and whose second element is an instance of `CharacterBoundarySplitProcessor`, in that order.

#### Scenario: CHARACTER returns merge then split

- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the result length MUST equal 2
- **AND** `isinstance(result[0], CharacterBoundaryMergeProcessor)` MUST be true
- **AND** `isinstance(result[1], CharacterBoundarySplitProcessor)` MUST be true

---

### Requirement: Factory returns time-based group for None

When `create(None, ctx)` is called, the factory SHALL return a list of length 2 whose first element is an instance of `TimeBasedMergeProcessor` and whose second element is an instance of `TimeBasedSplitProcessor`, in that order.

#### Scenario: None returns time-based fallback

- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the result length MUST equal 2
- **AND** `isinstance(result[0], TimeBasedMergeProcessor)` MUST be true
- **AND** `isinstance(result[1], TimeBasedSplitProcessor)` MUST be true

---

### Requirement: Factory raises on unknown granularity

If a future caller passes an `AlignmentGranularity` value not handled by the factory (i.e., neither `WORD` nor `CHARACTER` nor `None`), the factory SHALL raise `ValueError` with a message containing the offending value's name. This guards the OCP closure point declared in ADR-0003.

#### Scenario: Unknown granularity raises ValueError

- **GIVEN** a hypothetical extension `AlignmentGranularity.SYLLABLE`
- **WHEN** `factory.create(AlignmentGranularity.SYLLABLE, ctx)` is called
- **THEN** `ValueError` MUST be raised
- **AND** the message MUST contain `"SYLLABLE"`

---

### Requirement: WORD-group processors receive token map from factory

When `create(AlignmentGranularity.WORD, ctx)` is called, the factory SHALL build a `dict[int, list[AlignedToken]]` mapping each seed `Subtitle.index` (1-based, matching `i + 1` for `transcription_results[i]`) to that result's `aligned_tokens`. This map SHALL be injected into both `WordBoundaryMergeProcessor` and `WordBoundarySplitProcessor` via constructor argument `token_map_by_index`. If a `TranscriptionResult.aligned_tokens` is `None` or empty, the corresponding map entry SHALL be `[]`.

#### Scenario: Token map keys match seed indices

- **GIVEN** `ctx.transcription_results` of length 3 with non-empty `aligned_tokens`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the constructed merge processor's `token_map_by_index` MUST have keys `{1, 2, 3}`

##### Example: missing tokens map to empty list

- **GIVEN** `ctx.transcription_results = [TR(aligned_tokens=[t1, t2]), TR(aligned_tokens=None)]`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** `token_map_by_index[1]` MUST equal `[t1, t2]`
- **AND** `token_map_by_index[2]` MUST equal `[]`
