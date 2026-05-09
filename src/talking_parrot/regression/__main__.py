"""Runnable entry point for ``python -m talking_parrot.regression``.

Delegates to :func:`talking_parrot.regression.cli.main`. Exit codes are
documented under **Decision: CLI surface and exit codes** in the
``regression-runner`` change's ``design.md``.
"""

from __future__ import annotations

from talking_parrot.regression.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
