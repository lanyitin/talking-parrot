# pipeline-config Specification

## Purpose

TBD - created by archiving change 'bootstrap-pipeline-foundation'. Update Purpose after archive.

## Requirements

### Requirement: ConfigLoader parses YAML into PipelineConfig

The system SHALL provide a `ConfigLoader.load(path: str) -> PipelineConfig` method that reads a YAML file from disk and returns a strongly-typed `PipelineConfig` (pydantic model). YAML keys MUST map to the `PipelineConfig` schema declared in `pipeline-data-models`.

#### Scenario: Valid YAML loads successfully

- **WHEN** `ConfigLoader.load("config.yaml")` is called with a YAML file containing valid `expected_language`, `vad`, `chunking`, `transcribing`, `align`, and `post_processing` sections
- **THEN** the method MUST return a `PipelineConfig` instance with all sub-configs populated as their respective typed objects


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: ConfigLoader rejects unknown fields

The `ConfigLoader` SHALL reject unknown top-level or nested fields by raising `pydantic.ValidationError`. This prevents silent typos in YAML keys from being ignored.

#### Scenario: Unknown field rejected

- **WHEN** the YAML contains an unknown field (e.g., `vad.activty_threshold` instead of `activity_threshold`)
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError` identifying the offending field path


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: ConfigLoader warns on inconsistent VAD/chunking durations

When `vad.enabled` is true, `chunking.enabled` is true, and `vad.max_speech_duration_ms > chunking.max_chunk_seconds * 1000`, `ConfigLoader.load()` SHALL emit a WARNING log identifying both values and explaining that the chunker may have to perform a hard cut mid-word. The loader MUST NOT raise an error in this case.

#### Scenario: Inconsistent durations log warning

- **WHEN** `vad.max_speech_duration_ms = 60000` and `chunking.max_chunk_seconds = 30`
- **THEN** `ConfigLoader.load()` MUST emit a WARNING log mentioning both values and MUST still return a valid `PipelineConfig`


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: PipelineConfig sub-section optionality

`PipelineConfig.vad`, `PipelineConfig.chunking`, `PipelineConfig.align`, and `PipelineConfig.post_processing` SHALL be `Optional` (allow `None`). When a sub-section is `None`, the corresponding stage MUST behave as if `enabled = False`. `PipelineConfig.transcribing` SHALL be a non-empty list (validated by pydantic).

#### Scenario: Empty transcribing list rejected

- **WHEN** YAML defines `transcribing: []`
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError`

#### Scenario: Missing optional section treated as disabled

- **WHEN** YAML omits the `vad` section entirely
- **THEN** `PipelineConfig.vad` MUST be `None` and `VADStage.process()` MUST return its input context unchanged


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: First transcribing step condition must be "true"

`ConfigLoader` SHALL validate that `transcribing[0].condition` equals the literal string `"true"` (case-sensitive). Initial transcription metrics are empty, so any other expression would reference undefined fields.

#### Scenario: Non-true initial condition rejected

- **WHEN** YAML defines `transcribing[0].condition: "avg_logprob < -1.0"`
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError` identifying the first transcribing step

<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: ChunkingConfig has silence_pad_ms field

The system SHALL add a `silence_pad_ms: int` field to `ChunkingConfig` with a default value of `50`. The field MUST be accepted by the YAML loader and MUST be validated to reject negative values.

#### Scenario: Default value

- **WHEN** `ChunkingConfig` is instantiated without specifying `silence_pad_ms`
- **THEN** `config.chunking.silence_pad_ms` MUST equal `50`

#### Scenario: Explicit value from YAML

- **WHEN** the config YAML contains `chunking: { silence_pad_ms: 100 }`
- **THEN** `config.chunking.silence_pad_ms` MUST equal `100`

<!-- @trace
source: implement-chunking-stage
updated: 2026-05-01
code:
  - docs/TODOs.md
  - src/talking_parrot/config/models.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/__init__.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/transcription/factory.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
-->

---
### Requirement: TranscribingStep.backend is optional with platform-aware default

`TranscribingStep.backend` SHALL be an optional field. YAML that omits `backend:` from any transcribing step MUST be accepted by `ConfigLoader.load()` without raising `pydantic.ValidationError`.

When `backend` is omitted (or explicitly `null`) for a step, `ConfigLoader.load()` SHALL resolve the field to the value returned by `TranscriptionBackendFactory.default_for_platform()` before returning the `PipelineConfig`. After loading, every `TranscribingStep.backend` in the returned config MUST be a non-empty `str` so that downstream consumers (e.g., `TranscriptionStage`, `TranscriptionBackendFactory.create`) continue to receive a concrete backend name.

When `backend` is provided as a non-empty string, `ConfigLoader.load()` MUST preserve that explicit value unchanged. The platform default MUST NOT override an explicit value.

The runtime `TRANSCRIPTION_BACKEND` environment variable continues to be honoured by `TranscriptionBackendFactory.create()` and is out of scope for this loader-level resolution.

#### Scenario: Omitted backend resolves to platform default

- **WHEN** YAML defines a transcribing step with `condition: "true"`, no `backend:` key, and `model: large-v3`
- **THEN** `ConfigLoader.load()` MUST return a `PipelineConfig` whose corresponding `transcribing[i].backend` equals `TranscriptionBackendFactory.default_for_platform()`

##### Example: platform resolution table

| `sys.platform` | `platform.machine()` | Resolved `transcribing[0].backend` |
| -------------- | -------------------- | ---------------------------------- |
| `darwin`       | `arm64`              | `mlx-whisper`                      |
| `darwin`       | `x86_64`             | `faster-whisper`                   |
| `linux`        | `x86_64`             | `faster-whisper`                   |
| `win32`        | `AMD64`              | `faster-whisper`                   |

#### Scenario: Explicit backend value preserved

- **WHEN** YAML defines a transcribing step with explicit `backend: faster-whisper` while running on Apple Silicon macOS
- **THEN** `ConfigLoader.load()` MUST return a `PipelineConfig` whose `transcribing[i].backend` equals `"faster-whisper"` (the platform default MUST NOT override the explicit value)

#### Scenario: Null backend resolves to platform default

- **WHEN** YAML defines a transcribing step with `backend: null`
- **THEN** `ConfigLoader.load()` MUST treat the field as omitted and resolve it to `TranscriptionBackendFactory.default_for_platform()`

#### Scenario: Mixed cascade with one omitted backend

- **WHEN** YAML defines two transcribing steps where step 0 omits `backend:` and step 1 specifies `backend: whisper`
- **THEN** `ConfigLoader.load()` MUST resolve step 0 to `TranscriptionBackendFactory.default_for_platform()` and MUST preserve step 1 as `"whisper"` (which `TranscriptionBackendFactory.create()` may later reject at runtime if unknown — that validation is unchanged by this requirement)

<!-- @trace
source: optional-transcribing-backend
updated: 2026-05-07
code:
  - src/talking_parrot/logging_config.py
  - uv.lock
  - src/talking_parrot/io/audio_decoder.py
  - src/talking_parrot/vad/silero_vad.py
  - pyproject.toml
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/io/subtitle_export/base.py
  - config.example.yaml
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/transcription/factory.py
  - sample1.json
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/stages/chunking_stage.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/stages/post_processing_stage.py
  - sample1.srt
  - src/talking_parrot/__init__.py
  - src/talking_parrot/alignment/japanese_backend.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
tests:
  - tests/unit/config/test_models.py
  - tests/unit/config/test_loader.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/io/test_audio_decoder.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/vad/test_ten_vad.py
-->

---
### Requirement: HallucinationFilterConfig schema

`PipelineConfig` SHALL expose an optional `hallucination_filter: HallucinationFilterConfig | None` field. `HallucinationFilterConfig` SHALL be a pydantic model with the following fields and defaults:

- `enabled: bool = True`
- `min_avg_logprob: float = -1.0`
- `max_no_speech_prob: float = 0.6`
- `max_compression_ratio: float = 2.4`
- `max_repetition_ratio: float = 0.5`
- `known_hallucination_phrases: list[str] = ["ご視聴ありがとうございました", "ご視聴ありがとうございます", "おやすみなさい"]` (default list copied from the audio2subtitle reference; project SHALL allow this list to be overridden via YAML)
- `phrase_match_enabled: bool = True`
- `bracket_match_enabled: bool = True`
- `repeat_match_enabled: bool = True`
- `low_logprob_match_enabled: bool = True`
- `compression_match_enabled: bool = True`
- `repetition_match_enabled: bool = True`

When `hallucination_filter is None` or `enabled is False`, `HallucinationFilterStage.process()` MUST return its input context unchanged. The CLI wiring (see `pipeline-end-to-end-wiring`) SHALL include the stage only when `hallucination_filter is not None`.

#### Scenario: Default HallucinationFilterConfig

- **GIVEN** YAML containing `hallucination_filter: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `HallucinationFilterConfig` MUST have `enabled=True`, `min_avg_logprob=-1.0`, `max_no_speech_prob=0.6`, `max_compression_ratio=2.4`, `max_repetition_ratio=0.5`

#### Scenario: Missing section yields None

- **GIVEN** YAML omits the `hallucination_filter` key entirely
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `PipelineConfig.hallucination_filter` MUST be `None`


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
### Requirement: PostProcessingConfig dedup and Japanese fields

`PostProcessingConfig` SHALL expose the following additional fields with defaults:

- `dedup_enabled: bool = True`
- `dedup_similarity_threshold: float = 0.9`
- `dedup_max_gap_ms: int = 600`
- `japanese_filler_enabled: bool = True`
- `japanese_repetition_enabled: bool = True`
- `japanese_filler_words: list[str] = ["あのー", "えーと", "えー", "そのー"]`
- `japanese_onomatopoeia_whitelist: list[str] = ["どきどき", "わくわく", "きらきら", "ぴかぴか"]`

The default `japanese_filler_words` list MUST include only prolonged-vowel filler forms (those ending in the chōonpu `ー`). Bare-form fillers such as `その`, `あの`, `えっと`, `まあ`, `なんか`, `ね` MUST NOT appear in the default list because they collide with content words (most prominently the demonstrative pronoun `その`, observed in `test-samples/sample1`). Operators who need bare-form filler stripping for a specific corpus MAY add entries via the YAML `post_processing.japanese_filler_words` override.

`dedup_similarity_threshold` MUST be in the closed interval `[0.0, 1.0]`. `dedup_max_gap_ms` MUST be `>= 0`. Validation SHALL be enforced via pydantic field validators; out-of-range values MUST raise `pydantic.ValidationError`.

#### Scenario: Default fields populated

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `dedup_enabled=True`, `dedup_similarity_threshold=0.9`, `dedup_max_gap_ms=600`, `japanese_filler_enabled=True`, `japanese_repetition_enabled=True`

#### Scenario: Default japanese_filler_words excludes bare demonstrative

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `PostProcessingConfig.japanese_filler_words` MUST NOT contain the bare string `"その"`
- **AND** it MUST contain the prolonged form `"そのー"`

#### Scenario: Out-of-range threshold rejected

- **GIVEN** YAML with `post_processing.dedup_similarity_threshold: 1.5`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

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
### Requirement: PostProcessingConfig Japanese split-boundary fields

`PostProcessingConfig` SHALL expose the following additional fields with defaults that drive `JapaneseSplitBoundaryPolicy`:

- `japanese_split_search_radius: int = 4`
- `japanese_split_no_split_units: list[str] = ["ます", "ません", "まし", "です", "でし", "だっ", "った", "ない", "なかっ", "たい", "よう", "そう", "という", "について"]`
- `japanese_split_no_leading_particles: list[str] = ["て", "で", "に", "を", "が", "は", "も", "と", "から", "まで", "より", "へ", "や", "か", "の", "ね", "よ"]`
- `japanese_split_no_leading_finals: list[str] = ["た", "だ", "る", "い"]`

`japanese_split_search_radius` MUST be in the closed interval `[0, 20]`. Validation SHALL be enforced via a pydantic field validator; out-of-range values MUST raise `pydantic.ValidationError`. Each list field MUST contain only non-empty strings; empty-string entries MUST raise `pydantic.ValidationError`.

#### Scenario: Default fields populated

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `japanese_split_search_radius == 4`
- **AND** `japanese_split_no_split_units` MUST contain `"まし"`, `"です"`, and `"よう"`
- **AND** `japanese_split_no_leading_particles` MUST contain `"に"`, `"を"`, and `"の"`
- **AND** `japanese_split_no_leading_finals` MUST contain `"た"` and `"い"`

#### Scenario: Out-of-range radius rejected

- **GIVEN** YAML with `post_processing.japanese_split_search_radius: 25`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Empty string in list rejected

- **GIVEN** YAML with `post_processing.japanese_split_no_leading_particles: ["", "に"]`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Negative radius rejected

- **GIVEN** YAML with `post_processing.japanese_split_search_radius: -1`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

<!-- @trace
source: japanese-aware-cue-split
updated: 2026-05-08
code:
  - CLAUDE.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/japanese.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/post_processing/dedup.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/stages/transcription_stage.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
tests:
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/config/test_loader.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_dedup.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/post_processing/test_split_policy.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/post_processing/test_japanese.py
-->