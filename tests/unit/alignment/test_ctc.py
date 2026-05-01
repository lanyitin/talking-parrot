"""Tests for the shared CTC forced-alignment kernel.

These tests use a tiny in-memory tensor stub so the kernel can be exercised
without requiring ``torch``.
"""

from __future__ import annotations

import math
from typing import Sequence

import pytest

from talking_parrot.alignment.ctc import (
    Point,
    Segment,
    _backtrack,
    _get_trellis,
    _interpolate_nans,
    _merge_repeats,
    _segments_to_tokens,
    ctc_align,
)
from talking_parrot.models.transcription import AlignedToken


class _FakeTensor:
    """A 2-D float matrix supporting ``mat[t, j]`` and ``.shape``.

    Stands in for ``torch.Tensor`` in kernel tests so we do not need to
    install ``torch``.
    """

    def __init__(self, rows: Sequence[Sequence[float]]) -> None:
        """Wrap a list-of-lists of floats."""
        self._rows = [list(r) for r in rows]
        self.shape = (len(self._rows), len(self._rows[0]) if self._rows else 0)

    def __getitem__(self, key: tuple[int, int]) -> float:
        """Return the float at ``(row, column)``."""
        t, j = key
        return self._rows[t][j]


# ---------------------------------------------------------------------------
# (a) Empty transcript short-circuits
# ---------------------------------------------------------------------------


def test_empty_transcript_returns_empty_list() -> None:
    """An empty ``transcript_tokens`` MUST return ``[]`` immediately."""
    emissions = _FakeTensor([[0.0, 0.0]])
    out = ctc_align(
        emissions,
        dictionary={"a": 1},
        transcript_tokens=[],
        blank_id=0,
        frame_rate_hz=50.0,
        segment_offset_ms=0,
    )
    assert out == []


# ---------------------------------------------------------------------------
# (b) Trellis recurrence shape on a 3-frame, 2-token toy.
# ---------------------------------------------------------------------------


def test_trellis_shape_is_num_frames_plus_one_by_num_tokens_plus_one() -> None:
    """``_get_trellis`` MUST return a ``(T+1) x (N+1)`` matrix."""
    # 3 frames, 3 labels (blank=0, "a"=1, "b"=2). Strong "a" then strong "b" then "a".
    emissions = _FakeTensor(
        [
            [-3.0, 0.0, -3.0],
            [-3.0, -3.0, 0.0],
            [-3.0, 0.0, -3.0],
        ]
    )
    tokens = [1, 2]  # tokens "a" then "b"
    trellis = _get_trellis(
        emissions, tokens, blank_id=0, wildcard_scores=[0.0, 0.0, 0.0]
    )
    assert len(trellis) == 4  # T+1
    assert all(len(row) == 3 for row in trellis)  # N+1


# ---------------------------------------------------------------------------
# (c) Backtrack on the same toy yields a reasonable Point sequence.
# ---------------------------------------------------------------------------


def test_backtrack_emits_chronological_points_for_toy_emission() -> None:
    """Backtrack must produce points in chronological order whose token_index covers the transcript."""
    emissions = _FakeTensor(
        [
            [-3.0, 0.0, -3.0],
            [-3.0, -3.0, 0.0],
            [-3.0, 0.0, -3.0],
        ]
    )
    tokens = [1, 2]  # "a", "b"
    wildcard = [0.0, 0.0, 0.0]
    trellis = _get_trellis(emissions, tokens, blank_id=0, wildcard_scores=wildcard)
    path = _backtrack(trellis, emissions, tokens, blank_id=0, wildcard_scores=wildcard)
    # Chronological time ordering
    times = [p.time_index for p in path]
    assert times == sorted(times)
    # Both transcript tokens appear at least once
    indices = {p.token_index for p in path}
    assert 0 in indices and 1 in indices


# ---------------------------------------------------------------------------
# (d) merge_repeats averages the scores of consecutive identical-token points.
# ---------------------------------------------------------------------------


def test_merge_repeats_collapses_consecutive_same_token_points() -> None:
    """Two points with the same token_index collapse to one segment with mean score."""
    path = [
        Point(token_index=0, time_index=0, score=0.5),
        Point(token_index=0, time_index=1, score=0.6),
    ]
    segments = _merge_repeats(path, transcript_tokens=["a"])
    assert len(segments) == 1
    seg = segments[0]
    assert seg.label == "a"
    assert seg.start_frame == 0
    assert seg.end_frame == 2  # exclusive end — last_time + 1
    assert seg.score == pytest.approx(0.55)


# ---------------------------------------------------------------------------
# (e) _segments_to_tokens converts frames to milliseconds using the offset.
# ---------------------------------------------------------------------------


def test_segments_to_tokens_uses_frame_rate_and_offset() -> None:
    """At 50 Hz, 10 frames = 200 ms; the segment_offset is added to both ends."""
    segments = [Segment(label="a", start_frame=0, end_frame=10, score=0.9)]
    tokens = _segments_to_tokens(segments, frame_rate_hz=50.0, segment_offset_ms=1000)
    assert tokens == [AlignedToken(word="a", start_ms=1000, end_ms=1200, score=0.9)]


# ---------------------------------------------------------------------------
# (f) interpolate scenario from the spec.
# ---------------------------------------------------------------------------


def test_interpolate_nans_fills_middle_token_from_neighbours() -> None:
    """A middle NaN token MUST be filled from the nearest preceding end and following start."""
    tokens = [
        AlignedToken(word="a", start_ms=100, end_ms=200, score=0.9),
        AlignedToken(word="b", start_ms=float("nan"), end_ms=float("nan"), score=0.0),
        AlignedToken(word="c", start_ms=400, end_ms=500, score=0.9),
    ]
    fixed = _interpolate_nans(tokens, segment_offset_ms=0)
    assert fixed[1].start_ms == 200
    assert fixed[1].end_ms == 400


# ---------------------------------------------------------------------------
# (g) all-NaN fallback collapses to ``segment_offset_ms``.
# ---------------------------------------------------------------------------


def test_interpolate_nans_all_nan_collapses_to_segment_offset() -> None:
    """If every token is NaN, every token collapses to ``segment_offset_ms``."""
    tokens = [
        AlignedToken(word="a", start_ms=float("nan"), end_ms=float("nan"), score=0.0),
        AlignedToken(word="b", start_ms=float("nan"), end_ms=float("nan"), score=0.0),
    ]
    fixed = _interpolate_nans(tokens, segment_offset_ms=750)
    assert fixed[0].start_ms == 750 and fixed[0].end_ms == 750
    assert fixed[1].start_ms == 750 and fixed[1].end_ms == 750
    assert fixed[0].score == 0.0 and fixed[1].score == 0.0


def test_ctc_align_end_to_end_on_toy_emission_yields_two_tokens() -> None:
    """End-to-end: with a clear emission peak per token, ``ctc_align`` yields one token each."""
    # 3 frames, labels: blank(0), "a"(1), "b"(2). Strong "a" then strong "b" then strong "b".
    emissions = _FakeTensor(
        [
            [-5.0, 0.0, -5.0],
            [-5.0, -5.0, 0.0],
            [-5.0, -5.0, 0.0],
        ]
    )
    out = ctc_align(
        emissions,
        dictionary={"a": 1, "b": 2},
        transcript_tokens=["a", "b"],
        blank_id=0,
        frame_rate_hz=50.0,
        segment_offset_ms=0,
    )
    assert len(out) == 2
    assert out[0].word == "a"
    assert out[1].word == "b"
    assert all(not math.isnan(t.start_ms) for t in out)
