"""Unit tests for ``FasterWhisperBackend``.

All tests mock ``faster_whisper`` — no real model inference runs in CI.
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

    # Force ImportError by making sure the module is absent and patching importlib
    sys.modules.pop("faster_whisper", None)

    real_import = __import__

    def fake_import(name: str, *a, **kw):
        if name == "faster_whisper":
            raise ModuleNotFoundError("No module named 'faster_whisper'")
        return real_import(name, *a, **kw)

    with patch("builtins.__import__", side_effect=fake_import):
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

    # Once for "base", once for "large-v3"
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


def test_text_join_and_strip() -> None:
    """Text join: `[" hello", " world ", ""] → "hello  world"` (join by space, strip)."""
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(5.0, 8.0, " hello"),
        _segment(8.0, 12.0, " world "),
        _segment(12.0, 15.0, ""),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    assert result.text == "hello  world"


def test_weighted_mean_avg_logprob() -> None:
    """Weighted mean: durations [1000ms, 3000ms], avg_logprob [-0.5, -0.1] -> -0.2."""
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        # 1000 ms duration
        _segment(
            0.0, 1.0, "a", avg_logprob=-0.5, compression_ratio=1.5, no_speech_prob=0.1
        ),
        # 3000 ms duration
        _segment(
            1.0, 4.0, "b", avg_logprob=-0.1, compression_ratio=2.0, no_speech_prob=0.2
        ),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    assert result.metrics.avg_logprob == pytest.approx(-0.2)


def test_max_no_speech_prob() -> None:
    """``no_speech_prob`` MUST be the max across segments."""
    model_cls = MagicMock()
    instance = MagicMock()
    segs = [
        _segment(0.0, 1.0, "a", no_speech_prob=0.05),
        _segment(1.0, 2.0, "b", no_speech_prob=0.40),
        _segment(2.0, 3.0, "c", no_speech_prob=0.10),
    ]
    instance.transcribe.return_value = (iter(segs), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    assert result.metrics.no_speech_prob == pytest.approx(0.40)


def test_empty_text_repetition_ratio_zero() -> None:
    """Empty text MUST yield ``repetition_ratio == 0.0`` (total token count is 0)."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    assert result.text == ""
    assert result.metrics.repetition_ratio == 0.0


def test_auto_detected_language_surfaces() -> None:
    """``info.language="ja"`` MUST surface as ``result.language == "ja"``."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("ja"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk()
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "base", None)
    assert result.language == "ja"


def test_result_chunk_fields_and_aligned_tokens_none() -> None:
    """chunk_index / start_ms / end_ms / model_used MUST reflect inputs; aligned_tokens is None."""
    model_cls = MagicMock()
    instance = MagicMock()
    instance.transcribe.return_value = (iter([]), _info("en"))
    model_cls.return_value = instance
    _install_fake_faster_whisper(model_cls)

    backend = FasterWhisperBackend()
    chunk = _make_chunk(index=2, start_ms=10000, end_ms=20000)
    result = backend.transcribe(Path("/tmp/x.wav"), chunk, "medium", None)
    assert result.chunk_index == 2
    assert result.start_ms == 10000
    assert result.end_ms == 20000
    assert result.model_used == "medium"
    assert result.aligned_tokens is None
