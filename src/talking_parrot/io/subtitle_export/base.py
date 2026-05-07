"""``SubtitleExporter`` — abstract base class for subtitle file exporters.

Defines the contract every concrete exporter (e.g. :class:`SRTExporter`,
:class:`WebVTTExporter`) implements: a ``format_name`` / ``file_extension``
identity and an ``export(subtitles, output_path)`` method that serializes the
cue list and atomically writes it to disk as UTF-8 (no BOM, LF line endings).

Per design D8, all writes go through a shared ``_atomic_write_text`` helper
that writes to ``output_path + ".tmp"`` and then ``os.replace``-s the temporary
file onto the target path. The helper guarantees that an interrupted write
never leaves a partially-written subtitle file at ``output_path``.
"""

from __future__ import annotations

import abc
import structlog
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talking_parrot.models.subtitle import Subtitle

logger = structlog.get_logger(__name__)


class SubtitleExporter(abc.ABC):
    """Abstract base class for subtitle exporters.

    Subclasses MUST override :attr:`format_name`, :attr:`file_extension`, and
    :meth:`export`. Direct instantiation of ``SubtitleExporter`` raises
    :class:`TypeError`.
    """

    @property
    @abc.abstractmethod
    def format_name(self) -> str:
        """Short format identifier (e.g. ``"srt"``, ``"webvtt"``)."""

    @property
    @abc.abstractmethod
    def file_extension(self) -> str:
        """Conventional file extension including the leading dot (e.g. ``".srt"``)."""

    @abc.abstractmethod
    def export(self, subtitles: list["Subtitle"], output_path: str) -> None:
        """Serialize ``subtitles`` and write the result to ``output_path``.

        Implementations SHALL write UTF-8 with no BOM, use ``\\n`` line
        endings, and use the shared :meth:`_atomic_write_text` helper so the
        write is atomic from the reader's perspective.
        """

    @staticmethod
    def _atomic_write_text(output_path: str, text: str) -> None:
        """Write ``text`` to ``output_path`` atomically.

        Implements the write-then-rename pattern from design D8:
        1. Encode ``text`` as UTF-8 (no BOM).
        2. Write the bytes to ``output_path + ".tmp"``, flush, and ``fsync``.
        3. Use :func:`os.replace` to atomically rename the temporary file
           onto ``output_path``.

        If the rename fails, the partially-written ``.tmp`` file may be left
        on disk but ``output_path`` retains its prior state (or remains
        absent). The exception is re-raised to the caller.
        """
        tmp_path = output_path + ".tmp"
        encoded = text.encode("utf-8")

        logger.debug(
            "subtitle_export atomic_write begin",
            path=output_path,
            tmp=tmp_path,
            bytes=len(encoded),
        )

        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(tmp_path, "wb") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())

        os.replace(tmp_path, output_path)
        logger.debug("subtitle_export atomic_write done", path=output_path)
