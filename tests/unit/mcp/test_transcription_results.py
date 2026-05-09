"""Tests for ``transcription_results_for_chunk`` (task 4.3).

Covers the **`get_transcription_results` filters by chunk index**
requirement.
"""

from __future__ import annotations

from collections.abc import Callable

from talking_parrot.mcp.server import transcription_results_for_chunk
from talking_parrot.shared import ProjectSnapshot


def test_known_chunk_returns_single_result(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Default fixture has chunk_index 0,1,2; selecting 1 returns one item."""
    snap = make_snapshot()
    out = transcription_results_for_chunk(snap, chunk_index=1)
    assert len(out) == 1
    assert out[0]["chunk_index"] == 1


def test_unknown_chunk_returns_empty_list(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Unknown chunk_index → empty list."""
    snap = make_snapshot()
    out = transcription_results_for_chunk(snap, chunk_index=999)
    assert out == []


def test_no_filter_returns_all(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """``chunk_index=None`` returns every transcription result."""
    snap = make_snapshot()
    out = transcription_results_for_chunk(snap, chunk_index=None)
    assert len(out) == len(snap.transcription_results)
