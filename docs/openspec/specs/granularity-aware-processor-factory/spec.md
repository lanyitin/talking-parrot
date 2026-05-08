# granularity-aware-processor-factory Specification

## Purpose

TBD - created by archiving change 'implement-post-processing-stage'. Update Purpose after archive.

## Requirements

### Requirement: GranularityAwareProcessorFactory interface and concrete implementation

The system SHALL provide an abstract `GranularityAwareProcessorFactory` (in `src/talking_parrot/post_processing/factory.py`) declaring `create(granularity: AlignmentGranularity | None, ctx: PipelineContext) -> list[SubtitleProcessor]`. The system SHALL also provide a concrete implementation `DefaultGranularityAwareProcessorFactory` that returns ordered processor lists per the rules below. Direct instantiation of the abstract class MUST raise `TypeError`.

#### Scenario: Abstract base cannot be instantiated

- **WHEN** code calls `GranularityAwareProcessorFactory()` directly
- **THEN** Python MUST raise `TypeError`


<!-- @trace
source: implement-post-processing-stage
updated: 2026-05-02
code:
  - src/talking_parrot/config/models.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/cli.py
  - tests/unit/io/subtitle_export/__init__.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - tests/unit/post_processing/__init__.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/__init__.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/config/test_export_config.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/stages/test_post_processing_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_character_boundary.py
-->

---
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


<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->

---
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


<!-- @trace
source: vad-driven-cue-split
updated: 2026-05-08
code:
  - uv.lock
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - pyproject.toml
tests:
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
-->

---
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


<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->

---
### Requirement: Factory raises on unknown granularity

If a future caller passes an `AlignmentGranularity` value not handled by the factory (i.e., neither `WORD` nor `CHARACTER` nor `None`), the factory SHALL raise `ValueError` with a message containing the offending value's name. This guards the OCP closure point declared in ADR-0003.

#### Scenario: Unknown granularity raises ValueError

- **GIVEN** a hypothetical extension `AlignmentGranularity.SYLLABLE`
- **WHEN** `factory.create(AlignmentGranularity.SYLLABLE, ctx)` is called
- **THEN** `ValueError` MUST be raised
- **AND** the message MUST contain `"SYLLABLE"`


<!-- @trace
source: implement-post-processing-stage
updated: 2026-05-02
code:
  - src/talking_parrot/config/models.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/cli.py
  - tests/unit/io/subtitle_export/__init__.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - tests/unit/post_processing/__init__.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/__init__.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/config/test_export_config.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/stages/test_post_processing_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_character_boundary.py
-->

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

<!-- @trace
source: implement-post-processing-stage
updated: 2026-05-02
code:
  - src/talking_parrot/config/models.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/cli.py
  - tests/unit/io/subtitle_export/__init__.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - tests/unit/post_processing/__init__.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/__init__.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/config/test_export_config.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/stages/test_post_processing_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_character_boundary.py
-->

---
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


<!-- @trace
source: snap-split-timestamps-to-vad-silence
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/config/test_models.py
-->

---
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

<!-- @trace
source: snap-split-timestamps-to-vad-silence
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/config/test_models.py
-->