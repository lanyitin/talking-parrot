"""CLI entry point for the talking-parrot MCP server.

Realises the **Decision: CLI / env-var injection layer** from the
``mcp-core`` change:

- Parses ``--project`` (required), ``--transport`` (``http`` default,
  ``stdio`` opt-in), ``--host``, ``--port``.
- Resolves ``TALKING_PARROT_MCP_HOST`` and ``TALKING_PARROT_MCP_PORT`` env
  vars with **CLI flag > env var > built-in default** precedence (Factor
  III). Built-in defaults are ``127.0.0.1`` / ``8765``.
- Loads the project snapshot via :class:`SnapshotLoader` and installs it on
  :mod:`talking_parrot.mcp.server` exactly once before any transport is
  dispatched.
- Logs resolved configuration via :mod:`logging` to stdout (Factor XI). No
  file handler is registered — the **Logging targets stdout only**
  requirement is satisfied by attaching a single
  :class:`logging.StreamHandler` bound to :data:`sys.stdout`.
- Dispatches to the selected transport. The HTTP and stdio runners are
  injected via :func:`main`'s ``http_runner`` / ``stdio_runner`` keyword
  arguments so the no-dep portion of the change is unit-testable without
  the suggested ``mcp`` (FastMCP) third-party dependency.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from talking_parrot.shared import FileSnapshotLoader, ProjectSnapshot, SnapshotLoader

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_DEFAULT_TRANSPORT = "http"
_VALID_TRANSPORTS = ("http", "stdio")

_ENV_HOST = "TALKING_PARROT_MCP_HOST"
_ENV_PORT = "TALKING_PARROT_MCP_PORT"

_logger = logging.getLogger("talking_parrot.mcp")


@dataclass(frozen=True, slots=True)
class McpConfig:
    """Resolved MCP server configuration.

    Construction with no arguments yields the documented defaults
    (``host=127.0.0.1``, ``port=8765``, ``transport=http``,
    ``project=None``).
    """

    host: str = _DEFAULT_HOST
    port: int = _DEFAULT_PORT
    transport: str = _DEFAULT_TRANSPORT
    project: str | None = None


# A transport runner takes the resolved config plus the loaded snapshot and
# blocks until the transport exits. Returning an int communicates an exit
# code. Tests inject stub runners; the production runners that wrap FastMCP
# are added in tasks gated on operator approval.
TransportRunner = Callable[[McpConfig, ProjectSnapshot], int]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talking_parrot.mcp",
        description="Run the Talking Parrot MCP server.",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Path to the .tp project file to load (required).",
    )
    parser.add_argument(
        "--transport",
        default=None,
        help="Transport: 'http' (default) or 'stdio'.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Interface to bind for the HTTP transport.",
    )
    parser.add_argument(
        "--port",
        default=None,
        type=int,
        help="TCP port to bind for the HTTP transport.",
    )
    return parser


def resolve_config(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> McpConfig:
    """Resolve the effective :class:`McpConfig` from argv and the environment.

    Precedence: explicit CLI flag > environment variable > documented
    default. ``--transport`` accepts only ``http`` or ``stdio``; any other
    value triggers :class:`SystemExit` with a stderr message naming the
    invalid value.

    Raises:
        SystemExit: ``--transport`` is invalid, or
            ``TALKING_PARROT_MCP_PORT`` is not a parseable integer.
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

    transport = args.transport if args.transport is not None else _DEFAULT_TRANSPORT
    if transport not in _VALID_TRANSPORTS:
        raise SystemExit(
            f"error: invalid --transport value {transport!r}; "
            f"expected one of {list(_VALID_TRANSPORTS)}"
        )

    project = args.project

    return McpConfig(host=host, port=port, transport=transport, project=project)


def _ensure_stdout_logging() -> None:
    """Attach a single stdout :class:`StreamHandler` to the MCP logger.

    Idempotent: if the logger already has a stdout-targeted
    :class:`StreamHandler` we do not add another. No file handler is ever
    registered — the **Logging targets stdout only** requirement.
    """
    has_stdout_stream = any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in _logger.handlers
    )
    if not has_stdout_stream:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
    if _logger.level == logging.NOTSET:
        _logger.setLevel(logging.INFO)


def _install_signal_handlers() -> None:
    """Install SIGINT / SIGTERM handlers that raise ``SystemExit(0)``.

    Realises the **Shutdown is graceful on SIGINT** requirement: receiving
    SIGINT or SIGTERM during transport serve raises :class:`SystemExit` with
    code ``0``, which propagates through ``anyio`` / ``uvicorn`` and unwinds
    cleanly. The runner functions translate ``SystemExit(0)`` and
    ``KeyboardInterrupt`` into exit code ``0``.

    Idempotent on POSIX. On platforms where :data:`signal.SIGTERM` is not
    available the SIGTERM handler is silently skipped.
    """
    import signal

    def _graceful(signum: int, _frame: object) -> None:
        _logger.info("received signal %d; shutting down MCP transport", signum)
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGINT, _graceful)
    except (ValueError, OSError):  # pragma: no cover - non-main-thread test runs
        pass
    sigterm = getattr(signal, "SIGTERM", None)
    if sigterm is not None:
        try:
            signal.signal(sigterm, _graceful)
        except (ValueError, OSError):  # pragma: no cover
            pass


def _default_http_runner(config: McpConfig, snapshot: ProjectSnapshot) -> int:
    """Run the streamable-HTTP MCP transport at ``config.host:config.port``.

    Realises **Decision: Streamable HTTP is the default transport**: builds
    a :class:`FastMCP` instance with the seven tools registered, installs
    SIGINT / SIGTERM handlers (Shutdown-is-graceful), and serves on
    ``streamable_http_path='/mcp'``.

    Failure modes:

    - :class:`OSError` from the bind (port already in use, host invalid):
      writes a stderr message naming both ``host`` and ``port`` and returns
      a non-zero exit code per the **Port collision surfaces a clear
      failure** requirement.
    - :class:`KeyboardInterrupt` / :class:`SystemExit(0)`: clean shutdown,
      returns ``0``.
    """
    from talking_parrot.mcp import server as mcp_server

    _install_signal_handlers()

    _logger.debug(
        "calling server.build_mcp_app host=%s port=%d streamable_http_path=/mcp",
        config.host,
        config.port,
    )
    app = mcp_server.build_mcp_app(
        host=config.host,
        port=config.port,
        streamable_http_path="/mcp",
    )

    try:
        _logger.debug(
            "calling FastMCP.run transport=streamable-http host=%s port=%d",
            config.host,
            config.port,
        )
        app.run(transport="streamable-http")
    except KeyboardInterrupt:
        _logger.info("HTTP transport interrupted; exiting cleanly")
        return 0
    except SystemExit as exc:
        # Graceful exit raised from our SIGINT/SIGTERM handler.
        code = int(exc.code) if isinstance(exc.code, int) else 0
        return code
    except OSError as exc:
        sys.stderr.write(
            f"error: failed to bind MCP HTTP transport on host={config.host} "
            f"port={config.port}: {exc}\n"
        )
        return 4
    return 0


def _default_stdio_runner(config: McpConfig, snapshot: ProjectSnapshot) -> int:
    """Run the stdio MCP transport.

    Selected only when ``--transport stdio`` is explicit. Builds the same
    :class:`FastMCP` instance as the HTTP runner but invokes
    ``run(transport='stdio')``. Graceful shutdown is wired through the same
    SIGINT / SIGTERM handlers.
    """
    from talking_parrot.mcp import server as mcp_server

    _install_signal_handlers()

    app = mcp_server.build_mcp_app(
        host=config.host,
        port=config.port,
        streamable_http_path="/mcp",
    )

    try:
        _logger.debug("calling FastMCP.run transport=stdio")
        app.run(transport="stdio")
    except KeyboardInterrupt:
        _logger.info("stdio transport interrupted; exiting cleanly")
        return 0
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else 0
        return code
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    loader: SnapshotLoader | None = None,
    http_runner: TransportRunner | None = None,
    stdio_runner: TransportRunner | None = None,
) -> int:
    """CLI entry point. Returns the process exit code.

    The ``loader``, ``http_runner``, and ``stdio_runner`` keyword arguments
    are dependency-injection seams used by unit tests. Production callers
    pass nothing and the defaults are used.
    """
    config = resolve_config(argv, env=env)

    if not config.project:
        sys.stderr.write(
            "error: --project is required for the MCP server entry point.\n"
        )
        return 2

    _ensure_stdout_logging()

    if loader is None:
        loader = FileSnapshotLoader()

    _logger.debug(
        "calling SnapshotLoader.load source=%s loader=%s",
        config.project,
        type(loader).__name__,
    )
    snapshot = loader.load(config.project)
    assert isinstance(snapshot, ProjectSnapshot), (
        "SnapshotLoader.load did not return ProjectSnapshot — "
        "shared layer API may have changed"
    )

    # Install the snapshot on the server module before any transport
    # begins listening. ``install_snapshot`` raises if called twice, which
    # is exactly the audio2subtitle anti-pattern guard.
    from talking_parrot.mcp import server as mcp_server

    mcp_server.install_snapshot(snapshot)

    _logger.info(
        "mcp config resolved host=%s port=%d transport=%s project=%s",
        config.host,
        config.port,
        config.transport,
        config.project,
    )

    if config.transport == "http":
        runner = http_runner if http_runner is not None else _default_http_runner
    elif config.transport == "stdio":
        runner = stdio_runner if stdio_runner is not None else _default_stdio_runner
    else:  # pragma: no cover - resolve_config already rejected this
        sys.stderr.write(f"error: unknown transport {config.transport!r}\n")
        return 2

    return int(runner(config, snapshot))


__all__ = [
    "McpConfig",
    "TransportRunner",
    "main",
    "resolve_config",
]
