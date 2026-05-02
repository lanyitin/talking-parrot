"""Tests for :class:`SRTExporter`.

Covers the ``srt-exporter`` capability requirements:
- ``format_name`` / ``file_extension`` identity (``"srt"`` / ``".srt"``).
- Canonical SubRip cue serialization with comma decimal separator.
- Multi-line text preservation and hour-spanning timecode formatting.
- Empty input produces a zero-byte file.
"""

from __future__ import annotations

from pathlib import Path

from talking_parrot.io.subtitle_export.srt import SRTExporter
from talking_parrot.models.subtitle import Subtitle


class TestSRTIdentity:
    def test_format_name(self) -> None:
        assert SRTExporter().format_name == "srt"

    def test_file_extension(self) -> None:
        assert SRTExporter().file_extension == ".srt"


class TestSRTSerialization:
    def test_two_cue_canonical_layout(self, tmp_path: Path) -> None:
        out = tmp_path / "out.srt"
        subs = [
            Subtitle(1, 0, 1500, "hello"),
            Subtitle(2, 1500, 3000, "world"),
        ]
        SRTExporter().export(subs, str(out))
        content = out.read_bytes().decode("utf-8")
        assert content == (
            "1\n00:00:00,000 --> 00:00:01,500\nhello\n"
            "\n"
            "2\n00:00:01,500 --> 00:00:03,000\nworld\n"
        )

    def test_multiline_text_preserved(self, tmp_path: Path) -> None:
        out = tmp_path / "out.srt"
        SRTExporter().export([Subtitle(1, 0, 1000, "line one\nline two")], str(out))
        content = out.read_bytes().decode("utf-8")
        assert content == "1\n00:00:00,000 --> 00:00:01,000\nline one\nline two\n"

    def test_hour_spanning_timecode(self, tmp_path: Path) -> None:
        out = tmp_path / "out.srt"
        SRTExporter().export([Subtitle(1, 3_661_005, 3_662_500, "x")], str(out))
        content = out.read_bytes().decode("utf-8")
        assert "01:01:01,005 --> 01:01:02,500" in content


class TestSRTEmptyInput:
    def test_empty_input_produces_zero_byte_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.srt"
        SRTExporter().export([], str(out))
        assert out.exists()
        assert out.stat().st_size == 0
