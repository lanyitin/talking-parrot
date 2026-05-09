"""Time-range helper tests (task 4.2).

Covers the **Time-range tools accept optional millisecond bounds**
requirement for ``vad_segments_in_range``, ``vad_frames_in_range``,
``subtitles_in_range``, and ``pre_postprocess_subtitles_in_range``.
"""

from __future__ import annotations

from collections.abc import Callable

from talking_parrot.mcp.server import (
    pre_postprocess_subtitles_in_range,
    subtitles_in_range,
    vad_frames_in_range,
    vad_segments_in_range,
)
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.shared import ProjectSnapshot


def test_vad_segments_no_bounds_returns_all(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """No bounds → full collection."""
    snap = make_snapshot()
    out = vad_segments_in_range(snap)
    assert len(out) == len(snap.vad_segments)


def test_vad_segments_bounded_overlap(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Bounded range returns overlap only.

    Spec scenario: ``get_vad_segments(start_ms=1000, end_ms=2000)`` with
    fixture segments at ``[500,1500)`` and ``[2000,3000)`` returns the
    first segment only (the second one starts at 2000 which is the
    half-open upper bound and is therefore excluded).
    """
    snap = make_snapshot()
    out = vad_segments_in_range(snap, start_ms=1000, end_ms=2000)
    assert len(out) == 1
    assert out[0]["start_ms"] == 500
    assert out[0]["end_ms"] == 1500


def test_vad_frames_bounded(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """Frames within ``[1000, 1500)`` are returned."""
    snap = make_snapshot()
    out = vad_frames_in_range(snap, start_ms=1000, end_ms=1500)
    assert all(1000 <= f["time_ms"] < 1500 for f in out)
    assert len(out) > 0


def test_vad_frames_no_bounds_returns_all(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """No bounds → all frames."""
    snap = make_snapshot()
    out = vad_frames_in_range(snap)
    assert len(out) == len(snap.vad_frames)


def test_subtitles_no_bounds_returns_all(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """``get_subtitles()`` returns every subtitle."""
    snap = make_snapshot()
    out = subtitles_in_range(snap)
    assert len(out) == len(snap.subtitles)


def test_subtitles_bounded(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """Only subtitles overlapping ``[1000, 2000)`` are returned."""
    snap = make_snapshot()
    out = subtitles_in_range(snap, start_ms=1000, end_ms=2000)
    assert len(out) == 1
    assert out[0]["index"] == 1


def test_pre_postprocess_subtitles_helper(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """``pre_postprocess_subtitles_in_range`` honours bounds."""
    pre = [
        Subtitle(index=0, start_ms=100, end_ms=400, text="a"),
        Subtitle(index=1, start_ms=2000, end_ms=2500, text="b"),
    ]
    snap = make_snapshot(pre_postprocess_subtitles=pre)
    out_all = pre_postprocess_subtitles_in_range(snap)
    assert len(out_all) == 2
    out_bounded = pre_postprocess_subtitles_in_range(snap, start_ms=0, end_ms=500)
    assert len(out_bounded) == 1
    assert out_bounded[0]["text"] == "a"
