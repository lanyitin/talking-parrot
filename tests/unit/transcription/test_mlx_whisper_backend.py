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

    fake_reader = MagicMock()
    fake_reader.sample_rate = 16000
    fake_reader.read.return_value = b"\x00" * 64000

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

    fake_reader = MagicMock()
    fake_reader.sample_rate = sample_rate
    fake_reader.read.return_value = b"\x00\x00" * expected_samples  # int16 bytes

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


def test_language_from_dict_surfaces() -> None:
    """``language="en"`` from returned dict MUST surface as ``result.language``."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": [], "language": "en"})
    fake_reader = MagicMock()
    fake_reader.sample_rate = 16000
    fake_reader.read.return_value = b"\x00\x00" * 32000

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=fake_reader,
    ):
        result = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    assert result.language == "en"


def test_metrics_match_faster_whisper_examples() -> None:
    """Weighted-mean avg_logprob -0.2, max no_speech_prob 0.40, empty repetition_ratio 0.0."""
    from talking_parrot.transcription.mlx_whisper_backend import (
        MLXWhisperBackend,
    )

    segs = [
        _segment_dict(0.0, 1.0, "a", avg_logprob=-0.5, no_speech_prob=0.05),
        _segment_dict(1.0, 4.0, "b", avg_logprob=-0.1, no_speech_prob=0.40),
    ]
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": segs, "language": "en"})
    fake_reader = MagicMock()
    fake_reader.sample_rate = 16000
    fake_reader.read.return_value = b"\x00\x00" * 32000

    backend = MLXWhisperBackend()
    chunk = _make_chunk()

    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=fake_reader,
    ):
        result = backend.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)

    # Drop fake numpy before using pytest.approx (which probes numpy).
    sys.modules.pop("numpy", None)

    assert abs(result.metrics.avg_logprob - (-0.2)) < 1e-9
    assert abs(result.metrics.no_speech_prob - 0.40) < 1e-9

    # Empty-text repetition_ratio case (re-fresh fakes)
    sys.modules.pop("mlx_whisper", None)
    _install_fake_numpy(buffer_length=32000)
    _install_fake_mlx_whisper(transcribe_return={"segments": [], "language": "en"})
    fake_reader2 = MagicMock()
    fake_reader2.sample_rate = 16000
    fake_reader2.read.return_value = b"\x00\x00" * 32000
    backend2 = MLXWhisperBackend()
    with patch(
        "talking_parrot.transcription.mlx_whisper_backend.FfmpegAudioReader",
        return_value=fake_reader2,
    ):
        result2 = backend2.transcribe(Path("/tmp/x.wav"), chunk, "large-v3", None)
    assert result2.metrics.repetition_ratio == 0.0
    assert result2.text == ""
