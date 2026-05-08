"""Granularity-aware processor factory.

Spec: ``granularity-aware-processor-factory``. Design: D3, D7, plus the
decisions *Dedup added as the first processor in every granularity path*
and *Japanese processors appended only when ``expected_language == "ja"``*
in the ``segment-level-postprocessing-pipeline`` design doc.

The factory maps an ``AlignmentGranularity | None`` to an ordered list of
:class:`SubtitleProcessor` instances:

1. :class:`DedupSubtitleProcessor` is always prepended.
2. The granularity-specific ``[Merge, Split]`` pair is appended next
   (preserving D7 ordering and the WORD-path token-map injection per D3).
3. ``[JapaneseFillerProcessor, JapaneseRepetitionProcessor]`` is appended
   only when ``ctx.config.expected_language == "ja"`` (case-sensitive).
"""

from __future__ import annotations

import abc
import structlog
from typing import TYPE_CHECKING

from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.post_processing.character_boundary import (
    CharacterBoundaryMergeProcessor,
    CharacterBoundarySplitProcessor,
)
from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.post_processing.dedup import DedupSubtitleProcessor
from talking_parrot.post_processing.japanese import (
    JapaneseFillerProcessor,
    JapaneseRepetitionProcessor,
    JapaneseSplitBoundaryPolicy,
)
from talking_parrot.post_processing.split_policy import (
    LinearSplitBoundaryPolicy,
    SplitBoundaryPolicy,
)
from talking_parrot.post_processing.time_based import (
    TimeBasedMergeProcessor,
    TimeBasedSplitProcessor,
)
from talking_parrot.post_processing.word_boundary import (
    WordBoundaryMergeProcessor,
    WordBoundarySplitProcessor,
)

if TYPE_CHECKING:
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.models.transcription import (
        AlignedToken,
        TranscriptionResult,
    )
    from talking_parrot.post_processing.base import SubtitleProcessor

logger = structlog.get_logger(__name__)


class GranularityAwareProcessorFactory(abc.ABC):
    """Abstract factory mapping ``AlignmentGranularity | None`` to processors."""

    @abc.abstractmethod
    def create(
        self,
        granularity: AlignmentGranularity | None,
        ctx: "PipelineContext",
    ) -> list["SubtitleProcessor"]:
        """Return an ordered processor list for the given granularity."""


class DefaultGranularityAwareProcessorFactory(GranularityAwareProcessorFactory):
    """Default factory: ``[Dedup, Merge, Split, (Japanese pair)]`` per granularity."""

    def create(
        self,
        granularity: AlignmentGranularity | None,
        ctx: "PipelineContext",
    ) -> list["SubtitleProcessor"]:
        """Return the ordered processor list for ``granularity`` and ``ctx``.

        - ``WORD``: ``[Dedup, WordBoundaryMerge, WordBoundarySplit, ...]``
          with token-map injection (D3) on both word-boundary processors.
        - ``CHARACTER``: ``[Dedup, CharacterBoundaryMerge, CharacterBoundarySplit, ...]``.
        - ``None``: ``[Dedup, TimeBasedMerge, TimeBasedSplit, ...]``.
        - Anything else: raises ``ValueError`` (OCP closure point per ADR-0003).

        The Japanese filler + repetition pair is appended to the tail iff
        ``ctx.config.expected_language == "ja"``.
        """
        if granularity is AlignmentGranularity.WORD:
            token_map = self._build_token_map(ctx.transcription_results)
            logger.debug(
                "factory: WORD path",
                token_map_keys=sorted(token_map.keys()),
            )
            core: list["SubtitleProcessor"] = [
                WordBoundaryMergeProcessor(token_map_by_index=token_map),
                WordBoundarySplitProcessor(token_map_by_index=token_map),
            ]
        elif granularity is AlignmentGranularity.CHARACTER:
            logger.debug("factory: CHARACTER path")
            core = [
                CharacterBoundaryMergeProcessor(),
                CharacterBoundarySplitProcessor(policy=self._build_policy(ctx)),
            ]
        elif granularity is None:
            logger.debug("factory: time-based fallback path")
            core = [
                TimeBasedMergeProcessor(),
                TimeBasedSplitProcessor(policy=self._build_policy(ctx)),
            ]
        else:
            # Unknown granularity — guard the OCP closure point.
            name = getattr(granularity, "name", repr(granularity))
            raise ValueError(
                f"GranularityAwareProcessorFactory: unsupported granularity {name!r}"
            )

        processors = self._wrap(core, ctx)
        logger.debug(
            "factory: built processor list",
            count=len(processors),
            expected_language=ctx.config.expected_language,
        )
        return processors

    @staticmethod
    def _wrap(
        core: list["SubtitleProcessor"],
        ctx: "PipelineContext",
    ) -> list["SubtitleProcessor"]:
        """Prepend Dedup and conditionally append the Japanese processor pair.

        Per the design decisions, Dedup is always the first processor in
        every granularity path, and the Japanese filler + repetition pair is
        appended only when ``ctx.config.expected_language == "ja"`` (the
        comparison is case-sensitive — config-layer normalisation is not
        this factory's concern).
        """
        processors: list["SubtitleProcessor"] = [DedupSubtitleProcessor()]
        processors.extend(core)
        if ctx.config.expected_language == "ja":
            processors.append(JapaneseFillerProcessor())
            processors.append(JapaneseRepetitionProcessor())
        return processors

    @staticmethod
    def _build_policy(ctx: "PipelineContext") -> SplitBoundaryPolicy:
        """Pick the SplitBoundaryPolicy for ``ctx`` based on expected language.

        Returns ``JapaneseSplitBoundaryPolicy`` when ``expected_language ==
        "ja"`` and ``LinearSplitBoundaryPolicy`` otherwise. Falls back to
        ``PostProcessingConfig()`` defaults when the pipeline config does
        not declare a ``post_processing`` section.
        """
        if ctx.config.expected_language == "ja":
            pp = ctx.config.post_processing or PostProcessingConfig()
            return JapaneseSplitBoundaryPolicy(pp)
        return LinearSplitBoundaryPolicy()

    @staticmethod
    def _build_token_map(
        transcription_results: list["TranscriptionResult"],
    ) -> dict[int, list["AlignedToken"]]:
        """Build a ``{seed_index: aligned_tokens}`` map (1-based keys) per D3.

        ``None`` and empty ``aligned_tokens`` both map to ``[]``.
        """
        out: dict[int, list["AlignedToken"]] = {}
        for i, result in enumerate(transcription_results):
            tokens = result.aligned_tokens or []
            out[i + 1] = list(tokens)
        return out
