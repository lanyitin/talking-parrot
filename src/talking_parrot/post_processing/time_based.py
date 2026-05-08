"""Time-based fallback post-processors.

Spec: ``time-based-processors``. Design: D5 (merge), D6 (split fallback).

These processors do NOT consume any token data — they make decisions purely
from ``Subtitle.start_ms`` / ``end_ms`` / ``text`` and the configured
thresholds.
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


def _can_merge(
    a: Subtitle, b: Subtitle, config: "PostProcessingConfig", separator_len: int
) -> bool:
    """Return whether ``a`` and ``b`` can be merged under the time-based rule."""
    if b.start_ms - a.end_ms > config.merge_gap_threshold_ms:
        return False
    if b.end_ms - a.start_ms > config.merge_max_duration_ms:
        return False
    text_budget = config.max_line_length * config.max_lines_per_subtitle
    if len(a.text) + separator_len + len(b.text) > text_budget:
        return False
    return True


class TimeBasedMergeProcessor(SubtitleProcessor):
    """Merge adjacent cues using a single space separator (D5 fallback)."""

    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Run a single left-to-right pass merging adjacent eligible cues."""
        if not subtitles:
            return []

        merged: list[Subtitle] = [subtitles[0]]
        for nxt in subtitles[1:]:
            cur = merged[-1]
            if _can_merge(cur, nxt, config, separator_len=1):
                merged[-1] = Subtitle(
                    index=cur.index,
                    start_ms=cur.start_ms,
                    end_ms=nxt.end_ms,
                    text=cur.text + " " + nxt.text,
                )
            else:
                merged.append(nxt)
        return _renumber(merged)


class TimeBasedSplitProcessor(SubtitleProcessor):
    """Split oversized cues into ``ceil(duration / cap)`` equal-time slices."""

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
        """Split each cue exceeding ``split_max_duration_ms`` proportionally by length."""
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
                    "TimeBasedSplitProcessor: cue not splittable",
                    cue_index=sub.index,
                    text_len=len(sub.text),
                )
                out.append(sub)
                continue

            n = math.ceil(duration / config.split_max_duration_ms)
            text_len = len(sub.text)
            radius = config.japanese_split_search_radius
            text_boundaries: list[int] = [0]
            for i in range(1, n):
                candidate = round(i / n * text_len)
                adjusted = self._policy.adjust(sub.text, candidate, radius)
                text_boundaries.append(adjusted)
            text_boundaries.append(text_len)

            time_boundaries: list[int] = [sub.start_ms]
            for i in range(1, n):
                linear_ms = sub.start_ms + (i * duration) // n
                snapped = self._time_policy.adjust(linear_ms, sub.start_ms, sub.end_ms)
                if snapped <= time_boundaries[-1]:
                    logger.debug(
                        "TimeBasedSplitProcessor: time-boundary collision",
                        cue_index=sub.index,
                        slice_index=i,
                    )
                    snapped = time_boundaries[-1] + 1
                time_boundaries.append(snapped)
            if sub.end_ms <= time_boundaries[-1]:
                logger.debug(
                    "TimeBasedSplitProcessor: time-boundary collision",
                    cue_index=sub.index,
                    slice_index=n,
                )
                time_boundaries.append(time_boundaries[-1] + 1)
            else:
                time_boundaries.append(sub.end_ms)

            for i in range(n):
                slice_start = time_boundaries[i]
                slice_end = time_boundaries[i + 1]
                lo, hi = text_boundaries[i], text_boundaries[i + 1]
                if hi == lo and i > 0:
                    logger.debug(
                        "TimeBasedSplitProcessor: empty slice from policy snap",
                        cue_index=sub.index,
                        slice_index=i,
                    )
                    piece_text = ""
                else:
                    piece_text = sub.text[lo:hi]
                out.append(
                    Subtitle(
                        index=sub.index,
                        start_ms=slice_start,
                        end_ms=slice_end,
                        text=piece_text,
                    )
                )
        return _renumber(out)
