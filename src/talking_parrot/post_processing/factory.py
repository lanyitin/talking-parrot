"""Granularity-aware processor factory.

Spec: ``granularity-aware-processor-factory``. Design: D3, D7.

The factory maps an ``AlignmentGranularity | None`` to an ordered list of
:class:`SubtitleProcessor` instances. Per D7 every group is ordered
``[Merge, Split]``. Per D3, the WORD path additionally bakes a
``token_map_by_index`` (keyed by the seed ``Subtitle.index`` — i.e. the
1-based position of each :class:`TranscriptionResult` in input order) into
both word-boundary processors.
"""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING

from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.post_processing.character_boundary import (
    CharacterBoundaryMergeProcessor,
    CharacterBoundarySplitProcessor,
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

logger = logging.getLogger(__name__)


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
    """Default factory returning ``[Merge, Split]`` groups per D7."""

    def create(
        self,
        granularity: AlignmentGranularity | None,
        ctx: "PipelineContext",
    ) -> list["SubtitleProcessor"]:
        """Return the ``[Merge, Split]`` processor pair for ``granularity``.

        - ``WORD``: word-boundary processors with a baked-in token map (D3).
        - ``CHARACTER``: character-boundary processors (no token map).
        - ``None``: time-based fallback group.
        - Anything else: raises ``ValueError`` (OCP closure point per ADR-0003).
        """
        if granularity is AlignmentGranularity.WORD:
            token_map = self._build_token_map(ctx.transcription_results)
            logger.debug(
                "factory: WORD path — token_map keys=%s",
                sorted(token_map.keys()),
            )
            return [
                WordBoundaryMergeProcessor(token_map_by_index=token_map),
                WordBoundarySplitProcessor(token_map_by_index=token_map),
            ]
        if granularity is AlignmentGranularity.CHARACTER:
            logger.debug("factory: CHARACTER path")
            return [
                CharacterBoundaryMergeProcessor(),
                CharacterBoundarySplitProcessor(),
            ]
        if granularity is None:
            logger.debug("factory: time-based fallback path")
            return [
                TimeBasedMergeProcessor(),
                TimeBasedSplitProcessor(),
            ]
        # Unknown granularity — guard the OCP closure point.
        name = getattr(granularity, "name", repr(granularity))
        raise ValueError(
            f"GranularityAwareProcessorFactory: unsupported granularity {name!r}"
        )

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
