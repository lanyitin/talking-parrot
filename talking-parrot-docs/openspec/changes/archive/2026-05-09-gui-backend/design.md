# Design: gui-backend

## Context

The user explicitly likes the audio2subtitle GUI architecture: a vanilla-JS SPA served by a Python `http.server`-based local HTTP server with `/api/*` JSON endpoints (ADR-0001). This change is cross-cutting (a new top-level package, a new architectural pattern in the codebase) and warrants a design document. The shared layer (`ProjectSnapshot`, `SnapshotLoader`) was just archived; this change is its first consumer and MUST NOT redefine those types.

## Goals

- Stdlib-only HTTP backend; zero new third-party dependencies.
- Pure-function endpoint handlers in `api.py` so each handler is independently testable without spinning up a TCP socket.
- 12-factor-clean configuration: host, port, project path injected via CLI/env (Factor III); single read-only snapshot at module scope (Factor VI); log to stdout only (Factor XI).
- ISP-clean: one function per endpoint, no fat handler interface.

## Non-Goals

- Frontend SPA assets (handled by later changes).
- MCP integration (handled by `mcp-gui-bridge`).
- TLS / authentication (local developer tool only).

## Architectural Decisions

### Server Library Selection

Use `http.server.ThreadingHTTPServer` from the stdlib. It supports keep-alive, threaded request handling adequate for one-developer-at-a-time use, and `Range`-header parsing can be implemented in the handler since the binary endpoints already need custom logic. No new dependency. Alternative `aiohttp` / `fastapi` would require adding a third-party dep, which CLAUDE.md forbids without explicit instruction.

### Snapshot Bootstrap

`gui.cli` resolves project path, instantiates `FileSnapshotLoader`, calls `loader.load(path)`, and passes the resulting `ProjectSnapshot` to `gui.http_server.serve(snapshot, host, port)`. Inside `http_server`, the snapshot is stored on the `ThreadingHTTPServer` instance as an attribute (`server.snapshot`) so the request handler reads it without globals. The handler MUST treat the attribute as read-only.

### Endpoint Routing

`api.py` exports a `dispatch(method: str, path: str, query: Mapping[str, str], snapshot: ProjectSnapshot, body: bytes | None) -> ApiResponse` function. `ApiResponse` is a frozen dataclass with `status: int`, `content_type: str`, `body: bytes`, `headers: dict[str, str]`. The dispatcher is a flat `if/elif` over `(method, path)` pairs that delegates to one private function per endpoint. Each endpoint function has signature `(snapshot, query) -> ApiResponse` (or `(snapshot, query, body) -> ApiResponse` for the POST). This satisfies ISP (each endpoint is a separate function) and lets tests call endpoint functions directly.

### Configuration Resolution Order

For each of host, port, project path: CLI flag wins, then environment variable, then a documented default (`127.0.0.1`, `8765`, no default for project — it is required). `gui.cli.resolve_config()` returns a frozen `GuiConfig` dataclass; `serve()` accepts the config object plus the snapshot.

### Flagged Regions Bridge

A module-level `_flagged_regions: list[FlaggedRegion] = []` lives in `gui.http_server`. Two public functions: `get_flagged_regions() -> tuple[FlaggedRegion, ...]` returns an immutable snapshot of the current list; the `POST /api/flagged_regions` endpoint replaces the list contents atomically via a module-private `_set_flagged_regions(regions)` helper guarded by a `threading.Lock`. The future MCP server will import only `get_flagged_regions`, never the underlying list.

### Static Asset Serving

`http_server` resolves `gui/static/` relative to the package via `importlib.resources`. Requests for `/` rewrite to `/index.html`. Path traversal is rejected by resolving the requested path and verifying it stays within the static directory. MIME types come from `mimetypes.guess_type`.

## API Contract

All JSON responses are `application/json; charset=utf-8`. Error payloads are `{"error": "<message>"}`. `start_ms` and `end_ms` form a half-open interval `[start_ms, end_ms)`.

### GET /api/summary

- Query: none.
- 200 body: `{duration_ms: int, sample_rate: int, rms_mean: float, rms_peak: float, subtitle_count: int, quality_distribution: {accepted: int, low_confidence: int}, detected_language: str | null, hotspots: [{time_ms: int, type: str, text: str | null}]}`.
- Failures: 500 if snapshot is missing required scalar fields.

### GET /api/waveform

- Query: `start_ms: int >= 0`, `end_ms: int > start_ms`, `width: int in [1, 8192]`.
- 200 body: `[{peak_pos: float, peak_neg: float}]` of length exactly `width`.
- Failures: 400 on missing/invalid query params; 404 if `audio_info.duration_ms` is zero or interval is out of range.

### GET /api/vad_probs

- Query: `start_ms: int >= 0`, `end_ms: int > start_ms`, optional `downsample: int in [1, 64]` (default 1).
- 200 body: `{times_ms: [int], silero: [float], ten_vad: [float], composite: [float]}` — arrays equal length, indexed by frame.
- Failures: 400 on invalid query.

### GET /api/vad_segments

- Query: `start_ms: int >= 0`, `end_ms: int > start_ms`.
- 200 body: `[{start_ms: int, end_ms: int, composite_score: float}]` filtered to segments overlapping the interval.
- Failures: 400 on invalid query.

### GET /api/subtitles

- Query: `start_ms: int >= 0`, `end_ms: int > start_ms`.
- 200 body: `[{index: int, start_ms: int, end_ms: int, text: str, avg_logprob: float, no_speech_prob: float, quality_status: str}]`.
- Failures: 400 on invalid query.

### GET /api/subtitle_tokens

- Query: `index: int >= 0`.
- 200 body: `{subtitle: {index, start_ms, end_ms, text, avg_logprob, no_speech_prob}, tokens: [{word: str, start_ms: float, end_ms: float, score: float}]}`.
- Failures: 400 on missing `index`; 404 when `index` is out of range.

### GET /api/audio

- Query: `start_ms: int >= 0`, `end_ms: int > start_ms`.
- 200 response: `Content-Type: audio/wav`, body is a 16-bit PCM mono WAV file at `audio_info.sample_rate`.
- Failures: 400 on invalid query; 404 if the source audio file is missing.

### GET /api/video_info

- Query: none.
- 200 body: `{is_video: bool, container: str | null, browser_playable: bool, mime_type: str, duration_ms: int}`.
- Failures: 500 if snapshot lacks `source_path`.

### GET /api/video

- Query: none. Honors `Range: bytes=<start>-<end>` request header.
- 200 (no Range) or 206 (Range) response: body bytes from the source video file with appropriate `Content-Range`, `Accept-Ranges: bytes`, `Content-Length`, `Content-Type` headers.
- Failures: 404 if source file is not video or missing; 416 on unsatisfiable range.

### GET /api/flagged_regions

- Query: none.
- 200 body: `{status: "ok" | "empty", regions: [{start_ms: int, end_ms: int, label: str | null}]}`. `status` is `"empty"` when the list is empty, `"ok"` otherwise.

### POST /api/flagged_regions

- Request body: `{regions: [{start_ms: int, end_ms: int, label?: str}]}` as `application/json`.
- 200 body: `{status: "ok"}`.
- Failures: 400 on malformed JSON, missing `regions`, or per-region invalid `start_ms`/`end_ms`.

## Testing Strategy

Tests under `tests/unit/gui/` are split:

- `test_api.py` — calls each endpoint function directly with a fixture `ProjectSnapshot`; covers happy path and every documented failure mode.
- `test_http_server.py` — boots `ThreadingHTTPServer` on an ephemeral port (port `0`), issues stdlib `http.client` requests to verify routing, static asset serving, Range handling, and the flagged-regions bridge.
- `test_cli.py` — tests `resolve_config()` precedence (CLI > env > default) and the project-required failure path.

## Open Questions

None. All design decisions above are stdlib-only and require no external approval.

## Suggested Future Dependency

`numpy` is already used in the pipeline behind the `[align]` extra. If profiling shows pure-Python waveform downsampling is too slow on long recordings, a follow-up change MAY promote `numpy` to a base dependency for the `gui` package — but only with explicit user approval per CLAUDE.md.
