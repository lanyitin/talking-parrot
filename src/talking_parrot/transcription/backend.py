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
      returns a fully-populated ``TranscriptionResult``.
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
    ) -> TranscriptionResult:
        """Transcribe the chunk window and return a populated ``TranscriptionResult``.

        Args:
            audio_path: Path to the source audio file.
            chunk: The ``Chunk`` whose ``[start_ms, end_ms)`` window will be
                transcribed.
            model: Backend-specific model identifier (e.g. ``"base"``,
                ``"large-v3"``).
            language: Optional BCP-47 / two-letter language code. ``None`` means
                "auto-detect via the underlying library".

        Returns:
            A fully populated ``TranscriptionResult``.
        """
