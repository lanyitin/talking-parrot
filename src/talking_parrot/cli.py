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
import logging
from typing import TYPE_CHECKING

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
from talking_parrot.stages.vad_stage import VADStage
from talking_parrot.transcription.factory import TranscriptionBackendFactory
from talking_parrot.vad.silero_vad import SileroVADBackend
from talking_parrot.vad.ten_vad import TenVADBackend

if TYPE_CHECKING:
    from talking_parrot.config.models import PipelineConfig
    from talking_parrot.stages.base import PipelineStage

logger = logging.getLogger(__name__)


def _build_stages(cfg: "PipelineConfig", media_path: str) -> list["PipelineStage"]:
    """Construct the ordered pipeline stage list per the wiring spec.

    Order (per ``pipeline-end-to-end-wiring`` Requirement and D7):

    1. ``VADStage`` — only when ``cfg.vad is not None``.
    2. ``ChunkingStage`` — only when ``cfg.chunking is not None``.
    3. ``TranscriptionStage`` — always.
    4. ``AlignmentStage`` — only when ``cfg.align is not None``.
    5. ``PostProcessingStage`` — always.

    The function delegates to existing factories / backend constructors; it
    does NOT introduce any new wiring code beyond what already exists in the
    project. Per D9 the subtitle exporter is NOT a stage and SHALL NOT appear
    in the returned list.
    """
    stages: list["PipelineStage"] = []

    if cfg.vad is not None:
        backends = [TenVADBackend(), SileroVADBackend()]
        formula_evaluator = FormulaEvaluator()
        stages.append(VADStage(backends=backends, formula_evaluator=formula_evaluator))

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

    if cfg.align is not None:
        alignment_factory = AlignmentBackendFactory()
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


def main() -> None:
    """CLI entry point — runs the pipeline and (optionally) exports subtitles."""
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="talking-parrot",
        description="Subtitle generation pipeline",
    )
    parser.add_argument("input", help="Path to the media file")
    parser.add_argument(
        "--config", required=True, help="Path to the pipeline YAML config"
    )
    parser.add_argument("--output", required=True, help="Path for the output JSON file")
    args = parser.parse_args()

    cfg = ConfigLoader.load(args.config)

    sha256 = MediaHasher.hash(args.input)
    media_info = MediaInfo(path=args.input, duration_ms=0, sha256=sha256)

    ctx = PipelineContext(config=cfg, media_info=media_info)
    stages = _build_stages(cfg, media_path=args.input)
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
        vad_segments=ctx.vad_segments,
        transcription_results=ctx.transcription_results,
        subtitles=ctx.subtitles,
    )

    # D7: always write the project file BEFORE the exporter runs so a
    # disk-full failure during export does not lose the recoverable JSON.
    ProjectFileWriter.write(project_file, args.output)

    # D9: the exporter is invoked directly from the CLI, not as a stage.
    if cfg.export is not None:
        exporter = SubtitleExporterFactory.create(cfg.export.format)
        exporter.export(ctx.subtitles, cfg.export.output_path)


if __name__ == "__main__":
    main()
