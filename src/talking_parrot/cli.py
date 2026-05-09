"""talking-parrot CLI entry point.

Wires the full pipeline (Stages 1–5) and Stage 6 subtitle export per the
``pipeline-end-to-end-wiring`` capability spec and design D7/D8/D9:

1. Parse args + load config.
2. Build the stage list via :func:`_build_stages` honoring optional sections.
3. Run :class:`PipelineOrchestrator`.
4. Always write the :class:`ProjectFile` JSON.
5. If ``cfg.export is not None``, instantiate the exporter via
   :class:`SubtitleExporterFactory` and call ``exporter.export(...)``. The
   exporter is NOT registered as a Stage (D9); it runs after the project-file
   write so a disk-full failure on export still leaves the recoverable JSON.
"""

from __future__ import annotations

import argparse
import datetime
import structlog
import os
from pathlib import Path
from typing import TYPE_CHECKING

import ffmpeg

from talking_parrot.alignment.factory import AlignmentBackendFactory
from talking_parrot.config.loader import ConfigLoader
from talking_parrot.expression.condition import ConditionEvaluator
from talking_parrot.expression.formula import FormulaEvaluator
from talking_parrot.io.audio_decoder import FfmpegAudioReader
from talking_parrot.io.media_hasher import MediaHasher
from talking_parrot.io.project_writer import ProjectFileWriter
from talking_parrot.io.subtitle_export import SubtitleExporterFactory
from talking_parrot.logging_config import setup_logging
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.project_file import ProjectFile
from talking_parrot.pipeline.orchestrator import PipelineOrchestrator
from talking_parrot.post_processing.factory import (
    DefaultGranularityAwareProcessorFactory,
)
from talking_parrot.stages import (
    AlignmentStage,
    ChunkingStage,
    PostProcessingStage,
    TranscriptionStage,
)
from talking_parrot.stages.hallucination_filter_stage import HallucinationFilterStage
from talking_parrot.stages.vad_stage import VADStage
from talking_parrot.transcription.factory import TranscriptionBackendFactory
from talking_parrot.vad.silero_vad import SileroVADBackend
from talking_parrot.vad.ten_vad import TenVADBackend

if TYPE_CHECKING:
    from talking_parrot.config.models import PipelineConfig
    from talking_parrot.stages.base import PipelineStage

logger = structlog.get_logger(__name__)


def _build_stages(
    cfg: "PipelineConfig",
    media_path: str,
    audio_reader: "FfmpegAudioReader | None" = None,
) -> list["PipelineStage"]:
    """Construct the ordered pipeline stage list per the wiring spec.

    Order (per ``pipeline-end-to-end-wiring`` Requirement and D7):

    1. ``VADStage`` — only when ``cfg.vad is not None``.
    2. ``ChunkingStage`` — only when ``cfg.chunking is not None``.
    3. ``TranscriptionStage`` — always.
    4. ``HallucinationFilterStage`` — only when
       ``cfg.hallucination_filter is not None``. Inserted between
       transcription and alignment so downstream stages observe a filtered
       ``transcription_results``; when ``cfg.align is None`` it falls
       naturally between transcription and post-processing.
    5. ``AlignmentStage`` — only when ``cfg.align is not None``.
    6. ``PostProcessingStage`` — always.

    The function delegates to existing factories / backend constructors; it
    does NOT introduce any new wiring code beyond what already exists in the
    project. Per D9 the subtitle exporter is NOT a stage and SHALL NOT appear
    in the returned list.
    """
    stages: list["PipelineStage"] = []

    if cfg.vad is not None:
        backends = [TenVADBackend(), SileroVADBackend()]
        formula_evaluator = FormulaEvaluator()
        if audio_reader is None:
            audio_reader = FfmpegAudioReader(media_path)
        stages.append(
            VADStage(
                backends=backends,
                formula_evaluator=formula_evaluator,
                audio_reader=audio_reader,
            )
        )

    if cfg.chunking is not None:
        stages.append(ChunkingStage())

    transcription_factory = TranscriptionBackendFactory()
    condition_evaluator = ConditionEvaluator()
    stages.append(
        TranscriptionStage(
            factory=transcription_factory,
            evaluator=condition_evaluator,
        )
    )

    if cfg.hallucination_filter is not None:
        stages.append(HallucinationFilterStage(cfg.hallucination_filter))

    if cfg.align is not None:
        alignment_factory = AlignmentBackendFactory()
        if audio_reader is None:
            audio_reader = FfmpegAudioReader(media_path)
        stages.append(
            AlignmentStage(
                factory=alignment_factory,
                audio_reader=audio_reader,
            )
        )

    pp_factory = DefaultGranularityAwareProcessorFactory()
    stages.append(PostProcessingStage(processor_factory=pp_factory))

    return stages


_FORMAT_EXTENSION = {"srt": ".srt", "webvtt": ".vtt"}


def _resolve_output_paths(
    cfg: "PipelineConfig",
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> tuple[str | None, str]:
    """Resolve subtitle and project-JSON output paths from config + CLI flags.

    Returns ``(subtitle_path, project_json_path)``. ``subtitle_path`` is
    ``None`` when ``cfg.export`` is ``None``. Calls ``parser.error`` (which
    raises ``SystemExit``) when required flags are missing or extension does
    not match the configured export format.
    """
    if cfg.export is None:
        if args.output is None:
            parser.error(
                "--output is required when the config has no `export` section "
                "(it specifies the project-JSON output path)."
            )
        return None, args.output

    expected_ext = _FORMAT_EXTENSION[cfg.export.format]
    subtitle_path = args.output if args.output is not None else cfg.export.output_path
    actual_ext = os.path.splitext(subtitle_path)[1].lower()
    if actual_ext != expected_ext:
        parser.error(
            f"--output extension {actual_ext!r} does not match export format "
            f"{cfg.export.format!r} (expected {expected_ext!r}). The format is "
            f"taken from config, not inferred from the file extension."
        )

    if args.project_json is not None:
        project_json_path = args.project_json
    else:
        project_json_path = os.path.splitext(subtitle_path)[0] + ".json"

    return subtitle_path, project_json_path


def main() -> None:
    """CLI entry point — runs the pipeline and (optionally) exports subtitles."""
    parser = argparse.ArgumentParser(
        prog="talking-parrot",
        description="Subtitle generation pipeline",
    )
    parser.add_argument("input", help="Path to the media file")
    parser.add_argument(
        "--config", required=True, help="Path to the pipeline YAML config"
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=(
            "Log level. Overrides the LOG_LEVEL env var. "
            "Defaults to LOG_LEVEL or WARNING."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Subtitle output path when the config has an `export` section "
            "(overrides `export.output_path`). When the config has no "
            "`export` section, this is the project-JSON output path. "
            "Required in that case."
        ),
    )
    parser.add_argument(
        "--project-json",
        dest="project_json",
        default=None,
        help=(
            "Project-JSON output path. When omitted and `export` is "
            "configured, defaults to the subtitle path with the extension "
            "replaced by `.json`."
        ),
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    cfg = ConfigLoader.load(args.config)
    subtitle_path, project_json_path = _resolve_output_paths(cfg, args, parser)

    try:
        audio_reader = FfmpegAudioReader(args.input)
        duration_ms = audio_reader.duration_ms
    except (ffmpeg.Error, KeyError, ValueError, FileNotFoundError) as exc:
        parser.error(f"failed to probe input audio {args.input!r}: {exc}")

    sha256 = MediaHasher.hash(args.input)
    media_info = MediaInfo(
        path=Path(args.input), duration_ms=duration_ms, sha256=sha256
    )

    ctx = PipelineContext(config=cfg, media_info=media_info)
    stages = _build_stages(cfg, media_path=args.input, audio_reader=audio_reader)
    orchestrator = PipelineOrchestrator(stages)
    ctx = orchestrator.run(ctx)

    project_file = ProjectFile(
        version="0.1.0",
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        media={
            "path": media_info.path,
            "sha256": media_info.sha256,
            "duration_ms": media_info.duration_ms,
        },
        config=cfg.model_dump(),
        vad_frames=ctx.vad_frames,
        vad_segments=ctx.vad_segments,
        transcription_results=ctx.transcription_results,
        subtitles=ctx.subtitles,
    )

    # D7: always write the project file BEFORE the exporter runs so a
    # disk-full failure during export does not lose the recoverable JSON.
    ProjectFileWriter.write(project_file, project_json_path)

    # D9: the exporter is invoked directly from the CLI, not as a stage.
    if cfg.export is not None:
        assert subtitle_path is not None
        exporter = SubtitleExporterFactory.create(cfg.export.format)
        exporter.export(ctx.subtitles, subtitle_path)


if __name__ == "__main__":
    main()
