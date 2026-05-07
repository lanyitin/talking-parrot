"""``AlignmentStage`` — pipeline stage 4 of the talking_parrot pipeline.

The stage:

1. Resolves a single :class:`AlignmentBackend` per run via the injected
   :class:`AlignmentBackendFactory`.
2. For each :class:`TranscriptionResult`, reads the chunk's PCM bytes from the
   injected :class:`AudioReader`, calls ``backend.align(...)``, and shifts the
   returned chunk-relative timestamps to absolute time by adding
   ``chunk.start_ms``.
3. Applies a bounded per-chunk fallback: a backend exception for one chunk
   does not abort the run; that chunk's tokens become ``[]`` and processing
   continues.
4. Records ``alignment_status``, ``alignment_granularity``, and
   ``alignment_results`` on the returned :class:`PipelineContext`, and writes
   ``aligned_tokens`` onto each :class:`TranscriptionResult` via
   ``dataclasses.replace`` (the input context is never mutated).

The disabled path (``ctx.config.align is None`` or ``align.enabled is False``)
short-circuits without consulting the factory or audio reader.
"""

from __future__ import annotations

import dataclasses
import structlog
from typing import TYPE_CHECKING

from talking_parrot.models.context import (
    AlignmentResult,
    AlignmentStatus,
    GranularityPreference,
)
from talking_parrot.models.transcription import AlignedToken
from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.alignment.factory import AlignmentBackendFactory
    from talking_parrot.io.audio_reader import AudioReader
    from talking_parrot.models.context import PipelineContext

logger = structlog.get_logger(__name__)


class AlignmentStage(PipelineStage):
    """Per-chunk forced-alignment stage."""

    def __init__(
        self,
        factory: "AlignmentBackendFactory",
        audio_reader: "AudioReader",
    ) -> None:
        """Store the injected factory and audio reader; do no work."""
        self._factory = factory
        self._audio_reader = audio_reader

    @property
    def name(self) -> str:
        """Return the stage name."""
        return "alignment"

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run alignment for every transcription result and return a new context."""
        # ---- Disabled path -------------------------------------------------
        if ctx.config.align is None or ctx.config.align.enabled is False:
            logger.debug("AlignmentStage: alignment disabled — short-circuiting")
            return dataclasses.replace(
                ctx,
                alignment_status=AlignmentStatus.DISABLED,
                alignment_granularity=None,
                alignment_results=[],
            )

        # ---- Resolve a single backend per run -----------------------------
        try:
            granularity_pref = GranularityPreference(
                ctx.config.align.granularity.upper()
            )
        except ValueError as exc:
            logger.warning(
                "AlignmentStage: invalid granularity preference",
                granularity=ctx.config.align.granularity,
                error=str(exc),
            )
            return dataclasses.replace(
                ctx,
                alignment_status=AlignmentStatus.FAILED,
                alignment_granularity=None,
                alignment_results=[],
            )

        try:
            backend = self._factory.create(
                ctx.config.expected_language, granularity_pref
            )
        except ValueError as exc:
            logger.warning(
                "AlignmentStage: no backend",
                language=ctx.config.expected_language,
                granularity_pref=granularity_pref,
                error=str(exc),
            )
            return dataclasses.replace(
                ctx,
                alignment_status=AlignmentStatus.FAILED,
                alignment_granularity=None,
                alignment_results=[],
            )

        # ---- Per-chunk loop -----------------------------------------------
        if not ctx.transcription_results:
            logger.debug(
                "AlignmentStage: empty transcription_results with alignment "
                "enabled — returning FAILED"
            )
            return dataclasses.replace(
                ctx,
                alignment_status=AlignmentStatus.FAILED,
                alignment_granularity=None,
                alignment_results=[],
            )

        sample_rate = self._audio_reader.sample_rate
        absolute_tokens_per_result: list[list[AlignedToken]] = []
        successful_chunks_count = 0

        for result in ctx.transcription_results:
            chunk = ctx.chunks[result.chunk_index]
            audio_bytes = self._audio_reader.read(chunk.start_ms, chunk.end_ms)
            try:
                tokens = backend.align(audio_bytes, sample_rate, result.text)
            except Exception as exc:
                logger.warning(
                    "alignment failed for chunk",
                    chunk_index=result.chunk_index,
                    error=type(exc).__name__,
                )
                absolute_tokens_per_result.append([])
                continue

            shifted = [
                dataclasses.replace(
                    t,
                    start_ms=t.start_ms + chunk.start_ms,
                    end_ms=t.end_ms + chunk.start_ms,
                )
                for t in tokens
            ]
            absolute_tokens_per_result.append(shifted)
            if shifted:
                successful_chunks_count += 1

        # ---- Final status + outputs ---------------------------------------
        final_status = (
            AlignmentStatus.SUCCESS
            if successful_chunks_count > 0
            else AlignmentStatus.FAILED
        )

        new_results = [
            dataclasses.replace(r, aligned_tokens=absolute_tokens_per_result[i])
            for i, r in enumerate(ctx.transcription_results)
        ]
        alignment_results = [
            AlignmentResult(
                chunk_index=r.chunk_index, tokens=absolute_tokens_per_result[i]
            )
            for i, r in enumerate(ctx.transcription_results)
        ]

        return dataclasses.replace(
            ctx,
            transcription_results=new_results,
            alignment_results=alignment_results,
            alignment_status=final_status,
            alignment_granularity=(
                backend.granularity if final_status is AlignmentStatus.SUCCESS else None
            ),
        )
