# gui-snapshot-bootstrap Specification

## Purpose

TBD - created by archiving change 'gui-backend'. Update Purpose after archive.

## Requirements

### Requirement: Snapshot loaded once at startup

The CLI entry point `gui.cli.main` SHALL resolve the project path from CLI flag `--project` (overriding) or environment variable `TALKING_PARROT_GUI_PROJECT`, instantiate `talking_parrot.shared.snapshot_loader.FileSnapshotLoader`, call `loader.load(path)` exactly once, and pass the resulting `ProjectSnapshot` to `gui.http_server.serve`. The loader call MUST occur before the server binds its socket. If neither CLI flag nor environment variable supplies a project path, `gui.cli.main` MUST exit with a non-zero status and a stderr message naming `--project` and `TALKING_PARROT_GUI_PROJECT`.

#### Scenario: Loader invoked exactly once

- **WHEN** `gui.cli.main(["--project", "/tmp/x.tp"])` is invoked with `FileSnapshotLoader.load` patched to count calls
- **THEN** the recorded call count MUST equal `1`

#### Scenario: Missing project path exits non-zero

- **WHEN** `gui.cli.main([])` is invoked with the environment variable `TALKING_PARROT_GUI_PROJECT` unset
- **THEN** the call MUST exit with a non-zero status and the captured stderr MUST contain both `--project` and `TALKING_PARROT_GUI_PROJECT`


<!-- @trace
source: gui-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/gui/__init__.py
  - src/talking_parrot/gui/static/index.html
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/models/vad.py
  - docs/TODOs.md
  - src/talking_parrot/gui/api.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/stages/vad_stage.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/shared/__init__.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/gui/cli.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - src/talking_parrot/shared/snapshot_loader.py
  - tests/unit/shared/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/models/context.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
tests:
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/models/test_data_models.py
  - tests/unit/gui/test_cli.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_dependency_direction.py
-->

---
### Requirement: Snapshot held read-only after bootstrap

The HTTP server SHALL store the snapshot on the `ThreadingHTTPServer` instance as the attribute `snapshot` and MUST NOT reassign that attribute after the first call to `serve`. Request handlers MUST read the snapshot only via `self.server.snapshot` and MUST NOT mutate any field of the snapshot or any list it references.

#### Scenario: Reassignment attempt is rejected

- **WHEN** code calls `serve(snapshot, config)` once and then attempts to call `serve(other_snapshot, config)` on the same server instance
- **THEN** the second call MUST raise `RuntimeError` whose message names `snapshot already bound`

#### Scenario: Snapshot remains frozen during request handling

- **WHEN** any endpoint handler completes successfully
- **THEN** the bound `snapshot` MUST remain a `ProjectSnapshot` whose `frozen=True` invariant still holds (i.e. attribute reassignment still raises `dataclasses.FrozenInstanceError`)


<!-- @trace
source: gui-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/gui/__init__.py
  - src/talking_parrot/gui/static/index.html
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/models/vad.py
  - docs/TODOs.md
  - src/talking_parrot/gui/api.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/stages/vad_stage.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/shared/__init__.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/gui/cli.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - src/talking_parrot/shared/snapshot_loader.py
  - tests/unit/shared/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/models/context.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
tests:
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/models/test_data_models.py
  - tests/unit/gui/test_cli.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_dependency_direction.py
-->

---
### Requirement: Reuse of shared layer types

The `gui` package SHALL import `ProjectSnapshot`, `AudioInfo`, `FileSnapshotLoader`, and `SnapshotLoader` from `talking_parrot.shared` and MUST NOT redefine those types. The package MUST NOT contain any class or dataclass named `ProjectSnapshot`, `AudioInfo`, or `SnapshotLoader`.

#### Scenario: No duplicate definitions in gui package

- **WHEN** the `talking_parrot.gui` package is searched for class definitions
- **THEN** zero classes named `ProjectSnapshot`, `AudioInfo`, `FileSnapshotLoader`, or `SnapshotLoader` MUST be found


<!-- @trace
source: gui-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/gui/__init__.py
  - src/talking_parrot/gui/static/index.html
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/models/vad.py
  - docs/TODOs.md
  - src/talking_parrot/gui/api.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/stages/vad_stage.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/shared/__init__.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/gui/cli.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - src/talking_parrot/shared/snapshot_loader.py
  - tests/unit/shared/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/models/context.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
tests:
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/models/test_data_models.py
  - tests/unit/gui/test_cli.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_dependency_direction.py
-->

---
### Requirement: Configuration injected, never hardcoded

`GuiConfig` SHALL be the only source of truth for host, port, and project path inside `gui.http_server` and `gui.api`. No string literal naming a network host (e.g. `"127.0.0.1"`, `"0.0.0.0"`, `"localhost"`) and no integer port literal (e.g. `8765`, `8000`) MAY appear in `gui.http_server` or `gui.api` outside of the `GuiConfig` default-resolution helper.

#### Scenario: GuiConfig is the only literal source

- **WHEN** the source files `gui/http_server.py` and `gui/api.py` are scanned for the substrings `127.0.0.1`, `0.0.0.0`, `localhost`, and `8765`
- **THEN** zero matches MUST be found in `gui/api.py`, and any matches in `gui/http_server.py` MUST appear only inside the `GuiConfig` default-resolution helper or its docstring

<!-- @trace
source: gui-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/gui/__init__.py
  - src/talking_parrot/gui/static/index.html
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/models/vad.py
  - docs/TODOs.md
  - src/talking_parrot/gui/api.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/stages/vad_stage.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/shared/__init__.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/gui/cli.py
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - src/talking_parrot/shared/snapshot_loader.py
  - tests/unit/shared/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/models/context.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
tests:
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/models/test_data_models.py
  - tests/unit/gui/test_cli.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_api.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_public_api.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_dependency_direction.py
-->