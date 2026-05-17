## ADDED Requirements

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
