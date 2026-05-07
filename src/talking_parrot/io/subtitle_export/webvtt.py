"""``WebVTTExporter`` — concrete W3C WebVTT subtitle exporter.

Implements the ``webvtt-exporter`` capability per design D3 (serialization
rules) and D1 (per-format timecode formatting). The output begins with the
literal ``WEBVTT\\n\\n`` header. Each cue is ``{HH:MM:SS.mmm} --> {HH:MM:SS.mmm}\\n{text}``
separated by a single blank line. No per-cue index is written. Empty input
produces a 9-byte header-only file.
"""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

from talking_parrot.io.subtitle_export.base import SubtitleExporter

if TYPE_CHECKING:
    from talking_parrot.models.subtitle import Subtitle

logger = structlog.get_logger(__name__)


_HEADER = "WEBVTT\n\n"


class WebVTTExporter(SubtitleExporter):
    """W3C WebVTT subtitle exporter.

    Output layout (per D3)::

        WEBVTT
        <blank line>
        {HH:MM:SS.mmm} --> {HH:MM:SS.mmm}
        {text}
        <blank line between cues>

    Line endings are LF (``\\n``); no per-cue index is emitted.
    """

    @property
    def format_name(self) -> str:
        """Return the WebVTT format identifier."""
        return "webvtt"

    @property
    def file_extension(self) -> str:
        """Return the canonical WebVTT file extension."""
        return ".vtt"

    def export(self, subtitles: list["Subtitle"], output_path: str) -> None:
        """Serialize ``subtitles`` as WebVTT and write to ``output_path``."""
        body = self._render(subtitles)
        logger.debug(
            "WebVTTExporter export",
            count=len(subtitles),
            output_path=output_path,
            bytes=len(body.encode("utf-8")),
        )
        self._atomic_write_text(output_path, body)

    @staticmethod
    def _format_timecode(ms: int) -> str:
        """Return ``HH:MM:SS.mmm`` for a non-negative millisecond value.

        Uses period ``.`` as the decimal separator per the W3C WebVTT spec.
        """
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    @classmethod
    def _render(cls, subtitles: list["Subtitle"]) -> str:
        """Render the full WebVTT body (header always present)."""
        if not subtitles:
            return _HEADER
        cues: list[str] = []
        for s in subtitles:
            start = cls._format_timecode(s.start_ms)
            end = cls._format_timecode(s.end_ms)
            cues.append(f"{start} --> {end}\n{s.text}\n")
        return _HEADER + "\n".join(cues)
