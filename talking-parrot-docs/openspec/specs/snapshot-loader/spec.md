# snapshot-loader Specification

## Purpose

TBD - created by archiving change 'shared-layer'. Update Purpose after archive.

## Requirements

### Requirement: SnapshotLoader protocol

The system SHALL provide a `typing.Protocol` named `SnapshotLoader` in `src/talking_parrot/shared/snapshot_loader.py` declaring a single method `load(source: str | pathlib.Path) -> ProjectSnapshot`. The protocol MUST be decorated with `@typing.runtime_checkable` so that `isinstance(obj, SnapshotLoader)` succeeds for any object exposing a matching `load` attribute.

#### Scenario: Duck-typed loader satisfies the protocol

- **WHEN** a class `Stub` defining `def load(self, source): return snapshot` is instantiated as `s = Stub()`
- **THEN** `isinstance(s, SnapshotLoader)` MUST return `True`


<!-- @trace
source: shared-layer
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - docs/TODOs.md
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/shared/metrics.py
  - tests/unit/shared/__init__.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/shared/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/project_snapshot.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/shared-architecture.md
tests:
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/shared/test_snapshot_loader.py
-->

---
### Requirement: FileSnapshotLoader default implementation

The system SHALL provide a class `FileSnapshotLoader` in `src/talking_parrot/shared/snapshot_loader.py` whose `load(source)` method reads the file at `source` as JSON and returns a fully populated `ProjectSnapshot`. `FileSnapshotLoader` MUST satisfy the `SnapshotLoader` protocol.

#### Scenario: Loading a well-formed file

- **WHEN** `FileSnapshotLoader().load(path)` is called on a `.tp` JSON file containing all required scalar fields and well-formed list fields
- **THEN** the returned object MUST be a `ProjectSnapshot` whose fields equal the file's contents


<!-- @trace
source: shared-layer
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - docs/TODOs.md
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/shared/metrics.py
  - tests/unit/shared/__init__.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/shared/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/project_snapshot.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/shared-architecture.md
tests:
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/shared/test_snapshot_loader.py
-->

---
### Requirement: Tolerant defaults for missing list fields

`FileSnapshotLoader.load` SHALL default any of `vad_frames`, `vad_segments`, `chunks`, `transcription_results`, `pre_postprocess_subtitles`, and `subtitles` to an empty list when the underlying JSON omits the corresponding key. The loader MUST emit a `logging` debug-level message naming each list field that defaulted.

#### Scenario: Missing list field defaults to empty

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file that contains all required scalar fields but omits `vad_frames`
- **THEN** the returned `ProjectSnapshot.vad_frames` MUST equal `[]` and a debug-level log message naming `vad_frames` MUST be emitted


<!-- @trace
source: shared-layer
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - docs/TODOs.md
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/shared/metrics.py
  - tests/unit/shared/__init__.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/shared/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/project_snapshot.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/shared-architecture.md
tests:
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/shared/test_snapshot_loader.py
-->

---
### Requirement: Hard failure on missing required scalar field

`FileSnapshotLoader.load` SHALL raise `KeyError` whose message names the missing field when any of `version`, `created_at`, `source_path`, `config_snapshot`, or `audio_info` is absent from the JSON file. The loader MUST NOT silently substitute defaults for these fields.

#### Scenario: Missing required field

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file lacking `version`
- **THEN** the call MUST raise `KeyError` and the error message MUST contain the string `"version"`


<!-- @trace
source: shared-layer
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - docs/TODOs.md
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/shared/metrics.py
  - tests/unit/shared/__init__.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/shared/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/project_snapshot.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/shared-architecture.md
tests:
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/shared/test_snapshot_loader.py
-->

---
### Requirement: Underlying I/O errors propagate unchanged

`FileSnapshotLoader.load` SHALL propagate `FileNotFoundError` when `source` does not exist and `json.JSONDecodeError` when the file is not valid JSON. The loader MUST NOT wrap or suppress these errors.

#### Scenario: Missing file

- **WHEN** `FileSnapshotLoader().load("/nonexistent.tp")` is called
- **THEN** the call MUST raise `FileNotFoundError`

#### Scenario: Malformed JSON

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file whose contents are not valid JSON
- **THEN** the call MUST raise `json.JSONDecodeError`

<!-- @trace
source: shared-layer
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - docs/TODOs.md
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/shared/metrics.py
  - tests/unit/shared/__init__.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/shared/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/project_snapshot.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/shared-architecture.md
tests:
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/shared/test_snapshot_loader.py
-->

---
### Requirement: Legacy vad_frames without backend tag default to "unknown"

`FileSnapshotLoader.load` SHALL accept `.tp` files whose `vad_frames` items omit the `backend` key (legacy files written before the per-backend change). For each such item, the loader MUST substitute the literal string `"unknown"` for the missing `backend` field when constructing the `RawVadFrame`. The loader SHALL emit exactly one `logging.warning` per `load(...)` call when at least one such legacy frame is encountered; the warning's message MUST contain both the file path and the literal substring `legacy vad_frames without 'backend' tag`. Items that do supply `backend` MUST NOT trigger the warning.

#### Scenario: Legacy vad_frames load with backend "unknown"

- **GIVEN** a `.tp` file at path `P` whose `vad_frames` items contain only `{"time_ms": ..., "prob": ...}` (no `backend` key)
- **WHEN** `FileSnapshotLoader().load(P)` is called
- **THEN** every loaded `RawVadFrame` MUST have `backend == "unknown"`
- **THEN** exactly one `WARNING`-level log record MUST be emitted whose message contains the string representation of `P` and the substring `legacy vad_frames without 'backend' tag`

#### Scenario: Modern vad_frames load without warning

- **GIVEN** a `.tp` file whose `vad_frames` items each contain `{"time_ms": ..., "prob": ..., "backend": "silero_vad"}`
- **WHEN** `FileSnapshotLoader().load(...)` is called
- **THEN** every loaded `RawVadFrame` MUST have `backend == "silero_vad"`
- **THEN** no `WARNING`-level log record MUST be emitted whose message contains the substring `legacy vad_frames without 'backend' tag`

#### Scenario: Mixed vad_frames produce one warning

- **GIVEN** a `.tp` file whose `vad_frames` list contains 10 items where 3 carry `backend` and 7 omit it
- **WHEN** `FileSnapshotLoader().load(...)` is called
- **THEN** the 3 modern frames MUST keep their supplied `backend` and the 7 legacy frames MUST be loaded with `backend == "unknown"`
- **THEN** exactly one `WARNING` MUST be emitted (not seven)

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