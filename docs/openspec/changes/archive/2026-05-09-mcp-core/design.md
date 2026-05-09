## Context

This change introduces the talking-parrot MCP server core. Two factors warrant a design document:

1. **New external dependency** — `mcp` (FastMCP) must be adopted to provide decorator-based tool registration and dual stdio / streamable-HTTP transport handling. The dep is recorded as an Open Question and gated on operator approval.
2. **New transport / lifecycle behaviour** — streamable HTTP is the default (per ADR-0002), the snapshot is held at module level read-only (per shared-architecture §1 warning), and the entry point unifies CLI parsing, env-var resolution, snapshot loading, and transport dispatch.

Existing related artifacts: `docs/planning/quality-and-tooling/03-mcp-server.md`, `docs/planning/quality-and-tooling/shared-architecture.md`, `docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md`. Existing specs depended on (read-only): `project-snapshot`, `snapshot-loader`.

## Goals / Non-Goals

**Goals**

- Ship a runnable `uv run python -m talking_parrot.mcp --project <path>` entry point that defaults to streamable HTTP on `127.0.0.1:8765/mcp`.
- Expose seven read-only tools (`summary`, `get_vad_segments`, `get_vad_frames`, `get_subtitles`, `get_pre_postprocess_subtitles`, `get_transcription_results`, `diagnostics`) each as a separate decorated function (ISP).
- Keep tool implementations pure functions over `ProjectSnapshot` so they are hermetically unit-testable without FastMCP installed.
- Honour Factor III (env / CLI injection), Factor VI (read-only module-level snapshot), Factor XI (stdout logging only).

**Non-Goals**

- No GUI co-start, `get_flagged_regions`, or resource URIs (deferred to `mcp-gui-bridge`).
- No project mutation, no pipeline re-runs, no authentication beyond loopback binding.
- No multi-project loading; one snapshot per process lifetime.
- No auto-adoption of the `mcp` dep without operator approval.

## Decisions

### Decision: Streamable HTTP is the default transport

The MCP server SHALL default to streamable HTTP. `--transport stdio` is the explicit opt-in. Default bind is `127.0.0.1:8765` on path `/mcp`; both host and port SHALL be overridable by `TALKING_PARROT_MCP_HOST` / `TALKING_PARROT_MCP_PORT` env vars and `--host` / `--port` CLI flags, with CLI flags taking precedence over env vars and env vars taking precedence over built-in defaults. Rationale (ADR-0002): streamable HTTP survives agent restart, allows multiple concurrent agent connections, leaves the main thread free for a future GUI co-start, and aligns with Factor VII port binding.

### Decision: Module-level read-only snapshot, no global mutable state

`server.py` SHALL hold the loaded `ProjectSnapshot` in a module-level binding initialised exactly once during entry-point setup, before tools are registered. Tools SHALL read this binding via a pure accessor and SHALL NOT reassign or mutate it. This explicitly avoids the audio2subtitle `_project` global-mutable anti-pattern (shared-architecture §1 warning). Reload at runtime is not supported in this change; restart the process to load a different project.

### Decision: One decorated function per tool (ISP)

Each MCP tool SHALL be a separate `@mcp.tool()`-decorated function in `server.py`. No fat dispatcher, no method on a god-class. Each tool function SHALL delegate to a pure helper that takes `ProjectSnapshot` (and tool parameters) and returns the result dict, so the helper is unit-testable independent of FastMCP.

### Decision: Tool catalogue and time-range filtering

Tools SHALL accept optional `start_ms` and `end_ms` integer parameters where applicable. When both are `None`, the full collection is returned. When provided, items overlapping `[start_ms, end_ms]` (inclusive) SHALL be returned. Time units SHALL be milliseconds and SHALL be documented in each tool docstring. The seven tools are: `summary` (no args), `get_vad_segments(start_ms, end_ms)`, `get_vad_frames(start_ms, end_ms)`, `get_subtitles(start_ms, end_ms)`, `get_pre_postprocess_subtitles(start_ms, end_ms)`, `get_transcription_results(chunk_index)`, `diagnostics()`.

### Decision: Diagnostics are derived purely from snapshot

`diagnostics()` SHALL compute low-confidence cues, repetition flags, and no-speech flags purely from `ProjectSnapshot.transcription_results` / `ProjectSnapshot.subtitles`, with no I/O and no external calls. Thresholds SHALL be configurable via the existing project config snapshot when present, falling back to documented defaults otherwise.

### Decision: CLI / env-var injection layer

`cli.py` SHALL parse arguments (`--project`, `--transport`, `--host`, `--port`), resolve env vars, load the snapshot via `SnapshotLoader`, install it on the `server` module, and invoke transport-specific run. `--project` is required. `--transport` accepts `http` (default) or `stdio`. The CLI SHALL log resolved configuration to stdout via `logging` (Factor XI) before running the transport.

### Decision: Suggested dependency `mcp` (FastMCP), operator approval required

The `mcp` package (FastMCP) is the only new third-party dep. It SHALL NOT be added to `pyproject.toml` by this change's tasks; instead, an explicit operator-approval gate precedes any `uv add mcp`. Pure-function tool helpers and CLI argument parsing SHALL be implemented and tested independent of FastMCP, so the no-dep portions of the change are mergeable even if the dep approval slips.

## Risks / Trade-offs

- **`mcp` dep approval slips.** Mitigation: pure helpers and CLI argv parsing implemented and tested without the dep; transport wiring is the only blocked surface.
- **FastMCP API churn.** Mitigation: pin to a specific version when the dep is approved; keep transport wiring confined to `server.py` so churn is localised.
- **Port collision on default 8765.** Mitigation: rely on the OS to surface bind errors; document `--port` override and env var.
- **Time-range semantics ambiguity (ms vs seconds).** Mitigation: every tool docstring SHALL state milliseconds explicitly; helpers reject non-int inputs at the boundary.

## Manual smoke test (streamable-HTTP)

After `uv add mcp` and the HTTP runner wiring (tasks 14, 16) land, the
default transport can be validated with a manual `curl` smoke test:

```bash
# Terminal 1 — start the server with a known-good .tp project.
uv run python -m talking_parrot.mcp --project test-samples/sample1/sample1.tp

# Terminal 2 — list registered tools via JSON-RPC over streamable HTTP.
curl -sS -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

The response SHALL include the seven tool names registered in
`server.build_mcp_app`: `summary`, `get_vad_segments`, `get_vad_frames`,
`get_subtitles`, `get_pre_postprocess_subtitles`, `get_transcription_results`,
`diagnostics`. Press Ctrl-C in terminal 1; the process SHALL exit with
status `0` (Shutdown-is-graceful).

## Migration Plan

This is a new package; no migration. Existing `ProjectSnapshot` / `SnapshotLoader` consumers are unaffected.

## Open Questions

- **Suggested dependency: `mcp` (FastMCP).** Operator must approve before `uv add mcp` runs. Until then, transport wiring tasks are blocked but unblock automatically on approval.
- **Transport-level test harness.** Whether FastMCP exposes a usable in-process test client for streamable HTTP is unknown until the dep lands; transport-level tests are deferred to a follow-up change if the harness is unavailable.
