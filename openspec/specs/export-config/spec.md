# export-config Specification

## Purpose

TBD - created by archiving change 'implement-subtitle-export'. Update Purpose after archive.

## Requirements

### Requirement: ExportConfig declares format and output_path

The system SHALL provide a Pydantic model `ExportConfig` (in `src/talking_parrot/config/models.py`) with two fields:

- `format: Literal["srt", "webvtt"]` — required
- `output_path: str` — required, MUST be non-empty after `strip()`

`ExportConfig.model_config` SHALL set `extra = "forbid"` so misspelled keys raise a clear validation error.

#### Scenario: Valid YAML loads into ExportConfig

- **GIVEN** the input dict `{"format": "srt", "output_path": "out/movie.srt"}`
- **WHEN** `ExportConfig.model_validate(input)` is called
- **THEN** the result has `format == "srt"` and `output_path == "out/movie.srt"`

#### Scenario: An unknown format value is rejected

- **GIVEN** the input dict `{"format": "ssa", "output_path": "out/movie.ssa"}`
- **WHEN** `ExportConfig.model_validate(input)` is called
- **THEN** a `pydantic.ValidationError` is raised mentioning the `format` field

#### Scenario: An empty or whitespace-only output_path is rejected

- **GIVEN** the input dict `{"format": "srt", "output_path": "   "}`
- **WHEN** `ExportConfig.model_validate(input)` is called
- **THEN** a `pydantic.ValidationError` is raised mentioning `output_path` and the message `"output_path must be non-empty"`

#### Scenario: Unknown keys are forbidden

- **GIVEN** the input dict `{"format": "srt", "output_path": "x.srt", "unknown_field": 1}`
- **WHEN** `ExportConfig.model_validate(input)` is called
- **THEN** a `pydantic.ValidationError` is raised because `extra = "forbid"`


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
### Requirement: PipelineConfig gains an optional export field

`PipelineConfig` SHALL gain a field `export: Optional[ExportConfig] = None`. The default `None` MUST be preserved so YAML files that omit `export` continue to load identically to current behavior.

#### Scenario: A YAML config without export still loads

- **GIVEN** a YAML config that has `transcribing` but no `export` key
- **WHEN** `PipelineConfig.model_validate(yaml_dict)` is called
- **THEN** the resulting `PipelineConfig.export` is `None` and no validation error is raised

#### Scenario: A YAML config with export populates the field

- **GIVEN** a YAML config containing `export: {format: webvtt, output_path: out.vtt}`
- **WHEN** `PipelineConfig.model_validate(yaml_dict)` is called
- **THEN** the resulting `PipelineConfig.export` is an `ExportConfig` with `format == "webvtt"` and `output_path == "out.vtt"`

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