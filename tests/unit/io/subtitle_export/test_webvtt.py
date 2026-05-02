"""Tests for :class:`WebVTTExporter`.

Covers the ``webvtt-exporter`` capability requirements:
- ``format_name`` / ``file_extension`` identity (``"webvtt"`` / ``".vtt"``).
- Mandatory ``WEBVTT\\n\\n`` header.
- Cue serialization with period decimal separator and no per-cue index.
- Empty input produces the header-only 9-byte file.
"""

from __future__ import annotations

from pathlib import Path

from talking_parrot.io.subtitle_export.webvtt import WebVTTExporter
from talking_parrot.models.subtitle import Subtitle


class TestWebVTTIdentity:
    def test_format_name(self) -> None:
        assert WebVTTExporter().format_name == "webvtt"

    def test_file_extension(self) -> None:
        assert WebVTTExporter().file_extension == ".vtt"


class TestWebVTTSerialization:
    def test_two_cue_canonical_layout(self, tmp_path: Path) -> None:
        out = tmp_path / "out.vtt"
        subs = [
            Subtitle(1, 0, 1500, "hello"),
            Subtitle(2, 1500, 3000, "world"),
        ]
        WebVTTExporter().export(subs, str(out))
        content = out.read_bytes().decode("utf-8")
        assert content == (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:01.500\nhello\n"
            "\n"
            "00:00:01.500 --> 00:00:03.000\nworld\n"
        )

    def test_hour_spanning_uses_period_separator(self, tmp_path: Path) -> None:
        out = tmp_path / "out.vtt"
        WebVTTExporter().export([Subtitle(1, 3_661_005, 3_662_500, "x")], str(out))
        content = out.read_bytes().decode("utf-8")
        assert "01:01:01.005 --> 01:01:02.500" in content


class TestWebVTTEmptyInput:
    def test_empty_input_produces_header_only_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.vtt"
        WebVTTExporter().export([], str(out))
        # Spec scenario states the content is exactly the byte sequence
        # `"WEBVTT\n\n"`. That sequence is 8 bytes (6 ASCII + 2 LF). The
        # spec scenario also states `st_size == 9`, which contradicts the
        # literal content. Asserting the literal byte sequence — which is
        # the unambiguous statement and matches D3's "exactly `WEBVTT\n\n`".
        assert out.read_bytes() == b"WEBVTT\n\n"
        assert out.stat().st_size == 8
