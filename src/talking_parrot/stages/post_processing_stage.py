"""``PostProcessingStage`` — pipeline stage 5 of the talking_parrot pipeline.

The stage:

1. Builds a seed :class:`Subtitle` sequence (one cue per
   :class:`TranscriptionResult`, 1-based indexed) per design D1.
2. Short-circuits when ``ctx.config.post_processing`` is ``None`` or when
   ``post_processing.enabled is False`` (D9). The processor factory is NOT
   consulted in this path.
3. Otherwise selects the granularity argument for the factory based on
   ``ctx.alignment_status`` (D10): ``SUCCESS`` forwards
   ``ctx.alignment_granularity``; ``FAILED`` logs a WARNING and falls back
   to ``None``; ``DISABLED`` silently falls back to ``None``.
4. Runs each :class:`SubtitleProcessor` returned by the factory in order,
   piping the output of each processor as input to the next. The final list
   has ``Subtitle.index`` renumbered to ``1..N`` and is written onto the
   returned :class:`PipelineContext` via ``dataclasses.replace`` (the input
   context is never mutated).
"""

from __future__ import annotations

import dataclasses
import structlog
from typing import TYPE_CHECKING

from talking_parrot.models.context import AlignmentStatus
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import _renumber
from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.models.transcription import TranscriptionResult
    from talking_parrot.post_processing.factory import (
        GranularityAwareProcessorFactory,
    )

logger = structlog.get_logger(__name__)


def _build_seed_subtitles(
    transcription_results: list["TranscriptionResult"],
) -> list[Subtitle]:
    """Build the seed cue sequence per design D1.

    One :class:`Subtitle` per :class:`TranscriptionResult`, with
    ``index = i + 1`` (1-based, SRT convention), ``start_ms`` / ``end_ms``
    copied from the source result, and ``text`` copied from ``result.text``.
    """
    return [
        Subtitle(
            index=i + 1,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
            text=result.text,
        )
        for i, result in enumerate(transcription_results)
    ]


class PostProcessingStage(PipelineStage):
    """Stage 5: convert transcription results into a final subtitle sequence."""

    def __init__(self, processor_factory: "GranularityAwareProcessorFactory") -> None:
        """Store the injected processor factory; do no work."""
        self._processor_factory = processor_factory

    @property
    def name(self) -> str:
        """Return the stage name."""
        return "post_processing"

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run post-processing and return a new context with ``subtitles`` set."""
        seed = _build_seed_subtitles(ctx.transcription_results)

        # ---- Disabled path (D9) -------------------------------------------
        post_cfg = ctx.config.post_processing
        if post_cfg is None or post_cfg.enabled is False:
            logger.debug(
                "PostProcessingStage: post-processing disabled — returning seed"
            )
            return dataclasses.replace(ctx, subtitles=seed)

        # ---- Granularity resolution (D10) ---------------------------------
        if ctx.alignment_status is AlignmentStatus.SUCCESS:
            granularity_arg = ctx.alignment_granularity
        else:
            if ctx.alignment_status is AlignmentStatus.FAILED:
                logger.warning(
                    "alignment FAILED — falling back to time-based post-processing"
                )
            granularity_arg = None

        # ---- Factory + processor pipeline ---------------------------------
        processors = self._processor_factory.create(granularity_arg, ctx)

        subs: list[Subtitle] = list(seed)
        for processor in processors:
            subs = processor.process(subs, post_cfg)

        # ---- Final renumber (D2 contract) ---------------------------------
        final_subs = _renumber(subs)
        return dataclasses.replace(ctx, subtitles=final_subs)
