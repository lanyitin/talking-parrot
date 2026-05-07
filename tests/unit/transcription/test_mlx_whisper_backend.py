"""Unit tests for ``MLXWhisperBackend``.

All tests mock ``mlx_whisper`` and ``numpy`` so that no real Apple-Silicon
runtime, model download, or array library is required in CI.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from talking_parrot.models.chunk import Chunk


# ---------------------------------------------------------------------------
# Helpers — fake numpy / mlx_whisper modules for lazy-import tests
# ---------------------------------------------------------------------------


class _FakeArray:
    """Minimal stand-in for a numpy array supporting ``len`` and ``astype``."""

    def __init__(self, length: int, dtype: str = "int16") -> None:
        self._length = length
        self.dtype = dtype

    def __len__(self) -> int:
        return self._length

    def astype(self, dtype: str) -> "_FakeArray":
        """Return a new ``_FakeArray`` with the requested ``dtype`` and same length."""
        return _FakeArray(self._length, dtype=dtype)

    def __truediv__(self, divisor: float) -> "_FakeArray":
        """Pretend division returns a same-length array (for int16 → float32 scale)."""
        return _FakeArray(self._length, dtype="float32")

    def __getitem__(self, key: slice) -> "_FakeArray":
        """Slice support — returns a same-length array for our test purposes."""
        if isinstance(key, slice):
            start, stop, step = key.indices(self._length)
            new_length = max(
                0, (stop - start + (step - (1 if step > 0 else -1))) // step
            )
            return _FakeArray(new_length, dtype=self.dtype)
        raise TypeError("only slices supported in fake")


def _install_fake_numpy(buffer_length: int) -> types.ModuleType:
    """Install a fake ``numpy`` exposing ``frombuffer``, ``int16``, ``float32``."""
    module = types.ModuleType("numpy")

    def frombuffer(buf: bytes, dtype: object) -> _FakeArray:
        # buffer_length is the number of int16 samples we want frombuffer to emit
        return _FakeArray(buffer_length, dtype="int16")

    module.frombuffer = frombuffer  # type: ignore[attr-defined]
    module.int16 = "int16"  # type: ignore[attr-defined]
    module.float32 = "float32"  # type: ignore[attr-defined]
    sys.modules["numpy"] = module
    return module


def _install_fake_mlx_whisper(
    transcribe_return: dict,
) -> tuple[types.ModuleType, MagicMock]:
    """Install a fake ``mlx_whisper`` whose ``transcribe`` returns *transcribe_return*."""
    module = types.ModuleType("mlx_whisper")
    fake_transcribe = MagicMock(return_value=transcribe_return)
    module.transcribe = fake_transcribe  # type: ignore[attr-defined]
    sys.modules["mlx_whisper"] = module
    return module, fake_transcribe


@pytest.fixture(autouse=True)
def _platform_arm64_darwin():
    """Default to a patched Apple-Silicon environment for most tests."""
    with (
        patch.object(sys, "platform", "darwin"),
        patch("platform.machine", return_value="arm64"),
    ):
        yield


@pytest.fixture(autouse=True)
def _cleanup_modules() -> None:
    """Strip cached fakes between tests."""
    sys.modules.pop("mlx_whisper", None)
    sys.modules.pop("numpy", None)
    yield
    sys.modules.pop("mlx_whisper", None)
    sys.modules.pop("numpy", None)


def _make_chunk(index: int = 0, start_ms: int = 2000, end_ms: int = 4000) -> Chunk:
    """Return a Chunk with no source segments for backend testing."""
    return Chunk(index=index, start_ms=start_ms, end_ms=end_ms, source_segments=[])


def _segment_dict(
    start: float,
    end: float,
    text: str,
    avg_logprob: float = -0.5,
    compression_ratio: float = 1.5,
    no_speech_prob: float = 0.1,
) -> dict:
    """Build a segment dict matching the shape mlx_whisper.transcribe returns."""
    return {
        "start": start,
        "end": end,
        "text": text,
        "avg_logprob": avg_logprob,
        "compression_ratio": compression_ratio,
        "no_speech_prob": no_speech_prob,
    }


def _fake_reader(sample_rate: int = 16000, num_samples: int = 32000) -> MagicMock:
    """Return a MagicMock standing in for ``FfmpegAudioReader``."""
    reader = MagicMock()
    reader.sample_rate = sample_rate
    reader.read.return_value = b"\x00\x00" * num_samples
    return reader


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


def test_name() -> None:
    """``name`` MUST return the literal ``"mlx-whisper"``."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    backend = MLXWhisperBackend()
    assert backend.name == "mlx-whisper"


def test_linux_construction_rejected() -> None:
    """Construction MUST raise ``RuntimeError`` mentioning Apple Silicon macOS on linux."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    with (
        patch.object(sys, "platform", "linux"),
        patch("platform.machine", return_value="x86_64"),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            MLXWhisperBackend()
    assert "Apple Silicon macOS" in str(exc_info.value)


def test_intel_macos_construction_rejected() -> None:
    """Construction MUST raise ``RuntimeError`` mentioning Apple Silicon macOS on Intel macOS."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    with (
        patch.object(sys, "platform", "darwin"),
        patch("platform.machine", return_value="x86_64"),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            MLXWhisperBackend()
    assert "Apple Silicon macOS" in str(exc_info.value)


def test_missing_dependency_raises_actionable_import_error() -> None:
    """Missing ``mlx_whisper`` MUST raise ImportError naming the install extra."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *a, **kw):
        if name == "mlx_whisper":
            raise ModuleNotFoundError("No module named 'mlx_whisper'")
        return real_import_module(name, *a, **kw)

    # Provide fake numpy so import of numpy succeeds before mlx_whisper.
    _install_fake_numpy(buffer_length=32000)

    fake_reader = _fake_reader(num_samples=32000)

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=fake_reader,
    ):
        with patch(
            "talking_parrot.transcription.mlx_whisper_backend.importlib.import_module",
            side_effect=fake_import_module,
        ):
            with pytest.raises(ImportError) as exc_info:
                backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert "talking-parrot[mlx]" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Transcribe tests
# ---------------------------------------------------------------------------


def test_chunk_window_numpy_length_and_path_or_hf_repo_verbatim() -> None:
    """Window length samples == (end_ms-start_ms)*sample_rate/1000; model passed verbatim."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    sample_rate = 16000
    expected_samples = (4000 - 2000) * sample_rate // 1000  # 32000
    _install_fake_numpy(buffer_length=expected_samples)
    _module, fake_transcribe = _install_fake_mlx_whisper(
        transcribe_return={"segments": [], "language": "en"}
    )

    fake_reader = _fake_reader(sample_rate=sample_rate, num_samples=expected_samples)

    backend = MLXWhisperBackend()
    chunk = _make_chunk(start_ms=2000, end_ms=4000)

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=fake_reader,
    ):
        backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    args, kwargs = fake_transcribe.call_args
    audio_array = args[0]
    assert len(audio_array) == expected_samples
    assert kwargs["path_or_hf_repo"] == "large-v3"


def test_returns_one_result_per_segment_with_stripped_text() -> None:
    """Two segments ``" hello"``/``" world "`` MUST yield two results with stripped text."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [
        _segment_dict(0.0, 2.0, " hello"),
        _segment_dict(2.5, 5.0, " world "),
    ]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0].text == "hello"
    assert results[1].text == "world"


def test_language_from_dict_surfaces_on_each_result() -> None:
    """``language="en"`` from returned dict MUST surface on every per-segment result."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [
        _segment_dict(0.0, 1.0, "a"),
        _segment_dict(1.0, 2.0, "b"),
        _segment_dict(2.0, 3.0, "c"),
    ]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert len(results) == 3
    for r in results:
        assert r.language == "en"


def test_language_falls_back_to_argument_when_missing() -> None:
    """Dict missing ``language`` MUST fall back to the supplied ``language`` argument."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [_segment_dict(0.0, 1.0, "hi")]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert len(results) == 1
    # supplied language was None, dict had no language key → result.language is None
    assert results[0].language is None


def test_per_segment_metrics_are_raw_not_aggregated() -> None:
    """Each result MUST carry its own raw avg_logprob/compression_ratio/no_speech_prob."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [
        _segment_dict(
            0.0,
            1.0,
            "a",
            avg_logprob=-0.5,
            compression_ratio=1.2,
            no_speech_prob=0.05,
        ),
        _segment_dict(
            1.0,
            4.0,
            "b",
            avg_logprob=-0.1,
            compression_ratio=1.8,
            no_speech_prob=0.40,
        ),
    ]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert results[0].metrics.avg_logprob == -0.5
    assert results[0].metrics.compression_ratio == 1.2
    assert results[0].metrics.no_speech_prob == 0.05
    assert results[1].metrics.avg_logprob == -0.1
    assert results[1].metrics.compression_ratio == 1.8
    assert results[1].metrics.no_speech_prob == 0.40


def test_segment_derived_timestamps() -> None:
    """``start_ms``/``end_ms`` MUST be ``chunk.start_ms + int(round(seg.start*1000))``."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [_segment_dict(0.0, 2.0, "hello")]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk(index=4, start_ms=10000, end_ms=20000)

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert len(results) == 1
    assert results[0].chunk_index == 4
    assert results[0].start_ms == 10000
    assert results[0].end_ms == 12000
    assert results[0].aligned_tokens is None


def test_empty_segments_list_returns_empty_list() -> None:
    """Dict with ``segments=[]`` MUST yield an empty list (no error)."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": [], "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert results == []


@pytest.mark.parametrize(
    "text,expected_ratio",
    [
        ("hello hello world", 1 / 3),
        ("a b c", 0.0),
        ("", 0.0),
        ("x x x x", 0.75),
    ],
)
def test_repetition_ratio_per_segment(text: str, expected_ratio: float) -> None:
    """``repetition_ratio`` MUST be computed from each segment's stripped text."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [_segment_dict(0.0, 1.0, text)]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert len(results) == 1
    assert abs(results[0].metrics.repetition_ratio - expected_ratio) < 1e-9


def test_model_used_passed_through() -> None:
    """Each result's ``model_used`` MUST equal the ``model`` argument verbatim."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [
        _segment_dict(0.0, 1.0, "a"),
        _segment_dict(1.0, 2.0, "b"),
    ]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=_fake_reader(),
    ):
        results = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert all(r.model_used == "large-v3" for r in results)
