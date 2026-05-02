## ADDED Requirements

### Requirement: SubtitleExporterFactory.create returns the matching exporter

The system SHALL provide a class `SubtitleExporterFactory` (in `src/talking_parrot/io/subtitle_export/factory.py`) exposing a classmethod `create(cls, format_name: str) -> SubtitleExporter` that returns a fresh instance of the exporter registered for `format_name`. The factory SHALL register `"srt"` to `SRTExporter` and `"webvtt"` to `WebVTTExporter`.

#### Scenario: "srt" returns an SRTExporter instance

- **GIVEN** the factory
- **WHEN** `SubtitleExporterFactory.create("srt")` is called
- **THEN** the return value is an instance of `SRTExporter` and `result.format_name == "srt"`

#### Scenario: "webvtt" returns a WebVTTExporter instance

- **GIVEN** the factory
- **WHEN** `SubtitleExporterFactory.create("webvtt")` is called
- **THEN** the return value is an instance of `WebVTTExporter` and `result.format_name == "webvtt"`

### Requirement: SubtitleExporterFactory rejects unknown formats

If `format_name` is not a registered key, `SubtitleExporterFactory.create` SHALL raise `ValueError` whose message contains both the offending input and the sorted list of supported formats.

#### Scenario: An unknown format name raises ValueError mentioning the input and supported formats

- **GIVEN** the factory
- **WHEN** `SubtitleExporterFactory.create("ssa")` is called
- **THEN** a `ValueError` is raised whose `str()` contains `"ssa"`, `"srt"`, and `"webvtt"`

### Requirement: SubtitleExporterFactory returns a fresh instance per call

Each call to `create` SHALL construct a new exporter instance; the factory SHALL NOT cache or reuse instances across calls.

#### Scenario: Two calls with the same format yield distinct instances

- **GIVEN** the factory
- **WHEN** `a = SubtitleExporterFactory.create("srt")` and `b = SubtitleExporterFactory.create("srt")` are called
- **THEN** `a is not b` (they are two distinct objects), even though both are `SRTExporter`
