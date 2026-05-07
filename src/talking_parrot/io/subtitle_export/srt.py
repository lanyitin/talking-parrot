"""``SRTExporter`` — concrete SubRip (SRT) subtitle exporter.

Implements the ``srt-exporter`` capability per design D2 (serialization rules)
and D1 (per-format timecode formatting). Each cue is rendered as
``index\\n{HH:MM:SS,mmm} --> {HH:MM:SS,mmm}\\n{text}`` separated by a single
blank line, with a trailing ``\\n`` after the last cue's text. Empty input
produces a zero-byte file.
"""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

from talking_parrot.io.subtitle_export.base import SubtitleExporter

if TYPE_CHECKING:
    from talking_parrot.models.subtitle import Subtitle

logger = structlog.get_logger(__name__)


class SRTExporter(SubtitleExporter):
    """SubRip (SRT) subtitle exporter.

    Cue layout (per D2)::

        {index}
        {HH:MM:SS,mmm} --> {HH:MM:SS,mmm}
        {text}
        <blank line between cues>

    The trailing newline after the last cue is included; no extra blank line
    is appended at EOF. Line endings are LF (``\\n``).
    """

    @property
    def format_name(self) -> str:
        """Return the SRT format identifier."""
        return "srt"

    @property
    def file_extension(self) -> str:
        """Return the canonical SRT file extension."""
        return ".srt"

    def export(self, subtitles: list["Subtitle"], output_path: str) -> None:
        """Serialize ``subtitles`` as SubRip and write to ``output_path``.

        Empty input is written as a zero-byte file.
        """
        body = self._render(subtitles)
        logger.debug(
            "SRTExporter export",
            count=len(subtitles),
            output_path=output_path,
            bytes=len(body.encode("utf-8")),
        )
        self._atomic_write_text(output_path, body)

    @staticmethod
    def _format_timecode(ms: int) -> str:
        """Return ``HH:MM:SS,mmm`` for a non-negative millisecond value.

        Uses comma ``,`` as the decimal separator per the SubRip spec.
        """
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @classmethod
    def _render(cls, subtitles: list["Subtitle"]) -> str:
        """Render the full SRT body for ``subtitles`` (may be empty)."""
        if not subtitles:
            return ""
        cues: list[str] = []
        for s in subtitles:
            start = cls._format_timecode(s.start_ms)
            end = cls._format_timecode(s.end_ms)
            cues.append(f"{s.index}\n{start} --> {end}\n{s.text}\n")
        return "\n".join(cues)
