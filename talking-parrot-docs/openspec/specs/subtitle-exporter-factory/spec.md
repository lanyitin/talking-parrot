# subtitle-exporter-factory Specification

## Purpose

TBD - created by archiving change 'implement-subtitle-export'. Update Purpose after archive.

## Requirements

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
### Requirement: SubtitleExporterFactory rejects unknown formats

If `format_name` is not a registered key, `SubtitleExporterFactory.create` SHALL raise `ValueError` whose message contains both the offending input and the sorted list of supported formats.

#### Scenario: An unknown format name raises ValueError mentioning the input and supported formats

- **GIVEN** the factory
- **WHEN** `SubtitleExporterFactory.create("ssa")` is called
- **THEN** a `ValueError` is raised whose `str()` contains `"ssa"`, `"srt"`, and `"webvtt"`


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
### Requirement: SubtitleExporterFactory returns a fresh instance per call

Each call to `create` SHALL construct a new exporter instance; the factory SHALL NOT cache or reuse instances across calls.

#### Scenario: Two calls with the same format yield distinct instances

- **GIVEN** the factory
- **WHEN** `a = SubtitleExporterFactory.create("srt")` and `b = SubtitleExporterFactory.create("srt")` are called
- **THEN** `a is not b` (they are two distinct objects), even though both are `SRTExporter`

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