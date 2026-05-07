# pipeline-end-to-end-wiring Specification

## Purpose

TBD - created by archiving change 'implement-subtitle-export'. Update Purpose after archive.

## Requirements

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
### Requirement: cli.py invokes the subtitle exporter when export is configured

After `orchestrator.run(ctx)` returns, when `cfg.export is not None` `cli.main` SHALL:

1. Call `SubtitleExporterFactory.create(cfg.export.format)` to obtain an exporter instance
2. Call `exporter.export(ctx.subtitles, <resolved_subtitle_path>)`, where `<resolved_subtitle_path>` is the value of `--output` when supplied, otherwise `cfg.export.output_path`.

The subtitle export call SHALL run AFTER `ProjectFileWriter.write` so a failure in the exporter does NOT prevent the project file from being persisted.

#### Scenario: A configured export path writes the subtitle file

- **GIVEN** a `PipelineConfig` whose `export` is `ExportConfig(format="srt", output_path="<tmp>/out.srt")`, no `--output` is supplied, and a fake orchestrator that yields `ctx.subtitles = [Subtitle(1, 0, 1000, "hi")]`
- **WHEN** `cli.main` runs end-to-end
- **THEN** the file at `<tmp>/out.srt` exists and contains the SRT serialization of the subtitle
- **AND** the project-file JSON has also been written

#### Scenario: --output overrides the configured export path

- **GIVEN** a `PipelineConfig` whose `export` is `ExportConfig(format="srt", output_path="<tmp>/from-yaml.srt")` and `--output <tmp>/from-cli.srt` is supplied
- **WHEN** `cli.main` runs end-to-end
- **THEN** the subtitle file is written to `<tmp>/from-cli.srt`
- **AND** no file is created at `<tmp>/from-yaml.srt`

#### Scenario: An exporter error does not prevent the project file from being written

- **GIVEN** the same config as the first scenario, but the exporter is patched to raise `IOError("disk full")` on `export`
- **WHEN** `cli.main` runs
- **THEN** the project-file JSON has been written before the `IOError` propagates out of `cli.main`


<!-- @trace
source: redefine-cli-output-flag
updated: 2026-05-07
code:
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - pyproject.toml
  - sample1.json
  - src/talking_parrot/io/audio_decoder.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - sample1.srt
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
  - uv.lock
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/silero_vad.py
  - config.example.yaml
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/transcription/factory.py
tests:
  - tests/unit/config/test_models.py
  - tests/unit/io/test_audio_decoder.py
  - tests/unit/config/test_loader.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/cli/test_cli_wiring.py
-->

---
### Requirement: cli.py is silent when export is not configured

When `cfg.export is None`, `cli.main` SHALL NOT instantiate the factory, SHALL NOT call any exporter, and SHALL NOT emit a warning. Only the project-file write behavior runs, using `--output` (which is required in this mode) as the project-JSON path.

#### Scenario: Omitting export keeps the legacy CLI behavior

- **GIVEN** a `PipelineConfig` with `export = None` and `--output state/run.json` supplied
- **WHEN** `cli.main` runs
- **THEN** no subtitle file is created, no warning log record is emitted with respect to export, and the project-file JSON is written at `state/run.json`


<!-- @trace
source: redefine-cli-output-flag
updated: 2026-05-07
code:
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - pyproject.toml
  - sample1.json
  - src/talking_parrot/io/audio_decoder.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - sample1.srt
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
  - uv.lock
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/silero_vad.py
  - config.example.yaml
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/transcription/factory.py
tests:
  - tests/unit/config/test_models.py
  - tests/unit/io/test_audio_decoder.py
  - tests/unit/config/test_loader.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/cli/test_cli_wiring.py
-->

---
### Requirement: The exporter is not registered as a pipeline Stage

The system SHALL NOT include any subtitle-export step in the orchestrator's stage list. Subtitle export SHALL be invoked from `cli.py` directly, parallel to `ProjectFileWriter.write`.

#### Scenario: PipelineOrchestrator never receives a subtitle-export stage

- **GIVEN** any `PipelineConfig`, including one with `export` configured
- **WHEN** `cli.main` constructs its stage list
- **THEN** no element of the list has `name == "subtitle_export"` and no element is an instance of `SubtitleExporter`

<!-- @trace
source: implement-subtitle-export
updated: 2026-05-02
code:
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/stages/post_processing_stage.py
  - tests/unit/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/__init__.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/cli.py
  - tests/unit/post_processing/__init__.py
tests:
  - tests/unit/config/test_export_config.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/stages/test_post_processing_stage.py
-->

---
### Requirement: cli.py populates MediaInfo.duration_ms from the input file

Before constructing `MediaInfo` and running the orchestrator, `cli.main` SHALL probe the duration of `args.input` and populate `MediaInfo.duration_ms` with the real value in milliseconds. The probe SHALL use `FfmpegAudioReader` (whose `__init__` already calls `ffmpeg.probe`); the resulting `duration_ms` SHALL be exposed via a public property on `FfmpegAudioReader` and consumed by `cli.main`.

If the probe fails (e.g. the file does not exist, ffmpeg cannot decode it, or the duration field is missing from the probe result), `cli.main` SHALL exit non-zero with an error message that includes the input file path, BEFORE any pipeline stage runs. `cli.main` SHALL NOT silently fall back to `duration_ms == 0`.

When `cfg.align is not None`, the same `FfmpegAudioReader` instance used to probe the duration MAY be passed to `AlignmentStage` so the file is probed only once.

#### Scenario: A valid media file populates the real duration

- **GIVEN** a media file whose audio duration is 12_345 ms (per `ffmpeg.probe`)
- **WHEN** `cli.main` runs with that file as input
- **THEN** the `MediaInfo` passed to the orchestrator has `duration_ms == 12345` (within ±1 ms rounding tolerance)
- **AND** the project-JSON written to disk has `media.duration_ms == 12345` (within the same tolerance)

#### Scenario: A probe failure exits before the pipeline runs

- **GIVEN** an input path that points to a non-existent file (or any path `ffmpeg.probe` rejects)
- **WHEN** `cli.main` runs
- **THEN** the process exits non-zero with an error message that includes the input path
- **AND** no project-JSON file is written
- **AND** `PipelineOrchestrator.run` is not called

##### Example: probe-result mapping

| `ffmpeg.probe` result                    | `MediaInfo.duration_ms` | CLI exit code |
| ---------------------------------------- | ----------------------- | ------------- |
| `format.duration = "12.345"` (seconds)   | `12345`                 | 0 (success)   |
| `format.duration = "0.500"`              | `500`                   | 0 (success)   |
| Probe raises (file not found)            | (not constructed)       | non-zero      |
| Probe returns dict without `format.duration` | (not constructed)   | non-zero      |

<!-- @trace
source: populate-media-duration
updated: 2026-05-07
code:
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/alignment_stage.py
  - sample1.json
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/stages/post_processing_stage.py
  - uv.lock
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - sample1.srt
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/vad/ten_vad.py
  - config.example.yaml
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/io/audio_decoder.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/config/loader.py
tests:
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/config/test_loader.py
  - tests/unit/io/test_audio_decoder.py
  - tests/unit/vad/test_ten_vad.py
-->

---
### Requirement: cli.py accepts --output and --project-json with extension-aware semantics

`cli.main` SHALL define two distinct CLI flags:

- `--output <path>`: when `cfg.export is not None`, this is the **subtitle output path** and SHALL override `cfg.export.output_path`. When `cfg.export is None`, this is the **project-JSON output path** (preserves the only useful interpretation in that mode).
- `--project-json <path>` (optional): the **project-JSON output path**. When `cfg.export is not None` and `--project-json` is omitted, the project-JSON path SHALL be derived from the resolved subtitle path by replacing the file extension with `.json` (e.g. `out/sample1.srt` → `out/sample1.json`).

When `cfg.export is None`, `--output` SHALL be required (the project JSON is the only output and its path MUST be supplied).

When `cfg.export is not None` and the extension of the resolved subtitle path does not match `cfg.export.format` (`.srt` for `srt`, `.vtt` for `webvtt`), `cli.main` SHALL exit non-zero with a clear error message before running the pipeline. The format itself is NOT inferred from the extension.

#### Scenario: --output supplies the subtitle path when export is configured

- **GIVEN** a `PipelineConfig` whose `export` is `ExportConfig(format="srt", output_path="output/result.srt")`
- **WHEN** `cli.main` runs with `--output sample1.srt` and no `--project-json`
- **THEN** the subtitle file is written to `sample1.srt` (NOT `output/result.srt`)
- **AND** the project-JSON file is written to `sample1.json`

#### Scenario: --project-json overrides the derived JSON path

- **GIVEN** the same export config as above
- **WHEN** `cli.main` runs with `--output out/sub.srt --project-json state/run.json`
- **THEN** the subtitle file is written to `out/sub.srt`
- **AND** the project-JSON file is written to `state/run.json`

#### Scenario: --output is the project JSON path when export is not configured

- **GIVEN** a `PipelineConfig` with `export = None`
- **WHEN** `cli.main` runs with `--output state/run.json`
- **THEN** the project-JSON file is written to `state/run.json`
- **AND** no subtitle file is created

#### Scenario: Mismatched subtitle extension is rejected

- **GIVEN** a `PipelineConfig` whose `export.format` is `srt`
- **WHEN** `cli.main` runs with `--output sample1.vtt`
- **THEN** the process exits non-zero with an error mentioning the format/extension mismatch
- **AND** neither the subtitle file nor the project-JSON file is written

##### Example: path-resolution table

| `cfg.export`                | `--output`           | `--project-json`   | Subtitle path        | Project-JSON path |
| --------------------------- | -------------------- | ------------------ | -------------------- | ----------------- |
| `format=srt, path=a/b.srt`  | `c/d.srt`            | (omitted)          | `c/d.srt`            | `c/d.json`        |
| `format=srt, path=a/b.srt`  | `c/d.srt`            | `s/r.json`         | `c/d.srt`            | `s/r.json`        |
| `format=srt, path=a/b.srt`  | (omitted)            | `s/r.json`         | `a/b.srt`            | `s/r.json`        |
| `format=webvtt, path=...`   | `c/d.vtt`            | (omitted)          | `c/d.vtt`            | `c/d.json`        |
| `format=srt, path=...`      | `c/d.vtt`            | (any)              | error: ext mismatch  | (not written)     |
| `None`                      | `state/run.json`     | (omitted)          | (none)               | `state/run.json`  |
| `None`                      | (omitted)            | (any)              | error: --output required | (not written) |

<!-- @trace
source: redefine-cli-output-flag
updated: 2026-05-07
code:
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - pyproject.toml
  - sample1.json
  - src/talking_parrot/io/audio_decoder.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - sample1.srt
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
  - uv.lock
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/silero_vad.py
  - config.example.yaml
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/transcription/factory.py
tests:
  - tests/unit/config/test_models.py
  - tests/unit/io/test_audio_decoder.py
  - tests/unit/config/test_loader.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/cli/test_cli_wiring.py
-->