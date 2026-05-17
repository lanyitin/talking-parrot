# gui-http-server Specification

## Purpose

TBD - created by archiving change 'gui-backend'. Update Purpose after archive.

## Requirements

### Requirement: Stdlib-only server library

The system SHALL implement the GUI HTTP server using only Python stdlib modules. The implementation MUST NOT import any third-party HTTP library (`aiohttp`, `fastapi`, `flask`, `starlette`, `tornado`, `bottle`, `werkzeug`, `httpx`, `requests`).

#### Scenario: Module imports stay stdlib-only

- **WHEN** `gui.http_server` is imported
- **THEN** every top-level import MUST resolve to a Python stdlib module or to `talking_parrot.shared` / `talking_parrot.gui` siblings


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
### Requirement: Configurable host and port

The server SHALL bind to a host and port supplied through a `GuiConfig` value object. The defaults MUST be host `127.0.0.1` and port `8765` when neither CLI flag nor environment variable supplies a value. The server MUST NOT hardcode `0.0.0.0` or any other public interface.

#### Scenario: Defaults applied when nothing is configured

- **WHEN** `GuiConfig` is constructed with no host or port supplied via CLI or environment
- **THEN** the resulting config MUST have `host == "127.0.0.1"` and `port == 8765`

#### Scenario: Environment variable overrides default port

- **WHEN** environment variable `TALKING_PARROT_GUI_PORT` is set to `"9000"` and no CLI port flag is supplied
- **THEN** the resolved `GuiConfig.port` MUST equal `9000`

#### Scenario: CLI flag overrides environment variable

- **WHEN** environment variable `TALKING_PARROT_GUI_PORT` is set to `"9000"` and CLI flag `--port 9100` is supplied
- **THEN** the resolved `GuiConfig.port` MUST equal `9100`


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
### Requirement: Static asset serving from package directory

The server SHALL serve files under `src/talking_parrot/gui/static/` at HTTP paths rooted at `/`. A request for `/` MUST be rewritten to `/index.html`. The server MUST reject any request whose resolved path escapes the static directory by returning HTTP `403`.

#### Scenario: Root request returns index page

- **WHEN** `GET /` is issued to the running server
- **THEN** the response MUST have status `200`, `Content-Type` starting with `text/html`, and body equal to the bytes of `gui/static/index.html`

#### Scenario: Path traversal rejected

- **WHEN** `GET /../../etc/passwd` is issued to the running server
- **THEN** the response MUST have status `403`


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
### Requirement: Range header support for binary endpoints

The server SHALL honor `Range: bytes=<start>-<end>` request headers on `/api/audio` and `/api/video`. When a satisfiable Range is supplied, the response MUST have status `206` and include `Content-Range: bytes <start>-<end>/<total>`, `Accept-Ranges: bytes`, and a `Content-Length` matching the returned slice. When the requested Range is unsatisfiable, the response MUST have status `416`.

#### Scenario: Partial content for valid range

- **WHEN** a `GET /api/video` request includes `Range: bytes=0-1023` and the source file is at least 1024 bytes long
- **THEN** the response status MUST be `206`, `Content-Length` MUST equal `1024`, and `Content-Range` MUST equal `bytes 0-1023/<total>` where `<total>` is the file size

#### Scenario: Unsatisfiable range rejected

- **WHEN** a `GET /api/video` request includes `Range: bytes=999999999999-` for a file smaller than that offset
- **THEN** the response status MUST be `416`


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
### Requirement: Threaded request handling

The server SHALL use `http.server.ThreadingHTTPServer` so concurrent fetches from the SPA do not block one another. The server MUST NOT use the single-threaded `HTTPServer` class.

#### Scenario: Two simultaneous slow requests both complete

- **WHEN** two clients issue `GET /api/audio?start_ms=0&end_ms=1000` requests in parallel
- **THEN** both responses MUST have status `200` and neither client MUST observe the other's request blocking its connection


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
### Requirement: Stdout-only logging

The server SHALL emit operational logs only to stdout via Python `logging`. The `talking_parrot.gui` logger and its descendants MUST NOT register a `FileHandler` or any handler that writes to disk.

#### Scenario: Logger has no FileHandler attached

- **WHEN** `gui.http_server.serve(...)` has been called once
- **THEN** `logging.getLogger("talking_parrot.gui").handlers` and the handlers of all its ancestor loggers up to the root MUST contain zero instances of `logging.FileHandler`

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