# pipeline-foundation Specification

## Purpose

TBD - created by archiving change 'bootstrap-pipeline-foundation'. Update Purpose after archive.

## Requirements

### Requirement: PipelineStage interface

The system SHALL provide a `PipelineStage` abstract interface that every pipeline stage implements. The interface SHALL expose a read-only `name` property of type `str` and a single method `process(ctx: PipelineContext) -> PipelineContext`. Implementations SHALL NOT mutate the input context; they MUST return a new context (or the same instance unchanged when the stage is disabled in configuration).

#### Scenario: Disabled stage returns context unchanged

- **WHEN** a stage's corresponding section in `PipelineConfig` has `enabled = False` and `process(ctx)` is invoked
- **THEN** the stage MUST return the input `ctx` unchanged (same object identity or a structurally equal copy) and MUST NOT perform any side effects (no I/O, no model loading, no log output beyond a single DEBUG line)

#### Scenario: Enabled stage produces new context

- **WHEN** a concrete stage is enabled and `process(ctx)` runs to completion
- **THEN** the returned context MUST be a new `PipelineContext` instance (frozen dataclass; produced via `dataclasses.replace`) with the stage's output fields populated and all upstream fields preserved


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
### Requirement: PipelineContext immutability and field semantics

The `PipelineContext` SHALL be a `@dataclass(frozen=True)` with the fields specified in `pipeline-data-models`. Stages SHALL update fields exclusively via `dataclasses.replace`. Stages MUST NOT mutate any list, dict, or nested object reachable from the context.

#### Scenario: Replacing a list field

- **WHEN** a stage produces an updated `vad_segments` list
- **THEN** the stage MUST return `dataclasses.replace(ctx, vad_segments=new_list)` and MUST NOT call `ctx.vad_segments.append(...)`


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
### Requirement: PipelineOrchestrator drives stages in order

The system SHALL provide a `PipelineOrchestrator` that accepts an ordered sequence of `PipelineStage` instances at construction time and a `run(ctx: PipelineContext) -> PipelineContext` method that invokes each stage's `process()` in order, threading the returned context into the next stage.

#### Scenario: Stage ordering preserved

- **WHEN** an orchestrator is constructed with stages `[A, B, C]` and `run(ctx0)` is called
- **THEN** the orchestrator MUST invoke `A.process(ctx0) -> ctx1`, then `B.process(ctx1) -> ctx2`, then `C.process(ctx2) -> ctx3`, and return `ctx3`

#### Scenario: Stage exception aborts pipeline

- **WHEN** any stage's `process()` raises an exception
- **THEN** the orchestrator MUST propagate the exception unmodified and MUST NOT invoke subsequent stages


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
### Requirement: Orchestrator owns no business logic

The `PipelineOrchestrator` SHALL contain no stage-specific logic, no decision-making about which stages run, no audio reading, and no configuration validation. Its sole responsibility is sequencing.

#### Scenario: Orchestrator inspection

- **WHEN** the `PipelineOrchestrator` source is reviewed
- **THEN** it MUST NOT import any module under `talking_parrot.vad`, `talking_parrot.transcription`, `talking_parrot.alignment`, `talking_parrot.post_processing`, `talking_parrot.export`, `talking_parrot.expression`, or `talking_parrot.io`

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