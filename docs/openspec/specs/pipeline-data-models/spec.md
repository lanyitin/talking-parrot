# pipeline-data-models Specification

## Purpose

TBD - created by archiving change 'bootstrap-pipeline-foundation'. Update Purpose after archive.

## Requirements

### Requirement: PipelineContext fields

The system SHALL provide a frozen dataclass `PipelineContext` containing the following fields: `config: PipelineConfig`, `media_info: MediaInfo`, `vad_frames: list[RawVadFrame]`, `vad_segments: list[VadSegment]`, `chunks: list[Chunk]`, `transcription_results: list[TranscriptionResult]`, `alignment_status: AlignmentStatus`, `alignment_granularity: AlignmentGranularity | None`, `alignment_results: list[AlignmentResult]`, `subtitles: list[Subtitle]`. Default factory values MUST initialise list fields as empty lists, `alignment_status` as `AlignmentStatus.DISABLED`, and `alignment_granularity` as `None`.

#### Scenario: Default initialization

- **WHEN** `PipelineContext(config=cfg, media_info=info)` is constructed without other arguments
- **THEN** `vad_frames`, `vad_segments`, `chunks`, `transcription_results`, `alignment_results`, and `subtitles` MUST each be empty lists, `alignment_status` MUST equal `AlignmentStatus.DISABLED`, and `alignment_granularity` MUST be `None`


<!-- @trace
source: vad-frames-per-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/cli.py
  - src/talking_parrot/models/context.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - src/talking_parrot/gui/__init__.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - src/talking_parrot/gui/static/index.html
  - src/talking_parrot/gui/cli.py
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/gui/api.py
  - tests/unit/shared/__init__.py
  - docs/TODOs.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/shared/__init__.py
tests:
  - tests/unit/gui/test_cli.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/gui/test_api.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/gui/test_dependency_direction.py
  - tests/unit/shared/test_public_api.py
-->

---
### Requirement: AlignmentStatus enum has three states

The system SHALL define `AlignmentStatus` as an enum with exactly three members: `DISABLED`, `SUCCESS`, `FAILED`. `DISABLED` indicates `config.align.enabled == False`; `SUCCESS` indicates the alignment stage ran and produced results; `FAILED` indicates the alignment stage ran but failed (model load error, unsupported language, etc.) and downstream consumers MUST fall back.

#### Scenario: Three-state semantics

- **WHEN** the alignment stage is skipped because configuration disables it
- **THEN** `ctx.alignment_status` MUST equal `AlignmentStatus.DISABLED` and downstream stages MUST NOT log any warning about alignment

##### Example: status mapping

| Configuration / runtime | alignment_status | alignment_granularity |
| ----------------------- | ---------------- | --------------------- |
| `config.align.enabled = False` | `DISABLED` | `None` |
| Stage ran, English backend produced word tokens | `SUCCESS` | `WORD` |
| Stage ran, Japanese backend raised exception | `FAILED` | `None` |


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
### Requirement: AlignmentGranularity and GranularityPreference enums

The system SHALL define two enums. `AlignmentGranularity` SHALL have members `WORD` and `CHARACTER`. `GranularityPreference` SHALL have members `WORD`, `CHARACTER`, `AUTO`. The `AUTO` member is exclusive to `GranularityPreference` and MUST NOT appear in `AlignmentGranularity`.

#### Scenario: Enum value sets

- **WHEN** the enums are imported
- **THEN** `set(AlignmentGranularity)` MUST equal `{AlignmentGranularity.WORD, AlignmentGranularity.CHARACTER}` and `set(GranularityPreference)` MUST equal `{GranularityPreference.WORD, GranularityPreference.CHARACTER, GranularityPreference.AUTO}`


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
### Requirement: Chunk holds no audio bytes

The `Chunk` dataclass SHALL contain only `index: int`, `start_ms: int`, `end_ms: int`, and `source_segments: list[VadSegment]`. It MUST NOT contain any `bytes`, `bytearray`, or numpy-array field representing PCM audio data.

#### Scenario: Chunk inspection

- **WHEN** `Chunk.__dataclass_fields__` is inspected
- **THEN** the field set MUST equal `{"index", "start_ms", "end_ms", "source_segments"}`


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
### Requirement: TranscriptionResult exposes metrics for condition evaluation

The `TranscriptionResult` dataclass SHALL expose a `metrics: TranscriptionMetrics` field. `TranscriptionMetrics` SHALL contain at minimum `avg_logprob: float`, `compression_ratio: float`, `no_speech_prob: float`, `repetition_ratio: float`. `TranscriptionResult` SHALL also expose `chunk_index`, `start_ms`, `end_ms`, `text`, `language`, `model_used`, and `aligned_tokens: list[AlignedToken] | None`.

`start_ms` and `end_ms` SHALL represent the absolute time bounds of the Whisper internal segment that produced this result, NOT the bounds of the parent `Chunk`. Multiple `TranscriptionResult` instances MAY share the same `chunk_index`; their `start_ms`/`end_ms` ranges SHALL be non-overlapping and ordered ascending within a single chunk. `metrics` SHALL carry the segment's raw values, not chunk-level aggregates.

#### Scenario: Metrics are accessible by attribute name

- **WHEN** `result.metrics.avg_logprob` is read
- **THEN** the value MUST be a float (not a dict lookup)

#### Scenario: Segment bounds within parent chunk

- **GIVEN** a chunk with `start_ms=10000, end_ms=20000` and three `TranscriptionResult` instances sharing this `chunk_index`
- **WHEN** their `start_ms`/`end_ms` are inspected
- **THEN** each MUST satisfy `chunk.start_ms <= result.start_ms < result.end_ms <= chunk.end_ms`
- **AND** the three results MUST be sorted ascending by `start_ms` and have non-overlapping ranges


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
### Requirement: ProjectFile is pure data

The `ProjectFile` dataclass SHALL contain only fields (`version: str`, `created_at: str`, `media`, `config`, `vad_frames`, `vad_segments`, `transcription_results`, `subtitles`) and no methods beyond those auto-generated by `@dataclass`. Serialization MUST be performed exclusively by `ProjectFileWriter` (see `audio-io`). The `vad_frames` field SHALL default to an empty list and items MUST round-trip through `dataclasses.asdict` as plain dicts.

#### Scenario: ProjectFile has no behavior

- **WHEN** the `ProjectFile` class definition is reviewed
- **THEN** it MUST NOT define `to_json`, `save`, `write`, or any method beyond dataclass-generated `__init__`, `__repr__`, `__eq__`

#### Scenario: ProjectFile.vad_frames defaults to empty list

- **WHEN** `ProjectFile(version="1", created_at="2026-05-09T00:00:00Z", media=m, config={})` is constructed without supplying `vad_frames`
- **THEN** `ProjectFile.vad_frames` MUST equal `[]`

<!-- @trace
source: vad-frames-per-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/cli.py
  - src/talking_parrot/models/context.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - src/talking_parrot/gui/__init__.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - src/talking_parrot/gui/static/index.html
  - src/talking_parrot/gui/cli.py
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/gui/api.py
  - tests/unit/shared/__init__.py
  - docs/TODOs.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/shared/__init__.py
tests:
  - tests/unit/gui/test_cli.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/gui/test_api.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/gui/test_dependency_direction.py
  - tests/unit/shared/test_public_api.py
-->