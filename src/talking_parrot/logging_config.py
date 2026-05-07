"""Logging configuration that routes structlog through stdlib logging.

Wiring structlog via :class:`structlog.stdlib.LoggerFactory` keeps the
project on a single, structured logging API while preserving compatibility
with the standard library — pytest's ``caplog`` fixture and any third-party
handler attached to the stdlib root logger continue to receive records.

structlog is configured at import time so that any module obtaining a
logger via :func:`structlog.get_logger` is wired correctly even before
:func:`setup_logging` is called (e.g. in unit tests).
"""

import logging
import os
import sys

import structlog


def _configure_structlog() -> None:
    """Wire structlog to route through stdlib logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


_configure_structlog()


def setup_logging(level_name: str | None = None) -> None:
    """Configure stdlib + structlog logging.

    Args:
        level_name: Explicit level name (e.g. ``"DEBUG"``); when ``None``,
            falls back to the ``LOG_LEVEL`` env var, then ``"WARNING"``.
    """
    if level_name is None:
        level_name = os.environ.get("LOG_LEVEL", "WARNING")
    level_name = level_name.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.WARNING

    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s - %(message)s",
    )
    logging.getLogger().setLevel(level)

    _configure_structlog()
