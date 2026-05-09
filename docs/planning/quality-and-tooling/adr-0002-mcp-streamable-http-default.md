---
title: "ADR-0002: Streamable HTTP as Default MCP Transport"
tags:
  - adr
  - mcp
aliases:
  - adr-mcp-transport
---

# ADR-0002: Streamable HTTP as Default MCP Transport

## Status

Proposed

## Context

The MCP server must expose pipeline diagnostic tools to AI agents. Two MCP transports exist:

1. **stdio** — agent spawns the server as a subprocess; communication over stdin/stdout.
2. **Streamable HTTP** — server binds a port; agent connects via HTTP POST to `/mcp`.

audio2subtitle defaults to stdio with HTTP opt-in. The design brief for talking-parrot explicitly requires streamable HTTP as the default.

## Decision

The talking-parrot MCP server defaults to streamable HTTP (`--transport http` behaviour is the default). stdio is available via `--transport stdio` for environments that require it (e.g. Claude Desktop direct integration).

## Rationale

| Criterion | Streamable HTTP (default) | stdio (opt-in) |
|---|---|---|
| Survives agent restart | Yes — server stays running | No — server exits with agent |
| Multiple agents can connect | Yes | No |
| GUI co-start possible | Yes (independent process) | Harder (same process, blocked by stdio loop) |
| Factor VII (port binding) | Yes | No |
| Claude Desktop compatibility | Yes (via HTTP MCP config) | Yes (native) |

Streamable HTTP allows the GUI debug server and MCP server to both run in one `python -m talking_parrot.mcp` invocation without the stdio loop blocking the GUI thread. It also survives agent session restarts, which is important for iterative debugging workflows.

## Consequences

- Default port is `8765`; configurable via `TALKING_PARROT_MCP_PORT` env var or `--port` flag.
- Server binds to `127.0.0.1` by default; `--host` overrides for LAN use.
- MCP endpoint path is `/mcp` (matching audio2subtitle convention).
- The `--no-ui` flag disables GUI co-start; `--transport stdio` disables HTTP entirely.

## SOLID / 12-Factor Alignment

- **Factor III**: host and port are env-var injected, never hardcoded.
- **Factor VII**: service is exposed via port binding; no web server injection.
- **Factor VIII**: multiple agents may connect concurrently (scale-out via connections to a single process).
- **Factor IX**: startup is fast (project loaded synchronously at boot); SIGINT triggers graceful shutdown.
