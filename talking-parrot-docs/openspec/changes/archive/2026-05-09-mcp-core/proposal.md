## Why

`docs/TODOs.md` lists an MCP server (task 3 of the quality-and-tooling initiative) that will let AI agents (Claude, Cursor, etc.) introspect a loaded `.tp` project's pipeline intermediates — VAD frames, transcription results, subtitles, diagnostics — without parsing raw binary files. The shared layer (`ProjectSnapshot`, `SnapshotLoader`) landed via `2026-05-09-shared-layer`. This change implements the **core** MCP server: tools, transport, lifecycle, CLI. The GUI co-start, `get_flagged_regions`, and resource URIs are explicitly deferred to a separate `mcp-gui-bridge` change. Per ADR-0002, streamable HTTP MUST be the default transport (stdio opt-in only), differentiating talking-parrot from audio2subtitle's stdio-default heritage.

## What Changes

- Introduce `src/talking_parrot/mcp/` package with single-responsibility modules: `server.py` (FastMCP instance + `@mcp.tool()` definitions + entry point), `cli.py` (argument parsing + env-var resolution + transport selection), plus `__init__.py` and `__main__.py` so `uv run python -m talking_parrot.mcp --project <path>` is the supported entry point.
- Define an `mcp-server-lifecycle` capability covering startup snapshot load, transport selection (default streamable HTTP, opt-in stdio), env-var / CLI flag injection (Factor III), module-level read-only snapshot (Factor VI; explicitly forbidding the audio2subtitle global-mutable `_project` anti-pattern), and SIGINT graceful shutdown.
- Define an `mcp-streamable-http-transport` capability fixing the default transport contract: bind to `127.0.0.1:8765` on path `/mcp`, configurable via `TALKING_PARROT_MCP_HOST` / `TALKING_PARROT_MCP_PORT` and `--host` / `--port` flags.
- Define an `mcp-snapshot-tools` capability with one decorated function per tool (ISP): `summary`, `get_vad_segments`, `get_vad_frames`, `get_subtitles`, `get_pre_postprocess_subtitles`, `get_transcription_results`, `diagnostics`. All tools are read-only, depend on `ProjectSnapshot` (DIP), and never touch the filesystem.
- Add unit tests under `tests/unit/mcp/` exercising each tool's pure-function core against a fixture `ProjectSnapshot`. Transport-level integration testing is recorded as an Open Question pending FastMCP harness investigation.
- Consume `talking_parrot.shared` types only; this change MUST NOT redefine `ProjectSnapshot` or `SnapshotLoader`.

## Impact

- **Affected specs:** new capabilities `mcp-server-lifecycle`, `mcp-streamable-http-transport`, `mcp-snapshot-tools`.
- **Affected code:** new files under `src/talking_parrot/mcp/`, new tests under `tests/unit/mcp/`. Existing capabilities (`project-snapshot`, `snapshot-loader`) are imported only — not modified.
- **Tooling:** adds a runnable module `talking_parrot.mcp`; no change to `[build-system]`. `mcp` (FastMCP) is recorded as an **Open Question / suggested new dependency**, not auto-added — operator approval required before implementation can proceed.
- **GUI integration is out of scope.** `get_flagged_regions`, GUI background-thread co-start, and `talking-parrot://project/*` resource URIs are deferred to `mcp-gui-bridge`.
- **CI / quality:** unit tests cover tool logic with fixture snapshots so `uv run pytest` remains hermetic and dep-free; transport-level tests are gated on the FastMCP dep landing.

## Open Questions

- **Operator-approval gate for adding `mcp` (FastMCP).** Per CLAUDE.md ("Never add a new dependency without explicit instruction") and the **Decision: Suggested dependency `mcp` (FastMCP), operator approval required** in `design.md`, the `mcp` (FastMCP) third-party package SHALL NOT be added to `pyproject.toml` by the tasks of this change. The package is required for `@mcp.tool()` decorators and dual stdio / streamable-HTTP transport handling, and is already proven in audio2subtitle. Adding it requires:
    1. Explicit operator approval naming the package and version constraint.
    2. Running `uv add mcp` (and pinning a specific version) in a single, scoped step.
    3. Resuming tasks 5.2–6.5 in `tasks.md`, which are explicitly blocked on this approval.

  Until approval lands, tasks 1–5.1 of this change SHALL be implementable and mergeable on their own — pure-function tool helpers and CLI argv parsing do not import `mcp`. Verification of the gate's enforcement: `grep "^mcp" pyproject.toml` SHALL produce no match until approval, and the no-dep test suite (`uv run pytest tests/unit/mcp -q`) SHALL pass without `mcp` installed.

- **Transport-level test harness.** Whether FastMCP exposes a usable in-process test client for streamable HTTP (independent of the chosen dep version) is unknown. Pure-function tool cores will be tested directly; transport coverage is deferred until the dep is approved and surveyed.
