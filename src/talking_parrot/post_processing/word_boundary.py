"""Word-boundary post-processors.

Spec: ``word-boundary-processors``. Design: D3 (token-map closure) and D6.

These processors close over a per-cue ``AlignedToken`` map keyed by
``Subtitle.index``. The factory builds the initial map and the stage's helpers
keep it in sync as cues merge / split.
"""

from __future__ import annotations

import structlog
import math
from typing import TYPE_CHECKING

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import SubtitleProcessor, _renumber

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig
    from talking_parrot.models.transcription import AlignedToken

logger = structlog.get_logger(__name__)


def _can_merge_word(a: Subtitle, b: Subtitle, config: "PostProcessingConfig") -> bool:
    """Return whether ``a`` and ``b`` can be merged with a single space."""
    if b.start_ms - a.end_ms > config.merge_gap_threshold_ms:
        return False
    if b.end_ms - a.start_ms > config.merge_max_duration_ms:
        return False
    text_budget = config.max_line_length * config.max_lines_per_subtitle
    if len(a.text) + 1 + len(b.text) > text_budget:
        return False
    return True


class WordBoundaryMergeProcessor(SubtitleProcessor):
    """Merge adjacent cues whose join lands on a token boundary.

    The seed-cue construction guarantees each cue spans exactly one
    ``TranscriptionResult``, so any cue boundary is already a token boundary;
    merging therefore concatenates whole texts with `" "`.
    """

    def __init__(
        self,
        token_map_by_index: dict[int, list["AlignedToken"]],
    ) -> None:
        """Store the per-cue token map keyed by current ``Subtitle.index``."""
        self.token_map_by_index = token_map_by_index

    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Run a single left-to-right merge pass with `" "` separator."""
        if not subtitles:
            return []

        merged: list[Subtitle] = [subtitles[0]]
        for nxt in subtitles[1:]:
            cur = merged[-1]
            if _can_merge_word(cur, nxt, config):
                merged[-1] = Subtitle(
                    index=cur.index,
                    start_ms=cur.start_ms,
                    end_ms=nxt.end_ms,
                    text=cur.text + " " + nxt.text,
                )
            else:
                merged.append(nxt)
        return _renumber(merged)


class WordBoundarySplitProcessor(SubtitleProcessor):
    """Split oversized cues at token boundaries (D6 WORD branch)."""

    def __init__(
        self,
        token_map_by_index: dict[int, list["AlignedToken"]],
    ) -> None:
        """Store the per-cue token map keyed by current ``Subtitle.index``."""
        self.token_map_by_index = token_map_by_index

    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Slice each oversized cue into ``ceil(duration / cap)`` token groups."""
        if not subtitles:
            return []

        out: list[Subtitle] = []
        for sub in subtitles:
            duration = sub.end_ms - sub.start_ms
            if duration <= config.split_max_duration_ms:
                out.append(sub)
                continue

            tokens = self.token_map_by_index.get(sub.index, [])
            n = math.ceil(duration / config.split_max_duration_ms)
            if len(tokens) < n:
                logger.debug(
                    "WordBoundarySplitProcessor: cue not splittable",
                    cue_index=sub.index,
                    tokens_len=len(tokens),
                    n=n,
                )
                out.append(sub)
                continue

            # Partition tokens into n consecutive groups using slice boundaries.
            # A token belongs to slice i if its start_ms is closest to the
            # i-th slice; we use a simple cumulative-slice partitioning by
            # start_ms relative to slice boundaries.
            groups: list[list["AlignedToken"]] = [[] for _ in range(n)]
            for tok in tokens:
                # Slice index by token start_ms; clamp to [0, n-1].
                rel = tok.start_ms - sub.start_ms
                slice_idx = min(int(rel * n / duration), n - 1)
                slice_idx = max(slice_idx, 0)
                groups[slice_idx].append(tok)

            # If any group is empty (e.g. token clustering left a slice bare),
            # rebalance by re-distributing tokens evenly so every slice has
            # at least one token. This preserves the spec invariant that each
            # piece corresponds to a non-empty token range.
            if any(not g for g in groups):
                groups = [[] for _ in range(n)]
                per = max(1, len(tokens) // n)
                for i in range(n):
                    if i < n - 1:
                        groups[i] = list(tokens[i * per : (i + 1) * per])
                    else:
                        groups[i] = list(tokens[i * per :])

            for group in groups:
                first = group[0]
                last = group[-1]
                piece_text = " ".join(t.word for t in group)
                out.append(
                    Subtitle(
                        index=sub.index,
                        start_ms=int(first.start_ms),
                        end_ms=int(last.end_ms),
                        text=piece_text,
                    )
                )
        return _renumber(out)
