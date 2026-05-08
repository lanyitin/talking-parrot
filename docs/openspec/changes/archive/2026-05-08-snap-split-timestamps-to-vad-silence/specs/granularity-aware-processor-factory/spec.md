## ADDED Requirements

### Requirement: Factory injects SplitTimePolicy into split processors based on VAD context

`DefaultGranularityAwareProcessorFactory.create(granularity, ctx)` SHALL construct a `SplitTimePolicy` instance and pass it to `CharacterBoundarySplitProcessor` (when `granularity == AlignmentGranularity.CHARACTER`) and to `TimeBasedSplitProcessor` (when `granularity is None`) via the constructor's `time_policy` keyword argument.

The chosen time policy SHALL be derived as follows:

1. Let `pp = ctx.config.post_processing or PostProcessingConfig()`.
2. Let `radius_ms = pp.split_time_snap_radius_ms`.
3. Let `silences = [(ctx.vad_segments[i].end_ms, ctx.vad_segments[i + 1].start_ms) for i in range(len(ctx.vad_segments) - 1) if ctx.vad_segments[i + 1].start_ms > ctx.vad_segments[i].end_ms]`.
4. If `radius_ms > 0` AND `len(silences) > 0`, return `VadAlignedSplitTimePolicy(silences=silences, search_radius_ms=radius_ms)`.
5. Otherwise, return `LinearSplitTimePolicy()`.

`WordBoundarySplitProcessor` SHALL NOT receive a `SplitTimePolicy`. The factory SHALL NOT pass any `time_policy` keyword argument to the word-boundary path.

The factory's selection of `SplitTimePolicy` SHALL be independent of `ctx.config.expected_language`; the snap behaviour applies to every language whose pipeline produces non-empty `vad_segments` and whose configuration has `split_time_snap_radius_ms > 0`.

#### Scenario: CHARACTER + non-empty VAD + radius > 0 injects VadAlignedSplitTimePolicy

- **GIVEN** `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1500, 3000, ...)]` and `ctx.config.post_processing.split_time_snap_radius_ms = 250`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a `time_policy` of type `VadAlignedSplitTimePolicy`

#### Scenario: None granularity + non-empty VAD + radius > 0 injects VadAlignedSplitTimePolicy

- **GIVEN** `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1500, 3000, ...)]` and `ctx.config.post_processing.split_time_snap_radius_ms = 250`
- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the returned list's `TimeBasedSplitProcessor` instance MUST hold a `time_policy` of type `VadAlignedSplitTimePolicy`

#### Scenario: Empty vad_segments injects LinearSplitTimePolicy

- **GIVEN** `ctx.vad_segments = []` and `ctx.config.post_processing.split_time_snap_radius_ms = 250`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a `time_policy` of type `LinearSplitTimePolicy`

#### Scenario: Zero radius injects LinearSplitTimePolicy

- **GIVEN** `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1500, 3000, ...)]` and `ctx.config.post_processing.split_time_snap_radius_ms = 0`
- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the returned list's `TimeBasedSplitProcessor` instance MUST hold a `time_policy` of type `LinearSplitTimePolicy`

#### Scenario: WORD granularity does not receive a SplitTimePolicy

- **GIVEN** any `ctx`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the returned list's `WordBoundarySplitProcessor` constructor MUST NOT have been called with any `time_policy` keyword argument

#### Scenario: Non-positive gaps between segments are filtered

- **GIVEN** `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1000, 2000, ...), VadSegment(1900, 3000, ...)]` (back-to-back, then overlapping) and `radius_ms = 250`
- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the derived silence list MUST be empty
- **AND** the returned `time_policy` MUST be of type `LinearSplitTimePolicy` (per Decision 3's fallback when no silences exist)

##### Example: Single qualifying gap

- **GIVEN** `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1500, 3000, ...), VadSegment(3000, 4000, ...)]`
- **WHEN** the factory derives silences
- **THEN** the silences list MUST equal `[(1000, 1500)]` (the back-to-back gap between segments 2 and 3 is filtered)

## MODIFIED Requirements

### Requirement: Factory injects SplitBoundaryPolicy into split processors based on language

`DefaultGranularityAwareProcessorFactory.create(granularity, ctx)` SHALL construct a `SplitBoundaryPolicy` instance and pass it to `CharacterBoundarySplitProcessor` (when `granularity == AlignmentGranularity.CHARACTER`) and to `TimeBasedSplitProcessor` (when `granularity is None`) via the constructor's `policy` keyword argument.

The chosen policy SHALL be:

- `JapaneseSplitBoundaryPolicy(ctx.config.post_processing)` when `ctx.config.expected_language == "ja"`.
- `LinearSplitBoundaryPolicy()` for all other language values, including `None` and the empty string.

`WordBoundarySplitProcessor` SHALL NOT receive a `SplitBoundaryPolicy` (it already snaps via `AlignedToken` data). The factory SHALL NOT pass any `policy` keyword to the word-boundary path.

The language match SHALL be exact-string `"ja"` (case-sensitive), consistent with the existing `Factory returns word-boundary group for WORD granularity`, `Factory returns character-boundary group for CHARACTER granularity`, and `Factory returns time-based group for None` requirements.

The `policy` (boundary) and `time_policy` (time) keyword arguments SHALL be independent: the factory SHALL select each via its own decision rule and pass both to the same processor instance in a single constructor call.

#### Scenario: CHARACTER + Japanese injects JapaneseSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a boundary policy of type `JapaneseSplitBoundaryPolicy`

#### Scenario: CHARACTER + non-Japanese injects LinearSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "en"`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a boundary policy of type `LinearSplitBoundaryPolicy`

#### Scenario: None granularity + Japanese injects JapaneseSplitBoundaryPolicy

- **GIVEN** `ctx.config.expected_language == "ja"`
- **WHEN** `factory.create(None, ctx)` is called
- **THEN** the returned list's `TimeBasedSplitProcessor` instance MUST hold a boundary policy of type `JapaneseSplitBoundaryPolicy`

#### Scenario: WORD granularity does not receive a SplitBoundaryPolicy

- **GIVEN** any `ctx`
- **WHEN** `factory.create(AlignmentGranularity.WORD, ctx)` is called
- **THEN** the returned list's `WordBoundarySplitProcessor` constructor MUST NOT have been called with any `policy` keyword argument

#### Scenario: Boundary policy and time policy are passed in the same constructor call

- **GIVEN** `ctx.config.expected_language == "ja"`, `ctx.vad_segments = [VadSegment(0, 1000, ...), VadSegment(1500, 3000, ...)]`, and `ctx.config.post_processing.split_time_snap_radius_ms = 250`
- **WHEN** `factory.create(AlignmentGranularity.CHARACTER, ctx)` is called
- **THEN** the returned list's `CharacterBoundarySplitProcessor` instance MUST hold a boundary policy of type `JapaneseSplitBoundaryPolicy`
- **AND** the same instance MUST hold a `time_policy` of type `VadAlignedSplitTimePolicy`

<!-- @trace
source: snap-split-timestamps-to-vad-silence
-->
