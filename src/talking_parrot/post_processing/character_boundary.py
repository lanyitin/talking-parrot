"""Character-boundary post-processors (CJK and similar).

Spec: ``character-boundary-processors``. Design: ``vad-driven-cue-split``
Decisions 1, 3, 4 — split decision is time-first when a VAD silence is
found inside the cue, with grammar fallback otherwise.
"""

from __future__ import annotations

import bisect
import math
import structlog
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
    from talking_parrot.models.transcription import AlignedToken

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
    """Split oversized cues using a VAD-driven (time → text) primary path.

    Spec ``character-boundary-processors`` (change ``vad-driven-cue-split``).

    For each inner boundary the processor first asks
    :meth:`SplitTimePolicy.pick` for a silence midpoint inside the cue. If a
    midpoint is returned AND aligned tokens are available for the cue, the
    text-cut character index is derived by binary-searching the tokens by
    ``start_ms`` and clamped into ``[1, len(text) - 1]``. Otherwise the
    processor falls back to the historical grammar-snap algorithm using
    :meth:`SplitBoundaryPolicy.adjust` and :meth:`SplitTimePolicy.adjust`.
    """

    def __init__(
        self,
        policy: SplitBoundaryPolicy | None = None,
        time_policy: SplitTimePolicy | None = None,
        token_map_by_index: dict[int, list["AlignedToken"]] | None = None,
    ) -> None:
        """Capture the split policies and (optional) per-cue token map.

        ``token_map_by_index`` maps the seed cue's ``index`` (1-based) to a
        list of :class:`AlignedToken`. ``None`` is normalised to ``{}`` so
        absent entries fall through to the grammar-based fallback.
        """
        self._policy: SplitBoundaryPolicy = policy or LinearSplitBoundaryPolicy()
        self._time_policy: SplitTimePolicy = time_policy or LinearSplitTimePolicy()
        self._token_map_by_index: dict[int, list["AlignedToken"]] = (
            token_map_by_index if token_map_by_index is not None else {}
        )

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
            vad_grammar_radius = config.vad_grammar_search_radius
            tokens = self._token_map_by_index.get(sub.index, [])
            token_ends = [t.end_ms for t in tokens]

            # Compute (time_boundary, char_end_or_None) per inner boundary.
            # ``char_end_or_None is None`` signals "use grammar fallback".
            inner: list[tuple[int, int | None]] = []
            for i in range(1, n):
                silence_midpoint = self._time_policy.pick(sub.start_ms, sub.end_ms)
                if silence_midpoint is not None and tokens:
                    # Primary VAD-driven path: derive char_idx from token timestamps.
                    # Find the first token whose end_ms >= silence_midpoint, i.e.
                    # the token containing the silence or the first token after it.
                    found_idx = bisect.bisect_left(token_ends, silence_midpoint)
                    char_idx_vad = sum(len(t.word) for t in tokens[:found_idx])
                    char_idx_vad = max(1, min(char_idx_vad, text_len - 1))
                    char_idx = self._sanity_gate(
                        sub=sub,
                        char_idx_vad=char_idx_vad,
                        duration=duration,
                        n=n,
                        slice_index=i,
                        text_len=text_len,
                        vad_grammar_radius=vad_grammar_radius,
                        legacy_radius=radius,
                    )
                    inner.append((silence_midpoint, char_idx))
                else:
                    if silence_midpoint is None:
                        logger.debug(
                            "CharacterBoundarySplitProcessor: fallback no_silence",
                            cue_index=sub.index,
                            slice_index=i,
                        )
                    else:
                        logger.debug(
                            "CharacterBoundarySplitProcessor: fallback empty_token_map",
                            cue_index=sub.index,
                            slice_index=i,
                        )
                    inner.append((self._fallback_time(sub, duration, n, i), None))

            # Build full time-boundary list with 1ms-collision guard.
            time_boundaries: list[int] = [sub.start_ms]
            for i, (t_ms, _) in enumerate(inner, start=1):
                snapped = t_ms
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
                    primary_char_end = inner[i][1]
                    if primary_char_end is not None:
                        char_end = primary_char_end
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

    def _fallback_time(self, sub: Subtitle, duration: int, n: int, i: int) -> int:
        """Return ``time_policy.adjust`` of the linear slice-end timestamp."""
        linear_ms = sub.start_ms + (i * duration) // n
        return self._time_policy.adjust(linear_ms, sub.start_ms, sub.end_ms)

    def _sanity_gate(
        self,
        *,
        sub: Subtitle,
        char_idx_vad: int,
        duration: int,
        n: int,
        slice_index: int,
        text_len: int,
        vad_grammar_radius: int,
        legacy_radius: int,
    ) -> int:
        """Route ``char_idx_vad`` through grammar sanity check (ADR-0004).

        Three sub-paths:

        * 3a — ``policy.is_valid(char_idx_vad)`` True → use it (no log).
        * 3b — small-radius ``policy.adjust`` snaps to a valid index → use
          it and log INFO ``grammar_snap``.
        * 3c — small-radius snap fails → re-run ``policy.adjust`` against
          the linear-interpolation candidate with the legacy
          ``japanese_split_search_radius`` and log INFO ``grammar_fallback``.

        Time boundary stays as the silence midpoint in all three sub-paths
        (the caller passes that through unchanged); only the text cut index
        varies between the three sub-paths.
        """
        policy = self._policy
        text = sub.text
        # Path 3a: VAD-derived index is already grammar-valid.
        if policy.is_valid(text, char_idx_vad):
            return char_idx_vad
        # Path 3b: try a small-radius snap to the nearest valid boundary.
        snapped = policy.adjust(text, char_idx_vad, vad_grammar_radius)
        if policy.is_valid(text, snapped):
            logger.info(
                "grammar_snap",
                cue_id=sub.index,
                char_idx_vad=char_idx_vad,
                char_idx_final=snapped,
                fallback_reason="grammar_snap",
            )
            return snapped
        # Path 3c: fall back to the linear-interpolation candidate with the
        # larger legacy radius. This is the safety net for cases where the
        # VAD silence lands inside a region (e.g. a long katakana run) with
        # no valid boundary nearby — the linear midpoint is more likely to
        # land in usable territory.
        linear_slice_end_ms = sub.start_ms + (slice_index * duration) // n
        linear_candidate = round(
            (linear_slice_end_ms - sub.start_ms) / duration * text_len
        )
        linear_candidate = max(1, min(linear_candidate, text_len - 1))
        char_idx_final = policy.adjust(text, linear_candidate, legacy_radius)
        logger.info(
            "grammar_fallback",
            cue_id=sub.index,
            char_idx_vad=char_idx_vad,
            char_idx_final=char_idx_final,
            fallback_reason="grammar_fallback",
        )
        return char_idx_final
