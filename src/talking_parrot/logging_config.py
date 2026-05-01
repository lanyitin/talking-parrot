import logging
import os
import sys

import structlog


def setup_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.WARNING

    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(message)s",
    )
    logging.getLogger().setLevel(level)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )
