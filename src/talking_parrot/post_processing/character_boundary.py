"""Character-boundary post-processors (CJK and similar).

Spec: ``character-boundary-processors``. Design: D4 (no token map) and D6.
"""

from __future__ import annotations

import structlog
import math
from typing import TYPE_CHECKING

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import SubtitleProcessor, _renumber
from talking_parrot.post_processing.split_policy import (
    LinearSplitBoundaryPolicy,
    SplitBoundaryPolicy,
)
from talking_parrot.post_processing.split_time_policy import (
    LinearSplitTimePolicy,
    SplitTimePolicy,
)

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig

logger = structlog.get_logger(__name__)


def _can_merge_character(
    a: Subtitle, b: Subtitle, config: "PostProcessingConfig"
) -> bool:
    """Return whether ``a`` and ``b`` can be merged with empty separator."""
    if b.start_ms - a.end_ms > config.merge_gap_threshold_ms:
        return False
    if b.end_ms - a.start_ms > config.merge_max_duration_ms:
        return False
    text_budget = config.max_line_length * config.max_lines_per_subtitle
    if len(a.text) + len(b.text) > text_budget:
        return False
    return True


class CharacterBoundaryMergeProcessor(SubtitleProcessor):
    """Merge adjacent character-aligned cues with empty separator."""

    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Run a single left-to-right merge pass with empty join."""
        if not subtitles:
            return []

        merged: list[Subtitle] = [subtitles[0]]
        for nxt in subtitles[1:]:
            cur = merged[-1]
            if _can_merge_character(cur, nxt, config):
                merged[-1] = Subtitle(
                    index=cur.index,
                    start_ms=cur.start_ms,
                    end_ms=nxt.end_ms,
                    text=cur.text + nxt.text,
                )
            else:
                merged.append(nxt)
        return _renumber(merged)


class CharacterBoundarySplitProcessor(SubtitleProcessor):
    """Split oversized cues using linear interpolation on character indices."""

    def __init__(
        self,
        policy: SplitBoundaryPolicy | None = None,
        time_policy: SplitTimePolicy | None = None,
    ) -> None:
        """Capture the split-boundary and split-time policies (default: linear)."""
        self._policy: SplitBoundaryPolicy = policy or LinearSplitBoundaryPolicy()
        self._time_policy: SplitTimePolicy = time_policy or LinearSplitTimePolicy()

    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Slice each oversized cue into ``ceil(duration / cap)`` pieces."""
        if not subtitles:
            return []

        out: list[Subtitle] = []
        for sub in subtitles:
            duration = sub.end_ms - sub.start_ms
            if duration <= config.split_max_duration_ms:
                out.append(sub)
                continue
            if len(sub.text) <= 1:
                logger.debug(
                    "CharacterBoundarySplitProcessor: cue not splittable",
                    cue_index=sub.index,
                    text_len=len(sub.text),
                )
                out.append(sub)
                continue

            n = math.ceil(duration / config.split_max_duration_ms)
            text_len = len(sub.text)
            radius = config.japanese_split_search_radius

            time_boundaries: list[int] = [sub.start_ms]
            for i in range(1, n):
                linear_ms = sub.start_ms + (i * duration) // n
                snapped = self._time_policy.adjust(linear_ms, sub.start_ms, sub.end_ms)
                if snapped <= time_boundaries[-1]:
                    logger.debug(
                        "CharacterBoundarySplitProcessor: time-boundary collision",
                        cue_index=sub.index,
                        slice_index=i,
                    )
                    snapped = time_boundaries[-1] + 1
                time_boundaries.append(snapped)
            if sub.end_ms <= time_boundaries[-1]:
                logger.debug(
                    "CharacterBoundarySplitProcessor: time-boundary collision",
                    cue_index=sub.index,
                    slice_index=n,
                )
                time_boundaries.append(time_boundaries[-1] + 1)
            else:
                time_boundaries.append(sub.end_ms)

            prev_char = 0
            for i in range(n):
                slice_start_ms = time_boundaries[i]
                slice_end_ms = time_boundaries[i + 1]
                if i == n - 1:
                    char_end = text_len
                else:
                    candidate = round(
                        ((sub.start_ms + ((i + 1) * duration) // n) - sub.start_ms)
                        / duration
                        * text_len
                    )
                    char_end = self._policy.adjust(sub.text, candidate, radius)
                if char_end == prev_char:
                    logger.debug(
                        "CharacterBoundarySplitProcessor: empty slice from policy snap",
                        cue_index=sub.index,
                        slice_index=i,
                    )
                    piece_text = ""
                else:
                    piece_text = sub.text[prev_char:char_end]
                    prev_char = char_end
                out.append(
                    Subtitle(
                        index=sub.index,
                        start_ms=slice_start_ms,
                        end_ms=slice_end_ms,
                        text=piece_text,
                    )
                )
        return _renumber(out)
