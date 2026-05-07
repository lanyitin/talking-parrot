"""Segment-level deduplication post-processor.

Spec: ``dedup-subtitle-processor`` (change
``segment-level-postprocessing-pipeline``). Design decision: *Dedup added as
the first processor in every granularity path*.

The processor walks the input cues left-to-right and groups any maximal run
of two or more consecutive ``Subtitle`` entries whose adjacent pairs satisfy
BOTH a similarity threshold (``difflib.SequenceMatcher.ratio() >=
config.dedup_similarity_threshold``) and a gap threshold
(``b.start_ms - a.end_ms <= config.dedup_max_gap_ms``). Each group is
collapsed to a single ``Subtitle`` spanning the run, with the first cue's
text. Indexes are renumbered 1-based after merging.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import TYPE_CHECKING

import structlog

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import SubtitleProcessor, _renumber

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig

logger = structlog.get_logger(__name__)


def _similarity(a: str, b: str) -> float:
    """Return the ``difflib.SequenceMatcher`` ratio for two texts."""
    return SequenceMatcher(None, a, b).ratio()


def _adjacent_mergeable(
    a: Subtitle, b: Subtitle, config: "PostProcessingConfig"
) -> bool:
    """Return whether ``a`` and ``b`` are near-duplicates eligible for dedup.

    Both thresholds use inclusive comparisons per spec: similarity ``>=`` the
    configured threshold AND gap ``<=`` the configured maximum.
    """
    gap_ms = b.start_ms - a.end_ms
    if gap_ms > config.dedup_max_gap_ms:
        return False
    ratio = _similarity(a.text, b.text)
    return ratio >= config.dedup_similarity_threshold


class DedupSubtitleProcessor(SubtitleProcessor):
    """Collapse runs of near-duplicate consecutive cues into a single cue."""

    def process(
        self,
        subtitles: list[Subtitle],
        config: "PostProcessingConfig",
    ) -> list[Subtitle]:
        """Walk left-to-right and merge consecutive near-duplicate cues."""
        if not subtitles:
            return []

        if not config.dedup_enabled:
            # Spec: "element-wise equal to the input (text, start, end, index
            # unchanged)" — return a shallow copy preserving original indexes.
            return list(subtitles)

        # Build groups of consecutive cues whose adjacent pairs are mergeable.
        groups: list[list[Subtitle]] = [[subtitles[0]]]
        for nxt in subtitles[1:]:
            cur = groups[-1][-1]
            if _adjacent_mergeable(cur, nxt, config):
                groups[-1].append(nxt)
            else:
                groups.append([nxt])

        merged_count = 0
        out: list[Subtitle] = []
        for group in groups:
            if len(group) == 1:
                out.append(group[0])
            else:
                merged_count += len(group) - 1
                out.append(
                    Subtitle(
                        index=group[0].index,  # placeholder; renumbered below
                        start_ms=group[0].start_ms,
                        end_ms=group[-1].end_ms,
                        text=group[0].text,
                    )
                )

        if merged_count:
            logger.debug(
                "DedupSubtitleProcessor merged near-duplicate cues",
                input_count=len(subtitles),
                output_count=len(out),
                merged_away=merged_count,
            )
        return _renumber(out)
