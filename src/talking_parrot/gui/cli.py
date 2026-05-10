"""CLI entry point for the GUI backend.

Per the ``Configuration Resolution Order`` Architectural Decision in the
gui-backend design, this module:

- Defines a frozen :class:`GuiConfig` dataclass with documented defaults
  (host ``127.0.0.1``, port ``8765``).
- Implements :func:`resolve_config` so CLI flags override env vars override
  defaults (Factor III).
- Loads the project snapshot exactly once via
  :class:`talking_parrot.shared.FileSnapshotLoader` before binding the
  HTTP socket (``Snapshot loaded once at startup``).
- Exits non-zero with a stderr message naming both ``--project`` and
  ``TALKING_PARROT_GUI_PROJECT`` when no project path is provided.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from talking_parrot.gui import http_server
from talking_parrot.shared import FileSnapshotLoader

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765

_ENV_HOST = "TALKING_PARROT_GUI_HOST"
_ENV_PORT = "TALKING_PARROT_GUI_PORT"
_ENV_PROJECT = "TALKING_PARROT_GUI_PROJECT"

_logger = logging.getLogger("talking_parrot.gui.cli")


@dataclass(frozen=True, slots=True)
class GuiConfig:
    """Resolved GUI server configuration.

    Construction with no arguments yields the documented defaults.
    """

    host: str = _DEFAULT_HOST
    port: int = _DEFAULT_PORT
    project: str | None = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talking_parrot.gui",
        description="Run the Talking Parrot debug-timeline backend.",
    )
    parser.add_argument("--host", default=None, help="Interface to bind.")
    parser.add_argument("--port", default=None, type=int, help="TCP port to bind.")
    parser.add_argument(
        "--project",
        default=None,
        help="Path to the .tp project file to load.",
    )
    return parser


def resolve_config(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> GuiConfig:
    """Resolve the effective :class:`GuiConfig` from CLI args + env vars.

    Precedence: explicit CLI flag > environment variable > documented default.
    """
    if env is None:
        env = os.environ
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    host = args.host if args.host is not None else env.get(_ENV_HOST, _DEFAULT_HOST)

    if args.port is not None:
        port = int(args.port)
    elif _ENV_PORT in env:
        try:
            port = int(env[_ENV_PORT])
        except ValueError as exc:
            raise SystemExit(f"invalid {_ENV_PORT}: {exc}") from exc
    else:
        port = _DEFAULT_PORT

    project = args.project if args.project is not None else env.get(_ENV_PROJECT)

    return GuiConfig(host=host, port=port, project=project)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    config = resolve_config(argv)
    if not config.project:
        sys.stderr.write(
            f"error: no project path supplied. Pass --project or set {_ENV_PROJECT}.\n"
        )
        return 2

    loader = FileSnapshotLoader()
    _logger.debug("calling FileSnapshotLoader.load source=%s", config.project)
    snapshot = loader.load(config.project)
    # Verify the loader returned a usable snapshot before binding a socket.
    from talking_parrot.shared import ProjectSnapshot

    assert isinstance(snapshot, ProjectSnapshot), (
        "FileSnapshotLoader.load did not return ProjectSnapshot — "
        "shared layer API may have changed"
    )

    server = http_server.serve(snapshot, config)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _logger.info("interrupted; shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
