"""Time-based fallback post-processors.

Spec: ``time-based-processors``. Design: D5 (merge), D6 (split fallback).

These processors do NOT consume any token data — they make decisions purely
from ``Subtitle.start_ms`` / ``end_ms`` / ``text`` and the configured
thresholds.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import SubtitleProcessor, _renumber

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig

logger = logging.getLogger(__name__)


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
                    "TimeBasedSplitProcessor: cue index=%d not splittable "
                    "(len(text)=%d <= 1)",
                    sub.index,
                    len(sub.text),
                )
                out.append(sub)
                continue

            n = math.ceil(duration / config.split_max_duration_ms)
            text_len = len(sub.text)
            for i in range(n):
                slice_start = sub.start_ms + (i * duration) // n
                slice_end = sub.start_ms + ((i + 1) * duration) // n
                char_start = round(i / n * text_len)
                char_end = round((i + 1) / n * text_len)
                piece_text = sub.text[char_start:char_end]
                out.append(
                    Subtitle(
                        index=sub.index,  # placeholder; renumbered below
                        start_ms=slice_start,
                        end_ms=slice_end,
                        text=piece_text,
                    )
                )
        return _renumber(out)
