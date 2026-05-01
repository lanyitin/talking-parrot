"""Tests for :class:`EnglishAlignmentBackend`.

All ``torch`` / ``torchaudio`` / ``numpy`` interactions are mocked via
``sys.modules`` injection so that the heavy ``align`` extra need not be
installed.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest

from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.models.transcription import AlignedToken


# ---------------------------------------------------------------------------
# Fake torch / torchaudio / numpy modules
# ---------------------------------------------------------------------------


class _FakeTensor:
    """Tiny tensor stub: 2-D indexable + ``.shape`` + ``[0]`` slice."""

    def __init__(self, rows: list[list[float]]) -> None:
        """Wrap a list-of-lists."""
        self._rows = rows
        self.shape = (1, len(rows), len(rows[0]) if rows else 0)

    def __getitem__(self, key: Any) -> Any:
        """Support both ``t[0]`` (returns 2-D inner) and ``t[t,j]`` indexing."""
        if isinstance(key, int):
            inner = _Inner2D(self._rows)
            return inner
        if isinstance(key, tuple):
            # Not used at this outer level (Inner2D handles it).
            raise NotImplementedError
        raise TypeError(f"unsupported key {key!r}")


class _Inner2D:
    """2-D tensor used as the kernel input."""

    def __init__(self, rows: list[list[float]]) -> None:
        """Wrap rows."""
        self._rows = rows
        self.shape = (len(rows), len(rows[0]) if rows else 0)

    def __getitem__(self, key: tuple[int, int]) -> float:
        """Support ``mat[t, j]`` indexing."""
        t, j = key
        return self._rows[t][j]


def _install_fake_modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Inject fake ``torch``, ``torchaudio``, ``numpy`` modules into ``sys.modules``.

    Returns a dict of refs the test can use to assert call counts.
    """
    # numpy
    np_mod = types.ModuleType("numpy")
    np_mod.int16 = "int16"  # type: ignore[attr-defined]
    np_mod.float32 = "float32"  # type: ignore[attr-defined]

    class _FakeArray:
        """Minimal numpy array stub supporting astype/shape/concatenate."""

        def __init__(self, data: list[float]) -> None:
            """Wrap a Python list."""
            self.data = data
            self.shape = (len(data),)

        def astype(self, _dtype: Any) -> "_FakeArray":
            """Return self (no real cast)."""
            return self

        def __truediv__(self, _scalar: float) -> "_FakeArray":
            """Return self (normalisation is a no-op for the fake)."""
            return self

    def _frombuffer(buf: bytes, dtype: Any) -> _FakeArray:
        """Return a fake array sized as ``len(buf) // 2`` int16 samples."""
        return _FakeArray([0.0] * (len(buf) // 2))

    def _zeros(n: int, dtype: Any) -> _FakeArray:
        """Return a fake zero-filled array."""
        return _FakeArray([0.0] * n)

    def _concatenate(arrays: list[_FakeArray]) -> _FakeArray:
        """Concatenate fake arrays."""
        out: list[float] = []
        for a in arrays:
            out.extend(a.data)
        return _FakeArray(out)

    np_mod.frombuffer = _frombuffer  # type: ignore[attr-defined]
    np_mod.zeros = _zeros  # type: ignore[attr-defined]
    np_mod.concatenate = _concatenate  # type: ignore[attr-defined]

    # torch
    torch_mod = types.ModuleType("torch")
    torch_mod.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]

    class _PtTensor:
        """Tensor stub with reshape/to/shape; the body is irrelevant for tests."""

        def __init__(self, n: int) -> None:
            """Record the sample count for shape introspection."""
            self.shape = (n,)

        def reshape(self, *_args: int) -> "_PtTensor":
            """Return a 1×N flavour."""
            self.shape = (1, self.shape[-1])
            return self

        def to(self, _device: Any) -> "_PtTensor":
            """No-op device move for the fake."""
            return self

    def _from_numpy(arr: _FakeArray) -> _PtTensor:
        """Return a fake torch tensor sized like ``arr``."""
        return _PtTensor(len(arr.data))

    def _log_softmax(t: Any, dim: int) -> Any:  # noqa: ARG001
        """Identity for the fake."""
        return t

    torch_mod.from_numpy = _from_numpy  # type: ignore[attr-defined]
    torch_mod.log_softmax = _log_softmax  # type: ignore[attr-defined]

    # torchaudio
    torchaudio_mod = types.ModuleType("torchaudio")
    pipelines = types.ModuleType("torchaudio.pipelines")
    bundle = MagicMock(name="WAV2VEC2_ASR_BASE_960H")
    # Dummy emissions: 3 frames, 4 labels (blank=0 ([pad]), |=1, h=2, i=3)
    emissions_3x4 = _FakeTensor(
        [
            [-5.0, -5.0, 0.0, -5.0],  # frame 0: "h"
            [-5.0, -5.0, -5.0, 0.0],  # frame 1: "i"
            [-5.0, 0.0, -5.0, -5.0],  # frame 2: "|"
        ]
    )
    model_mock = MagicMock(return_value=(emissions_3x4, None))
    bundle.get_model.return_value = model_mock
    bundle.get_model.return_value.to = MagicMock(return_value=model_mock)
    # Make .to() return the model itself so our model_mock is preserved.
    model_mock.to = MagicMock(return_value=model_mock)
    bundle.get_model.return_value = MagicMock(side_effect=lambda *a, **k: emissions_3x4)
    # Reset to a callable that returns (emissions, None):
    real_model = MagicMock(return_value=(emissions_3x4, None))
    real_model.to = MagicMock(return_value=real_model)
    bundle.get_model.return_value = real_model
    bundle.get_labels.return_value = ("[pad]", "|", "h", "i")
    pipelines.WAV2VEC2_ASR_BASE_960H = bundle  # type: ignore[attr-defined]
    torchaudio_mod.pipelines = pipelines  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "numpy", np_mod)
    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "torchaudio", torchaudio_mod)
    monkeypatch.setitem(sys.modules, "torchaudio.pipelines", pipelines)

    return {
        "bundle": bundle,
        "real_model": real_model,
        "emissions": emissions_3x4,
        "torch": torch_mod,
        "torchaudio": torchaudio_mod,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_identity_properties() -> None:
    """``language`` and ``granularity`` MUST equal ``"en"`` and WORD."""
    from talking_parrot.alignment.english_backend import EnglishAlignmentBackend

    be = EnglishAlignmentBackend()
    assert be.language == "en"
    assert be.granularity is AlignmentGranularity.WORD


def test_missing_dependency_raises_actionable_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``torchaudio`` cannot be imported, ImportError MUST mention the extra."""
    from talking_parrot.alignment.english_backend import EnglishAlignmentBackend

    # Force ImportError when the backend tries to import torchaudio.
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "torchaudio", None)

    be = EnglishAlignmentBackend()
    with pytest.raises(ImportError, match=r"talking-parrot\[align\]"):
        be.align(b"\x00\x00", 16000, "hi")


def test_prepare_tokens_lowercases_and_replaces_spaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``"Hello World"`` MUST tokenise to the documented character list."""
    from talking_parrot.alignment.english_backend import EnglishAlignmentBackend

    be = EnglishAlignmentBackend()
    assert be._prepare_tokens("Hello World") == [
        "h",
        "e",
        "l",
        "l",
        "o",
        "|",
        "w",
        "o",
        "r",
        "l",
        "d",
    ]


def test_bundle_loaded_once_across_three_align_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three ``align()`` calls MUST trigger ``get_model`` exactly once."""
    refs = _install_fake_modules(monkeypatch)
    # Patch the kernel so we don't depend on the toy emission's actual alignment.
    from talking_parrot.alignment import english_backend as eb_mod

    monkeypatch.setattr(
        eb_mod,
        "ctc_align",
        lambda *a, **k: [
            AlignedToken(word="h", start_ms=0, end_ms=20, score=0.9),
            AlignedToken(word="i", start_ms=20, end_ms=40, score=0.8),
        ],
    )

    be = eb_mod.EnglishAlignmentBackend()
    for _ in range(3):
        be.align(b"\x00\x00" * 1000, 16000, "hi")

    assert refs["bundle"].get_model.call_count == 1
    assert refs["bundle"].get_labels.call_count == 1


def test_align_passes_frame_rate_50_hz_and_dictionary_to_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The backend MUST invoke the kernel with ``frame_rate_hz=50.0``."""
    _install_fake_modules(monkeypatch)
    from talking_parrot.alignment import english_backend as eb_mod

    captured: dict[str, Any] = {}

    def _spy(*args: Any, **kwargs: Any) -> list[AlignedToken]:
        """Capture kernel arguments and return a stub list."""
        captured["args"] = args
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(eb_mod, "ctc_align", _spy)

    be = eb_mod.EnglishAlignmentBackend()
    be.align(b"\x00\x00" * 1000, 16000, "hi")

    assert captured["kwargs"]["frame_rate_hz"] == 50.0
    # Positional kernel args: (emissions[0], dictionary, transcript_tokens, blank_id)
    _emissions, dictionary, transcript_tokens, blank_id = captured["args"]
    assert dictionary["h"] == 2 and dictionary["i"] == 3 and dictionary["|"] == 1
    assert transcript_tokens == ["h", "i"]
    assert blank_id == 0  # [pad] index


def test_group_words_two_word_example_from_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two-word grouping example from the spec MUST yield ``hi`` and ``yo``."""
    from talking_parrot.alignment.english_backend import EnglishAlignmentBackend

    be = EnglishAlignmentBackend()
    char_tokens = [
        AlignedToken(word="h", start_ms=0, end_ms=50, score=0.9),
        AlignedToken(word="i", start_ms=50, end_ms=100, score=0.8),
        AlignedToken(word="|", start_ms=100, end_ms=120, score=0.0),
        AlignedToken(word="y", start_ms=120, end_ms=180, score=0.7),
        AlignedToken(word="o", start_ms=180, end_ms=220, score=0.6),
    ]
    words = be._group_words(char_tokens)
    assert len(words) == 2
    assert words[0].word == "hi"
    assert words[0].start_ms == 0
    assert words[0].end_ms == 100
    assert words[0].score == pytest.approx(0.85)
    assert words[1].word == "yo"
    assert words[1].start_ms == 120
    assert words[1].end_ms == 220
    assert words[1].score == pytest.approx(0.65)


def test_group_words_consecutive_separators_do_not_emit_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two adjacent ``"|"`` tokens MUST NOT produce an empty-word output."""
    from talking_parrot.alignment.english_backend import EnglishAlignmentBackend

    be = EnglishAlignmentBackend()
    chars = [
        AlignedToken(word="a", start_ms=0, end_ms=10, score=0.5),
        AlignedToken(word="|", start_ms=10, end_ms=20, score=0.0),
        AlignedToken(word="|", start_ms=20, end_ms=30, score=0.0),
        AlignedToken(word="b", start_ms=30, end_ms=40, score=0.5),
    ]
    words = be._group_words(chars)
    assert [w.word for w in words] == ["a", "b"]
