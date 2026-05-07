"""Tests for CLI end-to-end wiring (``pipeline-end-to-end-wiring`` capability).

Covers:
- ``_build_stages`` produces the correct stage list for partial and full
  configs (Requirement: cli.py builds the full five-stage pipeline).
- ``cli.main`` invokes the subtitle exporter when ``cfg.export`` is set
  (Requirement: cli.py invokes the subtitle exporter when export is configured).
- The project-file JSON is written before the exporter runs, even when the
  exporter raises (D7).
- ``cli.main`` does not write a subtitle file when ``cfg.export`` is None
  (Requirement: cli.py is silent when export is not configured).
- No element of the stage list is a :class:`SubtitleExporter` instance
  (Requirement: The exporter is not registered as a pipeline Stage / D9).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Iterable
from unittest.mock import patch

import pytest

from talking_parrot import cli
from talking_parrot.config.models import (
    AlignConfig,
    ChunkingConfig,
    ExportConfig,
    PipelineConfig,
    PostProcessingConfig,
    TranscribingStep,
    VadConfig,
)
from talking_parrot.io.subtitle_export.base import SubtitleExporter
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.stages import (
    AlignmentStage,
    ChunkingStage,
    PostProcessingStage,
    TranscriptionStage,
)
from talking_parrot.stages.vad_stage import VADStage


def _transcribing_only_cfg() -> PipelineConfig:
    return PipelineConfig(
        transcribing=[TranscribingStep(condition="true", backend="faster-whisper")],
    )


def _full_cfg() -> PipelineConfig:
    return PipelineConfig(
        vad=VadConfig(),
        chunking=ChunkingConfig(),
        transcribing=[TranscribingStep(condition="true", backend="faster-whisper")],
        align=AlignConfig(),
        post_processing=PostProcessingConfig(),
    )


def _patch_heavy_constructors(reader_duration_ms: int = 1000):
    """Return a context-manager-stack of patches that neutralize heavy backends.

    The CLI's ``_build_stages`` instantiates real VAD backends, transcription
    factory, alignment factory, etc. Tests don't need these to actually run;
    they only need the stage objects to exist with the right types and order.
    We patch the constructors with no-op stand-ins.

    ``cli.main`` also constructs ``FfmpegAudioReader`` at the top level to
    probe the input audio's duration; the patched class returns a Mock whose
    ``duration_ms`` attribute is a real int (so the value can be JSON-encoded
    into the project file).
    """
    from unittest.mock import MagicMock

    reader_mock = MagicMock()
    reader_mock.return_value.duration_ms = reader_duration_ms
    return [
        patch("talking_parrot.cli.TenVADBackend"),
        patch("talking_parrot.cli.SileroVADBackend"),
        patch("talking_parrot.cli.FormulaEvaluator"),
        patch("talking_parrot.cli.ConditionEvaluator"),
        patch("talking_parrot.cli.TranscriptionBackendFactory"),
        patch("talking_parrot.cli.AlignmentBackendFactory"),
        patch("talking_parrot.cli.DefaultGranularityAwareProcessorFactory"),
        patch("talking_parrot.cli.FfmpegAudioReader", new=reader_mock),
    ]


def _enter_all(patches: Iterable):
    return [p.__enter__() for p in patches]


def _exit_all(patches: Iterable):
    for p in patches:
        p.__exit__(None, None, None)


class TestBuildStagesShape:
    def test_transcribing_only_yields_two_stages(self) -> None:
        patches = _patch_heavy_constructors()
        _enter_all(patches)
        try:
            stages = cli._build_stages(_transcribing_only_cfg(), media_path="x.mp4")
        finally:
            _exit_all(patches)

        assert [type(s) for s in stages] == [TranscriptionStage, PostProcessingStage]

    def test_full_config_yields_five_stages_in_order(self) -> None:
        patches = _patch_heavy_constructors()
        _enter_all(patches)
        try:
            stages = cli._build_stages(_full_cfg(), media_path="x.mp4")
        finally:
            _exit_all(patches)

        assert [type(s) for s in stages] == [
            VADStage,
            ChunkingStage,
            TranscriptionStage,
            AlignmentStage,
            PostProcessingStage,
        ]


class TestExporterNotAStage:
    def test_no_stage_is_a_subtitle_exporter(self) -> None:
        cfg = _full_cfg()
        cfg = cfg.model_copy(
            update={"export": ExportConfig(format="srt", output_path="o.srt")}
        )
        patches = _patch_heavy_constructors()
        _enter_all(patches)
        try:
            stages = cli._build_stages(cfg, media_path="x.mp4")
        finally:
            _exit_all(patches)

        for stage in stages:
            assert not isinstance(stage, SubtitleExporter)


@pytest.fixture
def fake_run_yielding_one_subtitle():
    """Patch ``PipelineOrchestrator.run`` to return a ctx with one subtitle."""

    def _run(self, ctx):
        return dataclasses.replace(ctx, subtitles=[Subtitle(1, 0, 1000, "hi")])

    with patch(
        "talking_parrot.cli.PipelineOrchestrator.run",
        new=_run,
    ):
        yield


def _yaml_text_no_export(out_json: str) -> str:
    return "transcribing:\n  - condition: 'true'\n    backend: faster-whisper\n"


def _yaml_text_with_export_srt(srt_path: str) -> str:
    return (
        "transcribing:\n"
        "  - condition: 'true'\n"
        "    backend: faster-whisper\n"
        "export:\n"
        f"  format: srt\n"
        f"  output_path: {srt_path}\n"
    )


def _run_main_with_args(monkeypatch, argv: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()


class TestExporterInvokedWhenConfigured:
    def test_srt_file_written_with_expected_content(
        self, tmp_path: Path, monkeypatch, fake_run_yielding_one_subtitle
    ) -> None:
        config_yaml = tmp_path / "cfg.yaml"
        srt_out = tmp_path / "out.srt"
        json_out = tmp_path / "project.json"
        config_yaml.write_text(
            _yaml_text_with_export_srt(str(srt_out)), encoding="utf-8"
        )
        media = tmp_path / "media.mp4"
        media.write_bytes(b"\x00\x01\x02")

        # Patch the heavy stage constructors so _build_stages does not load
        # real ML backends. Patch MediaHasher to skip a real hash.
        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
        ]
        _enter_all(patches)
        try:
            _run_main_with_args(
                monkeypatch,
                [
                    "talking-parrot",
                    str(media),
                    "--config",
                    str(config_yaml),
                    "--project-json",
                    str(json_out),
                ],
            )
        finally:
            _exit_all(patches)

        assert srt_out.exists(), "SRT file was not created"
        content = srt_out.read_bytes().decode("utf-8")
        assert content == "1\n00:00:00,000 --> 00:00:01,000\nhi\n"
        assert json_out.exists(), "Project-file JSON was not written"

    def test_exporter_failure_does_not_prevent_project_file_write(
        self, tmp_path: Path, monkeypatch, fake_run_yielding_one_subtitle
    ) -> None:
        config_yaml = tmp_path / "cfg.yaml"
        srt_out = tmp_path / "out.srt"
        json_out = tmp_path / "project.json"
        config_yaml.write_text(
            _yaml_text_with_export_srt(str(srt_out)), encoding="utf-8"
        )
        media = tmp_path / "media.mp4"
        media.write_bytes(b"\x00")

        # Patch the exporter's export method to raise IOError. The project
        # file MUST still have been written before the IOError propagates.
        from talking_parrot.io.subtitle_export.srt import SRTExporter

        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
            patch.object(
                SRTExporter,
                "export",
                side_effect=IOError("disk full"),
            ),
        ]
        _enter_all(patches)
        try:
            with pytest.raises(IOError):
                _run_main_with_args(
                    monkeypatch,
                    [
                        "talking-parrot",
                        str(media),
                        "--config",
                        str(config_yaml),
                        "--project-json",
                        str(json_out),
                    ],
                )
        finally:
            _exit_all(patches)

        assert json_out.exists(), (
            "project-file JSON must be written before exporter is invoked (D7)"
        )


class TestSilentWhenExportNotConfigured:
    def test_no_subtitle_file_no_warning(
        self, tmp_path: Path, monkeypatch, caplog, fake_run_yielding_one_subtitle
    ) -> None:
        config_yaml = tmp_path / "cfg.yaml"
        json_out = tmp_path / "project.json"
        config_yaml.write_text(_yaml_text_no_export(str(json_out)), encoding="utf-8")
        media = tmp_path / "media.mp4"
        media.write_bytes(b"\x00")

        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
        ]
        _enter_all(patches)
        try:
            with caplog.at_level("WARNING"):
                _run_main_with_args(
                    monkeypatch,
                    [
                        "talking-parrot",
                        str(media),
                        "--config",
                        str(config_yaml),
                        "--output",
                        str(json_out),
                    ],
                )
        finally:
            _exit_all(patches)

        assert json_out.exists()
        # No subtitle file was created next to the JSON output.
        assert not any(p.suffix in {".srt", ".vtt"} for p in tmp_path.iterdir())
        # No WARNING log records mention "export" — i.e. silent path.
        for record in caplog.records:
            assert "export" not in record.getMessage().lower(), (
                "CLI must be silent about export when cfg.export is None"
            )


class TestOutputFlagSemantics:
    """Tests for the --output / --project-json flag semantics
    (Requirement: cli.py accepts --output and --project-json with extension-aware semantics).
    """

    def _run(
        self,
        tmp_path: Path,
        monkeypatch,
        argv_extra: list[str],
        config_yaml_text: str,
    ) -> tuple[Path, Path]:
        config_yaml = tmp_path / "cfg.yaml"
        config_yaml.write_text(config_yaml_text, encoding="utf-8")
        media = tmp_path / "media.mp4"
        media.write_bytes(b"\x00")
        return config_yaml, media

    def test_output_overrides_yaml_subtitle_path_and_derives_json(
        self, tmp_path: Path, monkeypatch, fake_run_yielding_one_subtitle
    ) -> None:
        # --output supplies the subtitle path; project-JSON derives by ext-swap.
        # Also covers: cfg.export.output_path is NOT written when --output overrides it.
        from_yaml = tmp_path / "from-yaml.srt"
        from_cli = tmp_path / "from-cli.srt"
        derived_json = tmp_path / "from-cli.json"
        config_yaml, media = self._run(
            tmp_path,
            monkeypatch,
            [],
            _yaml_text_with_export_srt(str(from_yaml)),
        )
        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
        ]
        _enter_all(patches)
        try:
            _run_main_with_args(
                monkeypatch,
                [
                    "talking-parrot",
                    str(media),
                    "--config",
                    str(config_yaml),
                    "--output",
                    str(from_cli),
                ],
            )
        finally:
            _exit_all(patches)

        assert from_cli.exists(), "subtitle should be written to --output path"
        assert derived_json.exists(), "project-JSON should derive from subtitle path"
        assert not from_yaml.exists(), (
            "cfg.export.output_path must be ignored when --output is supplied"
        )

    def test_project_json_overrides_derived_path(
        self, tmp_path: Path, monkeypatch, fake_run_yielding_one_subtitle
    ) -> None:
        srt_out = tmp_path / "sub.srt"
        json_out = tmp_path / "state-run.json"
        config_yaml, media = self._run(
            tmp_path,
            monkeypatch,
            [],
            _yaml_text_with_export_srt(str(tmp_path / "ignored.srt")),
        )
        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
        ]
        _enter_all(patches)
        try:
            _run_main_with_args(
                monkeypatch,
                [
                    "talking-parrot",
                    str(media),
                    "--config",
                    str(config_yaml),
                    "--output",
                    str(srt_out),
                    "--project-json",
                    str(json_out),
                ],
            )
        finally:
            _exit_all(patches)

        assert srt_out.exists()
        assert json_out.exists()
        # The auto-derived path (sub.json) must NOT be created.
        assert not (tmp_path / "sub.json").exists()

    def test_output_required_when_no_export_configured(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        config_yaml, media = self._run(
            tmp_path,
            monkeypatch,
            [],
            _yaml_text_no_export(""),
        )
        with pytest.raises(SystemExit):
            _run_main_with_args(
                monkeypatch,
                [
                    "talking-parrot",
                    str(media),
                    "--config",
                    str(config_yaml),
                ],
            )

    def test_extension_mismatch_exits_before_pipeline_runs(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # cfg.export.format == 'srt' but --output sample.vtt
        srt_yaml_path = tmp_path / "yaml.srt"
        bad_out = tmp_path / "sample.vtt"
        config_yaml, media = self._run(
            tmp_path,
            monkeypatch,
            [],
            _yaml_text_with_export_srt(str(srt_yaml_path)),
        )
        run_patch = patch("talking_parrot.cli.PipelineOrchestrator.run")
        patches = _patch_heavy_constructors() + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
            run_patch,
        ]
        entered = _enter_all(patches)
        run_mock = entered[-1]
        try:
            with pytest.raises(SystemExit):
                _run_main_with_args(
                    monkeypatch,
                    [
                        "talking-parrot",
                        str(media),
                        "--config",
                        str(config_yaml),
                        "--output",
                        str(bad_out),
                    ],
                )
        finally:
            _exit_all(patches)

        run_mock.assert_not_called()
        assert not bad_out.exists()
        assert not (tmp_path / "sample.json").exists()
        assert not srt_yaml_path.exists()


class TestMediaDurationProbing:
    """Tests for the duration-probing behavior
    (Requirement: cli.py populates MediaInfo.duration_ms from the input file).
    """

    def test_real_duration_is_written_into_project_json(
        self, tmp_path: Path, monkeypatch, fake_run_yielding_one_subtitle
    ) -> None:
        config_yaml = tmp_path / "cfg.yaml"
        json_out = tmp_path / "project.json"
        config_yaml.write_text(_yaml_text_no_export(""), encoding="utf-8")
        media = tmp_path / "media.mp4"
        media.write_bytes(b"\x00")

        patches = _patch_heavy_constructors(reader_duration_ms=12345) + [
            patch("talking_parrot.cli.MediaHasher.hash", return_value="deadbeef"),
        ]
        _enter_all(patches)
        try:
            _run_main_with_args(
                monkeypatch,
                [
                    "talking-parrot",
                    str(media),
                    "--config",
                    str(config_yaml),
                    "--output",
                    str(json_out),
                ],
            )
        finally:
            _exit_all(patches)

        import json

        payload = json.loads(json_out.read_text(encoding="utf-8"))
        assert payload["media"]["duration_ms"] == 12345

    def test_probe_failure_exits_before_pipeline_runs(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        config_yaml = tmp_path / "cfg.yaml"
        json_out = tmp_path / "project.json"
        config_yaml.write_text(_yaml_text_no_export(""), encoding="utf-8")
        media = tmp_path / "missing.mp4"
        # Note: do NOT create the media file — probe must fail.

        run_patch = patch("talking_parrot.cli.PipelineOrchestrator.run")
        reader_patch = patch(
            "talking_parrot.cli.FfmpegAudioReader",
            side_effect=FileNotFoundError("no such file"),
        )
        patches = [reader_patch, run_patch]
        entered = _enter_all(patches)
        run_mock = entered[1]
        try:
            with pytest.raises(SystemExit):
                _run_main_with_args(
                    monkeypatch,
                    [
                        "talking-parrot",
                        str(media),
                        "--config",
                        str(config_yaml),
                        "--output",
                        str(json_out),
                    ],
                )
        finally:
            _exit_all(patches)

        run_mock.assert_not_called()
        assert not json_out.exists()
