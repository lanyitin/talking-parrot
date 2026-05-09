# gui-api-endpoints Specification

## Purpose

TBD - created by archiving change 'gui-backend'. Update Purpose after archive.

## Requirements

### Requirement: Pure-function endpoint dispatcher

The system SHALL provide `dispatch(method: str, path: str, query: Mapping[str, str], snapshot: ProjectSnapshot, body: bytes | None) -> ApiResponse` in `src/talking_parrot/gui/api.py`. `ApiResponse` MUST be a frozen dataclass with fields `status: int`, `content_type: str`, `body: bytes`, and `headers: dict[str, str]`. Each endpoint MUST be implemented as a separate module-level function whose only inputs are the snapshot, the parsed query, and (for POST) the request body bytes. Endpoint functions MUST NOT perform network I/O and MUST NOT mutate the snapshot.

#### Scenario: Unknown route returns 404

- **WHEN** `dispatch("GET", "/api/does_not_exist", {}, snapshot, None)` is called
- **THEN** the returned `ApiResponse.status` MUST equal `404`

#### Scenario: Unsupported method returns 405

- **WHEN** `dispatch("DELETE", "/api/summary", {}, snapshot, None)` is called
- **THEN** the returned `ApiResponse.status` MUST equal `405`


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
### Requirement: GET /api/summary contract

The `/api/summary` endpoint SHALL accept no query parameters and return JSON with keys `duration_ms` (int), `sample_rate` (int), `rms_mean` (float), `rms_peak` (float), `subtitle_count` (int), `quality_distribution` (object with int fields `accepted` and `low_confidence`), `detected_language` (string or null), and `hotspots` (list of objects with `time_ms: int`, `type: str`, `text: str | null`).

#### Scenario: Summary returns audio info from snapshot

- **WHEN** `dispatch("GET", "/api/summary", {}, snapshot, None)` is called for a snapshot whose `audio_info.sample_rate` is `16000` and `audio_info.duration_ms` is `42000`
- **THEN** the parsed JSON body MUST contain `sample_rate == 16000` and `duration_ms == 42000`


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
### Requirement: GET /api/waveform contract

The `/api/waveform` endpoint SHALL require integer query parameters `start_ms`, `end_ms`, `width`. It MUST return a JSON array of exactly `width` objects, each with float fields `peak_pos` and `peak_neg`. The endpoint MUST return status `400` when any required parameter is missing, non-integer, or violates `start_ms >= 0`, `end_ms > start_ms`, or `1 <= width <= 8192`. It MUST return status `404` when the requested interval lies entirely outside `[0, audio_info.duration_ms)`.

#### Scenario: Returned array length matches width

- **WHEN** `dispatch("GET", "/api/waveform", {"start_ms": "0", "end_ms": "1000", "width": "200"}, snapshot, None)` is called against a snapshot with `duration_ms >= 1000`
- **THEN** the response status MUST be `200` and the JSON body MUST be a list of exactly `200` objects

#### Scenario: Missing query parameter rejected

- **WHEN** `dispatch("GET", "/api/waveform", {"start_ms": "0", "end_ms": "1000"}, snapshot, None)` is called without `width`
- **THEN** the response status MUST be `400`

#### Scenario: Width above maximum rejected

- **WHEN** `dispatch("GET", "/api/waveform", {"start_ms": "0", "end_ms": "1000", "width": "9000"}, snapshot, None)` is called
- **THEN** the response status MUST be `400`


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
### Requirement: GET /api/vad_probs contract

The `/api/vad_probs` endpoint SHALL accept integer query parameters `start_ms` and `end_ms` and an optional integer `downsample` defaulting to `1` and constrained to `[1, 64]`. It MUST return JSON `{times_ms: [int], silero: [float], ten_vad: [float], composite: [float]}` where the four arrays have equal length and contain only frames whose `time_ms` falls in `[start_ms, end_ms)`. Frames missing a backend probability MUST be encoded as `0.0` in the corresponding array.

#### Scenario: Frame filtering by interval

- **WHEN** the endpoint is called for `start_ms=1000, end_ms=2000` against a snapshot with vad_frames at 500, 1500, and 2500 ms
- **THEN** the returned `times_ms` array MUST equal `[1500]`


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
### Requirement: GET /api/vad_segments contract

The `/api/vad_segments` endpoint SHALL accept integer query parameters `start_ms` and `end_ms`. It MUST return a JSON list of objects `{start_ms: int, end_ms: int, composite_score: float}` containing exactly those `VadSegment` entries whose `[seg.start_ms, seg.end_ms)` interval overlaps `[start_ms, end_ms)`.

#### Scenario: Overlapping segment included

- **WHEN** the endpoint is called for `start_ms=1000, end_ms=2000` against a snapshot whose only segment is `[1500, 2500)`
- **THEN** the returned list MUST contain exactly one entry with `start_ms == 1500` and `end_ms == 2500`


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
### Requirement: GET /api/subtitles contract

The `/api/subtitles` endpoint SHALL accept integer query parameters `start_ms` and `end_ms` and return a JSON list of `{index: int, start_ms: int, end_ms: int, text: str, avg_logprob: float, no_speech_prob: float, quality_status: str}` objects covering subtitles whose interval overlaps the query interval. The `index` field MUST equal the subtitle's position in `snapshot.subtitles`.

#### Scenario: Index reflects snapshot position

- **WHEN** the endpoint is called against a snapshot with three subtitles all overlapping the query interval
- **THEN** the returned list MUST contain three entries whose `index` fields equal `0`, `1`, and `2` in order


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
### Requirement: GET /api/subtitle_tokens contract

The `/api/subtitle_tokens` endpoint SHALL accept the integer query parameter `index`. It MUST return JSON `{subtitle: {...}, tokens: [...]}` where `tokens` lists the aligned tokens covering the subtitle's interval as `{word: str, start_ms: float, end_ms: float, score: float}`. The endpoint MUST return status `400` when `index` is missing or non-integer and status `404` when `index` is outside `[0, len(snapshot.subtitles))`.

#### Scenario: Out-of-range index rejected

- **WHEN** the endpoint is called with `index=99` against a snapshot containing two subtitles
- **THEN** the response status MUST be `404`


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
### Requirement: GET /api/audio contract

The `/api/audio` endpoint SHALL accept integer query parameters `start_ms` and `end_ms` and return a 16-bit PCM mono WAV byte stream at `audio_info.sample_rate` for the requested interval. The response `content_type` MUST equal `audio/wav`. The endpoint MUST return status `400` on invalid query and status `404` when the source audio file referenced by `snapshot.source_path` is missing.

#### Scenario: Response content-type is audio/wav

- **WHEN** the endpoint returns a successful slice
- **THEN** `ApiResponse.content_type` MUST equal `audio/wav` and `ApiResponse.body` MUST begin with the four-byte RIFF header `b"RIFF"`


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
### Requirement: GET /api/video_info contract

The `/api/video_info` endpoint SHALL accept no query parameters and return JSON `{is_video: bool, container: str | null, browser_playable: bool, mime_type: str, duration_ms: int}`. The `browser_playable` field MUST be `true` only when `mime_type` is one of `video/mp4`, `video/webm`, or `video/ogg`.

#### Scenario: MKV reports not browser-playable

- **WHEN** the snapshot's source file has the suffix `.mkv`
- **THEN** the returned `browser_playable` MUST be `false` and `is_video` MUST be `true`


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
### Requirement: GET /api/flagged_regions contract

The `GET /api/flagged_regions` endpoint SHALL return JSON `{status: "ok" | "empty", regions: [...]}`. `status` MUST equal `"empty"` when the in-process region list is empty and `"ok"` otherwise. Each region object MUST contain integer `start_ms`, integer `end_ms`, and either a string `label` or `null`.

#### Scenario: Empty list reported as empty

- **WHEN** no regions have been posted and the endpoint is called
- **THEN** the response body MUST satisfy `status == "empty"` and `regions == []`


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
### Requirement: POST /api/flagged_regions contract

The `POST /api/flagged_regions` endpoint SHALL accept an `application/json` body of shape `{regions: [{start_ms: int, end_ms: int, label?: str}]}` and replace the in-process region list with the supplied entries. On success it MUST return JSON `{status: "ok"}` with HTTP status `200`. The endpoint MUST return status `400` when the body is not valid JSON, when `regions` is missing or not a list, or when any region violates `start_ms >= 0` or `end_ms > start_ms`.

#### Scenario: Replaces previous regions atomically

- **WHEN** the endpoint is invoked with a body listing two regions after a previous call posted three regions
- **THEN** a subsequent `GET /api/flagged_regions` MUST return exactly the two newly-posted regions

#### Scenario: Malformed JSON rejected

- **WHEN** the endpoint is invoked with body bytes `b"not-json"`
- **THEN** the response status MUST be `400`


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
### Requirement: Forbidden weasel words excluded from JSON keys

API response keys SHALL use lowercase snake_case identifiers and MUST NOT include the strings `tbd`, `todo`, or `tktk` in any field name.

#### Scenario: All summary keys are snake_case

- **WHEN** the `/api/summary` endpoint returns a successful response
- **THEN** every top-level key in the parsed JSON MUST match the regex `^[a-z][a-z0-9_]*$`

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