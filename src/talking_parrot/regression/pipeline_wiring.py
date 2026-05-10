"""Production pipeline runner factory for the regression harness.

Bridges the regression harness with the full talking-parrot pipeline by
loading a :class:`~talking_parrot.config.models.PipelineConfig`, building
the real stage sequence, and converting the resulting
:class:`~talking_parrot.models.context.PipelineContext` into a
:class:`~talking_parrot.shared.ProjectSnapshot`.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from talking_parrot.alignment.factory import AlignmentBackendFactory
from talking_parrot.config.loader import ConfigLoader
from talking_parrot.expression.condition import ConditionEvaluator
from talking_parrot.expression.formula import FormulaEvaluator
from talking_parrot.io.audio_decoder import FfmpegAudioReader
from talking_parrot.io.media_hasher import MediaHasher
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.pipeline.orchestrator import PipelineOrchestrator
from talking_parrot.post_processing.factory import (
    DefaultGranularityAwareProcessorFactory,
)
from talking_parrot.regression.runner import PipelineRunner, PipelineRunnerFactory
from talking_parrot.shared import AudioInfo, ProjectSnapshot
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


def _build_stages(cfg, media_path: str, audio_reader: FfmpegAudioReader):  # type: ignore[no-untyped-def]
    """Build the ordered stage list for a given config and media path."""
    from talking_parrot.stages.base import PipelineStage

    stages: list[PipelineStage] = []

    if cfg.vad is not None:
        stages.append(
            VADStage(
                backends=[TenVADBackend(), SileroVADBackend()],
                formula_evaluator=FormulaEvaluator(),
                audio_reader=audio_reader,
            )
        )

    if cfg.chunking is not None:
        stages.append(ChunkingStage())

    stages.append(
        TranscriptionStage(
            factory=TranscriptionBackendFactory(),
            evaluator=ConditionEvaluator(),
        )
    )

    if cfg.hallucination_filter is not None:
        stages.append(HallucinationFilterStage(cfg.hallucination_filter))

    if cfg.align is not None:
        stages.append(
            AlignmentStage(
                factory=AlignmentBackendFactory(),
                audio_reader=audio_reader,
            )
        )

    stages.append(PostProcessingStage(processor_factory=DefaultGranularityAwareProcessorFactory()))
    return stages


def build_production_pipeline_runner_factory(
    config_path: Path,
) -> PipelineRunnerFactory:
    """Return a :class:`PipelineRunnerFactory` backed by the real pipeline.

    The config is loaded once when the factory is invoked. Each runner call
    spins up a fresh set of stages for the given audio variant.
    """

    def factory() -> PipelineRunner:
        """Construct the shared config and return a per-variant runner."""
        cfg = ConfigLoader.load(str(config_path))

        def runner(sample_dir: Path, variant_file: str) -> ProjectSnapshot:
            """Run the full pipeline for one audio file and return a snapshot."""
            media_path = str(sample_dir / variant_file)
            audio_reader = FfmpegAudioReader(media_path)
            stages = _build_stages(cfg, media_path, audio_reader)
            orchestrator = PipelineOrchestrator(stages)
            sha256 = MediaHasher.hash(media_path)
            media_info = MediaInfo(
                path=Path(media_path),
                duration_ms=audio_reader.duration_ms,
                sha256=sha256,
            )
            ctx = PipelineContext(config=cfg, media_info=media_info)
            ctx = orchestrator.run(ctx)
            audio_info = AudioInfo(
                sample_rate=audio_reader.sample_rate,
                duration_ms=audio_reader.duration_ms,
                rms_mean=0.0,
                rms_peak=0.0,
            )
            return ProjectSnapshot(
                version="1",
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
                source_path=media_path,
                config_snapshot=cfg.model_dump(),
                audio_info=audio_info,
                vad_frames=list(ctx.vad_frames),
                vad_segments=list(ctx.vad_segments),
                chunks=list(ctx.chunks),
                transcription_results=list(ctx.transcription_results),
                pre_postprocess_subtitles=[],
                subtitles=list(ctx.subtitles),
            )

        return runner

    return factory


__all__ = ["build_production_pipeline_runner_factory"]