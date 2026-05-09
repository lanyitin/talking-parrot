"""Talking-parrot MCP server package.

This package implements the MCP (Model Context Protocol) server core for
talking-parrot, exposing a loaded ``ProjectSnapshot`` to AI agents over
streamable HTTP (default) or stdio (opt-in).

Per the change ``mcp-core``:

- ``server`` realises the **Decision: Module-level read-only snapshot, no
  global mutable state** and the **Decision: One decorated function per tool
  (ISP)** by holding a single module-level snapshot binding consumed by pure
  helpers.
- ``cli`` realises the **Decision: CLI / env-var injection layer** by parsing
  ``--project`` / ``--transport`` / ``--host`` / ``--port`` and resolving
  ``TALKING_PARROT_MCP_HOST`` / ``TALKING_PARROT_MCP_PORT`` with CLI > env >
  default precedence.
- ``__main__`` provides the runnable entry point ``uv run python -m
  talking_parrot.mcp --project <path>``.

Pure-function tool helpers are implemented and unit-testable independent of
the suggested ``mcp`` (FastMCP) third-party dependency, so the no-dep portions
of the change are exercisable before operator approval lands.
"""
