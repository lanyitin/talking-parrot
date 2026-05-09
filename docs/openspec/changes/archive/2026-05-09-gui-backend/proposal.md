# Proposal: gui-backend

## Why

Task 2 in `docs/planning/quality-and-tooling/02-analysis-gui.md` requires a browser-based debug timeline viewer so developers can inspect VAD probabilities, waveforms, transcription metrics, and subtitles for a `.tp` project. ADR-0001 commits the project to a Browser-SPA-over-local-HTTP architecture (no Electron, no Qt, no new GUI framework dependency). This change delivers the **backend half**: a stdlib-only HTTP server, a pure-function `/api/*` router over `ProjectSnapshot`, a CLI entry point, and the bridge surface that a future MCP server will read flagged regions from. The frontend SPA is split into the follow-up `gui-frontend-timeline` and `gui-playback` changes; this change ships only a placeholder `static/index.html` so the backend can be exercised end-to-end without depending on the SPA work.

The shared layer (`ProjectSnapshot`, `SnapshotLoader`, `FileSnapshotLoader`) was archived as `shared-layer` on 2026-05-09. This change is the first consumer of that layer.

## What Changes

- Add a new `src/talking_parrot/gui/` package with four modules: `__init__.py`, `http_server.py` (stdlib `http.server` based local server), `api.py` (pure-function endpoint router taking `ProjectSnapshot` and query mappings, returning JSON-serialisable dicts or `bytes`), `cli.py` (`uv run python -m talking_parrot.gui` entry point).
- Add `src/talking_parrot/gui/static/index.html` — a placeholder page declaring the SPA mount point and listing the `/api/*` endpoints; CSS/JS modules are out of scope here and arrive in `gui-frontend-timeline`.
- Define eight `GET` JSON endpoints — `/api/summary`, `/api/waveform`, `/api/vad_probs`, `/api/vad_segments`, `/api/subtitles`, `/api/subtitle_tokens`, `/api/video_info`, `/api/flagged_regions` — each as a separate function in `api.py` (ISP).
- Define one `POST` endpoint `/api/flagged_regions` that writes into a module-level read-only-after-startup-but-mutable-via-explicit-API in-process dict; expose a public read-only accessor `gui.http_server.get_flagged_regions()` that the future MCP server will call.
- Define two binary endpoints — `/api/audio` (PCM WAV slice, stdlib `wave`/`struct`) and `/api/video` (Range-aware byte serving from the source path recorded in `ProjectSnapshot.source_path`).
- Wire CLI flags `--project`, `--host` (default `127.0.0.1`), `--port` (default `8765`) and corresponding env vars `TALKING_PARROT_GUI_HOST`, `TALKING_PARROT_GUI_PORT`, `TALKING_PARROT_GUI_PROJECT` for Factor III configuration injection.
- Load the project once at startup via `FileSnapshotLoader`, hold the resulting `ProjectSnapshot` in a module-level value that is set exactly once and never reassigned (Factor VI).
- Log to stdout only via `logging.getLogger("talking_parrot.gui")`; no file handler (Factor XI).
- Add tests under `tests/unit/gui/` exercising every endpoint against a fixture `ProjectSnapshot`, using stdlib `http.client` against a server bound to an ephemeral port (no new dep).

## Impact

- **New capabilities** (specs created): `gui-http-server`, `gui-api-endpoints`, `gui-snapshot-bootstrap`, `gui-flagged-regions-bridge`.
- **Touched files**: only additions under `src/talking_parrot/gui/` and `tests/unit/gui/`. No existing module changes.
- **Dependencies**: zero new third-party packages. `http.server`, `wave`, `struct`, `json`, `logging`, `argparse`, `os`, `pathlib`, `urllib.parse`, `mimetypes` from the stdlib only. `numpy` is already an `[align]` extra and is the only candidate for waveform downsampling; this change implements waveform downsampling using pure Python list arithmetic so the GUI runs without the `[align]` extra.
- **Downstream consumers**: `gui-frontend-timeline` and `gui-playback` will consume `/api/*`. `mcp-gui-bridge` (later change) will call `gui.http_server.get_flagged_regions()`.
- **Out of scope**: SPA frontend (CSS/JS modules), MCP integration, ASR re-run, project mutation.
