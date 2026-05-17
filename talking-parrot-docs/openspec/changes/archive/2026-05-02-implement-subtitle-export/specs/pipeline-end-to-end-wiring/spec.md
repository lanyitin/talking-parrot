## ADDED Requirements

### Requirement: cli.py builds the full five-stage pipeline

`cli.main` SHALL construct a `PipelineOrchestrator` whose stage list contains, in this order:

1. `VadStage` — included only when `cfg.vad is not None`
2. `ChunkingStage` — included only when `cfg.chunking is not None`
3. `TranscriptionStage` — always included (the `transcribing` field is required by `PipelineConfig`)
4. `AlignmentStage` — included only when `cfg.align is not None`
5. `PostProcessingStage` — always included

The CLI SHALL invoke `orchestrator.run(ctx)` and use the returned `PipelineContext` for both project-file write and (conditionally) subtitle export.

#### Scenario: A config with only transcribing builds a two-stage pipeline

- **GIVEN** a `PipelineConfig` with only the required `transcribing` field set
- **WHEN** `cli.main` constructs its stage list (e.g. observed via a test that patches `PipelineOrchestrator`)
- **THEN** the stage list is `[TranscriptionStage, PostProcessingStage]` in that order

#### Scenario: A config with vad, chunking, transcribing, align, post-processing builds the full five-stage pipeline

- **GIVEN** a `PipelineConfig` with all five optional sections populated (`vad`, `chunking`, `transcribing`, `align`, `post_processing`)
- **WHEN** `cli.main` constructs its stage list
- **THEN** the stage list is `[VadStage, ChunkingStage, TranscriptionStage, AlignmentStage, PostProcessingStage]` in that order

### Requirement: cli.py invokes the subtitle exporter when export is configured

After `orchestrator.run(ctx)` returns, when `cfg.export is not None` `cli.main` SHALL:

1. Call `SubtitleExporterFactory.create(cfg.export.format)` to obtain an exporter instance
2. Call `exporter.export(ctx.subtitles, cfg.export.output_path)`

The subtitle export call SHALL run AFTER `ProjectFileWriter.write` so a failure in the exporter does NOT prevent the project file from being persisted.

#### Scenario: A configured export path writes the subtitle file

- **GIVEN** a `PipelineConfig` whose `export` is `ExportConfig(format="srt", output_path="<tmp>/out.srt")`, and a fake orchestrator that yields `ctx.subtitles = [Subtitle(1, 0, 1000, "hi")]`
- **WHEN** `cli.main` runs end-to-end
- **THEN** the file at `<tmp>/out.srt` exists and contains the SRT serialization of the subtitle
- **AND** the project-file JSON has also been written

#### Scenario: An exporter error does not prevent the project file from being written

- **GIVEN** the same config as above, but the exporter is patched to raise `IOError("disk full")` on `export`
- **WHEN** `cli.main` runs
- **THEN** the project-file JSON has been written before the `IOError` propagates out of `cli.main`

### Requirement: cli.py is silent when export is not configured

When `cfg.export is None`, `cli.main` SHALL NOT instantiate the factory, SHALL NOT call any exporter, and SHALL NOT emit a warning. Only the existing project-file write behavior runs.

#### Scenario: Omitting export keeps the legacy CLI behavior

- **GIVEN** a `PipelineConfig` with `export = None`
- **WHEN** `cli.main` runs
- **THEN** no subtitle file is created, no warning log record is emitted with respect to export, and the project-file JSON is still written

### Requirement: The exporter is not registered as a pipeline Stage

The system SHALL NOT include any subtitle-export step in the orchestrator's stage list. Subtitle export SHALL be invoked from `cli.py` directly, parallel to `ProjectFileWriter.write`.

#### Scenario: PipelineOrchestrator never receives a subtitle-export stage

- **GIVEN** any `PipelineConfig`, including one with `export` configured
- **WHEN** `cli.main` constructs its stage list
- **THEN** no element of the list has `name == "subtitle_export"` and no element is an instance of `SubtitleExporter`
