# gui-flagged-regions-bridge Specification

## Purpose

TBD - created by archiving change 'gui-backend'. Update Purpose after archive.

## Requirements

### Requirement: FlaggedRegion value object

The system SHALL provide a frozen dataclass `FlaggedRegion` in `src/talking_parrot/gui/http_server.py` with fields `start_ms: int`, `end_ms: int`, and `label: str | None`. The dataclass MUST be declared with `frozen=True` and `slots=True`.

#### Scenario: Reassignment rejected

- **WHEN** code attempts `region.label = "x"` on a constructed `FlaggedRegion` instance
- **THEN** the system MUST raise `dataclasses.FrozenInstanceError`


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
### Requirement: Public read-only accessor for MCP bridge

The `gui.http_server` module SHALL expose a public function `get_flagged_regions() -> tuple[FlaggedRegion, ...]` that returns a tuple snapshot of the currently-flagged regions in the order they were posted. The returned object MUST be a `tuple` (immutable). The function MUST NOT expose the underlying mutable list.

#### Scenario: Accessor returns immutable tuple

- **WHEN** `get_flagged_regions()` is called after two regions have been posted
- **THEN** the returned object MUST be an instance of `tuple` of length `2`

#### Scenario: Mutating the returned value does not affect server state

- **WHEN** the caller calls `get_flagged_regions()`, then issues another `POST /api/flagged_regions` with a different region list
- **THEN** the previously-returned tuple MUST remain unchanged in length and contents


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
### Requirement: Atomic replacement under lock

The internal write helper SHALL acquire a `threading.Lock` for the duration of replacing the in-process region list, so that concurrent `POST /api/flagged_regions` requests cannot interleave to produce a partially-written list. The lock MUST be a module-level singleton.

#### Scenario: Concurrent posts produce a coherent end state

- **WHEN** two `POST /api/flagged_regions` requests run concurrently, one with two regions and one with three regions
- **THEN** a subsequent `get_flagged_regions()` call MUST return either exactly the two-region list or exactly the three-region list, and never a mixed combination


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
### Requirement: Cleared by POST with empty list

`POST /api/flagged_regions` with body `{"regions": []}` SHALL clear the in-process region list. After such a request, `get_flagged_regions()` MUST return an empty tuple and `GET /api/flagged_regions` MUST return `{"status": "empty", "regions": []}`.

#### Scenario: Empty post clears prior regions

- **WHEN** a region was previously posted, then a POST with body `{"regions": []}` is issued
- **THEN** `get_flagged_regions()` MUST return `()` and the next `GET /api/flagged_regions` body MUST satisfy `status == "empty"`


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
### Requirement: MCP integration boundary documented

The `gui.http_server` module SHALL document, in the docstring of `get_flagged_regions`, that the function is the sole sanctioned interface for any future MCP bridge to read flagged regions, and that no other code outside `talking_parrot.gui` MAY import the underlying region list. The docstring MUST contain the substring `MCP bridge`.

#### Scenario: Docstring mentions MCP bridge

- **WHEN** `inspect.getdoc(gui.http_server.get_flagged_regions)` is called
- **THEN** the returned string MUST contain the substring `MCP bridge`

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