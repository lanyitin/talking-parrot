"""Tests for ``ExportConfig`` and its integration into ``PipelineConfig``.

Covers the requirements declared in the ``export-config`` capability spec:
``ExportConfig`` field validation, ``extra="forbid"`` behavior, and the
optional ``export`` field on ``PipelineConfig``.
"""

from __future__ import annotations

import pydantic
import pytest

from talking_parrot.config.models import (
    ExportConfig,
    PipelineConfig,
    TranscribingStep,
)


class TestExportConfigValidation:
    """Validation rules for the standalone ``ExportConfig`` model."""

    def test_valid_srt_loads(self) -> None:
        cfg = ExportConfig.model_validate(
            {"format": "srt", "output_path": "out/movie.srt"}
        )
        assert cfg.format == "srt"
        assert cfg.output_path == "out/movie.srt"

    def test_valid_webvtt_loads(self) -> None:
        cfg = ExportConfig.model_validate(
            {"format": "webvtt", "output_path": "out/movie.vtt"}
        )
        assert cfg.format == "webvtt"
        assert cfg.output_path == "out/movie.vtt"

    def test_unknown_format_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ExportConfig.model_validate(
                {"format": "ssa", "output_path": "out/movie.ssa"}
            )
        assert "format" in str(exc_info.value)

    def test_empty_output_path_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ExportConfig.model_validate({"format": "srt", "output_path": ""})
        assert "output_path must be non-empty" in str(exc_info.value)

    def test_whitespace_output_path_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            ExportConfig.model_validate({"format": "srt", "output_path": "   "})
        assert "output_path must be non-empty" in str(exc_info.value)
        assert "output_path" in str(exc_info.value)

    def test_extra_keys_forbidden(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ExportConfig.model_validate(
                {
                    "format": "srt",
                    "output_path": "x.srt",
                    "unknown_field": 1,
                }
            )


class TestPipelineConfigExportField:
    """Round-trip tests for the optional ``export`` field on PipelineConfig."""

    def _yaml_without_export(self) -> dict:
        return {"transcribing": [{"condition": "true", "backend": "faster-whisper"}]}

    def test_yaml_without_export_loads(self) -> None:
        cfg = PipelineConfig.model_validate(self._yaml_without_export())
        assert cfg.export is None

    def test_yaml_with_export_populates_field(self) -> None:
        data = self._yaml_without_export()
        data["export"] = {"format": "webvtt", "output_path": "out.vtt"}
        cfg = PipelineConfig.model_validate(data)
        assert isinstance(cfg.export, ExportConfig)
        assert cfg.export.format == "webvtt"
        assert cfg.export.output_path == "out.vtt"

    def test_construct_pipeline_config_with_export_kwarg(self) -> None:
        cfg = PipelineConfig(
            transcribing=[TranscribingStep(condition="true", backend="faster-whisper")],
            export=ExportConfig(format="srt", output_path="o.srt"),
        )
        assert cfg.export is not None
        assert cfg.export.format == "srt"
