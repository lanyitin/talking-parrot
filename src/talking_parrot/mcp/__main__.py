"""Runnable entry point for ``python -m talking_parrot.mcp``.

Delegates to :func:`talking_parrot.mcp.cli.main`. See the package docstring
and the ``mcp-core`` change's **Decision: CLI / env-var injection layer** for
configuration semantics.
"""

from __future__ import annotations

from talking_parrot.mcp.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
