"""``SubtitleExporterFactory`` — selects a :class:`SubtitleExporter` by name.

Implements the ``subtitle-exporter-factory`` capability per design D5 (class
method on a class with a class-level registry) and D10 (unknown formats raise
``ValueError`` whose message contains the offending value and the supported
list).
"""

from __future__ import annotations

import logging
from typing import ClassVar

from talking_parrot.io.subtitle_export.base import SubtitleExporter
from talking_parrot.io.subtitle_export.srt import SRTExporter
from talking_parrot.io.subtitle_export.webvtt import WebVTTExporter

logger = logging.getLogger(__name__)


class SubtitleExporterFactory:
    """Class-method factory for :class:`SubtitleExporter` instances.

    The class-level :attr:`_REGISTRY` maps a ``format_name`` string to the
    matching exporter class. :meth:`create` instantiates a fresh exporter on
    every call; the factory does not cache instances.
    """

    _REGISTRY: ClassVar[dict[str, type[SubtitleExporter]]] = {
        "srt": SRTExporter,
        "webvtt": WebVTTExporter,
    }

    @classmethod
    def create(cls, format_name: str) -> SubtitleExporter:
        """Return a fresh exporter for ``format_name``.

        Raises:
            ValueError: If ``format_name`` is not a registered key. The
                message contains both the offending input and the sorted
                list of supported formats.
        """
        exporter_cls = cls._REGISTRY.get(format_name)
        if exporter_cls is None:
            supported = sorted(cls._REGISTRY.keys())
            raise ValueError(
                f"SubtitleExporterFactory: unsupported format "
                f"{format_name!r}. Supported: {supported}."
            )
        logger.debug(
            "SubtitleExporterFactory.create format_name=%s class=%s",
            format_name,
            exporter_cls.__name__,
        )
        return exporter_cls()
