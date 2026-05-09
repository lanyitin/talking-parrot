---
name: Quality & Tooling Planning (2026-05-09)
description: Design documents produced for regression harness, analysis GUI, and MCP server under docs/planning/quality-and-tooling/
type: project
---

Three quality-and-tooling initiatives planned and documented on 2026-05-09.

Documents live under `docs/planning/quality-and-tooling/`:
- `README.md` — overview, change order
- `shared-architecture.md` — shared `ProjectSnapshot` layer, directory tree, data model
- `01-regression-harness.md` — regression runner, scorer, baseline JSON store
- `02-analysis-gui.md` — browser SPA over local Python HTTP (mirrors audio2subtitle GUI)
- `03-mcp-server.md` — FastMCP, streamable HTTP default, tool catalogue
- `adr-0001-gui-browser-spa.md`
- `adr-0002-mcp-streamable-http-default.md`

**Why:** User wants automated quality tracking (regression), visual diagnostics (GUI), and AI-agent-assisted analysis (MCP).

**How to apply:** When implementing any of these three tasks, start by reading the shared-architecture doc first — `shared/` sub-package must land before regression, GUI, or MCP work begins. Suggested first Spectra change: `shared-layer`.
