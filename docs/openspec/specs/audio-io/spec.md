# audio-io Specification

## Purpose

TBD - created by archiving change 'bootstrap-pipeline-foundation'. Update Purpose after archive.

## Requirements

### Requirement: AudioReader interface for lazy interval reads

The system SHALL provide an `AudioReader` interface that exposes a read-only `sample_rate: int` property and a method `read(start_ms: int, end_ms: int) -> bytes` returning PCM audio bytes for the requested interval. An `AudioReader` instance is bound at construction time to a single media file path.

#### Scenario: Interval read returns PCM bytes

- **WHEN** `reader.read(1000, 2000)` is called on a reader bound to a 60-second media file
- **THEN** the method MUST return a `bytes` object containing exactly 1 second of PCM data at `reader.sample_rate`

#### Scenario: Out-of-range request raises

- **WHEN** `reader.read(start_ms, end_ms)` is called with `end_ms > media_duration_ms` or `start_ms < 0` or `start_ms >= end_ms`
- **THEN** the method MUST raise `ValueError`


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
### Requirement: Default AudioReader implementation uses ffmpeg with LRU cache

The system SHALL provide a default implementation `FfmpegAudioReader` that decodes via ffmpeg and caches the most recent N decoded intervals using an LRU policy. The cache size SHALL default to 4 and SHALL be configurable via the `AUDIO_CACHE_SIZE` environment variable.

#### Scenario: Repeated read uses cache

- **WHEN** `reader.read(1000, 2000)` is called twice in succession on the same `FfmpegAudioReader`
- **THEN** the underlying ffmpeg decode MUST execute only once


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
### Requirement: MediaHasher computes SHA-256

The system SHALL provide a `MediaHasher.hash(path: str) -> str` method that returns the SHA-256 hex digest of the file at `path`. The implementation MUST stream the file in chunks (not load it entirely into memory) to support large media files.

#### Scenario: Same content yields same hash

- **WHEN** `MediaHasher.hash()` is invoked twice on identical file contents at different paths
- **THEN** both calls MUST return the same 64-character lowercase hex string


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
### Requirement: ProjectFileWriter serializes ProjectFile to JSON

The system SHALL provide a `ProjectFileWriter.write(project_file: ProjectFile, output_path: str) -> None` method that serializes the `ProjectFile` to JSON and writes it to `output_path`. Enums SHALL be serialized by name (not by integer value). Datetime strings SHALL be in ISO 8601 format.

#### Scenario: Enum serialised by name

- **WHEN** a `ProjectFile` with `config.align.granularity = GranularityPreference.AUTO` is written
- **THEN** the resulting JSON MUST contain the literal string `"AUTO"` (not `2` or another integer)

#### Scenario: Output is valid JSON

- **WHEN** any `ProjectFile` is written to disk
- **THEN** the resulting file MUST be parseable by `json.loads()` without error

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