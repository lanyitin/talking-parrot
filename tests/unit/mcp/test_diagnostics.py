"""Tests for ``diagnostics_from_snapshot`` (task 4.4).

Covers:

- The **`diagnostics` is derived purely from the snapshot** requirement —
  the helper computes flags entirely from the snapshot.
- The **Tools depend on `ProjectSnapshot`, not on filesystem paths (DIP)**
  requirement — verified by ``monkeypatch``-ing builtins ``open`` to fail
  during the call. If the helper touches the filesystem the test fails.
- Threshold override via ``snapshot.config_snapshot``.
"""

from __future__ import annotations

import builtins
from collections.abc import Callable

import pytest

from talking_parrot.mcp.server import diagnostics_from_snapshot
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.shared import ProjectSnapshot


def _tr(
    chunk_index: int,
    *,
    avg_logprob: float = -0.3,
    no_speech_prob: float = 0.05,
    repetition_ratio: float = 0.0,
) -> TranscriptionResult:
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=chunk_index * 1000,
        end_ms=(chunk_index + 1) * 1000,
        text=f"line {chunk_index}",
        language="en",
        model_used="test",
        metrics=TranscriptionMetrics(
            avg_logprob=avg_logprob,
            compression_ratio=1.2,
            no_speech_prob=no_speech_prob,
            repetition_ratio=repetition_ratio,
        ),
        aligned_tokens=None,
    )


def test_low_confidence_flag_uses_avg_logprob(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """A transcription with ``avg_logprob`` below threshold is flagged."""
    snap = make_snapshot(transcription_results=[_tr(0, avg_logprob=-2.0)])
    out = diagnostics_from_snapshot(snap)
    assert len(out["low_confidence"]) == 1
    entry = out["low_confidence"][0]
    assert entry["chunk_index"] == 0
    assert entry["reason"] == "avg_logprob"


def test_no_speech_flag(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """A transcription with high ``no_speech_prob`` is flagged."""
    snap = make_snapshot(transcription_results=[_tr(0, no_speech_prob=0.9)])
    out = diagnostics_from_snapshot(snap)
    assert len(out["no_speech"]) == 1
    assert out["no_speech"][0]["reason"] == "no_speech_prob"


def test_repetition_flag(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """A transcription with high ``repetition_ratio`` is flagged."""
    snap = make_snapshot(transcription_results=[_tr(0, repetition_ratio=0.8)])
    out = diagnostics_from_snapshot(snap)
    assert len(out["repetition"]) == 1
    assert out["repetition"][0]["reason"] == "repetition_ratio"


def test_clean_snapshot_has_no_flags(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Default fixture transcripts are clean."""
    snap = make_snapshot()
    out = diagnostics_from_snapshot(snap)
    assert out["low_confidence"] == []
    assert out["no_speech"] == []
    assert out["repetition"] == []


def test_threshold_override_via_config(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Thresholds in ``config_snapshot`` override the documented defaults."""
    snap = make_snapshot(
        transcription_results=[_tr(0, avg_logprob=-0.5)],
        config_snapshot={"low_confidence_avg_logprob": -0.4},
    )
    out = diagnostics_from_snapshot(snap)
    assert len(out["low_confidence"]) == 1


def test_no_filesystem_access(
    make_snapshot: Callable[..., ProjectSnapshot],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patching ``open`` to raise must not affect ``diagnostics_from_snapshot``.

    Realises the **Tools depend on `ProjectSnapshot`, not on filesystem
    paths (DIP)** requirement.
    """
    snap = make_snapshot(transcription_results=[_tr(0, avg_logprob=-2.0)])

    def _explode(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "diagnostics_from_snapshot must not call open() — "
            "tools depend on ProjectSnapshot, not on filesystem paths"
        )

    monkeypatch.setattr(builtins, "open", _explode)
    out = diagnostics_from_snapshot(snap)
    assert len(out["low_confidence"]) == 1
