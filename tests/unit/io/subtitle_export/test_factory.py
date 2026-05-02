"""Tests for :class:`SubtitleExporterFactory`.

Covers the ``subtitle-exporter-factory`` capability requirements:
- ``"srt"`` and ``"webvtt"`` map to their concrete exporters.
- Unknown formats raise ``ValueError`` whose message contains the offending
  input and the supported list.
- Each call returns a fresh instance.
"""

from __future__ import annotations

import pytest

from talking_parrot.io.subtitle_export.factory import SubtitleExporterFactory
from talking_parrot.io.subtitle_export.srt import SRTExporter
from talking_parrot.io.subtitle_export.webvtt import WebVTTExporter


class TestFactoryCreate:
    def test_srt_returns_srt_exporter(self) -> None:
        result = SubtitleExporterFactory.create("srt")
        assert isinstance(result, SRTExporter)
        assert result.format_name == "srt"

    def test_webvtt_returns_webvtt_exporter(self) -> None:
        result = SubtitleExporterFactory.create("webvtt")
        assert isinstance(result, WebVTTExporter)
        assert result.format_name == "webvtt"


class TestFactoryRejectsUnknown:
    def test_unknown_format_raises_value_error_with_input_and_supported(
        self,
    ) -> None:
        with pytest.raises(ValueError) as exc_info:
            SubtitleExporterFactory.create("ssa")
        message = str(exc_info.value)
        assert "ssa" in message
        assert "srt" in message
        assert "webvtt" in message


class TestFactoryFreshInstance:
    def test_two_calls_yield_distinct_instances(self) -> None:
        a = SubtitleExporterFactory.create("srt")
        b = SubtitleExporterFactory.create("srt")
        assert a is not b
