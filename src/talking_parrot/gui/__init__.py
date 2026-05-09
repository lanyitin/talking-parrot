"""GUI backend package for the Talking Parrot debug timeline viewer.

This package implements the stdlib-only HTTP backend described in the
``gui-backend`` change proposal. It exposes:

- ``http_server``: the threaded ``http.server`` integration.
- ``api``: pure-function endpoint dispatcher over a ``ProjectSnapshot``.
- ``cli``: ``uv run python -m talking_parrot.gui`` entry point.

No public symbols are re-exported at the package level on purpose; consumers
should import from the explicit submodule that owns the type they need.
"""
