"""Unit tests for the ``TranscriptionBackend`` abstract interface.

Covers (from ``transcription-backend`` spec):
- Direct instantiation rejected: ``TranscriptionBackend()`` raises ``TypeError``.
- Concrete subclass satisfies interface (new contract: returns
  ``list[TranscriptionResult]``).
- Empty segment list permitted: a backend MAY return ``[]`` for a chunk.
- Result fields reflect segment window (per-segment ``start_ms``/``end_ms``
  derived from chunk offset + segment seconds).
- Empty text yields zero repetition ratio.
- Per-segment values not averaged: each segment carries its own raw metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.transcription.backend import TranscriptionBackend


@dataclass(frozen=True)
class _StubSegment:
    """Stand-in for a Whisper internal segment used by the stub backend."""

    start_seconds: float
    end_seconds: float
    text: str
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float


def _repetition_ratio(text: str) -> float:
    """Compute ``1 - unique/total`` over whitespace-split tokens; 0 when empty."""
    tokens = text.split()
    if not tokens:
        return 0.0
    return 1.0 - (len(set(tokens)) / len(tokens))


class _StubBackend(TranscriptionBackend):
    """Concrete backend that replays a pre-supplied list of stub segments.

    It performs no I/O; it just maps the supplied ``_StubSegment`` list into
    the per-segment ``TranscriptionResult`` shape required by the new spec.
    """

    def __init__(self, segments: list[_StubSegment]) -> None:
        """Capture the segments this stub will emit on ``transcribe()``."""
        self._segments = segments

    @property
    def name(self) -> str:
        """Return the backend identifier."""
        return "stub"

    def transcribe(
        self,
        audio_path: Path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> list[TranscriptionResult]:
        """Return one ``TranscriptionResult`` per stub segment, in order."""
        results: list[TranscriptionResult] = []
        for seg in self._segments:
            text = seg.text.strip()
            results.append(
                TranscriptionResult(
                    chunk_index=chunk.index,
                    start_ms=chunk.start_ms + int(round(seg.start_seconds * 1000)),
                    end_ms=chunk.start_ms + int(round(seg.end_seconds * 1000)),
                    text=text,
                    language=language or "en",
                    model_used=model,
                    metrics=TranscriptionMetrics(
                        avg_logprob=seg.avg_logprob,
                        compression_ratio=seg.compression_ratio,
                        no_speech_prob=seg.no_speech_prob,
                        repetition_ratio=_repetition_ratio(text),
                    ),
                    aligned_tokens=None,
                )
            )
        return results


def _make_chunk(index: int = 0, start_ms: int = 0, end_ms: int = 1000) -> Chunk:
    """Build a minimal ``Chunk`` with no source VAD segments."""
    return Chunk(index=index, start_ms=start_ms, end_ms=end_ms)


def test_direct_instantiation_rejected() -> None:
    """``TranscriptionBackend()`` MUST raise ``TypeError`` because it is abstract."""
    with pytest.raises(TypeError):
        TranscriptionBackend()  # type: ignore[abstract]


def test_concrete_subclass_satisfies_interface() -> None:
    """A subclass implementing both members instantiates and passes isinstance.

    The new contract requires ``transcribe`` to return ``list[TranscriptionResult]``.
    """
    backend = _StubBackend(
        segments=[
            _StubSegment(
                start_seconds=0.0,
                end_seconds=1.0,
                text="hello",
                avg_logprob=-0.2,
                compression_ratio=1.1,
                no_speech_prob=0.05,
            )
        ]
    )
    assert isinstance(backend, TranscriptionBackend)
    assert backend.name == "stub"

    chunk = _make_chunk()
    result = backend.transcribe(
        audio_path=Path("/nonexistent.wav"),
        chunk=chunk,
        model="base",
        language="en",
    )
    assert isinstance(result, list), (
        "transcribe() MUST return list[TranscriptionResult] under the new contract"
    )
    assert len(result) == 1
    assert isinstance(result[0], TranscriptionResult)


def test_empty_segment_list_permitted() -> None:
    """A backend MAY return ``[]`` for a chunk; callers MUST treat it as valid."""
    backend = _StubBackend(segments=[])
    result = backend.transcribe(
        audio_path=Path("/nonexistent.wav"),
        chunk=_make_chunk(),
        model="base",
        language="en",
    )
    assert isinstance(result, list)
    assert result == []


def test_result_fields_reflect_segment_window() -> None:
    """Per the spec scenario: chunk(index=2, start_ms=10000, end_ms=20000) with
    Whisper segments [(0.0, 2.0), (2.5, 5.0)] MUST yield two results with
    chunk_index=2, start_ms=[10000, 12500], end_ms=[12000, 15000], and
    aligned_tokens is None for each.
    """
    chunk = Chunk(index=2, start_ms=10000, end_ms=20000)
    backend = _StubBackend(
        segments=[
            _StubSegment(
                start_seconds=0.0,
                end_seconds=2.0,
                text="alpha",
                avg_logprob=-0.3,
                compression_ratio=1.2,
                no_speech_prob=0.05,
            ),
            _StubSegment(
                start_seconds=2.5,
                end_seconds=5.0,
                text="beta",
                avg_logprob=-0.4,
                compression_ratio=1.3,
                no_speech_prob=0.06,
            ),
        ]
    )

    results = backend.transcribe(
        audio_path=Path("/nonexistent.wav"),
        chunk=chunk,
        model="base",
        language="en",
    )

    assert len(results) == 2
    assert [r.chunk_index for r in results] == [2, 2]
    assert [r.start_ms for r in results] == [10000, 12500]
    assert [r.end_ms for r in results] == [12000, 15000]
    for r in results:
        assert r.aligned_tokens is None


def test_empty_text_yields_zero_repetition_ratio() -> None:
    """A segment with empty text MUST have ``metrics.repetition_ratio == 0.0``."""
    backend = _StubBackend(
        segments=[
            _StubSegment(
                start_seconds=0.0,
                end_seconds=1.0,
                text="",
                avg_logprob=-0.1,
                compression_ratio=1.0,
                no_speech_prob=0.5,
            )
        ]
    )
    results = backend.transcribe(
        audio_path=Path("/nonexistent.wav"),
        chunk=_make_chunk(),
        model="base",
        language="en",
    )
    assert len(results) == 1
    assert results[0].metrics.repetition_ratio == 0.0


def test_per_segment_values_not_averaged() -> None:
    """Per the spec scenario: segments with avg_logprob [-0.5, -0.1] and
    durations [1000ms, 3000ms] MUST yield two results carrying the raw values,
    not a duration-weighted mean.
    """
    backend = _StubBackend(
        segments=[
            _StubSegment(
                start_seconds=0.0,
                end_seconds=1.0,  # 1000 ms duration
                text="one",
                avg_logprob=-0.5,
                compression_ratio=1.0,
                no_speech_prob=0.1,
            ),
            _StubSegment(
                start_seconds=1.0,
                end_seconds=4.0,  # 3000 ms duration
                text="two",
                avg_logprob=-0.1,
                compression_ratio=1.0,
                no_speech_prob=0.1,
            ),
        ]
    )
    results = backend.transcribe(
        audio_path=Path("/nonexistent.wav"),
        chunk=_make_chunk(end_ms=5000),
        model="base",
        language="en",
    )

    assert len(results) == 2
    assert results[0].metrics.avg_logprob == -0.5
    assert results[1].metrics.avg_logprob == -0.1
