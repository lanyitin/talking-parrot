"""Tests for :class:`JapaneseAlignmentBackend`.

All ``torch`` / ``transformers`` / ``numpy`` interactions are mocked via
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
# Fakes
# ---------------------------------------------------------------------------


class _Inner2D:
    """2-D matrix with ``[t, j]`` indexing and ``.shape``."""

    def __init__(self, rows: list[list[float]]) -> None:
        """Wrap rows."""
        self._rows = rows
        self.shape = (len(rows), len(rows[0]) if rows else 0)

    def __getitem__(self, key: tuple[int, int]) -> float:
        """Return ``rows[t][j]``."""
        t, j = key
        return self._rows[t][j]


class _Outer3D:
    """Outer 1×T×N tensor stub: ``t[0]`` returns the inner 2-D matrix."""

    def __init__(self, rows: list[list[float]]) -> None:
        """Wrap rows."""
        self._inner = _Inner2D(rows)
        self.shape = (1, *self._inner.shape)

    def __getitem__(self, key: Any) -> Any:
        """Support ``t[0]`` only."""
        if key == 0:
            return self._inner
        raise NotImplementedError


def _install_fake_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Inject fake ``torch``, ``transformers``, ``numpy`` modules into ``sys.modules``."""
    # --- numpy ----
    np_mod = types.ModuleType("numpy")
    np_mod.int16 = "int16"  # type: ignore[attr-defined]
    np_mod.float32 = "float32"  # type: ignore[attr-defined]

    class _FakeArray:
        """Tiny numpy ndarray stand-in."""

        def __init__(self, data: list[float]) -> None:
            """Wrap a Python list."""
            self.data = data
            self.shape = (len(data),)

        def astype(self, _dtype: Any) -> "_FakeArray":
            """No-op cast."""
            return self

        def __truediv__(self, _scalar: float) -> "_FakeArray":
            """No-op normalisation."""
            return self

    def _frombuffer(buf: bytes, dtype: Any) -> _FakeArray:
        """Return a fake int16-shaped array."""
        return _FakeArray([0.0] * (len(buf) // 2))

    def _zeros(n: int, dtype: Any) -> _FakeArray:
        """Zero-filled array."""
        return _FakeArray([0.0] * n)

    def _concatenate(arrays: list[_FakeArray]) -> _FakeArray:
        """Concatenate."""
        out: list[float] = []
        for a in arrays:
            out.extend(a.data)
        return _FakeArray(out)

    np_mod.frombuffer = _frombuffer  # type: ignore[attr-defined]
    np_mod.zeros = _zeros  # type: ignore[attr-defined]
    np_mod.concatenate = _concatenate  # type: ignore[attr-defined]

    # --- torch ----
    torch_mod = types.ModuleType("torch")
    torch_mod.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    torch_mod.log_softmax = lambda t, dim: t  # type: ignore[attr-defined]

    # --- transformers ----
    transformers_mod = types.ModuleType("transformers")

    # Processor mock: callable returns object with .input_values having .to(device)
    proc_input_values = MagicMock(name="input_values")
    proc_input_values.to = MagicMock(return_value=proc_input_values)
    proc_call_out = types.SimpleNamespace(input_values=proc_input_values)

    processor = MagicMock(name="Wav2Vec2Processor")
    processor.return_value = (
        proc_call_out  # processor(audio, sampling_rate=, return_tensors=)
    )
    processor.tokenizer = MagicMock()
    processor.tokenizer.pad_token_id = 0
    processor.tokenizer.get_vocab = MagicMock(
        return_value={"こ": 1, "ん": 2, "に": 3, "ち": 4, "は": 5}
    )

    # Wav2Vec2ForCTC: model(input_values=...) returns object with .logits
    logits = _Outer3D(
        [
            [-5.0, 0.0, -5.0, -5.0, -5.0, -5.0],
            [-5.0, -5.0, 0.0, -5.0, -5.0, -5.0],
            [-5.0, -5.0, -5.0, 0.0, -5.0, -5.0],
            [-5.0, -5.0, -5.0, -5.0, 0.0, -5.0],
            [-5.0, -5.0, -5.0, -5.0, -5.0, 0.0],
        ]
    )
    model_out = types.SimpleNamespace(logits=logits)
    model = MagicMock(name="Wav2Vec2ForCTC", return_value=model_out)
    model.to = MagicMock(return_value=model)

    proc_factory = MagicMock(name="Wav2Vec2Processor.from_pretrained_factory")
    proc_factory.from_pretrained = MagicMock(return_value=processor)
    model_factory = MagicMock(name="Wav2Vec2ForCTC.from_pretrained_factory")
    model_factory.from_pretrained = MagicMock(return_value=model)

    transformers_mod.Wav2Vec2Processor = proc_factory  # type: ignore[attr-defined]
    transformers_mod.Wav2Vec2ForCTC = model_factory  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "numpy", np_mod)
    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "transformers", transformers_mod)

    return {
        "processor": processor,
        "proc_factory": proc_factory,
        "model": model,
        "model_factory": model_factory,
        "logits": logits,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_identity_properties() -> None:
    """``language`` and ``granularity`` MUST equal ``"ja"`` and CHARACTER."""
    from talking_parrot.alignment.japanese_backend import JapaneseAlignmentBackend

    be = JapaneseAlignmentBackend()
    assert be.language == "ja"
    assert be.granularity is AlignmentGranularity.CHARACTER


def test_missing_dependency_raises_actionable_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``transformers`` cannot be imported, ImportError MUST mention the extra."""
    from talking_parrot.alignment.japanese_backend import JapaneseAlignmentBackend

    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "transformers", None)

    be = JapaneseAlignmentBackend()
    with pytest.raises(ImportError, match=r"talking-parrot\[align\]"):
        be.align(b"\x00\x00", 16000, "こんにちは")


def test_prepare_tokens_strips_whitespace_and_yields_codepoints() -> None:
    """``"  こんにちは 世界  "`` MUST tokenise to 7 codepoints."""
    from talking_parrot.alignment.japanese_backend import JapaneseAlignmentBackend

    be = JapaneseAlignmentBackend()
    assert be._prepare_tokens("  こんにちは 世界  ") == [
        "こ",
        "ん",
        "に",
        "ち",
        "は",
        "世",
        "界",
    ]


def test_models_loaded_once_across_three_align_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three ``align()`` calls MUST trigger each ``from_pretrained`` exactly once."""
    refs = _install_fake_modules(monkeypatch)
    from talking_parrot.alignment import japanese_backend as jb_mod

    # Bypass the kernel — focus on the load-once contract.
    monkeypatch.setattr(
        jb_mod,
        "ctc_align",
        lambda *a, **k: [
            AlignedToken(word="こ", start_ms=0, end_ms=20, score=0.9),
        ],
    )

    be = jb_mod.JapaneseAlignmentBackend()
    for _ in range(3):
        be.align(b"\x00\x00" * 1000, 16000, "こ")

    assert refs["proc_factory"].from_pretrained.call_count == 1
    assert refs["model_factory"].from_pretrained.call_count == 1


def test_kernel_invoked_with_blank_id_and_dictionary_from_processor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The backend MUST forward ``pad_token_id`` and ``get_vocab`` to the kernel."""
    refs = _install_fake_modules(monkeypatch)
    from talking_parrot.alignment import japanese_backend as jb_mod

    captured: dict[str, Any] = {}

    def _spy(*args: Any, **kwargs: Any) -> list[AlignedToken]:
        """Capture kernel arguments."""
        captured["args"] = args
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(jb_mod, "ctc_align", _spy)

    be = jb_mod.JapaneseAlignmentBackend()
    be.align(b"\x00\x00" * 1000, 16000, "こんにちは")

    _emissions, dictionary, transcript_tokens, blank_id = captured["args"]
    assert blank_id == 0
    assert captured["kwargs"]["frame_rate_hz"] == 50.0
    assert dictionary == refs["processor"].tokenizer.get_vocab.return_value
    assert transcript_tokens == ["こ", "ん", "に", "ち", "は"]


def test_align_returns_one_token_per_character_when_kernel_returns_five(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the kernel returns 5 tokens for ``"こんにちは"``, the backend forwards them unchanged."""
    _install_fake_modules(monkeypatch)
    from talking_parrot.alignment import japanese_backend as jb_mod

    fake_tokens = [
        AlignedToken(word=ch, start_ms=i * 100, end_ms=(i + 1) * 100, score=0.9)
        for i, ch in enumerate("こんにちは")
    ]
    monkeypatch.setattr(jb_mod, "ctc_align", lambda *a, **k: fake_tokens)

    be = jb_mod.JapaneseAlignmentBackend()
    out = be.align(b"\x00\x00" * 1000, 16000, "こんにちは")
    assert len(out) == 5
    assert [t.word for t in out] == ["こ", "ん", "に", "ち", "は"]
