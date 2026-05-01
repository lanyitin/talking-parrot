"""Unit tests for the ``TranscriptionBackend`` abstract interface.

Covers (from ``transcription-backend`` spec):
- Direct instantiation rejected: ``TranscriptionBackend()`` raises ``TypeError``.
- Concrete subclass satisfies interface: a subclass implementing both members
  is instantiable and passes ``isinstance`` check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.transcription.backend import TranscriptionBackend


class _ConcreteBackend(TranscriptionBackend):
    """Minimal concrete subclass used to verify the interface is satisfiable."""

    @property
    def name(self) -> str:
        """Return the backend identifier."""
        return "concrete"

    def transcribe(
        self,
        audio_path: Path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> TranscriptionResult:
        """Return a stub TranscriptionResult."""
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="",
            language=language or "en",
            model_used=model,
            metrics=TranscriptionMetrics(0.0, 0.0, 0.0, 0.0),
            aligned_tokens=None,
        )


def test_direct_instantiation_rejected() -> None:
    """``TranscriptionBackend()`` MUST raise ``TypeError`` because it is abstract."""
    with pytest.raises(TypeError):
        TranscriptionBackend()  # type: ignore[abstract]


def test_concrete_subclass_satisfies_interface() -> None:
    """A subclass implementing both members instantiates and passes isinstance."""
    backend = _ConcreteBackend()
    assert isinstance(backend, TranscriptionBackend)
    assert backend.name == "concrete"
