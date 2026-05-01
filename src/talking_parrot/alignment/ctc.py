"""Shared CTC forced-alignment kernel.

This module mirrors the WhisperX (m-bain/whisperX) ``alignment.py`` algorithm:

1. Build a trellis ``T[t, j]`` via the standard CTC dynamic-programming
   recurrence.
2. Backtrack the optimal path producing ``(token_index, time_index, score)``
   triples in chronological order.
3. Collapse runs of identical token indices into segments via
   :func:`_merge_repeats`.
4. Convert each segment to an :class:`AlignedToken`.
5. Fill NaN start/end timestamps for unalignable tokens via nearest-neighbour
   :func:`_interpolate_nans`.

The kernel is **tensor-agnostic** — it only requires that ``emissions`` support
2-D indexing ``emissions[t, j]`` returning a Python-castable float and exposes
a ``.shape`` 2-tuple ``(num_frames, num_labels)``. This lets callers pass
``torch.Tensor`` instances in production while tests substitute a tiny
in-memory stub. ``torch`` itself is lazy-imported only for type-checking; the
kernel performs no ``torch.*`` calls.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, NamedTuple

from talking_parrot.models.transcription import AlignedToken

if TYPE_CHECKING:  # pragma: no cover - type-only import
    try:
        import torch  # noqa: F401
    except ImportError:  # pragma: no cover
        pass


# -- Wildcard column sentinel -------------------------------------------------
#
# Tokens absent from the supplied dictionary are mapped to a synthetic
# "wildcard" column appended after the real label space. The wildcard score per
# frame is ``max(emissions[t, j != blank_id])``. The wildcard column index is
# encoded as ``_WILDCARD = -1`` in the internal tokens list (we avoid relying
# on ``num_labels`` because we never materialise an expanded tensor).
_WILDCARD: int = -1


class Point(NamedTuple):
    """One step of the optimal CTC alignment path."""

    token_index: int
    time_index: int
    score: float


class Segment(NamedTuple):
    """A merged run of identical-token-index points."""

    label: str
    start_frame: int
    end_frame: int
    score: float


def ctc_align(
    emissions: Any,
    dictionary: dict[str, int],
    transcript_tokens: list[str],
    blank_id: int,
    frame_rate_hz: float,
    *,
    segment_offset_ms: int,
) -> list[AlignedToken]:
    """Force-align ``transcript_tokens`` to ``emissions`` and return AlignedTokens.

    Args:
        emissions: 2-D tensor-like of log-probabilities, shape
            ``(num_frames, num_labels)``. Must support ``emissions[t, j]``
            returning a Python-castable float and expose ``.shape``.
        dictionary: Mapping ``label -> column_index`` describing the model's
            label space.
        transcript_tokens: Tokens (characters or pieces) to align, in reading
            order. Empty list short-circuits to ``[]``.
        blank_id: Column index of the CTC blank label.
        frame_rate_hz: Number of emission frames per second.
        segment_offset_ms: Offset added to every produced ``start_ms`` /
            ``end_ms`` so the kernel can be called per chunk and still emit
            absolute timestamps when desired.

    Returns:
        One :class:`AlignedToken` per entry in ``transcript_tokens``, in the
        same order. Tokens whose dictionary lookup fails AND whose wildcard
        column is unusable get NaN placeholder timestamps that are then
        filled by :func:`_interpolate_nans`.
    """
    if not transcript_tokens:
        return []

    # Map each transcript token to a column index, or ``_WILDCARD`` when the
    # token is absent from the dictionary.
    token_indices: list[int] = [
        dictionary.get(tok, _WILDCARD) for tok in transcript_tokens
    ]

    num_frames, num_labels = emissions.shape

    # Pre-compute the per-frame wildcard score (max over non-blank columns).
    # When every non-blank column is ``-inf`` the wildcard is unusable.
    wildcard_scores: list[float] = _compute_wildcard_scores(
        emissions, num_frames, num_labels, blank_id
    )
    wildcard_usable: bool = any(not math.isinf(s) for s in wildcard_scores)

    # Token-with-no-dictionary-entry AND wildcard unusable → emit a NaN
    # placeholder for those tokens and skip them in the trellis. The NaN
    # placeholders are interpolated at the end.
    alignable_mask: list[bool] = [
        (idx != _WILDCARD) or wildcard_usable for idx in token_indices
    ]

    if not any(alignable_mask):
        # Degenerate fallback: every token unalignable.
        return [
            AlignedToken(
                word=tok,
                start_ms=segment_offset_ms,
                end_ms=segment_offset_ms,
                score=0.0,
            )
            for tok in transcript_tokens
        ]

    alignable_indices: list[int] = [i for i, ok in enumerate(alignable_mask) if ok]
    alignable_columns: list[int] = [token_indices[i] for i in alignable_indices]

    trellis = _get_trellis(emissions, alignable_columns, blank_id, wildcard_scores)
    path = _backtrack(trellis, emissions, alignable_columns, blank_id, wildcard_scores)
    alignable_labels: list[str] = [transcript_tokens[i] for i in alignable_indices]
    segments = _merge_repeats(path, alignable_labels)
    aligned_alignable = _segments_to_tokens(segments, frame_rate_hz, segment_offset_ms)

    # Stitch alignable AlignedTokens back into the full transcript order,
    # inserting NaN placeholders at the dropped positions.
    nan = float("nan")
    aligned_full: list[AlignedToken] = []
    alignable_iter = iter(aligned_alignable)
    for i, tok in enumerate(transcript_tokens):
        if alignable_mask[i]:
            aligned_full.append(next(alignable_iter))
        else:
            aligned_full.append(
                AlignedToken(word=tok, start_ms=nan, end_ms=nan, score=0.0)
            )

    return _interpolate_nans(aligned_full, segment_offset_ms)


# ---------------------------------------------------------------------------
# Internal helpers (not exported)
# ---------------------------------------------------------------------------


def _compute_wildcard_scores(
    emissions: Any, num_frames: int, num_labels: int, blank_id: int
) -> list[float]:
    """Return the per-frame ``max(emissions[t, j != blank_id])`` as a Python list."""
    scores: list[float] = []
    neg_inf = float("-inf")
    for t in range(num_frames):
        row_max = neg_inf
        for j in range(num_labels):
            if j == blank_id:
                continue
            v = float(emissions[t, j])
            if v > row_max:
                row_max = v
        scores.append(row_max)
    return scores


def _get_trellis(
    emission: Any,
    tokens: list[int],
    blank_id: int,
    wildcard_scores: list[float],
) -> list[list[float]]:
    """Build the CTC trellis ``T[t, j]`` via standard dynamic programming.

    The recurrence is::

        T[t+1, j+1] = max(
            T[t, j+1] + emission[t, blank_id],          # stay (emit blank)
            T[t,   j] + emission[t, tokens[j]],         # advance to next token
        )

    with ``T[0, 0] = 0`` and ``T[0, j>0] = -inf``. Wildcard columns
    (``tokens[j] == _WILDCARD``) read from ``wildcard_scores[t]`` instead.

    Returns a Python list-of-lists of shape ``(num_frames + 1, num_tokens + 1)``.
    """
    num_frames, _ = emission.shape
    num_tokens = len(tokens)

    neg_inf = float("-inf")
    trellis: list[list[float]] = [
        [neg_inf] * (num_tokens + 1) for _ in range(num_frames + 1)
    ]
    trellis[0][0] = 0.0

    for t in range(num_frames):
        emit_blank = float(emission[t, blank_id])
        # j == 0: only the "stay-blank" transition is valid (no token to advance into).
        if trellis[t][0] != neg_inf:
            trellis[t + 1][0] = trellis[t][0] + emit_blank
        for j in range(num_tokens):
            tok_col = tokens[j]
            emit_tok = (
                wildcard_scores[t]
                if tok_col == _WILDCARD
                else float(emission[t, tok_col])
            )
            stay = (
                trellis[t][j + 1] + emit_blank
                if trellis[t][j + 1] != neg_inf
                else neg_inf
            )
            advance = trellis[t][j] + emit_tok if trellis[t][j] != neg_inf else neg_inf
            best = stay if stay >= advance else advance
            trellis[t + 1][j + 1] = best

    return trellis


def _backtrack(
    trellis: list[list[float]],
    emission: Any,
    tokens: list[int],
    blank_id: int,
    wildcard_scores: list[float],
) -> list[Point]:
    """Backtrack the optimal CTC path from ``(num_frames, num_tokens)``.

    Emits points in chronological order (oldest frame first).
    """
    num_frames = len(trellis) - 1
    num_tokens = len(tokens)

    t = num_frames
    j = num_tokens
    path_reversed: list[Point] = []

    while t > 0 and j > 0:
        emit_blank = float(emission[t - 1, blank_id])
        tok_col = tokens[j - 1]
        emit_tok = (
            wildcard_scores[t - 1]
            if tok_col == _WILDCARD
            else float(emission[t - 1, tok_col])
        )
        stay = trellis[t - 1][j] + emit_blank
        advance = trellis[t - 1][j - 1] + emit_tok
        if advance >= stay:
            # Advanced to the j-1 token at frame t-1.
            path_reversed.append(
                Point(token_index=j - 1, time_index=t - 1, score=emit_tok)
            )
            j -= 1
            t -= 1
        else:
            # Stayed on a blank — record the current token (still j-1) at this frame.
            path_reversed.append(
                Point(token_index=j - 1, time_index=t - 1, score=emit_blank)
            )
            t -= 1

    # If we ran out of frames before consuming all tokens, pad the remaining
    # tokens at frame 0 (mirrors WhisperX's behaviour for tight alignments).
    while j > 0:
        path_reversed.append(Point(token_index=j - 1, time_index=0, score=0.0))
        j -= 1

    path_reversed.reverse()
    return path_reversed


def _merge_repeats(path: list[Point], transcript_tokens: list[str]) -> list[Segment]:
    """Collapse consecutive points with identical ``token_index`` into segments.

    The averaged per-frame score is recorded on each :class:`Segment`.
    """
    segments: list[Segment] = []
    if not path:
        return segments

    i = 0
    n = len(path)
    while i < n:
        j = i
        scores: list[float] = []
        while j < n and path[j].token_index == path[i].token_index:
            scores.append(path[j].score)
            j += 1
        avg = sum(scores) / len(scores) if scores else 0.0
        segments.append(
            Segment(
                label=transcript_tokens[path[i].token_index],
                start_frame=path[i].time_index,
                end_frame=path[j - 1].time_index + 1,
                score=avg,
            )
        )
        i = j
    return segments


def _segments_to_tokens(
    segments: list[Segment],
    frame_rate_hz: float,
    segment_offset_ms: int,
) -> list[AlignedToken]:
    """Convert :class:`Segment` instances to chunk-relative :class:`AlignedToken`."""
    ms_per_frame = 1000.0 / frame_rate_hz
    tokens: list[AlignedToken] = []
    for seg in segments:
        start_ms = segment_offset_ms + round(seg.start_frame * ms_per_frame)
        end_ms = segment_offset_ms + round(seg.end_frame * ms_per_frame)
        tokens.append(
            AlignedToken(
                word=seg.label,
                start_ms=int(start_ms),
                end_ms=int(end_ms),
                score=float(seg.score),
            )
        )
    return tokens


def _interpolate_nans(
    tokens: list[AlignedToken], segment_offset_ms: int
) -> list[AlignedToken]:
    """Fill NaN ``start_ms`` / ``end_ms`` values from nearest non-NaN neighbours.

    Rules:

    - For each token whose ``start_ms`` is NaN, fill from the nearest preceding
      non-NaN token's ``end_ms``.
    - For each token whose ``end_ms`` is NaN, fill from the nearest following
      non-NaN token's ``start_ms``.
    - When a NaN token has no neighbour on a side, fall back to
      ``segment_offset_ms`` (leading) or the last frame's end (trailing).
    - If every token is NaN, set every ``start_ms = end_ms = segment_offset_ms``
      and ``score = 0.0``.
    """
    if not tokens:
        return tokens

    def _is_nan(x: int | float) -> bool:
        """Return True when ``x`` is a float NaN."""
        return isinstance(x, float) and math.isnan(x)

    # All-NaN fallback: collapse every token to the segment offset.
    if all(_is_nan(t.start_ms) and _is_nan(t.end_ms) for t in tokens):
        return [
            AlignedToken(
                word=t.word,
                start_ms=segment_offset_ms,
                end_ms=segment_offset_ms,
                score=0.0,
            )
            for t in tokens
        ]

    # Pre-compute trailing fallback: the last non-NaN ``end_ms``.
    last_concrete_end: int | None = None
    for t in tokens:
        if not _is_nan(t.end_ms):
            last_concrete_end = int(t.end_ms)

    n = len(tokens)
    fixed: list[AlignedToken] = []
    for i, tok in enumerate(tokens):
        new_start: int | float = tok.start_ms
        new_end: int | float = tok.end_ms

        if _is_nan(new_start):
            # Look left for the nearest non-NaN ``end_ms``.
            left: int | None = None
            for k in range(i - 1, -1, -1):
                if not _is_nan(tokens[k].end_ms):
                    left = int(tokens[k].end_ms)
                    break
            new_start = left if left is not None else segment_offset_ms

        if _is_nan(new_end):
            # Look right for the nearest non-NaN ``start_ms``.
            right: int | None = None
            for k in range(i + 1, n):
                if not _is_nan(tokens[k].start_ms):
                    right = int(tokens[k].start_ms)
                    break
            if right is None:
                right = (
                    last_concrete_end
                    if last_concrete_end is not None
                    else segment_offset_ms
                )
            new_end = right

        fixed.append(
            AlignedToken(
                word=tok.word,
                start_ms=int(new_start),
                end_ms=int(new_end),
                score=float(tok.score),
            )
        )
    return fixed
