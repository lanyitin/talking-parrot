"""Abstract ``TranscriptionBackend`` interface.

Every concrete transcription backend (``FasterWhisperBackend``,
``MLXWhisperBackend``, ...) MUST implement this interface so that
``TranscriptionStage`` can drive the cascade without knowing which underlying
library is in use.
"""

from __future__ import annotations

import abc
from pathlib import Path

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.transcription import TranscriptionResult


class TranscriptionBackend(abc.ABC):
    """Abstract base class for all transcription backends.

    Concrete subclasses MUST implement:
    - The ``name`` property returning a unique short identifier
      (``"faster-whisper"``, ``"mlx-whisper"``, ...).
    - The ``transcribe`` method which transcribes the audio window
      ``[chunk.start_ms, chunk.end_ms)`` of ``audio_path`` using ``model`` and
      returns a ``list[TranscriptionResult]`` with one element per Whisper
      internal segment, ordered ascending by ``start_ms``.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return the short identifier of this backend."""

    @abc.abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> list[TranscriptionResult]:
        """Transcribe the chunk window and return per-segment results.

        Each Whisper internal segment MUST become exactly one
        ``TranscriptionResult`` in the returned list, with absolute timing
        (``chunk.start_ms + segment.start * 1000`` for ``start_ms``, similarly
        for ``end_ms``). The list MUST be ordered by ascending ``start_ms``.

        Metrics carried on each result MUST be the raw per-segment values
        reported by the underlying Whisper library (``avg_logprob``,
        ``compression_ratio``, ``no_speech_prob``) plus a per-segment
        ``repetition_ratio`` computed over the segment's text. Backends MUST
        NOT aggregate metrics across segments — chunk-level aggregation for
        cascade decisions is the responsibility of ``TranscriptionStage``.

        ``aligned_tokens`` MUST be ``None`` on every returned result;
        word-level alignment is produced later by ``AlignmentStage``.

        The returned list MAY be empty when the underlying model produces no
        segments for the chunk window. Callers MUST treat an empty list as a
        valid (no-op) outcome and MUST NOT raise.

        Args:
            audio_path: Path to the source audio file.
            chunk: The ``Chunk`` whose ``[start_ms, end_ms)`` window will be
                transcribed.
            model: Backend-specific model identifier (e.g. ``"base"``,
                ``"large-v3"``).
            language: Optional BCP-47 / two-letter language code. ``None`` means
                "auto-detect via the underlying library".

        Returns:
            A list of populated ``TranscriptionResult`` instances, one per
            Whisper internal segment, in temporal order. May be empty.
        """
