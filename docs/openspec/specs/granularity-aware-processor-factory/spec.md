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