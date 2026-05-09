# Tasks: gui-backend

## 1. Package scaffolding

- [x] 1.1 Create empty package `src/talking_parrot/gui/__init__.py` exporting nothing public; verify via `uv run python -c "import talking_parrot.gui"`.
- [x] 1.2 Create empty test package `tests/unit/gui/__init__.py`; verify via `uv run pytest tests/unit/gui -q` collecting zero tests.

## 2. Server Library Selection — Stdlib-only server library

- [x] 2.1 [P] Implement requirement `Stdlib-only server library` by adding `gui/http_server.py` that imports only stdlib modules; verified by `tests/unit/gui/test_http_server_imports.py::test_no_third_party_imports`.

## 3. Configuration Resolution Order — Configurable host and port

- [x] 3.1 Implement requirement `Configurable host and port` defaults (`127.0.0.1`/`8765`) in a frozen `GuiConfig` dataclass in `gui/cli.py`; verified by `test_cli.py::test_gui_config_defaults`.
- [x] 3.2 Implement env-var resolution (`TALKING_PARROT_GUI_HOST`, `TALKING_PARROT_GUI_PORT`) in `resolve_config(argv, env)`; verified by `test_cli.py::test_resolve_config_env_overrides_default`.
- [x] 3.3 Implement CLI override of env (`--host`, `--port`) in `resolve_config`; verified by `test_cli.py::test_resolve_config_cli_overrides_env`.

## 4. Snapshot Bootstrap — Snapshot loaded once at startup

- [x] 4.1 Implement requirement `Snapshot loaded once at startup` in `gui.cli.main(argv)` calling `FileSnapshotLoader().load(...)` exactly once before serving; verified by `test_cli.py::test_loader_called_once` patching `FileSnapshotLoader.load` to count invocations.
- [x] 4.2 Implement missing-project failure: exit non-zero with stderr containing `--project` and `TALKING_PARROT_GUI_PROJECT`; verified by `test_cli.py::test_missing_project_exits` (capsys).

## 5. Snapshot Bootstrap — Snapshot held read-only after bootstrap

- [x] 5.1 Implement requirement `Snapshot held read-only after bootstrap` in `gui.http_server.serve` storing snapshot on the server instance and refusing rebind; verified by `test_http_server.py::test_serve_rejects_rebind` (RuntimeError contains `snapshot already bound`).
- [x] 5.2 Verify the snapshot remains frozen during request handling via `test_http_server.py::test_snapshot_remains_frozen`.

## 6. Snapshot Bootstrap — Reuse of shared layer types

- [x] 6.1 [P] Implement requirement `Reuse of shared layer types`: `gui` package imports `ProjectSnapshot`, `AudioInfo`, `FileSnapshotLoader`, `SnapshotLoader` from `talking_parrot.shared`; verified by `test_http_server.py::test_no_shared_layer_redefinition` walking package members.

## 7. Snapshot Bootstrap — Configuration injected, never hardcoded

- [x] 7.1 [P] Implement requirement `Configuration injected, never hardcoded`: ensure no hardcoded host/port literals in `gui/api.py` or in `gui/http_server.py` outside the `GuiConfig` default helper; verified by `test_http_server.py::test_no_hardcoded_host_port` (regex scan).

## 8. Static Asset Serving — Static asset serving from package directory

- [x] 8.1 Create `src/talking_parrot/gui/static/index.html` placeholder with a `<div id="app"></div>` mount point and `<noscript>` API catalogue; verified by `test_http_server.py::test_root_returns_index_html`.
- [x] 8.2 Implement requirement `Static asset serving from package directory` via `importlib.resources.files("talking_parrot.gui.static")`, rewriting `/` to `/index.html` and rejecting traversal with HTTP 403; verified by `test_http_server.py::test_path_traversal_rejected`.

## 9. Endpoint Routing — Pure-function endpoint dispatcher

- [x] 9.1 Define frozen `ApiResponse` dataclass in `gui/api.py`; verified by `test_api.py::test_api_response_frozen`.
- [x] 9.2 Implement requirement `Pure-function endpoint dispatcher` (`dispatch(method, path, query, snapshot, body)`) returning 404 for unknown paths and 405 for unsupported methods; verified by `test_api.py::test_dispatch_unknown_route` and `::test_dispatch_method_not_allowed`.

## 10. API Contract — JSON GET endpoints (parallel-safe)

- [x] 10.1 [P] Implement requirement `GET /api/summary contract` returning the contracted JSON keys; verified by `test_api.py::test_summary_returns_audio_info_keys`.
- [x] 10.2 [P] Implement requirement `GET /api/waveform contract` with `start_ms`/`end_ms`/`width` validation and pure-Python downsampling; verified by `test_api.py::test_waveform_length_matches_width`, `::test_waveform_rejects_missing_width`, `::test_waveform_rejects_oversized_width`.
- [x] 10.3 [P] Implement requirement `GET /api/vad_probs contract` with `[start_ms, end_ms)` filtering and optional `downsample`; verified by `test_api.py::test_vad_probs_filters_by_interval` and `::test_vad_probs_arrays_equal_length`.
- [x] 10.4 [P] Implement requirement `GET /api/vad_segments contract` returning overlapping segments; verified by `test_api.py::test_vad_segments_overlap_filter`.
- [x] 10.5 [P] Implement requirement `GET /api/subtitles contract` preserving snapshot indices; verified by `test_api.py::test_subtitles_preserve_index`.
- [x] 10.6 [P] Implement requirement `GET /api/subtitle_tokens contract` with `index` validation (400 missing/invalid, 404 out-of-range); verified by `test_api.py::test_subtitle_tokens_index_required` and `::test_subtitle_tokens_out_of_range`.
- [x] 10.7 [P] Implement requirement `GET /api/video_info contract` computing `browser_playable` from MIME; verified by `test_api.py::test_video_info_mkv_not_browser_playable`.

## 11. API Contract — Binary endpoints

- [x] 11.1 Implement requirement `GET /api/audio contract` assembling 16-bit PCM mono WAV via stdlib `wave`/`struct`; verified by `test_api.py::test_audio_response_starts_with_riff_header` and `::test_audio_404_when_source_missing`.
- [x] 11.2 Implement requirement `Range header support for binary endpoints` for `/api/video` (full body without Range; 206 with Range; 416 unsatisfiable); verified by `test_http_server.py::test_video_full_when_no_range`, `::test_video_range_partial_content`, `::test_video_range_unsatisfiable_416`.

## 12. Endpoint Routing — Threaded request handling

- [x] 12.1 Implement requirement `Threaded request handling` using `http.server.ThreadingHTTPServer`; verified by `test_http_server.py::test_two_simultaneous_requests_complete` issuing two concurrent slow requests.

## 13. Flagged Regions Bridge — FlaggedRegion value object

- [x] 13.1 Implement requirement `FlaggedRegion value object` as frozen dataclass with `slots=True` in `gui/http_server.py`; verified by `test_http_server.py::test_flagged_region_frozen`.

## 14. Flagged Regions Bridge — Public read-only accessor for MCP bridge

- [x] 14.1 Implement requirement `Public read-only accessor for MCP bridge` (`get_flagged_regions() -> tuple[FlaggedRegion, ...]`); verified by `test_http_server.py::test_get_flagged_regions_returns_tuple`.
- [x] 14.2 Implement requirement `MCP integration boundary documented` in the `get_flagged_regions` docstring (must contain substring `MCP bridge`); verified by `test_http_server.py::test_get_flagged_regions_docstring_mentions_mcp_bridge`.

## 15. Flagged Regions Bridge — Atomic replacement under lock

- [x] 15.1 Implement requirement `Atomic replacement under lock` using a module-level `threading.Lock`; verified by `test_http_server.py::test_post_flagged_regions_concurrent_replacement_is_coherent` (two threaded POSTs leave a coherent end state).

## 16. Flagged Regions Bridge — REST surface

- [x] 16.1 Implement requirement `GET /api/flagged_regions contract` returning `{status, regions}`; verified by `test_api.py::test_flagged_regions_empty_status` and `::test_flagged_regions_after_post`.
- [x] 16.2 Implement requirement `POST /api/flagged_regions contract` with JSON validation and atomic replacement; verified by `test_api.py::test_post_flagged_regions_rejects_malformed_json` and `::test_post_flagged_regions_replaces_atomically`.
- [x] 16.3 Implement requirement `Cleared by POST with empty list`; verified by `test_api.py::test_post_empty_list_clears_regions`.

## 17. API Contract — Forbidden weasel words excluded from JSON keys

- [x] 17.1 [P] Implement requirement `Forbidden weasel words excluded from JSON keys` (snake_case keys; no `tbd`/`todo`/`tktk` substrings); verified by `test_api.py::test_summary_keys_are_snake_case` (regex `^[a-z][a-z0-9_]*$`).

## 18. Goals — Stdout-only logging

- [x] 18.1 Implement requirement `Stdout-only logging` configuring `logging.getLogger("talking_parrot.gui")` with `StreamHandler(sys.stdout)` only; verified by `test_http_server.py::test_no_file_handler_attached` walking the handler ancestry.

## 19. Testing Strategy — Fixture builder

- [x] 19.1 [P] Add `tests/unit/gui/conftest.py` providing `make_snapshot(...)` constructing a fully populated `ProjectSnapshot` with temporary audio/video files; verified by `test_api.py::test_fixture_builder_produces_valid_snapshot`.
- [x] 19.2 Boot `ThreadingHTTPServer` on ephemeral port `0` for integration tests using stdlib `http.client`; verified by `test_http_server.py::test_server_binds_ephemeral_port`.

## 20. Non-Goals — Frontend out of scope

- [x] 20.1 [P] Confirm `gui/static/` contains only `index.html` (no `js/`, no `css/`); verified by `test_http_server.py::test_static_only_contains_index_html`.

## 21. Architectural Decisions / Context — Documentation cross-check

- [x] 21.1 [P] Add `tests/unit/gui/test_design_alignment.py` asserting module docstrings of `gui.http_server`, `gui.api`, `gui.cli` cite the relevant Architectural Decisions sections (`Server Library Selection`, `Endpoint Routing`, `Configuration Resolution Order`).
- [x] 21.2 [P] Add an import-graph test asserting `talking_parrot.gui` does not import from `talking_parrot.regression` or `talking_parrot.mcp`; place under `tests/unit/gui/test_dependency_direction.py`.

## 22. Open Questions / Suggested Future Dependency

- [x] 22.1 Add a comment block at the top of `gui/api.py` enumerating the pure-Python waveform downsampling complexity and naming `numpy` as the candidate replacement for a future change; verified by `test_api.py::test_api_module_lists_numpy_followup`.

## 23. Quality gates

- [x] 23.1 Run `uv run ruff check .` and `uv run ruff format --check .` with zero errors.
- [x] 23.2 Run `uv run mypy src` with zero errors for the new `gui` package.
- [x] 23.3 Run `uv run pytest` with the full test suite green.
