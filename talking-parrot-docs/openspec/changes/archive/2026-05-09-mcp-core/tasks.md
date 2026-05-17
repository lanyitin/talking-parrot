## 1. Package scaffold

- [x] 1.1 Create `src/talking_parrot/mcp/__init__.py`, `__main__.py`, `cli.py`, and `server.py` with module docstrings; verify `uv run python -c "import talking_parrot.mcp"` succeeds.
- [x] 1.2 Add `tests/unit/mcp/__init__.py` and a `conftest.py` exposing a fixture `ProjectSnapshot` (no FastMCP import); verify with `uv run pytest tests/unit/mcp -q`.

## 2. Decision: CLI / env-var injection layer

- [x] 2.1 [P] Implement argument parsing in `cli.py` for `--project`, `--transport`, `--host`, `--port` realising the **Decision: CLI / env-var injection layer** and satisfying the **Entry point loads snapshot then dispatches transport** requirement's missing-flag scenario; verify with `uv run pytest tests/unit/mcp/test_cli_args.py` covering required-flag and invalid-transport cases.
- [x] 2.2 [P] Implement env-var resolution (`TALKING_PARROT_MCP_HOST`, `TALKING_PARROT_MCP_PORT`) with CLI-flag precedence to satisfy the **Configuration is injected via env vars and CLI flags** requirement; verify with `uv run pytest tests/unit/mcp/test_cli_env.py` covering CLI-overrides-env and env-overrides-default cases.
- [x] 2.3 Implement `--transport http|stdio` selection logic and reject any other value with non-zero exit, satisfying the **Transport selection supports HTTP default and stdio opt-in** requirement; verify with `uv run pytest tests/unit/mcp/test_cli_transport_selection.py`.
- [x] 2.4 Wire `cli.py` to load the snapshot via `SnapshotLoader`, install it on `server`, log resolved configuration to stdout via `logging` to satisfy the **Logging targets stdout only** requirement, and dispatch to the selected transport completing the **Entry point loads snapshot then dispatches transport** requirement's HTTP-bind scenario; verify with `uv run pytest tests/unit/mcp/test_cli_dispatch.py` using a stub transport runner that asserts no log file is created on disk.

## 3. Decision: Module-level read-only snapshot, no global mutable state

- [x] 3.1 Implement a single module-level snapshot binding in `server.py` with a pure accessor and a one-shot installer realising the **Decision: Module-level read-only snapshot, no global mutable state** and satisfying the **Module-level snapshot is read-only after init** requirement; verify with `uv run pytest tests/unit/mcp/test_snapshot_binding.py` confirming the accessor returns the installed snapshot.
- [x] 3.2 Add a unit test asserting double-install is rejected and tools never reassign the binding, codifying the audio2subtitle anti-pattern guard called out in the **Module-level snapshot is read-only after init** requirement; verify with `uv run pytest tests/unit/mcp/test_snapshot_binding.py::test_no_reassign`.

## 4. Decision: One decorated function per tool (ISP) and Decision: Tool catalogue and time-range filtering — pure helpers

- [x] 4.1 [P] Implement pure helper `summary_from_snapshot(snapshot)` returning aggregate counts and `audio_duration_ms` realising the **Decision: Tool catalogue and time-range filtering** and satisfying the **`summary` returns aggregate counts and audio duration** requirement; verify with `uv run pytest tests/unit/mcp/test_summary.py`.
- [x] 4.2 [P] Implement pure helpers `vad_segments_in_range`, `vad_frames_in_range`, `subtitles_in_range`, `pre_postprocess_subtitles_in_range` accepting optional `start_ms` / `end_ms` realising the **Decision: Tool catalogue and time-range filtering** and satisfying the **Time-range tools accept optional millisecond bounds** requirement; verify with `uv run pytest tests/unit/mcp/test_range_helpers.py` covering no-bounds and bounded-overlap cases per tool.
- [x] 4.3 [P] Implement pure helper `transcription_results_for_chunk(snapshot, chunk_index)` satisfying the **`get_transcription_results` filters by chunk index** requirement; verify with `uv run pytest tests/unit/mcp/test_transcription_results.py` covering known-chunk and unknown-chunk cases.
- [x] 4.4 [P] Implement pure helper `diagnostics_from_snapshot` computing low-confidence / repetition / no-speech flags realising the **Decision: Diagnostics are derived purely from snapshot** and satisfying the **`diagnostics` is derived purely from the snapshot** requirement; verify with `uv run pytest tests/unit/mcp/test_diagnostics.py` asserting no filesystem access (use `monkeypatch` to fail any `open()` call) and confirming the **Tools depend on `ProjectSnapshot`, not on filesystem paths (DIP)** requirement.

## 5. Decision: Suggested dependency `mcp` (FastMCP), operator approval required

- [x] 5.1 Document the operator-approval gate for adding `mcp` in `proposal.md` Open Questions, realising the **Decision: Suggested dependency `mcp` (FastMCP), operator approval required**; do NOT run `uv add mcp`. Verification: `grep "mcp" pyproject.toml` SHALL show no `mcp` line until approval.
- [x] 5.2 (Blocked on operator approval) Run `uv add mcp` and pin a specific version, completing the **Decision: Suggested dependency `mcp` (FastMCP), operator approval required**; verify with `uv run python -c "import mcp"`.

## 6. Decision: Streamable HTTP is the default transport — wiring (post-approval)

- [x] 6.1 (Blocked on 5.2) Construct a `FastMCP` instance in `server.py` and register all seven tools as separate `@mcp.tool()`-decorated functions delegating to the pure helpers, realising the **Decision: One decorated function per tool (ISP)** and satisfying the **Each tool is a separate decorated function (ISP)** requirement; verify with `uv run pytest tests/unit/mcp/test_tool_registration.py` listing the seven registered tool names.
- [x] 6.2 (Blocked on 5.2) Implement streamable-HTTP transport dispatch defaulting to `127.0.0.1:8765` on path `/mcp`, realising the **Decision: Streamable HTTP is the default transport** and satisfying the **Streamable HTTP is the default transport**, **Default bind is loopback host and port 8765**, and **MCP endpoint path is `/mcp`** requirements; verify with a documented manual `curl` smoke test and `uv run pytest tests/unit/mcp/test_http_dispatch.py` asserting FastMCP's HTTP runner is invoked with the resolved host / port / path.
- [x] 6.3 (Blocked on 5.2) Catch `OSError`/`EADDRINUSE` from the HTTP bind and exit non-zero with a stderr message naming host and port, satisfying the **Port collision surfaces a clear failure** requirement; verify with `uv run pytest tests/unit/mcp/test_port_collision.py`.
- [x] 6.4 (Blocked on 5.2) Implement stdio transport dispatch behind `--transport stdio`, completing the **Transport selection supports HTTP default and stdio opt-in** requirement (stdio opt-in only); verify with `uv run pytest tests/unit/mcp/test_stdio_dispatch.py` asserting FastMCP's stdio runner is invoked only when stdio is explicitly selected.
- [x] 6.5 (Blocked on 5.2) Install SIGINT / SIGTERM handlers that stop the transport cleanly and exit 0, satisfying the **Shutdown is graceful on SIGINT** requirement; verify with `uv run pytest tests/unit/mcp/test_shutdown.py` signalling the dispatcher and asserting a graceful exit path.

## 7. Quality gates

- [x] 7.1 Run `uv run ruff check .` and `uv run ruff format --check .`; both SHALL pass with zero errors.
- [x] 7.2 Run `uv run mypy src`; SHALL pass with zero errors.
- [x] 7.3 Run `uv run pytest`; full suite SHALL be 100% green.
