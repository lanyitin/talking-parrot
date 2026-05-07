## MODIFIED Requirements

### Requirement: cli.py builds the full five-stage pipeline

`cli.main` SHALL construct a `PipelineOrchestrator` whose stage list contains, in this order:

1. `VadStage` — included only when `cfg.vad is not None`
2. `ChunkingStage` — included only when `cfg.chunking is not None`
3. `TranscriptionStage` — always included (the `transcribing` field is required by `PipelineConfig`)
4. `HallucinationFilterStage` — included only when `cfg.hallucination_filter is not None`
5. `AlignmentStage` — included only when `cfg.align is not None`
6. `PostProcessingStage` — always included

`HallucinationFilterStage` SHALL be inserted between `TranscriptionStage` and `AlignmentStage` (or directly before `PostProcessingStage` when `cfg.align is None`) so that downstream stages observe a filtered `transcription_results`.

The CLI SHALL invoke `orchestrator.run(ctx)` and use the returned `PipelineContext` for both project-file write and (conditionally) subtitle export.

#### Scenario: A config with only transcribing builds a two-stage pipeline

- **GIVEN** a `PipelineConfig` with only the required `transcribing` field set (`vad`, `chunking`, `hallucination_filter`, `align`, `post_processing` all None or absent — though `post_processing` is always included)
- **WHEN** `cli.main` constructs its stage list
- **THEN** the stage list is `[TranscriptionStage, PostProcessingStage]` in that order

#### Scenario: A config with vad, chunking, transcribing, hallucination_filter, align, post-processing builds the full six-stage pipeline

- **GIVEN** a `PipelineConfig` with all six optional sections populated (`vad`, `chunking`, `transcribing`, `hallucination_filter`, `align`, `post_processing`)
- **WHEN** `cli.main` constructs its stage list
- **THEN** the stage list is `[VadStage, ChunkingStage, TranscriptionStage, HallucinationFilterStage, AlignmentStage, PostProcessingStage]` in that order

#### Scenario: Hallucination filter inserted before post-processing when align is None

- **GIVEN** a `PipelineConfig` with `hallucination_filter` set, `align` None, no vad, no chunking
- **WHEN** `cli.main` constructs its stage list
- **THEN** the stage list is `[TranscriptionStage, HallucinationFilterStage, PostProcessingStage]` in that order
