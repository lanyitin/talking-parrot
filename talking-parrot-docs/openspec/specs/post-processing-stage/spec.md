# post-processing-stage Specification

## Purpose

TBD - created by archiving change 'implement-post-processing-stage'. Update Purpose after archive.

## Requirements

### Requirement: PostProcessingStage exposes name and constructor injection

The system SHALL provide `PostProcessingStage(PipelineStage)` constructed with a single argument `(processor_factory: GranularityAwareProcessorFactory)`. Its `name` property SHALL return the literal string `"post_processing"`. The stage MUST NOT mutate the input `PipelineContext`; it MUST return a new context via `dataclasses.replace`.

#### Scenario: Name property returns post_processing

- **WHEN** an instantiated `PostProcessingStage`'s `name` property is read
- **THEN** the value MUST equal `"post_processing"`

#### Scenario: Input context is not mutated

- **GIVEN** a `PipelineContext` instance `ctx_in`
- **WHEN** `PostProcessingStage.process(ctx_in)` is called
- **THEN** the returned context MUST be a different object from `ctx_in`
- **AND** `ctx_in.subtitles` MUST be unchanged


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
### Requirement: PostProcessingStage disabled-path

When `ctx.config.post_processing is None` OR `ctx.config.post_processing.enabled is False`, `PostProcessingStage.process(ctx)` SHALL return a new context whose `subtitles` field contains exactly one `Subtitle` per `TranscriptionResult` in `ctx.transcription_results`, with indices renumbered to `1..N`, `start_ms` and `end_ms` copied from the source result, and `text` copied from `result.text`. The processor factory MUST NOT be consulted in the disabled path.

#### Scenario: post_processing config absent emits seed cues

- **GIVEN** `ctx.config.post_processing is None`
- **AND** `ctx.transcription_results` contains 3 results
- **WHEN** `PostProcessingStage.process(ctx)` is called
- **THEN** the returned context's `subtitles` MUST have length 3
- **AND** `subtitles[0].index, subtitles[1].index, subtitles[2].index` MUST equal `1, 2, 3`
- **AND** the processor factory's `create` method MUST NOT be invoked

#### Scenario: post_processing disabled flag emits seed cues

- **GIVEN** `ctx.config.post_processing.enabled == False`
- **WHEN** `PostProcessingStage.process(ctx)` is called
- **THEN** the returned context's `subtitles` length MUST equal `len(ctx.transcription_results)`
- **AND** the processor factory's `create` method MUST NOT be invoked


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
### Requirement: PostProcessingStage selects factory group by alignment status

When `post_processing` is enabled, `PostProcessingStage` SHALL invoke `processor_factory.create(granularity_arg)` with `granularity_arg` resolved as follows: if `ctx.alignment_status == AlignmentStatus.SUCCESS`, pass `ctx.alignment_granularity`; otherwise pass `None`. When `ctx.alignment_status == AlignmentStatus.FAILED`, the stage MUST emit a WARNING log containing the substring `"alignment FAILED"` before invoking the factory. When `ctx.alignment_status == AlignmentStatus.DISABLED`, no WARNING is emitted.

#### Scenario: SUCCESS forwards granularity to factory

- **GIVEN** `ctx.alignment_status == AlignmentStatus.SUCCESS` and `ctx.alignment_granularity == AlignmentGranularity.WORD`
- **WHEN** `PostProcessingStage.process(ctx)` runs
- **THEN** `processor_factory.create` MUST be called with `AlignmentGranularity.WORD`

#### Scenario: FAILED falls back to None and warns

- **GIVEN** `ctx.alignment_status == AlignmentStatus.FAILED` and `ctx.alignment_granularity is None`
- **WHEN** `PostProcessingStage.process(ctx)` runs
- **THEN** a WARNING log containing `"alignment FAILED"` MUST be emitted
- **AND** `processor_factory.create` MUST be called with `None`

#### Scenario: DISABLED falls back to None silently

- **GIVEN** `ctx.alignment_status == AlignmentStatus.DISABLED`
- **AND** `ctx.config.post_processing.enabled == True`
- **WHEN** `PostProcessingStage.process(ctx)` runs
- **THEN** no WARNING log MUST be emitted
- **AND** `processor_factory.create` MUST be called with `None`


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
### Requirement: PostProcessingStage builds seed subtitles from transcription results

`PostProcessingStage` SHALL produce an initial `Subtitle` sequence before invoking any processor. The seed sequence SHALL contain one `Subtitle` per `TranscriptionResult` in input order, with `start_ms` and `end_ms` copied from the source result, `text` copied from `result.text`, and `index` set to the 1-based position in the seed list.

#### Scenario: Seed cues preserve transcription order and timing

- **GIVEN** `ctx.transcription_results = [TR(start_ms=0, end_ms=1000, text="a"), TR(start_ms=1500, end_ms=3000, text="b")]`
- **WHEN** the seed subtitles are built (verifiable via a no-op processor factory)
- **THEN** the seed list MUST equal `[Subtitle(index=1, start_ms=0, end_ms=1000, text="a"), Subtitle(index=2, start_ms=1500, end_ms=3000, text="b")]`


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
### Requirement: PostProcessingStage runs processors in factory-returned order

When `post_processing` is enabled, `PostProcessingStage` SHALL call each `SubtitleProcessor` returned by the factory in the order returned, passing the output of each processor as input to the next. After all processors complete, the stage SHALL renumber `Subtitle.index` to `1..N` and write the final list to `ctx.subtitles`.

#### Scenario: Processors are applied in order

- **GIVEN** the factory returns `[ProcA, ProcB]`
- **WHEN** `PostProcessingStage.process(ctx)` runs
- **THEN** `ProcA.process` MUST be called before `ProcB.process`
- **AND** the input to `ProcB.process` MUST equal the output of `ProcA.process`

#### Scenario: Final indices are renumbered to 1..N

- **GIVEN** the final processor returns 4 subtitles with arbitrary `index` values
- **WHEN** `PostProcessingStage.process(ctx)` finishes
- **THEN** the returned context's `subtitles[i].index` MUST equal `i + 1` for `i` in `0..3`


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
### Requirement: PostProcessingStage handles empty transcription results

When `ctx.transcription_results` is empty, `PostProcessingStage` SHALL return a new context with `subtitles == []`. This holds regardless of `post_processing.enabled` or `alignment_status`. The processor factory MAY be consulted but processors MUST receive an empty list.

#### Scenario: Empty input yields empty subtitles

- **GIVEN** `ctx.transcription_results == []`
- **WHEN** `PostProcessingStage.process(ctx)` runs
- **THEN** the returned context's `subtitles` MUST equal `[]`

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