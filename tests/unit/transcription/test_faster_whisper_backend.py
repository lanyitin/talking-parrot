"""Unit tests for ``FasterWhisperBackend``.

All tests mock ``faster_whisper`` — no real model inference runs in CI.

Under the segment-level contract (`segment-level-postprocessing-pipeline`),
``transcribe()`` returns ``list[TranscriptionResult]`` with one element per
yielded Whisper internal segment. Per-segment metrics carry raw values; no
chunk-level aggregation is performed by the backend.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from talking_parrot.models.chunk import Chunk
from talking_parrot.transcription.faster_whisper_backend import (
    FasterWhisperBackend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(index: int = 0, start_ms: int = 5000, end_ms: int = 15000) -> Chunk:
    """Return a Chunk with no source segments for backend testing."""
    return Chunk(index=index, start_ms=start_ms, end_ms=end_ms, source_segments=[])


def _segment(
    start: float,
    end: float,
    text: str,
    avg_logprob: float = -0.5,
    compression_ratio: float = 1.5,
    no_speech_prob: float = 0.1,
) -> MagicMock:
    """Build a mock segment matching faster_whisper.Segment's attributes."""
    seg = MagicMock()
    seg.start = start
    seg.end = end
    seg.text = text
    seg.avg_logprob = avg_logprob
    seg.compression_ratio = compression_ratio
    seg.no_speech_prob = no_speech_prob
    return seg


def _info(language: str = "en") -> MagicMock:
    """Build a mock TranscriptionInfo with .language."""
    info = MagicMock()
    info.language = language
    return info


def _install_fake_faster_whisper(model_cls: MagicMock) -> types.ModuleType:
    """Install a fake ``faster_whisper`` module exposing ``WhisperModel=model_cls``.

    Returns the module so tests can inspect / clean up.
    """
    module = types.ModuleType("faster_whisper")
    module.WhisperModel = model_cls  # type: ignore[attr-defined]
    sys.modules["faster_whisper"] = module
    return module


@pytest.fixture(autouse=True)
def _cleanup_faster_whisper() -> None:
    """Ensure each test starts without a stale ``faster_whisper`` import."""
    sys.modules.pop("faster_whisper", None)
    yield
    sys.modules.pop("faster_whisper", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_name() -> None:
    """``name`` property MUST return the literal ``"faster-whisper"``."""
    backend = FasterWhisperBackend()
    assert backend.name == "faster-whisper"


def test_missing_dependency_raises_actionable_import_error() -> None:
    """When ``faster_whisper`` is not importable, the call MUST raise ImportError mentioning the extra."""
    backend = FasterWhisperBackend()
    chunk = _make_chunk()

    sys.modules.pop("faster_whisper", None)

    def fake_import_module(name: str, *a, **kw):
        if name == "faster_whisper":
            raise ModuleNotFoundError("No module named 'faster_whisper'")
        raise AssertionError(f"unexpected import_module call: {name!r}")

    with patch(
        "talking_parrot.transcription.faster_whisper_backend.importlib.import_module",
        side_effect=fake_import_module,
    ):
        with pytest.raises(ImportError) as exc_info:
            backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert "talking-parrot[faster-whisper]" in str(exc_info.value)


def test_models_cached_per_name() -> None:
    """``WhisperModel`` MUST be constructed once per distinct model argument."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert model_cls.call_count == 2
    constructed_models = [
        c.kwargs.get("model_size_or_path") for c in model_cls.call_args_list
    ]
    assert sorted(constructed_models) == ["base", "large-v3"]


def test_clip_timestamps_passed() -> None:
    """The ``clip_timestamps`` kwarg MUST equal ``[start_s, end_s]`` (chunk-window seconds)."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk(start_ms=5000, end_ms=15000)
    backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    kwargs = instance.transcribe.call_args.kwargs
    assert kwargs["clip_timestamps"] == [5.0, 15.0]


# --- Segment-level contract tests -----------------------------------------


def test_one_result_per_yielded_segment() -> None:
    """Spec: Two segments [' hello', ' world '] -> two results, stripped texts."""
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(0.0, 1.0, " hello"),
        _segment(1.0, 2.0, " world "),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0].text == "hello"
    assert results[1].text == "world"


def test_empty_iterator_returns_empty_list() -> None:
    """Spec example: zero segments -> [] (no raise)."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert results == []


def test_auto_detected_language_surfaced_on_each_result() -> None:
    """Spec: ``info.language='ja'`` with three segments and ``language=None``
    surfaces on every element of the list.
    """
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(0.0, 1.0, "a"),
        _segment(1.0, 2.0, "b"),
        _segment(2.0, 3.0, "c"),
    ]
    instance.transcribe.return_value = (iter(segs), _info("ja"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert len(results) == 3
    assert all(r.language == "ja" for r in results)


def test_per_segment_metrics_raw_not_aggregated() -> None:
    """Each result carries its segment's raw avg_logprob / compression_ratio /
    no_speech_prob — no weighted mean across segments.
    """
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(
            0.0,
            1.0,
            "one",
            avg_logprob=-0.5,
            compression_ratio=1.5,
            no_speech_prob=0.1,
        ),
        _segment(
            1.0,
            4.0,
            "two",
            avg_logprob=-0.1,
            compression_ratio=2.0,
            no_speech_prob=0.2,
        ),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert len(results) == 2
    assert results[0].metrics.avg_logprob == -0.5
    assert results[1].metrics.avg_logprob == -0.1
    assert results[0].metrics.compression_ratio == 1.5
    assert results[1].metrics.compression_ratio == 2.0
    assert results[0].metrics.no_speech_prob == 0.1
    assert results[1].metrics.no_speech_prob == 0.2


def test_segment_start_end_ms_use_segment_timestamps() -> None:
    """Per-segment ``start_ms``/``end_ms`` MUST be ``chunk.start_ms +
    int(round(segment.start * 1000))`` (and end likewise), not the chunk bounds.
    """
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(0.0, 2.0, "alpha"),
        _segment(2.5, 5.0, "beta"),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk(index=2, start_ms=10000, end_ms=20000)
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "medium", None)

    assert [r.start_ms for r in results] == [10000, 12500]
    assert [r.end_ms for r in results] == [12000, 15000]
    assert [r.chunk_index for r in results] == [2, 2]
    assert all(r.aligned_tokens is None for r in results)
    assert all(r.model_used == "medium" for r in results)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("hello hello world", 1.0 - 2.0 / 3.0),
        ("a b c", 0.0),
        ("a a", 0.5),
        ("", 0.0),
        ("   ", 0.0),
    ],
)
def test_repetition_ratio_per_segment(text: str, expected: float) -> None:
    """``repetition_ratio = 1 - unique/total`` over whitespace tokens; 0 when empty."""
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [_segment(0.0, 1.0, text)]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    results = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)

    assert len(results) == 1
    assert results[0].metrics.repetition_ratio == pytest.approx(expected)
