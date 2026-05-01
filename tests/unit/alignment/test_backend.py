"""Tests for the :class:`AlignmentBackend` abstract interface."""

from __future__ import annotations

import pytest

from talking_parrot.alignment.backend import AlignmentBackend
from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.models.transcription import AlignedToken


class _FakeBackend(AlignmentBackend):
    """Minimal concrete subclass that satisfies the interface for testing."""

    @property
    def language(self) -> str:
        """Return a fixed language code."""
        return "xx"

    @property
    def granularity(self) -> AlignmentGranularity:
        """Return a fixed granularity."""
        return AlignmentGranularity.WORD

    def align(
        self, audio_data: bytes, sample_rate: int, transcript: str
    ) -> list[AlignedToken]:
        """Return an empty token list."""
        return []


def test_direct_instantiation_raises_type_error() -> None:
    """``AlignmentBackend()`` MUST raise ``TypeError`` because it is abstract."""
    with pytest.raises(TypeError):
        AlignmentBackend()  # type: ignore[abstract]


def test_concrete_subclass_satisfies_interface() -> None:
    """A subclass implementing all abstract members instantiates and is an AlignmentBackend."""
    backend = _FakeBackend()
    assert isinstance(backend, AlignmentBackend)
    assert backend.language == "xx"
    assert backend.granularity is AlignmentGranularity.WORD
    assert backend.align(b"", 16000, "hello") == []
