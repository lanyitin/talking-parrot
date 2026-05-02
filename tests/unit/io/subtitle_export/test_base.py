"""Tests for the ``SubtitleExporter`` abstract base class.

Covers the ``subtitle-exporter`` capability requirements:
- Direct ABC instantiation raises ``TypeError``.
- A complete concrete subclass is constructible.
- ``export`` writes UTF-8 with no BOM and uses LF line endings.
- ``export`` is atomic (write-then-rename via ``os.replace``).
- ``export`` accepts an empty subtitle list without raising.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from talking_parrot.io.subtitle_export.base import SubtitleExporter
from talking_parrot.models.subtitle import Subtitle


class _FakeExporter(SubtitleExporter):
    """Minimal concrete ``SubtitleExporter`` used for ABC contract tests."""

    @property
    def format_name(self) -> str:
        return "fake"

    @property
    def file_extension(self) -> str:
        return ".fake"

    def export(self, subtitles: list[Subtitle], output_path: str) -> None:
        body = "".join(f"{s.text}\n" for s in subtitles)
        self._atomic_write_text(output_path, body)


class TestSubtitleExporterABC:
    def test_direct_instantiation_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            SubtitleExporter()  # type: ignore[abstract]

    def test_concrete_subclass_is_constructible(self) -> None:
        instance = _FakeExporter()
        assert isinstance(instance, SubtitleExporter)
        assert instance.format_name == "fake"
        assert instance.file_extension == ".fake"


class TestUtf8NoBom:
    def test_first_byte_is_not_bom(self, tmp_path: Path) -> None:
        out = tmp_path / "out.fake"
        exporter = _FakeExporter()
        exporter.export([Subtitle(1, 0, 1000, "こんにちは")], str(out))
        data = out.read_bytes()
        assert len(data) > 0
        assert data[0] != 0xEF, "Output starts with UTF-8 BOM"

    def test_non_ascii_round_trips(self, tmp_path: Path) -> None:
        out = tmp_path / "out.fake"
        exporter = _FakeExporter()
        exporter.export([Subtitle(1, 0, 1000, "héllo こんにちは")], str(out))
        text = out.read_bytes().decode("utf-8")
        assert "héllo こんにちは" in text


class TestAtomicWrite:
    def test_failure_after_tmp_creation_leaves_target_untouched(
        self, tmp_path: Path
    ) -> None:
        out = tmp_path / "out.fake"
        exporter = _FakeExporter()

        # Patch os.replace inside the base module to raise after the .tmp file
        # is created — simulating a crash between flush and rename.
        with patch(
            "talking_parrot.io.subtitle_export.base.os.replace",
            side_effect=IOError("simulated failure during rename"),
        ):
            with pytest.raises(IOError):
                exporter.export([Subtitle(1, 0, 1000, "x")], str(out))

        # output_path must NOT exist (the rename never happened).
        assert not out.exists(), "Target path was created despite rename failure"

    def test_failure_preserves_prior_target_contents(self, tmp_path: Path) -> None:
        out = tmp_path / "out.fake"
        out.write_text("PRIOR CONTENT", encoding="utf-8")
        exporter = _FakeExporter()
        with patch(
            "talking_parrot.io.subtitle_export.base.os.replace",
            side_effect=IOError("boom"),
        ):
            with pytest.raises(IOError):
                exporter.export([Subtitle(1, 0, 1000, "x")], str(out))
        assert out.read_text(encoding="utf-8") == "PRIOR CONTENT"


class TestEmptyInput:
    def test_empty_input_does_not_raise(self, tmp_path: Path) -> None:
        out = tmp_path / "out.fake"
        exporter = _FakeExporter()
        result = exporter.export([], str(out))
        assert result is None
        assert out.exists()
