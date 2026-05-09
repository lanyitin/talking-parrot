"""Tests for ``summary_from_snapshot`` (task 4.1).

Covers the **`summary` returns aggregate counts and audio duration**
requirement.
"""

from __future__ import annotations

from collections.abc import Callable

from talking_parrot.mcp.server import summary_from_snapshot
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.vad import VadSegment
from talking_parrot.shared import ProjectSnapshot


def test_summary_includes_aggregate_counts(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Default fixture produces matching counts."""
    snap = make_snapshot()
    out = summary_from_snapshot(snap)
    assert out["n_vad_segments"] == 2
    assert out["n_subtitles"] == 3
    assert out["n_transcription_results"] == 3
    assert out["audio_duration_ms"] == 5000


def test_summary_scenario_twelve_segments_thirty_subtitles(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Spec example: 12 VAD segments + 30 subtitles."""
    vad_segments = [
        VadSegment(
            start_ms=i * 100,
            end_ms=i * 100 + 50,
            ten_vad_prob=0.5,
            silero_vad_prob=0.5,
            composite_score=0.5,
        )
        for i in range(12)
    ]
    subtitles = [
        Subtitle(index=i, start_ms=i * 100, end_ms=i * 100 + 50, text=f"x{i}")
        for i in range(30)
    ]
    snap = make_snapshot(vad_segments=vad_segments, subtitles=subtitles)
    out = summary_from_snapshot(snap)
    assert out["n_vad_segments"] == 12
    assert out["n_subtitles"] == 30
    assert out["audio_duration_ms"] == snap.audio_info.duration_ms


def test_summary_keys_present(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """All required keys are emitted."""
    snap = make_snapshot()
    out = summary_from_snapshot(snap)
    for key in (
        "n_vad_segments",
        "n_vad_frames",
        "n_chunks",
        "n_transcription_results",
        "n_subtitles",
        "n_pre_postprocess_subtitles",
        "audio_duration_ms",
    ):
        assert key in out
