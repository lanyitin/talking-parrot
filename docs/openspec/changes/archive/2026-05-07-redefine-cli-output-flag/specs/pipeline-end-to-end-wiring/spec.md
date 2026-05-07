## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: cli.py is silent when export is not configured

When `cfg.export is None`, `cli.main` SHALL NOT instantiate the factory, SHALL NOT call any exporter, and SHALL NOT emit a warning. Only the project-file write behavior runs, using `--output` (which is required in this mode) as the project-JSON path.

#### Scenario: Omitting export keeps the legacy CLI behavior

- **GIVEN** a `PipelineConfig` with `export = None` and `--output state/run.json` supplied
- **WHEN** `cli.main` runs
- **THEN** no subtitle file is created, no warning log record is emitted with respect to export, and the project-file JSON is written at `state/run.json`
